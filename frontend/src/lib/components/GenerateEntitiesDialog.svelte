<script lang="ts">
    import { generateEntitiesFromEvent, generateEntitiesFromProcess, updateBusinessEvent, updateBusinessEventProcess, saveDataModel, getBusinessEvents } from '$lib/api';
    import type {
        BusinessEvent,
        BusinessEventAnnotations,
        BusinessEventProcess,
        GeneratedEntitiesResult,
    } from '$lib/types';
    import { nodes, edges, modelingStyle, sourceColors, dimensionPrefixes, factPrefixes } from '$lib/stores';
    import { formatModelNameForLabel, generateEntityId, generateSlug, mergeRelationshipIntoEdges, normalizeTags, shouldAutoSyncGeneratedEntityLabel } from '$lib/utils';
    import { DimensionalModelPositioner } from '$lib/services/position-calculator';
    import CustomEntitySelect from './CustomEntitySelect.svelte';
    import type { Node, Edge } from '@xyflow/svelte';
    import Icon from '@iconify/svelte';
    import { untrack } from 'svelte';
    import { get } from 'svelte/store';

    type Props = {
        open: boolean;
        event: BusinessEvent | null;
        process: BusinessEventProcess | null;
        onConfirm: () => void;
        onCancel: () => void;
    };

    let { open, event, process, onConfirm, onCancel }: Props = $props();

    const mode = $derived(event ? 'event' : (process ? 'process' : null));

    let loading = $state(false);
    let error = $state<string | null>(null);
    let previewData = $state<GeneratedEntitiesResult | null>(null);
    let editedEntities = $state<Array<{ id: string; label: string; entity_type: string; tags?: string[] }>>([]);
    type EditedRelationship = { source: string; target: string; label: string; type: string };
    type EditedDraftedField = { name: string; datatype: string; targetEntityId: string };

    let editedRelationships = $state<EditedRelationship[]>([]);
    let editedDraftedFields = $state<EditedDraftedField[]>([]);
    let validationErrors = $state<string[]>([]);
    let creating = $state(false);
    let success = $state(false);
    /** When false, "existing canvas" options are limited to entities referenced by this event/process. */
    let topologyShowAllCanvasEntities = $state(false);
    /** Bumps on each preview load so stale async completions do not leave `loading` stuck. */
    let loadPreviewGeneration = $state(0);

    const positioner = new DimensionalModelPositioner();

    /** IDs referenced by preview, annotations (dimension links), relationships, and derived entities. */
    function collectScopedCanvasEntityIds(
        pd: GeneratedEntitiesResult,
        evt: BusinessEvent | null,
        proc: BusinessEventProcess | null,
        rels: EditedRelationship[]
    ): Set<string> {
        const ids = new Set<string>();
        for (const e of pd.entities) {
            ids.add(e.id);
        }
        const relList = rels.length > 0 ? rels : (pd.relationships || []);
        for (const rel of relList) {
            ids.add(rel.source);
            ids.add(rel.target);
        }
        const scanAnnotations = (ann: BusinessEventAnnotations | undefined) => {
            if (!ann) return;
            const buckets = [
                ann.who,
                ann.what,
                ann.when,
                ann.where,
                ann.how,
                ann.why,
                ann.how_many,
            ];
            for (const bucket of buckets) {
                for (const entry of bucket || []) {
                    if (entry.dimension_id) ids.add(entry.dimension_id);
                }
            }
        };
        scanAnnotations(evt?.annotations);
        scanAnnotations(proc?.annotations_superset);
        for (const d of evt?.derived_entities ?? []) {
            const id = typeof d === 'string' ? d : d.entity_id;
            if (id) ids.add(id);
        }
        for (const d of proc?.derived_entities ?? []) {
            if (d.entity_id) ids.add(d.entity_id);
        }
        return ids;
    }

    const previewEntityIdSet = $derived(new Set((previewData?.entities || []).map((e) => e.id)));

    const scopedCanvasEntityIds = $derived(
        $modelingStyle === 'entity_model' && previewData
            ? collectScopedCanvasEntityIds(previewData, event, process, editedRelationships)
            : new Set<string>()
    );

    const fullExistingCanvasEntityOptions = $derived(
        $modelingStyle === 'entity_model' && previewData
            ? $nodes
                  .filter(
                      (n) =>
                          n.type === 'entity' &&
                          !previewEntityIdSet.has(n.id)
                  )
                  .map((n) => ({
                      id: n.id,
                      label: String((n.data as any)?.label || n.id),
                      isNew: false as const,
                  }))
            : []
    );

    const existingCanvasEntityOptions = $derived(
        topologyShowAllCanvasEntities
            ? fullExistingCanvasEntityOptions
            : fullExistingCanvasEntityOptions.filter((o) => scopedCanvasEntityIds.has(o.id))
    );

    const linkedEntityOptions = $derived.by(() => {
        if ($modelingStyle !== 'entity_model' || !previewData) return [];
        const options = new Map<string, { id: string; label: string, isNew: false }>();
        
        for (const rel of previewData.relationships || []) {
            if (!previewEntityIdSet.has(rel.target)) {
                const onCanvas = fullExistingCanvasEntityOptions.find(o => o.id === rel.target);
                if (!onCanvas) {
                    options.set(rel.target, { id: rel.target, label: rel.label || rel.target, isNew: false });
                }
            }
        }
        return Array.from(options.values());
    });

    /** Preview entities plus relationship endpoints from the API preview (not yet on canvas). Shown under “From this generation”. */
    const generationTopologyOptions = $derived.by(() => {
        if ($modelingStyle !== 'entity_model' || !previewData) return [];
        const byId = new Map<string, { id: string; label: string; isNew: boolean }>();
        const entities = previewData.entities || [];
        for (let i = 0; i < entities.length; i++) {
            const e = entities[i];
            byId.set(e.id, {
                id: e.id,
                label: editedEntities[i]?.label || e.label,
                isNew: true,
            });
        }
        for (const opt of linkedEntityOptions) {
            if (!byId.has(opt.id)) {
                byId.set(opt.id, { id: opt.id, label: opt.label, isNew: false });
            }
        }
        return Array.from(byId.values()).sort((a, b) => a.label.localeCompare(b.label));
    });

    /** On-canvas entities in scope (second group). */
    const combinedExistingOptions = $derived(
        [...existingCanvasEntityOptions].sort((a, b) => a.label.localeCompare(b.label))
    );

    const selectGroups = $derived([
        ...(generationTopologyOptions.length > 0
            ? [{ label: 'From this generation', options: generationTopologyOptions }]
            : []),
        ...(combinedExistingOptions.length > 0
            ? [
                  {
                      label: topologyShowAllCanvasEntities
                          ? 'All available entities'
                          : `Available in this ${mode === 'process' ? 'process' : 'event'}`,
                      options: combinedExistingOptions,
                  },
              ]
            : []),
    ]);

    // Load preview data when dialog opens
    $effect(() => {
        if (open && mode) {
            const ac = new AbortController();
            // Use untrack so reactive reads/writes inside loadPreview (e.g. the
            // loadPreviewGeneration counter and preview state) do not make this
            // effect depend on them and self-retrigger in a loop.
            untrack(() => {
                void loadPreview(ac.signal);
            });
            return () => ac.abort();
        }
        if (!open) {
            // Reset state when dialog closes - use untrack to avoid triggering validation effect
            untrack(() => {
                previewData = null;
                editedEntities = [];
                editedRelationships = [];
                editedDraftedFields = [];
                topologyShowAllCanvasEntities = false;
                validationErrors = [];
                error = null;
                success = false;
                loading = false;
            });
        }
    });

    async function loadPreview(abortSignal?: AbortSignal) {
        if (!mode) return;

        const gen = ++loadPreviewGeneration;
        try {
            loading = true;
            error = null;
            let result: GeneratedEntitiesResult | null = null;
            if (mode === 'event' && event) {
                result = await generateEntitiesFromEvent(event.id, { signal: abortSignal });
            } else if (mode === 'process' && process) {
                result = await generateEntitiesFromProcess(process.id, { signal: abortSignal });
            } else {
                return;
            }
            if (gen !== loadPreviewGeneration) {
                return;
            }
            previewData = result;
            const existingDerivedIds =
                mode === 'event'
                    ? (event?.derived_entities ?? [])
                          .map((derived) =>
                              typeof derived === 'string' ? derived : derived.entity_id
                          )
                          .filter(Boolean)
                    : (process?.derived_entities ?? [])
                          .map((derived) => derived.entity_id)
                          .filter(Boolean);

            // Initialize edited entities with preview data, but prefer any already-saved
            // derived entity names so reopening the dialog preserves prior custom renames.
            // Match by entity ID (not index) to avoid stale derived_entities corrupting types
            // when annotations_superset changes between generation runs.
            const existingDerivedIdSet = new Set(existingDerivedIds);
            // Pre-build the list of derived nodes for fallback matching by entity_type.
            const derivedNodes = $nodes.filter(
                (node) => node.type === 'entity' && existingDerivedIdSet.has(node.id)
            );
            // Track which derived nodes have already been matched to avoid double-assignment.
            const matchedDerivedNodeIds = new Set<string>();
            editedEntities = previewData.entities.map((e) => {
                // Try exact ID match first (entity was not renamed).
                let existingNode =
                    existingDerivedIdSet.has(e.id)
                        ? $nodes.find((node) => node.type === 'entity' && node.id === e.id)
                        : undefined;

                // Fallback: entity was renamed — find a derived node with matching entity_type.
                // This preserves custom renames across dialog re-opens.
                if (!existingNode) {
                    existingNode = derivedNodes.find(
                        (node) =>
                            (node.data as any)?.entity_type === e.entity_type &&
                            !matchedDerivedNodeIds.has(node.id)
                    );
                }

                if (existingNode) {
                    matchedDerivedNodeIds.add(existingNode.id);
                }

                return {
                    id: existingNode?.id || e.id,
                    label: String((existingNode?.data as any)?.label || e.label),
                    entity_type: String(e.entity_type),
                    tags: e.tags || [],
                };
            });

            if (get(modelingStyle) === 'entity_model' && previewData) {
                // Drop auto-generated relationship labels that are just the target
                // entity's id or label (filler like “Employee” on employee→booking).
                const isFillerLabel = (label: string, targetId: string): boolean => {
                    const l = label.trim().toLowerCase();
                    if (!l) return true;
                    if (l === targetId.trim().toLowerCase()) return true;
                    const targetEntity = previewData?.entities.find((e) => e.id === targetId);
                    if (targetEntity?.label && l === targetEntity.label.trim().toLowerCase()) {
                        return true;
                    }
                    return false;
                };
                editedRelationships = (previewData.relationships || []).map((rel) => ({
                    source: rel.source,
                    target: rel.target,
                    label: isFillerLabel(rel.label || '', rel.target) ? '' : (rel.label || ''),
                    type: rel.type || 'many_to_one',
                }));

                editedDraftedFields = previewData.entities.flatMap((e) =>
                    ((e as any).drafted_fields || []).map((f: any) => ({
                        name: f.name,
                        datatype: f.datatype || 'unknown',
                        targetEntityId: e.id,
                    }))
                );
            } else {
                editedRelationships = [];
                editedDraftedFields = [];
            }
        } catch (e) {
            if (abortSignal?.aborted) {
                return;
            }
            if (gen !== loadPreviewGeneration) {
                return;
            }
            error = e instanceof Error ? e.message : 'Failed to generate preview';
            console.error('Error generating preview:', error);
        } finally {
            if (gen === loadPreviewGeneration) {
                loading = false;
            }
        }
    }

    function updateEntityName(index: number, name: string) {
        const currentEntity = editedEntities[index];
        const originalLabel = previewData?.entities[index]?.label || '';
        const entityPrefixes = [...get(dimensionPrefixes), ...get(factPrefixes)];
        const nextLabel = shouldAutoSyncGeneratedEntityLabel(
            currentEntity?.id || '',
            currentEntity?.label || '',
            originalLabel,
            entityPrefixes
        )
            ? formatModelNameForLabel(name.trim(), entityPrefixes)
            : currentEntity?.label;

        editedEntities[index] = {
            ...currentEntity,
            id: name,
            label: nextLabel,
        };
        validateEntities();
    }

    function updateEntityLabel(index: number, label: string) {
        editedEntities[index] = { ...editedEntities[index], label };
        validateEntities();
    }

    function escapeRegex(value: string): string {
        return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    function isLegacyGeneratedAlias(candidateId: string, canonicalId: string): boolean {
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

    function removeDraftedField(index: number) {
        editedDraftedFields.splice(index, 1);
        validateEntities();
    }

    function removeRelationship(index: number) {
        editedRelationships.splice(index, 1);
        validateEntities();
    }

    function validateEntities(): void {
        validationErrors = [];

        if ($modelingStyle === 'entity_model') {
            // It's okay to have 0 entities if we are just routing relationships/attributes to existing entities
            // But we must ensure all relationships and drafted fields have valid targets
            const validIds = new Set([
                ...editedEntities.map((e) => e.id),
                ...existingCanvasEntityOptions.map((e) => e.id),
                ...fullExistingCanvasEntityOptions.map((e) => e.id),
                ...linkedEntityOptions.map((e) => e.id),
            ]);

            for (const rel of editedRelationships) {
                if (rel.source && !validIds.has(rel.source)) {
                    validationErrors.push(`Relationship source is invalid or missing.`);
                    break;
                }
            }
            for (const f of editedDraftedFields) {
                if (f.targetEntityId && !validIds.has(f.targetEntityId)) {
                    validationErrors.push(`Attribute target is invalid or missing.`);
                    break;
                }
            }
            if (editedEntities.length === 0 && editedRelationships.length === 0 && editedDraftedFields.length === 0) {
                validationErrors.push('Nothing to create (no entities, relationships, or attributes).');
            }
        } else {
            const dimensions = editedEntities.filter((e) => e.entity_type === 'dimension');
            const facts = editedEntities.filter((e) => e.entity_type === 'fact');

            if (dimensions.length === 0) {
                validationErrors.push('At least one dimension is required');
            }
            if (facts.length === 0) {
                validationErrors.push('At least one fact is required');
            }
        }

        if ($modelingStyle !== 'entity_model') {
            // Check for empty names
            for (let i = 0; i < editedEntities.length; i++) {
                if (!editedEntities[i].id || !editedEntities[i].id.trim()) {
                    validationErrors.push(`Entity ${i + 1} name cannot be empty`);
                }
            }

            // Check for duplicate names
            const nameCounts = new Map<string, number>();
            for (let i = 0; i < editedEntities.length; i++) {
                const name = editedEntities[i].id.trim();
                if (name) {
                    nameCounts.set(name, (nameCounts.get(name) || 0) + 1);
                }
            }

            for (const [name, count] of nameCounts.entries()) {
                if (count > 1) {
                    validationErrors.push(`Duplicate entity name: "${name}"`);
                }
            }
        }

    }

    async function handleCreateAll() {
        if (!previewData || !mode) return;

        validateEntities();
        if (validationErrors.length > 0) {
            return;
        }

        try {
            creating = true;
            error = null;
            // For process mode: collect event-level entity IDs to skip
            const eventLevelEntityIds = new Set<string>();
            if (mode === 'process' && process) {
                const allEvents = await getBusinessEvents();
                const processEvents = allEvents.filter(e => e.process_id === process.id);
                for (const evt of processEvents) {
                    if (evt.derived_entities) {
                        for (const derived of evt.derived_entities) {
                            const entityId = typeof derived === 'string' ? derived : derived.entity_id;
                            if (entityId) {
                                eventLevelEntityIds.add(entityId);
                            }
                        }
                    }
                }
            }

            // Remove event-level entities from nodes/edges before creating new ones
            let nodesToUse = $nodes;
            let edgesToUse = $edges;
            // Map of entityId → drafted_fields for entities that are about to be removed (process mode).
            // Used below to re-apply manually drafted fields onto freshly created nodes.
            const previousDraftedFieldsMap = new Map<string, any[]>();
            if (mode === 'process' && process) {
                const processDerivedEntityIds = new Set(
                    (process.derived_entities ?? [])
                        .map((derived) => derived.entity_id)
                        .filter(Boolean)
                );
                const canonicalEntityIds = new Set(
                    editedEntities
                        .map((entity) => generateEntityId(entity.id.trim(), []))
                        .filter(Boolean)
                );
                const removableEntityIds = new Set<string>([
                    ...eventLevelEntityIds,
                    ...processDerivedEntityIds,
                ]);

                for (const node of $nodes) {
                    if (node.type !== 'entity') continue;
                    if ([...canonicalEntityIds].some((canonicalId) => isLegacyGeneratedAlias(node.id, canonicalId))) {
                        removableEntityIds.add(node.id);
                    }
                }

                // Capture drafted_fields from entities about to be removed so they can be
                // re-merged onto the freshly created nodes (see creation loop below).
                for (const node of $nodes) {
                    if (node.type !== 'entity') continue;
                    if (removableEntityIds.has(node.id) && Array.isArray((node.data as any)?.drafted_fields)) {
                        previousDraftedFieldsMap.set(node.id, (node.data as any).drafted_fields);
                    }
                }

                nodesToUse = $nodes.filter(n => {
                    if (n.type !== 'entity') return true;
                    return !removableEntityIds.has(n.id);
                });
                edgesToUse = $edges.filter(e => {
                    return !removableEntityIds.has(e.source) && !removableEntityIds.has(e.target);
                });
            }
            // Create entities on canvas (skip ones that already exist)
            const createdEntityIds: string[] = [];
            const entityIdByIndex: string[] = [];
            const maxZIndex = Math.max(
                ...nodesToUse.map((n) => n.zIndex || (n.type === 'group' ? 1 : 10)),
                10
            );

            let fieldsByEntity = new Map<string, any[]>();
            if ($modelingStyle === 'entity_model') {
                const preliminaryIdMap = new Map(
                    previewData.entities.map((e, i) => [
                        e.id,
                        generateEntityId(editedEntities[i].id.trim(), []),
                    ])
                );
                fieldsByEntity = new Map();
                for (const f of editedDraftedFields) {
                    const actualId = preliminaryIdMap.get(f.targetEntityId) ?? f.targetEntityId;
                    if (!fieldsByEntity.has(actualId)) fieldsByEntity.set(actualId, []);
                    fieldsByEntity.get(actualId)!.push({ name: f.name, datatype: f.datatype });
                }
            }

            for (let i = 0; i < editedEntities.length; i++) {
                const edited = editedEntities[i];
                const original = previewData.entities[i];
                const trimmedId = edited.id.trim();
                const inheritedDomain =
                    mode === 'event' ? event?.domain?.trim() : process?.domain?.trim();
                const normalizedEditedId = generateEntityId(trimmedId, []);

                const generatedFieldsForMerge: any[] =
                    $modelingStyle === 'entity_model'
                        ? (fieldsByEntity.get(normalizedEditedId) ?? [])
                        : Array.isArray((original as any).drafted_fields)
                          ? (original as any).drafted_fields
                          : [];

                // Check against current nodesToUse (updated in-loop) to avoid duplicates
                // when the same generation is run more than once
                const currentEntityIds = new Set(
                    nodesToUse.filter((n) => n.type === 'entity').map((n) => n.id)
                );

                if (currentEntityIds.has(normalizedEditedId)) {
                    const previewAnnotation =
                        (original as any)?.annotation_type ||
                        (original as any)?.metadata?.annotation_type;
                    const previewRoles = (original as any)?.roles;
                    if (previewAnnotation) {
                        nodesToUse = nodesToUse.map((n) => {
                            if (n.id === normalizedEditedId) {
                                return {
                                    ...n,
                                    data: {
                                        ...n.data,
                                        annotation_type: (n.data as any)?.annotation_type || previewAnnotation,
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
                                const existingDomains = Array.isArray((n.data as any)?.domains)
                                    ? ((n.data as any)?.domains as string[])
                                    : (n.data as any)?.domain
                                        ? [String((n.data as any)?.domain)]
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
                                const existingDraftedFields: any[] = Array.isArray((n.data as any)?.drafted_fields)
                                    ? (n.data as any).drafted_fields
                                    : [];
                                // Keep all existing (manually drafted) fields; add generated fields
                                // only if no field with the same name already exists
                                const existingNames = new Set(existingDraftedFields.map((f: any) => f.name));
                                const mergedFields = [
                                    ...existingDraftedFields,
                                    ...generatedFieldsForMerge.filter((f: any) => !existingNames.has(f.name)),
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
                if ($modelingStyle === 'dimensional_model' && edited.entity_type) {
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
                const _prevFields: any[] = previousDraftedFieldsMap.get(normalizedEditedId) ?? [];
                const _prevNames = new Set(_prevFields.map((f: any) => f.name));
                const _mergedDraftedFields = [
                    ..._prevFields,
                    ...generatedFieldsForMerge.filter((f: any) => !_prevNames.has(f.name)),
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
                            (original as any).annotation_type ||
                            (original as any)?.metadata?.annotation_type ||
                            undefined,
                        tags: original.tags || [],
                        drafted_fields: _mergedDraftedFields.length > 0 ? _mergedDraftedFields : undefined,
                        roles: (original as any).roles || undefined,
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

            if ($modelingStyle === 'entity_model') {
                // Create stub entities for relationship endpoints that are neither in the
                // preview entities nor already on the canvas. These represent entities
                // referenced by the event/process (e.g. Employee, Account) that must exist
                // so their relationships can be drawn and they appear on the canvas.
                const rels = editedRelationships.length > 0
                    ? editedRelationships
                    : (previewData.relationships || []);
                const existingIdSet = new Set(nodesToUse.filter((n) => n.type === 'entity').map((n) => n.id));
                const previewIdSet = new Set(previewData.entities.map((e) => e.id));
                const endpointIds = new Set<string>();
                for (const rel of rels) {
                    for (const id of [rel.source, rel.target]) {
                        if (!id) continue;
                        if (previewIdSet.has(id)) continue;
                        if (existingIdSet.has(id)) continue;
                        endpointIds.add(id);
                    }
                }
                const inheritedDomain =
                    mode === 'event' ? event?.domain?.trim() : process?.domain?.trim();
                let stubIdx = 0;
                // Prefer the original preview relationship label when naming stub nodes
                // (it carries the nice display form e.g. "Employee"); the *edge* label itself
                // is scrubbed of filler separately at preview-load time.
                const previewRels = previewData.relationships || [];
                for (const endpointId of endpointIds) {
                    const incomingRel = previewRels.find((r) => r.target === endpointId);
                    const outgoingRel = previewRels.find((r) => r.source === endpointId);
                    const stubLabel =
                        incomingRel?.label || outgoingRel?.label || endpointId;
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
                    stubIdx += 1;
                }

                for (const [entityId, fields] of fieldsByEntity) {
                    if (entityIdByIndex.includes(entityId) || createdEntityIds.includes(entityId)) continue;

                    const isOnCanvas = nodesToUse.some(n => n.id === entityId);
                    if (!isOnCanvas) {
                        const rel = previewData.relationships?.find(r => r.target === entityId || r.source === entityId);
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
                        if (n.id !== entityId || n.type !== 'entity') return n;
                        const existing: any[] = Array.isArray((n.data as any)?.drafted_fields)
                            ? (n.data as any).drafted_fields
                            : [];
                        const existingNames = new Set(existing.map((f: any) => f.name));
                        const merged = [
                            ...existing,
                            ...fields.filter((f) => !existingNames.has(f.name)),
                        ];
                        return {
                            ...n,
                            data: {
                                ...n.data,
                                drafted_fields: merged.length > 0 ? merged : undefined,
                            },
                        };
                    });
                }
            }

            // Update nodes store with filtered + new nodes
            $nodes = nodesToUse;

            // Create relationships
            const relsToCreate =
                $modelingStyle === 'entity_model'
                    ? editedRelationships
                    : (previewData.relationships || []);
            if (relsToCreate.length > 0) {
                // Map original entity IDs to created entity IDs
                const idMapping = new Map<string, string>();
                for (let i = 0; i < previewData.entities.length; i++) {
                    const originalId = previewData.entities[i].id;
                    const mappedId = entityIdByIndex[i] || createdEntityIds[i];
                    if (mappedId) {
                        idMapping.set(originalId, mappedId);
                    }
                }
                const allEntityIds = new Set(nodesToUse.filter((n) => n.type === 'entity').map((n) => n.id));

                // Treat any label that just restates the target's id/label as filler
                // (e.g. backend emits "Employee" as the rel label on booking→employee).
                const isEdgeFillerLabel = (rawLabel: string, targetId: string): boolean => {
                    const l = (rawLabel || '').trim().toLowerCase();
                    if (!l) return true;
                    if (l === targetId.trim().toLowerCase()) return true;
                    const targetNode = nodesToUse.find((n) => n.id === targetId);
                    const targetNodeLabel = String((targetNode?.data as any)?.label || '');
                    if (targetNodeLabel && l === targetNodeLabel.trim().toLowerCase()) {
                        return true;
                    }
                    return false;
                };

                let updatedEdges = edgesToUse;
                for (const rel of relsToCreate) {
                    const sourceId = idMapping.get(rel.source) || rel.source;
                    const targetId = idMapping.get(rel.target) || rel.target;

                    // Only create relationship if both entities exist
                    if (
                        allEntityIds.has(sourceId) &&
                        allEntityIds.has(targetId)
                    ) {
                        const cleanLabel = isEdgeFillerLabel(rel.label || '', targetId)
                            ? ''
                            : rel.label || '';
                        const relationship = {
                            source: sourceId,
                            target: targetId,
                            label: cleanLabel,
                            type: (rel.type || 'one_to_many') as 'one_to_many' | 'many_to_one' | 'one_to_one' | 'many_to_many',
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
                            const existing = String((e.data as any)?.label ?? '');
                            if (!isEdgeFillerLabel(existing, endpointForLabel)) return e;
                            return {
                                ...e,
                                data: { ...(e.data || {}), label: cleanLabel },
                            };
                        });
                    }
                }
                $edges = updatedEdges;
            } else {
                $edges = edgesToUse;
            }

            // Update event's or process's derived_entities list
            if (mode === 'event' && event) {
                const uniqueDerivedIds = Array.from(
                    new Set([...entityIdByIndex, ...createdEntityIds].filter(Boolean))
                );
                const derivedEntities = uniqueDerivedIds.map((id) => ({
                    entity_id: id,
                    created_at: new Date().toISOString(),
                }));

                await updateBusinessEvent(event.id, {
                    derived_entities: derivedEntities,
                });
            } else if (mode === 'process' && process) {
                // Set derived_entities for the process
                const uniqueDerivedIds = Array.from(
                    new Set([...entityIdByIndex, ...createdEntityIds].filter(Boolean))
                );
                const derivedEntities = uniqueDerivedIds.map((id) => ({
                    entity_id: id,
                    created_at: new Date().toISOString(),
                }));
                await updateBusinessEventProcess(process.id, {
                    derived_entities: derivedEntities,
                });

                // Clear derived_entities for all events in the process
                const allEvents = await getBusinessEvents();
                const processEvents = allEvents.filter(e => e.process_id === process.id);
                for (const evt of processEvents) {
                    await updateBusinessEvent(evt.id, {
                        derived_entities: [],
                    });
                }
            }

            // Save the data model to persist entities to data_model.yml
            const dataModel = buildDataModelFromState($nodes, $edges);
            await saveDataModel(dataModel);

            success = true;
            // Close dialog after a short delay
            setTimeout(() => {
                onConfirm();
            }, 1500);
        } catch (e) {
            error = e instanceof Error ? e.message : 'Failed to create entities';
            console.error('Error creating entities:', error);
        } finally {
            creating = false;
        }
    }

    /**
     * Build data model from node/edge state
     * (Copied from AutoSaveService to avoid circular dependencies)
     */
    function buildDataModelFromState(currentNodes: Node[], currentEdges: Edge[]) {
        const sourceColorsValue = get(sourceColors);

        return {
            version: 0.1,
            source_colors: Object.keys(sourceColorsValue).length > 0 ? sourceColorsValue : undefined,
            entities: currentNodes
                .filter((n) => n.type === 'entity')
                .map((n) => {
                    const displayTags = normalizeTags(n.data?.tags);
                    const uiTags = normalizeTags((n.data as any)?.ui_tags);
                    const isBound = Boolean(n.data?.dbt_model);

                    const source_system = ((n.data as any)?.source_system) as string[] | undefined;
                    const domain = ((n.data as any)?.domain) as string | undefined;
                    const domains = ((n.data as any)?.domains) as string[] | undefined;
                    const annotation_type = ((n.data as any)?.annotation_type) as string | undefined;
                    const roles = ((n.data as any)?.roles) as string[] | undefined;
                    const isDimensional = $modelingStyle === 'dimensional_model';
                    const entity: any = {
                        id: n.id,
                        label: ((n.data.label as string) || '').trim() || 'Entity',
                        description: n.data.description as string | undefined,
                        dbt_model: n.data.dbt_model as string | undefined,
                        additional_models: n.data?.additional_models as string[] | undefined,
                        drafted_fields: n.data?.drafted_fields as any[] | undefined,
                        position: n.position,
                        width: n.data?.width as number | undefined,
                        panel_height: n.data?.panelHeight as number | undefined,
                        collapsed: (n.data?.collapsed as boolean) ?? false,
                        // Bound entities: `dbt_tags`/`tags` mirror schema.yml and are
                        // reconcile-owned; never hand-written here, only `ui_tags`.
                        // Unbound entities: `tags` remains the single freely-editable field.
                        ...(isBound
                            ? { ui_tags: uiTags.length > 0 ? uiTags : undefined }
                            : { tags: displayTags.length > 0 ? displayTags : undefined }),
                    };
                    // Only include entity_type for dimensional modeling
                    if (isDimensional) {
                        entity.entity_type = ((n.data as any)?.entity_type) || 'unclassified';
                    }

                    if (domain && domain.trim()) {
                        entity.domain = domain.trim();
                    }
                    if (Array.isArray(domains) && domains.length > 0) {
                        entity.domains = domains;
                        if (!entity.domain) {
                            entity.domain = domains[0];
                        }
                    }
                    
                    if (!isBound && source_system && source_system.length > 0) {
                        entity.source_system = source_system;
                    }

                    if (annotation_type) {
                        entity.annotation_type = annotation_type;
                    }
                    if (roles !== undefined) {
                        entity.roles = roles;
                    }
                    
                    return entity;
                }),
            relationships: currentEdges.flatMap((e) => {
                const models = (e.data?.models as any[]) || [];
                if (models.length > 0) {
                    return models.map((m) => ({
                        source: e.source,
                        target: e.target,
                        label: (e.data?.label as string) || '',
                        type:
                            (e.data?.type as
                                | 'one_to_many'
                                | 'many_to_one'
                                | 'one_to_one'
                                | 'many_to_many') || 'one_to_many',
                        source_field: m.source_field as string | undefined,
                        target_field: m.target_field as string | undefined,
                        source_model_name: m.source_model_name as string | undefined,
                        source_model_version: m.source_model_version as number | null | undefined,
                        target_model_name: m.target_model_name as string | undefined,
                        target_model_version: m.target_model_version as number | null | undefined,
                        label_dx: e.data?.label_dx as number | undefined,
                        label_dy: e.data?.label_dy as number | undefined,
                    }));
                } else {
                    return [{
                        source: e.source,
                        target: e.target,
                        label: (e.data?.label as string) || '',
                        type:
                            (e.data?.type as
                                | 'one_to_many'
                                | 'many_to_one'
                                | 'one_to_one'
                                | 'many_to_many') || 'one_to_many',
                        source_field: e.data?.source_field as string | undefined,
                        target_field: e.data?.target_field as string | undefined,
                        label_dx: e.data?.label_dx as number | undefined,
                        label_dy: e.data?.label_dy as number | undefined,
                    }];
                }
            }),
        };
    }

    function getPreviewDisplayId(originalId: string): string {
        if (!previewData || editedEntities.length === 0) {
            return originalId;
        }

        const index = previewData.entities.findIndex((entity) => entity.id === originalId);
        if (index === -1) {
            return originalId;
        }

        const editedId = editedEntities[index]?.id?.trim();
        return editedId || originalId;
    }

    function handleKeydown(event: KeyboardEvent) {
        if (event.key === 'Escape') {
            onCancel();
        }
    }

    function handleBackdropClick(event: MouseEvent) {
        if (event.target === event.currentTarget) {
            onCancel();
        }
    }

    // Validate on entity changes - only when dialog is open to prevent infinite loops
    $effect(() => {
        const hasEntityModelContent =
            $modelingStyle === 'entity_model' &&
            (editedRelationships.length > 0 || editedDraftedFields.length > 0);
        if (
            open &&
            (editedEntities.length > 0 || hasEntityModelContent)
        ) {
            // Use untrack to prevent reading $nodes from triggering this effect
            untrack(() => {
                validateEntities();
            });
        }
    });
</script>

{#if open}
    <!-- Backdrop -->
    <div
        class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center"
        onclick={handleBackdropClick}
        onkeydown={handleKeydown}
        role="dialog"
        tabindex="-1"
        aria-modal="true"
        aria-labelledby="generate-entities-dialog-title"
    >
        <!-- Modal -->
        <div
            class="bg-white rounded-lg shadow-xl p-6 max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto"
            role="document"
            tabindex="-1"
            onclick={(e) => e.stopPropagation()}
        >
            <div class="flex items-center justify-between mb-4">
                <h2
                    id="generate-entities-dialog-title"
                    class="text-xl font-semibold text-gray-900"
                >
                    {#if $modelingStyle === 'entity_model'}
                        {mode === 'process' ? 'Generate Entities and Relationships from Process' : 'Generate Entities and Relationships from Event'}
                    {:else}
                        {mode === 'process' ? 'Generate Entities from Process' : 'Generate Entities from Event'}
                    {/if}
                </h2>
                <button
                    onclick={onCancel}
                    class="p-1 text-gray-400 hover:text-gray-600 rounded transition-colors"
                    title="Close"
                >
                    <Icon icon="lucide:x" class="w-5 h-5" />
                </button>
            </div>

            {#if loading}
                <div class="flex items-center justify-center py-12">
                    <div class="text-center">
                        <div class="w-8 h-8 animate-spin border-4 border-primary-600 border-t-transparent rounded-full mx-auto mb-2"></div>
                        <p class="text-sm text-gray-600">Generating preview...</p>
                    </div>
                </div>
            {:else if error}
                <div class="bg-red-50 border border-red-200 rounded p-4 mb-4">
                    <div class="flex items-center gap-2">
                        <Icon icon="lucide:alert-circle" class="w-5 h-5 text-red-600" />
                        <p class="text-sm text-red-800">{error}</p>
                    </div>
                </div>
                <div class="flex justify-end gap-2">
                    <button
                        onclick={onCancel}
                        class="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 transition-colors"
                    >
                        Close
                    </button>
                </div>
            {:else if success}
                <div class="bg-green-50 border border-green-200 rounded p-4 mb-4">
                    <div class="flex items-center gap-2">
                        <Icon icon="lucide:check-circle" class="w-5 h-5 text-green-600" />
                        <p class="text-sm text-green-800">
                            {$modelingStyle === 'entity_model'
                                ? 'Entities and relationships created successfully!'
                                : 'Entities created successfully!'}
                        </p>
                    </div>
                </div>
            {:else if previewData && (editedEntities.length > 0 || ($modelingStyle === 'entity_model' && (editedRelationships.length > 0 || editedDraftedFields.length > 0)))}
                <div class="space-y-4">
                    <!-- Validation Errors -->
                    {#if validationErrors.length > 0}
                        <div class="bg-red-50 border border-red-200 rounded p-4">
                            <div class="flex items-start gap-2">
                                <Icon icon="lucide:alert-triangle" class="w-5 h-5 text-red-600 mt-0.5" />
                                <div class="flex-1">
                                    <p class="text-sm font-medium text-red-800 mb-1">Validation Errors:</p>
                                    <ul class="text-sm text-red-700 list-disc list-inside">
                                        {#each validationErrors as err}
                                            <li>{err}</li>
                                        {/each}
                                    </ul>
                                </div>
                            </div>
                        </div>
                    {/if}

                    <!-- Domain Tag Note -->
                    {#if (mode === 'event' && event?.domain) || (mode === 'process' && process?.domain)}
                        <div class="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
                            <div class="flex items-start gap-2">
                                <Icon icon="lucide:info" class="w-5 h-5 text-blue-600 mt-0.5 flex-shrink-0" />
                                <p class="text-sm text-blue-800">
                                    <strong>Domain Tag:</strong> All entities will inherit the "<span class="font-mono font-semibold">{mode === 'event' ? event?.domain : process?.domain}</span>" tag from this {mode === 'event' ? 'event' : 'process'}.
                                </p>
                            </div>
                        </div>
                    {/if}

                    {#if $modelingStyle === 'entity_model'}
                        <p class="text-sm text-gray-600">
                            Assign each attribute to an entity and choose the source for each relationship. New entities
                            from this preview and other relationship endpoints from the event appear under “From this
                            generation”; entities already on the canvas (in scope) appear under “Available in this
                            {mode === 'process' ? 'process' : 'event'}”.
                        </p>
                    {:else}
                        <!-- Dimensional: editable entity rows -->
                        <div class="border border-gray-200 rounded-lg overflow-hidden">
                            <table class="w-full">
                                <thead class="bg-gray-50 border-b border-gray-200">
                                    <tr>
                                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                                            Entity Type
                                        </th>
                                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                                            Name
                                        </th>
                                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                                            Label
                                        </th>
                                        <th class="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase">
                                            Tags
                                        </th>
                                    </tr>
                                </thead>
                                <tbody class="bg-white divide-y divide-gray-200">
                                    {#each editedEntities as entity, index}
                                        <tr class="hover:bg-gray-50">
                                            <td class="px-4 py-3">
                                                <span
                                                    class="px-2 py-1 text-xs font-medium rounded {entity.entity_type === 'dimension'
                                                        ? 'bg-green-100 text-green-700'
                                                        : entity.entity_type === 'fact'
                                                          ? 'bg-blue-100 text-blue-700'
                                                          : entity.entity_type === 'entity'
                                                            ? 'bg-purple-100 text-purple-700'
                                                            : 'bg-gray-100 text-gray-800'}"
                                                >
                                                    {entity.entity_type === 'dimension'
                                                        ? 'Dimension'
                                                        : entity.entity_type === 'fact'
                                                          ? 'Fact'
                                                          : entity.entity_type === 'entity'
                                                            ? 'Entity'
                                                            : 'Unclassified'}
                                                </span>
                                            </td>
                                            <td class="px-4 py-3">
                                                <input
                                                    type="text"
                                                    value={entity.id}
                                                    oninput={(e) =>
                                                        updateEntityName(
                                                            index,
                                                            (e.target as HTMLInputElement).value
                                                        )}
                                                    class="w-full px-2 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                                                    placeholder="Entity name"
                                                />
                                            </td>
                                            <td class="px-4 py-3">
                                                <input
                                                    type="text"
                                                    value={entity.label}
                                                    oninput={(e) =>
                                                        updateEntityLabel(
                                                            index,
                                                            (e.target as HTMLInputElement).value
                                                        )}
                                                    class="w-full px-2 py-1 border border-gray-300 rounded text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                                                    placeholder="Display label"
                                                />
                                            </td>
                                            <td class="px-4 py-3">
                                                {#if previewData.entities[index]?.tags && previewData.entities[index].tags!.length > 0}
                                                    <div class="flex flex-wrap gap-1">
                                                        {#each previewData.entities[index].tags! as tag}
                                                            <span
                                                                class="px-2 py-0.5 bg-blue-50 text-blue-700 text-xs rounded border border-blue-200 font-mono"
                                                                title="Inherited tag from event domain"
                                                            >
                                                                {tag}
                                                            </span>
                                                        {/each}
                                                    </div>
                                                {:else}
                                                    <span class="text-xs text-gray-400">—</span>
                                                {/if}
                                            </td>
                                        </tr>
                                    {/each}
                                </tbody>
                            </table>
                        </div>
                    {/if}

                    {#if $modelingStyle === 'entity_model' && fullExistingCanvasEntityOptions.length > 0}
                        <label
                            class="flex cursor-pointer items-start gap-3 rounded-xl border border-gray-200/90 bg-gradient-to-r from-gray-50/90 to-white px-4 py-3 text-sm text-gray-600 shadow-sm"
                        >
                            <input
                                type="checkbox"
                                class="mt-0.5 h-4 w-4 shrink-0 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                                bind:checked={topologyShowAllCanvasEntities}
                            />
                            <span>
                                <span class="font-medium text-gray-800">Show all entities on the canvas</span>
                                <span class="mt-0.5 block text-xs text-gray-500">
                                    Off by default: only entities linked in this {mode === 'process' ? 'process' : 'event'}
                                    (annotations, relationships, derived) appear in the lists below.
                                </span>
                            </span>
                        </label>
                    {/if}

                    <!-- Drafted Fields (entity_model only) -->
                    {#if $modelingStyle === 'entity_model' && editedDraftedFields.length > 0}
                        <div
                            class="rounded-xl border border-amber-200/80 bg-gradient-to-br from-amber-50/95 to-white p-4 shadow-sm"
                        >
                            <div class="mb-3 flex items-start gap-2.5">
                                <Icon icon="lucide:list" class="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
                                <div>
                                    <h3 class="text-sm font-semibold text-amber-900">Attributes (drafted fields)</h3>
                                    <p class="mt-0.5 text-xs text-amber-800/80">
                                        Choose which entity each attribute belongs to.
                                    </p>
                                </div>
                            </div>
                            <div class="space-y-2.5">
                                {#each editedDraftedFields as field, i}
                                    <div
                                        class="flex flex-wrap items-center gap-2 rounded-lg border border-amber-100/90 bg-white/90 px-3 py-2.5 shadow-sm"
                                    >
                                        <span
                                            class="min-w-0 shrink-0 rounded-md border border-amber-200 bg-amber-50/80 px-2 py-1 font-mono text-xs font-medium text-amber-950"
                                        >
                                            {field.name}
                                        </span>
                                        <span class="shrink-0 text-xs font-medium text-gray-400">on</span>
                                        <div class="min-w-[12rem] max-w-full flex-1">
                                            <CustomEntitySelect
                                                value={field.targetEntityId}
                                                groups={selectGroups}
                                                onChange={(val) => {
                                                    editedDraftedFields[i] = {
                                                        ...field,
                                                        targetEntityId: val,
                                                    };
                                                }}
                                            />
                                        </div>
                                        <button
                                            onclick={() => removeDraftedField(i)}
                                            class="ml-auto text-gray-400 hover:text-red-500 transition-colors"
                                            title="Remove attribute"
                                        >
                                            <Icon icon="lucide:x" class="h-4 w-4" />
                                        </button>
                                    </div>
                                {/each}
                            </div>
                        </div>
                    {/if}

                    <!-- Relationships Section -->
                    {#if previewData.relationships && previewData.relationships.length > 0}
                        <div
                            class="rounded-xl border border-gray-200/90 bg-gradient-to-b from-white to-gray-50/90 p-4 shadow-sm"
                        >
                            <h3 class="mb-3 text-sm font-semibold text-gray-800">Relationships</h3>
                            {#if $modelingStyle === 'entity_model'}
                                <div class="space-y-2.5">
                                    {#each editedRelationships as rel, i}
                                        <div
                                            class="flex flex-wrap items-center gap-2 rounded-lg border border-gray-100 bg-white/95 px-3 py-2.5 text-sm shadow-sm"
                                        >
                                            <div class="min-w-[12rem] max-w-full flex-1 sm:max-w-[18rem]">
                                                <CustomEntitySelect
                                                    value={rel.source}
                                                    groups={selectGroups}
                                                    onChange={(val) => {
                                                        editedRelationships[i] = {
                                                            ...rel,
                                                            source: val,
                                                        };
                                                    }}
                                                />
                                            </div>
                                            <span class="text-gray-300">→</span>
                                            <span class="font-mono text-sm text-gray-800">{getPreviewDisplayId(rel.target)}</span>
                                            {#if rel.label}
                                                <span class="text-xs text-gray-500">({rel.label})</span>
                                            {/if}
                                            <button
                                                onclick={() => removeRelationship(i)}
                                                class="ml-auto text-gray-400 hover:text-red-500 transition-colors"
                                                title="Remove relationship"
                                            >
                                                <Icon icon="lucide:x" class="h-4 w-4" />
                                            </button>
                                        </div>
                                    {/each}
                                </div>
                            {:else}
                                <div class="space-y-1">
                                    {#each previewData.relationships as rel}
                                        <p class="text-sm text-gray-600">
                                            <span class="font-mono">{getPreviewDisplayId(rel.source)}</span>
                                            <span class="mx-2">→</span>
                                            <span class="font-mono">{getPreviewDisplayId(rel.target)}</span>
                                            {#if rel.label}<span class="text-gray-500 ml-2">({rel.label})</span>{/if}
                                        </p>
                                    {/each}
                                </div>
                            {/if}
                        </div>
                    {/if}

                    <!-- Actions -->
                    <div class="flex justify-end gap-2 pt-4 border-t border-gray-200">
                        <button
                            onclick={onCancel}
                            class="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 transition-colors"
                            disabled={creating}
                        >
                            Cancel
                        </button>
                        <button
                            onclick={handleCreateAll}
                            class="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center gap-2"
                            disabled={creating || validationErrors.length > 0}
                        >
                            {#if creating}
                                <div class="w-4 h-4 animate-spin border-2 border-white border-t-transparent rounded-full"></div>
                                <span>Creating...</span>
                            {:else}
                                <Icon icon="lucide:sparkles" class="w-4 h-4" />
                                <span>Create All</span>
                            {/if}
                        </button>
                    </div>
                </div>
            {:else}
                <div class="text-center py-8 text-gray-500">
                    {#if previewData?.errors && previewData.errors.length > 0}
                        <p class="font-medium text-red-700 mb-2">
                            No entities could be generated from this {mode === 'process' ? 'process' : 'event'}.
                        </p>
                        <ul class="text-sm text-red-700 list-disc list-inside space-y-1 text-left max-w-2xl mx-auto">
                            {#each previewData.errors as generationError}
                                <li>{generationError}</li>
                            {/each}
                        </ul>
                    {:else}
                        <p>
                            No entities to generate. Please add annotations to the {mode === 'process' ? 'process' : 'event'} first.
                        </p>
                    {/if}
                </div>
                <div class="flex justify-end gap-2 pt-4">
                    <button
                        onclick={onCancel}
                        class="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 transition-colors"
                    >
                        Close
                    </button>
                </div>
            {/if}
        </div>
    </div>
{/if}
