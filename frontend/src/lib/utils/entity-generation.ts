import type { Node } from '@xyflow/svelte';
import type { DraftedField, GeneratedEntitiesResult } from '$lib/types';
import { generateEntityId } from './slug';

export type EditedEntity = {
    id: string;
    label: string;
    entity_type: string;
    tags?: string[];
};

export type PreviewEntity = GeneratedEntitiesResult['entities'][number] & {
    annotation_type?: string;
    roles?: unknown[];
};

type DraftedFieldLike = { name: string; datatype?: string } & Partial<DraftedField>;

export interface EntityPositioner {
    calculateSmartPosition(
        entityType: 'fact' | 'dimension' | 'unclassified',
        nodes: Node[]
    ): { x: number; y: number };
}

export interface BuildEntityNodesParams {
    editedEntities: EditedEntity[];
    previewEntities: PreviewEntity[];
    initialNodes: Node[];
    /** entityId -> drafted_fields of nodes removed before creation (process mode). */
    previousDraftedFieldsMap: Map<string, DraftedFieldLike[]>;
    /** entityId -> generated fields (entity_model only). */
    fieldsByEntity: Map<string, DraftedFieldLike[]>;
    modelingStyle: string;
    inheritedDomain: string | undefined;
    maxZIndex: number;
    positioner: EntityPositioner;
}

export interface BuildEntityNodesResult {
    nodes: Node[];
    createdEntityIds: string[];
    entityIdByIndex: string[];
}

