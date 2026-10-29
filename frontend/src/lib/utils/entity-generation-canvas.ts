import type { Node, Edge } from '@xyflow/svelte';
import type { BusinessEvent, BusinessEventProcess, DraftedField } from '$lib/types';
import { isEntityNode } from '$lib/types';
import { generateEntityId } from './slug';
import { mergeRelationshipIntoEdges } from './relationship-edges';
import { findLegacyAliasNodeIds, type EditedEntity } from './entity-generation';

export type EditedRelationship = { source: string; target: string; label: string; type: string };
export type EditedDraftedField = {
    name: string;
    datatype: DraftedField['datatype'];
    targetEntityId: string;
};
export type PreviewRelationship = {
    source: string;
    target: string;
    type?: string;
    label?: string;
};

/** Entity IDs already derived at event level for the events of a process. */
export function collectEventLevelEntityIds(processEvents: BusinessEvent[]): Set<string> {
    const ids = new Set<string>();
    for (const evt of processEvents) {
        if (!evt.derived_entities) continue;
        for (const derived of evt.derived_entities) {
            const entityId = typeof derived === 'string' ? derived : derived.entity_id;
            if (entityId) ids.add(entityId);
        }
    }
    return ids;
}

/**
 * Process mode: drop previously derived entities (event-level, process-level and legacy aliases)
 * and their edges from the canvas, remembering their drafted_fields so they can be re-applied.
 */
export function removeProcessDerivedEntities(params: {
    nodes: Node[];
    edges: Edge[];
    process: BusinessEventProcess;
    eventLevelEntityIds: Set<string>;
    editedEntities: Pick<EditedEntity, 'id'>[];
}): { nodes: Node[]; edges: Edge[]; previousDraftedFieldsMap: Map<string, DraftedField[]> } {
    const { nodes, edges, process, eventLevelEntityIds, editedEntities } = params;
    const previousDraftedFieldsMap = new Map<string, DraftedField[]>();
    const processDerivedEntityIds = new Set(
        (process.derived_entities ?? []).map((derived) => derived.entity_id).filter(Boolean)
    );
    const removableEntityIds = new Set<string>([...eventLevelEntityIds, ...processDerivedEntityIds]);

    for (const aliasId of findLegacyAliasNodeIds(editedEntities, nodes)) {
        removableEntityIds.add(aliasId);
    }

    for (const node of nodes) {
        if (!isEntityNode(node)) continue;
        if (removableEntityIds.has(node.id) && Array.isArray(node.data?.drafted_fields)) {
            previousDraftedFieldsMap.set(node.id, node.data.drafted_fields);
        }
    }

    return {
        nodes: nodes.filter((n) => {
            if (n.type !== 'entity') return true;
            return !removableEntityIds.has(n.id);
        }),
        edges: edges.filter(
            (e) => !removableEntityIds.has(e.source) && !removableEntityIds.has(e.target)
        ),
        previousDraftedFieldsMap,
    };
}

/** Group edited drafted fields by the entity ID the (re-slugged) target entity will get. */
export function groupDraftedFieldsByEntity(
    previewEntities: Array<{ id: string }>,
    editedEntities: Array<Pick<EditedEntity, 'id'>>,
    editedDraftedFields: EditedDraftedField[]
): Map<string, DraftedField[]> {
    const preliminaryIdMap = new Map(
        previewEntities.map((e, i) => [e.id, generateEntityId(editedEntities[i].id.trim(), [])])
    );
    const fieldsByEntity = new Map<string, DraftedField[]>();
    for (const f of editedDraftedFields) {
        const actualId = preliminaryIdMap.get(f.targetEntityId) ?? f.targetEntityId;
        if (!fieldsByEntity.has(actualId)) fieldsByEntity.set(actualId, []);
        fieldsByEntity.get(actualId)!.push({ name: f.name, datatype: f.datatype });
    }
    return fieldsByEntity;
}

/**
 * entity_model: add stub nodes for relationship endpoints that are neither preview entities nor
 * already on the canvas, then place or merge drafted fields targeting entities not created in
 * this run. Returns the new node list and the IDs of the stub endpoint nodes.
 */
export function addEntityModelStubs(params: {
    nodes: Node[];
    previewEntities: Array<{ id: string }>;
    previewRelationships: PreviewRelationship[];
    relationships: PreviewRelationship[];
    fieldsByEntity: Map<string, DraftedField[]>;
    entityIdByIndex: string[];
    createdEntityIds: string[];
    inheritedDomain: string | undefined;
    maxZIndex: number;
}): { nodes: Node[]; stubEntityIds: string[] } {
    const {
        previewEntities,
        previewRelationships,
        relationships,
        fieldsByEntity,
        entityIdByIndex,
        inheritedDomain,
        maxZIndex,
    } = params;
    let nodesToUse = params.nodes;
    const createdEntityIds = [...params.createdEntityIds];
    const stubEntityIds: string[] = [];

    const existingIdSet = new Set(nodesToUse.filter((n) => n.type === 'entity').map((n) => n.id));
    const previewIdSet = new Set(previewEntities.map((e) => e.id));
    const endpointIds = new Set<string>();
    for (const rel of relationships) {
        for (const id of [rel.source, rel.target]) {
            if (!id) continue;
            if (previewIdSet.has(id)) continue;
            if (existingIdSet.has(id)) continue;
            endpointIds.add(id);
        }
    }

    let stubIdx = 0;
    // Prefer the original preview relationship label when naming stub nodes
    // (it carries the nice display form e.g. "Employee"); the *edge* label itself
    // is scrubbed of filler separately at preview-load time.
    for (const endpointId of endpointIds) {
        const incomingRel = previewRelationships.find((r) => r.target === endpointId);
        const outgoingRel = previewRelationships.find((r) => r.source === endpointId);
        const stubLabel = incomingRel?.label || outgoingRel?.label || endpointId;
        const newNode: Node = {
            id: endpointId,
            type: 'entity',
            position: {
                x: 200 + ((stubIdx % 5) * 260),
                y: 400 + (Math.floor(stubIdx / 5) * 220),
            },
            data: {
                label: stubLabel,
                entity_type: 'dimension',
                width: 280,
                panelHeight: 200,
                collapsed: false,
                domain: inheritedDomain || undefined,
                domains: inheritedDomain ? [inheritedDomain] : undefined,
            },
            zIndex: maxZIndex + 5 + stubIdx,
        };
        nodesToUse = [...nodesToUse, newNode];
        existingIdSet.add(endpointId);
        createdEntityIds.push(endpointId);
        stubEntityIds.push(endpointId);
        stubIdx += 1;
    }

    for (const [entityId, fields] of fieldsByEntity) {
        if (entityIdByIndex.includes(entityId) || createdEntityIds.includes(entityId)) continue;

        const isOnCanvas = nodesToUse.some((n) => n.id === entityId);
        if (!isOnCanvas) {
            const rel = previewRelationships.find((r) => r.target === entityId || r.source === entityId);
            const stubLabel = rel?.label || entityId;

            const newNode: Node = {
                id: entityId,
                type: 'entity',
                position: { x: 100 + Math.random() * 200, y: 100 + Math.random() * 200 },
                data: {
                    label: stubLabel,
                    entity_type: 'dimension',
                    width: 280,
                    panelHeight: 200,
                    collapsed: false,
                    drafted_fields: fields,
                },
                zIndex: maxZIndex + 10,
            };
            nodesToUse = [...nodesToUse, newNode];
            continue;
        }

        nodesToUse = nodesToUse.map((n) => {
            if (n.id !== entityId || !isEntityNode(n)) return n;
            const existing: DraftedField[] = Array.isArray(n.data?.drafted_fields)
                ? n.data.drafted_fields
                : [];
            const existingNames = new Set(existing.map((f) => f.name));
            const merged = [...existing, ...fields.filter((f) => !existingNames.has(f.name))];
            return {
                ...n,
                data: {
                    ...n.data,
                    drafted_fields: merged.length > 0 ? merged : undefined,
                },
            };
        });
    }

    return { nodes: nodesToUse, stubEntityIds };
}