function escapeRegex(value: string): string {
    return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export function isLegacyGeneratedAlias(candidateId: string, canonicalId: string): boolean {
    const collapsedId = canonicalId.replace(/_+/g, '_');
    if (collapsedId === canonicalId) {
        return false;
    }

    if (candidateId === collapsedId) {
        return true;
    }

    const collapsedAliasPattern = new RegExp(`^${escapeRegex(collapsedId)}_\\d+$`);
    return collapsedAliasPattern.test(candidateId);
}

/** IDs of entity nodes that are stale legacy aliases (collapsed underscores) of the edited entities' canonical IDs. */
export function findLegacyAliasNodeIds(
    editedEntities: Pick<EditedEntity, 'id'>[],
    nodes: Node[]
): string[] {
    const canonicalEntityIds = new Set(
        editedEntities.map((entity) => generateEntityId(entity.id.trim(), [])).filter(Boolean)
    );
    const aliasIds: string[] = [];
    for (const node of nodes) {
        if (node.type !== 'entity') continue;
        if ([...canonicalEntityIds].some((canonicalId) => isLegacyGeneratedAlias(node.id, canonicalId))) {
            aliasIds.push(node.id);
        }
    }
    return aliasIds;
}

/**
 * Entity-creation loop of GenerateEntitiesDialog `handleCreateAll`.
 * Invariant: `currentEntityIds` is recomputed from `nodesToUse` on every iteration so entities
 * added in earlier passes are visible to later ones (no duplicates when two entries resolve to
 * the same entity ID).
 */
export function buildEntityNodes(params: BuildEntityNodesParams): BuildEntityNodesResult {
    const {
        editedEntities,
        previewEntities,
        previousDraftedFieldsMap,
        fieldsByEntity,
        modelingStyle,
        inheritedDomain,
        maxZIndex,
        positioner,
    } = params;
    let nodesToUse = params.initialNodes;
    const createdEntityIds: string[] = [];
    const entityIdByIndex: string[] = [];

    for (let i = 0; i < editedEntities.length; i++) {
        const edited = editedEntities[i];
        const original = previewEntities[i];
        const trimmedId = edited.id.trim();
        const normalizedEditedId = generateEntityId(trimmedId, []);

        const generatedFieldsForMerge: DraftedFieldLike[] =
            modelingStyle === 'entity_model'
                ? (fieldsByEntity.get(normalizedEditedId) ?? [])
                : Array.isArray(original.drafted_fields)
                  ? original.drafted_fields
                  : [];

        // Check against current nodesToUse (updated in-loop) to avoid duplicates
        // when the same generation is run more than once
        const currentEntityIds = new Set(
            nodesToUse.filter((n) => n.type === 'entity').map((n) => n.id)
        );

        if (currentEntityIds.has(normalizedEditedId)) {
            const previewAnnotation = original?.annotation_type || original?.metadata?.annotation_type;
            const previewRoles = original?.roles;
            if (previewAnnotation) {
                nodesToUse = nodesToUse.map((n) => {
                    if (n.id === normalizedEditedId) {
                        return {
                            ...n,
                            data: {
                                ...n.data,
                                annotation_type: n.data?.annotation_type || previewAnnotation,
                            },
                        };
                    }
                    return n;
                });
            }
            if (Array.isArray(previewRoles) && previewRoles.length > 0) {
                nodesToUse = nodesToUse.map((n) => {
                    if (n.id === normalizedEditedId) {
                        return {
                            ...n,
                            data: {
                                ...n.data,
                                roles: previewRoles,
                            },
                        };
                    }
                    return n;
                });
            }
            if (inheritedDomain) {
                nodesToUse = nodesToUse.map((n) => {
                    if (n.id === normalizedEditedId) {
                        const existingDomains = Array.isArray(n.data?.domains)
                            ? (n.data.domains as string[])
                            : n.data?.domain
                                ? [String(n.data.domain)]
                                : [];
                        const nextDomains = Array.from(
                            new Set(
                                existingDomains
                                    .map((domain) => domain.trim())
                                    .filter(Boolean)
                                    .concat(inheritedDomain)
                            )
                        );
                        return {
                            ...n,
                            data: {
                                ...n.data,
                                domains: nextDomains.length > 0 ? nextDomains : undefined,
                                domain: nextDomains.length > 0 ? nextDomains[0] : undefined,
                            },
                        };
                    }
                    return n;
                });
            }
            // Entity already exists - merge drafted_fields (preserve manually added fields)
            // and update description if provided
            if (
                (edited.entity_type === 'fact' || edited.entity_type === 'entity') &&
                (generatedFieldsForMerge.length > 0 || original.description)
            ) {
                nodesToUse = nodesToUse.map((n) => {
                    if (n.id === normalizedEditedId) {
                        const existingDraftedFields: DraftedFieldLike[] = Array.isArray(n.data?.drafted_fields)
                            ? (n.data.drafted_fields as DraftedFieldLike[])
                            : [];
                        // Keep all existing (manually drafted) fields; add generated fields
                        // only if no field with the same name already exists
                        const existingNames = new Set(existingDraftedFields.map((f) => f.name));
                        const mergedFields = [
                            ...existingDraftedFields,
                            ...generatedFieldsForMerge.filter((f) => !existingNames.has(f.name)),
                        ];
                        return {
                            ...n,
                            data: {
                                ...n.data,
                                ...(generatedFieldsForMerge.length > 0 || existingDraftedFields.length > 0
                                    ? { drafted_fields: mergedFields }
                                    : {}),
                                ...(original.description ? { description: original.description } : {}),
                            },
                        };
                    }
                    return n;
                });
            }
            entityIdByIndex.push(normalizedEditedId);
            continue;
        }

        // Generate unique ID while preserving configured prefixes like dim__/fact__
        const id = generateEntityId(trimmedId, [
            ...nodesToUse.map((n) => n.id),
            ...createdEntityIds,
        ]);

        // Calculate position based on entity type
        let position: { x: number; y: number };
        if (modelingStyle === 'dimensional_model' && edited.entity_type) {
            position = positioner.calculateSmartPosition(
                edited.entity_type as 'fact' | 'dimension' | 'unclassified',
                nodesToUse
            );
        } else {
            position = {
                x: 100 + Math.random() * 200,
                y: 100 + Math.random() * 200,
            };
        }

        // Merge drafted_fields: start with any manually drafted fields that were on
        // the previous node with this ID (captured before the removal step), then
        // append generated fields that don't already exist by name.
        const _prevFields: DraftedFieldLike[] = previousDraftedFieldsMap.get(normalizedEditedId) ?? [];
        const _prevNames = new Set(_prevFields.map((f) => f.name));
        const _mergedDraftedFields = [
            ..._prevFields,
            ...generatedFieldsForMerge.filter((f) => !_prevNames.has(f.name)),
        ];

        // Create node (include tags, domain, annotation_type, and drafted_fields from preview data)
        const newNode: Node = {
            id,
            type: 'entity',
            position,
            data: {
                label: edited.label.trim() || edited.id.trim(),
                description: original.description || '',
                entity_type: edited.entity_type,
                annotation_type:
                    original.annotation_type || original.metadata?.annotation_type || undefined,
                tags: original.tags || [],
                drafted_fields: _mergedDraftedFields.length > 0 ? _mergedDraftedFields : undefined,
                roles: original.roles || undefined,
                domain: inheritedDomain || undefined,
                domains: inheritedDomain ? [inheritedDomain] : undefined,
                width: 280,
                panelHeight: 200,
                collapsed: false,
            },
            zIndex: maxZIndex + i + 1,
        };
        // Add new node to the filtered nodes list
        nodesToUse = [...nodesToUse, newNode];
        createdEntityIds.push(id);
        entityIdByIndex.push(id);
    }

    return { nodes: nodesToUse, createdEntityIds, entityIdByIndex };
}