/** Merge generated relationships into the edge list, cleaning up filler labels. */
export function mergeGeneratedRelationships(params: {
    relationships: PreviewRelationship[];
    previewEntities: Array<{ id: string }>;
    entityIdByIndex: string[];
    createdEntityIds: string[];
    nodes: Node[];
    edges: Edge[];
}): Edge[] {
    const { relationships, previewEntities, entityIdByIndex, createdEntityIds, nodes } = params;
    // Map original entity IDs to created entity IDs
    const idMapping = new Map<string, string>();
    for (let i = 0; i < previewEntities.length; i++) {
        const originalId = previewEntities[i].id;
        const mappedId = entityIdByIndex[i] || createdEntityIds[i];
        if (mappedId) {
            idMapping.set(originalId, mappedId);
        }
    }
    const allEntityIds = new Set(nodes.filter((n) => n.type === 'entity').map((n) => n.id));

    // Treat any label that just restates the target's id/label as filler
    // (e.g. backend emits "Employee" as the rel label on booking→employee).
    const isEdgeFillerLabel = (rawLabel: string, targetId: string): boolean => {
        const l = (rawLabel || '').trim().toLowerCase();
        if (!l) return true;
        if (l === targetId.trim().toLowerCase()) return true;
        const targetNode = nodes.find((n) => n.id === targetId);
        const targetNodeLabel = String(targetNode?.data?.label || '');
        if (targetNodeLabel && l === targetNodeLabel.trim().toLowerCase()) {
            return true;
        }
        return false;
    };

    let updatedEdges = params.edges;
    for (const rel of relationships) {
        const sourceId = idMapping.get(rel.source) || rel.source;
        const targetId = idMapping.get(rel.target) || rel.target;

        // Only create relationship if both entities exist
        if (allEntityIds.has(sourceId) && allEntityIds.has(targetId)) {
            const cleanLabel = isEdgeFillerLabel(rel.label || '', targetId) ? '' : rel.label || '';
            const relationship = {
                source: sourceId,
                target: targetId,
                label: cleanLabel,
                type: (rel.type || 'one_to_many') as
                    | 'one_to_many'
                    | 'many_to_one'
                    | 'one_to_one'
                    | 'many_to_many',
            };
            updatedEdges = mergeRelationshipIntoEdges(updatedEdges, relationship);
            // mergeRelationshipIntoEdges skips updating the label on an existing
            // edge; explicitly overwrite pre-existing filler labels so old runs
            // (e.g. "Employee") get cleaned up on regeneration.
            updatedEdges = updatedEdges.map((e) => {
                const samePair =
                    (e.source === sourceId && e.target === targetId) ||
                    (e.source === targetId && e.target === sourceId);
                if (!samePair) return e;
                const endpointForLabel = e.target;
                const existing = String(e.data?.label ?? '');
                if (!isEdgeFillerLabel(existing, endpointForLabel)) return e;
                return {
                    ...e,
                    data: { ...(e.data || {}), label: cleanLabel },
                };
            });
        }
    }
    return updatedEdges;
}

/** derived_entities payload for an event or process from the entities of this run. */
export function buildDerivedEntities(
    entityIdByIndex: string[],
    createdEntityIds: string[],
    now: Date = new Date()
): Array<{ entity_id: string; created_at: string }> {
    const uniqueDerivedIds = Array.from(
        new Set([...entityIdByIndex, ...createdEntityIds].filter(Boolean))
    );
    return uniqueDerivedIds.map((id) => ({
        entity_id: id,
        created_at: now.toISOString(),
    }));
}
