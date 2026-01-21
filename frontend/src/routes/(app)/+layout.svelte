<script lang="ts">
    import '@xyflow/svelte/dist/style.css';
    import '../../app.css';
    import logoHref from '$lib/assets/trellis_squared.svg?url';
    import { page } from '$app/stores';
    import { onMount, setContext, untrack } from 'svelte';
    import { writable } from 'svelte/store';
    import {
    nodes,
    edges,
    dbtModels,
    viewMode,
    configStatus,
    initHistory,
    pushHistory,
    undo,
    redo,
    folderFilter,
    tagFilter,
    groupByFolder,
        modelingStyle,
        labelPrefixes,
        dimensionPrefixes,
        factPrefixes,
        sourceColors,
    } from "$lib/stores";
    import {
        getApiBase,
        getManifest,
        getDataModel,
        saveDataModel,
        getConfigStatus,
        getConfigInfo,
        inferRelationships,
        syncDbtTests,
        getExposures,
    } from "$lib/api";
import {
    getModelFolder,
    normalizeTags,
    aggregateRelationshipsIntoEdges,
    mergeRelationshipIntoEdges,
    formatModelNameForLabel,
    getLabelPrefixesFromConfig,
} from "$lib/utils";
    import { applyDagreLayout } from "$lib/layout";
    import Sidebar from "$lib/components/Sidebar.svelte";
    import ConfigInfoModal from "$lib/components/ConfigInfoModal.svelte";
    import LineageModal from "$lib/components/LineageModal.svelte";
    import IncompleteEntitiesWarningModal from "$lib/components/IncompleteEntitiesWarningModal.svelte";
    import UndescribedAttributesWarningModal from "$lib/components/UndescribedAttributesWarningModal.svelte";
    import SourceEditorModal from "$lib/components/SourceEditorModal.svelte";
    import DeleteConfirmModal from "$lib/components/DeleteConfirmModal.svelte";
    import { type Node, type Edge } from "@xyflow/svelte";
    import type { ConfigInfo, DbtModel, GuidanceConfig } from "$lib/types";
    import Icon from "$lib/components/Icon.svelte";
    import { lineageModal, closeLineageModal, sourceEditorModal, closeSourceEditorModal, deleteConfirmModal, closeDeleteConfirmModal } from "$lib/stores";
    import { AutoSaveService } from "$lib/services/auto-save";
    import { 
        getIncompleteEntities, 
        getEntitiesWithUndescribedAttributes,
        shouldShowValidationModal,
    } from "$lib/services/entity-validation";

    let { children } = $props();

    const API_BASE = getApiBase();
    let loading = $state(true);
    let syncing = $state(false);
    let syncMessage = $state<string | null>(null);
    
    // AutoSave service instance
    let autoSaveService: AutoSaveService | null = null;
    let lastSyncedState = $state("");
    let needsSync = $state(false);
    let saving = $state(false);

    // Update derived values once autoSaveService is initialized
    $effect(() => {
        if (autoSaveService) {
            lastSyncedState = autoSaveService.getLastSavedState();
            needsSync = lastSyncedState !== "" && autoSaveService.hasUnsavedChanges($nodes, $edges);
            saving = autoSaveService.isSavingActive();
        }
    });

    let showConfigInfoModal = $state(false);
    let configInfoLoading = $state(false);
    let configInfoError = $state<string | null>(null);
    let configInfo = $state<ConfigInfo | null>(null);
    let lineageEnabled = $state(false);
    let exposuresEnabled = $state(false);
    let exposuresDefaultLayout = $state<'dashboards-as-rows' | 'entities-as-rows'>('dashboards-as-rows');
    let busMatrixEnabled = $state(false);
    let businessEventsEnabled = $state(false);
    let hasExposuresData = $state(false);
    let guidanceConfig = $state<GuidanceConfig>({
        entity_wizard_enabled: true,
        push_warning_enabled: true,
        min_description_length: 10,
        disabled_guidance: [],
    });
    const guidanceConfigStore = writable(guidanceConfig);
    const lineageEnabledStore = writable(lineageEnabled);
    const exposuresEnabledStore = writable(exposuresEnabled);
    const hasExposuresDataStore = writable(hasExposuresData);
    setContext('guidanceConfig', guidanceConfigStore);
    setContext('lineageEnabled', lineageEnabledStore);
    setContext('exposuresEnabled', exposuresEnabledStore);
    setContext('hasExposuresData', hasExposuresDataStore);

    let warningModalOpen = $state(false);
    let incompleteEntitiesForWarning = $state<Node[]>([]);
    let warningModalResolve: ((value: boolean) => void) | null = null;
    let undescribedAttributesModalOpen = $state(false);
    let entitiesWithUndescribedAttributes = $state<Array<{ entityLabel: string; entityId: string; attributeNames: string[] }>>([]);
    let undescribedAttributesResolve: ((value: boolean) => void) | null = null;

    // Drive viewMode from current route on load
    $effect(() => {
        const currentPath = $page.url.pathname;
        if (currentPath === '/canvas') {
            if ($viewMode !== 'conceptual' && $viewMode !== 'logical') {
                $viewMode = 'conceptual';
            }
        } else if (currentPath === '/exposures') {
            if ($viewMode !== 'exposures') {
                $viewMode = 'exposures';
            }
        } else if (currentPath === '/bus-matrix') {
            if ($viewMode !== 'bus_matrix') {
                $viewMode = 'bus_matrix';
            }
        } else if (currentPath === '/business-events') {
            if ($viewMode !== 'business_events') {
                $viewMode = 'business_events';
            }
        }
    });

    $effect(() => {
        if (!lineageEnabled) {
            closeLineageModal();
        }
        if (!exposuresEnabled || !hasExposuresData) {
            $viewMode = $viewMode === 'exposures' ? 'conceptual' : $viewMode;
        }
    });

    $effect(() => {
        guidanceConfigStore.set(guidanceConfig);
        lineageEnabledStore.set(lineageEnabled);
        exposuresEnabledStore.set(exposuresEnabled);
        hasExposuresDataStore.set(hasExposuresData);
    });

    // Show warning modal for incomplete entities and wait for user decision
    function showIncompleteEntitiesWarning(incompleteEntities: Node[]): Promise<boolean> {
        return new Promise((resolve) => {
            incompleteEntitiesForWarning = incompleteEntities;
            warningModalResolve = resolve;
            warningModalOpen = true;
        });
    }

    function handleWarningConfirm() {
        warningModalOpen = false;
        if (warningModalResolve) {
            warningModalResolve(true);
            warningModalResolve = null;
        }
    }

    function handleWarningCancel() {
        warningModalOpen = false;
        if (warningModalResolve) {
            warningModalResolve(false);
            warningModalResolve = null;
        }
    }

    // Show warning modal for undescribed attributes and wait for user decision
    function showUndescribedAttributesWarning(entities: Array<{ entityLabel: string; entityId: string; attributeNames: string[] }>): Promise<boolean> {
        return new Promise((resolve) => {
            entitiesWithUndescribedAttributes = entities;
            undescribedAttributesResolve = resolve;
            undescribedAttributesModalOpen = true;
        });
    }

    function handleUndescribedAttributesConfirm() {
        undescribedAttributesModalOpen = false;
        if (undescribedAttributesResolve) {
            undescribedAttributesResolve(true);
            undescribedAttributesResolve = null;
        }
    }

    function handleUndescribedAttributesCancel() {
        undescribedAttributesModalOpen = false;
        if (undescribedAttributesResolve) {
            undescribedAttributesResolve(false);
            undescribedAttributesResolve = null;
        }
    }

    async function handleSyncDbt() {
        syncing = true;
        syncMessage = null;
        try {
            // Check for validation issues using EntityValidation service
            const incompleteEntities = getIncompleteEntities($nodes);
            const entitiesWithUndescribed = getEntitiesWithUndescribedAttributes($nodes);

            // Check if validation modal should be shown
            if (guidanceConfig.push_warning_enabled && shouldShowValidationModal($nodes, true, true)) {
                if (incompleteEntities.length > 0) {
                    const proceed = await showIncompleteEntitiesWarning(incompleteEntities);
                    if (!proceed) {
                        syncing = false;
                        return;
                    }
                }
                if (entitiesWithUndescribed.length > 0) {
                    const proceed = await showUndescribedAttributesWarning(entitiesWithUndescribed);
                    if (!proceed) {
                        syncing = false;
                        return;
                    }
                }
            }

            // Proceed with sync
            const result = await syncDbtTests();
            syncMessage = `✓ ${result.message}`;
            // Mark current state as synced
            if (autoSaveService) {
                lastSyncedState = autoSaveService.getLastSavedState();
            }
            setTimeout(() => {
                syncMessage = null;
            }, 3000);
        } catch (e) {
            syncMessage = `✗ ${e instanceof Error ? e.message : "Sync failed"}`;
            setTimeout(() => {
                syncMessage = null;
            }, 5000);
        } finally {
            syncing = false;
        }
    }

    async function handleOpenConfigInfo() {
        showConfigInfoModal = true;
        configInfoLoading = true;
        configInfoError = null;
        try {
            const info = await getConfigInfo();
            if (!info) {
                configInfoError = "Unable to fetch config info";
            } else {
                configInfo = info;
                lineageEnabled = info.lineage_enabled ?? false;
                exposuresEnabled = info.exposures_enabled ?? false;
                exposuresDefaultLayout = info.exposures_default_layout ?? 'dashboards-as-rows';
                $modelingStyle = info.modeling_style ?? 'entity_model';
                $labelPrefixes = getLabelPrefixesFromConfig(info);
                dimensionPrefixes.set(info.dimension_prefix ?? []);
                factPrefixes.set(info.fact_prefix ?? []);
            }
        } catch (e) {
            console.error(e);
            configInfoError = "Unable to fetch config info";
        } finally {
            configInfoLoading = false;
        }
    }

    async function handleInferFromDbt() {
        syncing = true;
        syncMessage = "Inferring...";
        try {
            const inferred = await inferRelationships();
            if (inferred.length > 0) {
                let addedCount = 0;
                let addedNodes = 0;
                let newEdges = [...$edges];
                const existingEntityIds = new Set(
                    $nodes.filter((n) => n.type === "entity").map((n) => n.id),
                );

                function maybeAddEntity(id: string | undefined | null) {
                    if (!id) return;
                    if (existingEntityIds.has(id)) return;

                    const model =
                        $dbtModels.find(
                            (m) => m.unique_id === id || m.name === id,
                        ) ?? null;
                    const folder = model ? getModelFolder(model) : null;

                    const newNode: Node = {
                        id,
                        type: "entity",
                        position: { x: 200 + addedNodes * 60, y: 200 },
                        zIndex: 10,
                        data: {
                            label: formatModelNameForLabel((model?.name ?? id).trim(), $labelPrefixes),
                            description: model?.description ?? "",
                            dbt_model: model?.unique_id ?? null,
                            additional_models: [],
                            drafted_fields: [],
                            width: 280,
                            panelHeight: 200,
                            collapsed: false,
                            folder,
                            tags: normalizeTags(model?.tags),
                        },
                    };

                    $nodes = [...$nodes, newNode];
                    existingEntityIds.add(id);
                    addedNodes += 1;
                }

                inferred.forEach((r: any) => {
                    maybeAddEntity(r.source);
                    maybeAddEntity(r.target);

                    // Merge relationship into edges (will aggregate by entity pair)
                    const beforeCount = newEdges.length;
                    newEdges = mergeRelationshipIntoEdges(newEdges, r);
                    if (newEdges.length > beforeCount) {
                        addedCount++;
                    }
                });

                if (addedCount > 0 || addedNodes > 0) {
                    $edges = newEdges;
                    syncMessage = `✓ Added ${addedCount} relationship${addedCount !== 1 ? 's' : ''}${addedNodes ? `, ${addedNodes} node${addedNodes !== 1 ? 's' : ''}` : ""}`;
                    setTimeout(() => {
                        syncMessage = null;
                    }, 3000);
                } else {
                    syncMessage = "✓ No new relationships found";
                    setTimeout(() => {
                        syncMessage = null;
                    }, 3000);
                }
            } else {
                syncMessage = "No relationships in dbt";
                setTimeout(() => {
                    syncMessage = null;
                }, 3000);
            }
        } catch (e) {
            console.error(e);
            syncMessage = "✗ Failed to infer";
            setTimeout(() => {
                syncMessage = null;
            }, 5000);
        } finally {
            syncing = false;
        }
    }

    async function handleAutoLayout() {
        if (loading) return;

        const entityNodes = $nodes.filter((n) => n.type === "entity");
        if (entityNodes.length === 0) return;

        // If dimensional modeling is enabled, use smart positioning
        if ($modelingStyle === "dimensional_model") {
            await applySmartPositioning(entityNodes);
        } else {
            // Use dagre layout for entity modeling
            const layoutedNodes = await applyDagreLayout($nodes, $edges);
            $nodes = layoutedNodes;
        }
        // fitView prop on Canvas will automatically adjust the view
    }

    async function applySmartPositioning(entityNodes: Node[]) {
        // Calculate canvas center (average of all entity positions, or default)
        const allEntityNodes = $nodes.filter((n) => n.type === "entity");
        let centerX = 500;
        let centerY = 400;

        if (allEntityNodes.length > 0) {
            const xPositions = allEntityNodes.map((n) => n.position.x);
            const yPositions = allEntityNodes.map((n) => n.position.y);
            centerX = (Math.min(...xPositions) + Math.max(...xPositions)) / 2;
            centerY = (Math.min(...yPositions) + Math.max(...yPositions)) / 2;
        }

        // Separate facts and dimensions
        const facts = entityNodes.filter(
            (n) => (n.data as any)?.entity_type === "fact"
        );
        const dimensions = entityNodes.filter(
            (n) => (n.data as any)?.entity_type === "dimension"
        );
        const unclassified = entityNodes.filter(
            (n) => (n.data as any)?.entity_type !== "fact" && (n.data as any)?.entity_type !== "dimension"
        );

        // Position facts in center area
        const updatedFacts = facts.map((fact, i) => {
            const gridSize = Math.ceil(Math.sqrt(facts.length));
            const row = Math.floor(i / gridSize);
            const col = i % gridSize;
            const offset = 200;
            return {
                ...fact,
                position: {
                    x: centerX + (col - gridSize / 2) * offset,
                    y: centerY + (row - gridSize / 2) * offset,
                },
            };
        });

        // Position dimensions in outer ring
        const updatedDimensions = dimensions.map((dim, i) => {
            const radius = 500;
            const angle = (2 * Math.PI * i) / dimensions.length;
            return {
                ...dim,
                position: {
                    x: centerX + Math.cos(angle) * radius,
                    y: centerY + Math.sin(angle) * radius,
                },
            };
        });

        // Position unclassified entities randomly around center
        const updatedUnclassified = unclassified.map((entity) => ({
            ...entity,
            position: {
                x: centerX + (Math.random() - 0.5) * 600,
                y: centerY + (Math.random() - 0.5) * 600,
            },
        }));

        // Update nodes with new positions
        const nodeIdMap = new Map($nodes.map((n) => [n.id, n]));
        const updatedNodes = $nodes.map((n) => {
            const factNode = updatedFacts.find((fn) => fn.id === n.id);
            if (factNode) return factNode;

            const dimensionNode = updatedDimensions.find((dn) => dn.id === n.id);
            if (dimensionNode) return dimensionNode;

            const unclassifiedNode = updatedUnclassified.find((un) => un.id === n.id);
            if (unclassifiedNode) return unclassifiedNode;

            return n;
        });

        $nodes = updatedNodes;
    }

    // Expand/Collapse all entities toggle
    const STORAGE_KEY = "trellis_all_expanded";
    let allExpanded = $state(true);
    let stateApplied = $state(false);

    // Restore state from localStorage on mount
    onMount(() => {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved !== null) {
            allExpanded = saved === "true";
        }
    });

    // Watch for nodes changes and apply persisted state once when nodes are first loaded
    $effect(() => {
        const currentNodes = $nodes;
        const entityNodes = currentNodes.filter((n) => n.type === "entity");
        if (entityNodes.length > 0 && !stateApplied) {
            // Apply the persisted state to all entity nodes
            applyExpandCollapseState(allExpanded);
            stateApplied = true;
        }
    });

    function applyExpandCollapseState(expanded: boolean) {
        const entityNodes = $nodes.filter((n) => n.type === "entity");
        if (entityNodes.length === 0) return;

        $nodes = $nodes.map((node) => {
            if (node.type === "entity") {
                return {
                    ...node,
                    data: { ...node.data, collapsed: !expanded },
                };
            }
            return node;
        });
    }

    function toggleAllEntities() {
        allExpanded = !allExpanded;
        applyExpandCollapseState(allExpanded);
        // Persist to localStorage
        localStorage.setItem(STORAGE_KEY, String(allExpanded));
        // Save immediately using AutoSave service
        autoSaveService?.saveNow($nodes, $edges);
    }
    
    onMount(() => {
        (async () => {
            try {
                console.log(`[${Date.now()}] Page onMount starting...`);
                // Check Config Status
                const status = await getConfigStatus();
                $configStatus = status;

                // Load Config Info (includes guidance config)
                const info = await getConfigInfo();
                if (info?.guidance) {
                    guidanceConfig = info.guidance;
                }
                lineageEnabled = info?.lineage_enabled ?? false;
                exposuresEnabled = info?.exposures_enabled ?? false;
                exposuresDefaultLayout = info?.exposures_default_layout ?? 'dashboards-as-rows';
                busMatrixEnabled = info?.bus_matrix_enabled ?? false;
                businessEventsEnabled = info?.business_events_enabled ?? false;
                $modelingStyle = info?.modeling_style ?? 'entity_model';
                $labelPrefixes = getLabelPrefixesFromConfig(info ?? null);
                dimensionPrefixes.set(info?.dimension_prefix ?? []);
                factPrefixes.set(info?.fact_prefix ?? []);

                // Check if exposures data exists
                if (exposuresEnabled) {
                    try {
                        const exposuresData = await getExposures();
                        hasExposuresData = exposuresData.exposures.length > 0;
                    } catch (e) {
                        console.error("Failed to check exposures data:", e);
                        hasExposuresData = false;
                    }
                }

                // Load Manifest
                const models = await getManifest();
                $dbtModels = models;

                // Load Data Model
                const dataModel = await getDataModel();

                // Load source_colors from canvas_layout.yml
                if (dataModel.source_colors) {
                    $sourceColors = dataModel.source_colors;
                }

                // If no relationships in data model, try to infer from dbt yml files
                let relationships = dataModel.relationships || [];
                if (relationships.length === 0) {
                    console.log(
                        "No relationships found in data model, attempting to infer from dbt yml files...",
                    );
                    const inferred = await inferRelationships();
                    if (inferred.length > 0) {
                        relationships = inferred;
                        console.log(
                            `Inferred ${inferred.length} relationships from dbt yml files`,
                        );
                    }
                }

                // Helper to get folder and tags from dbt model
                function getEntityMetadata(entity: any) {
                    if (!entity.dbt_model) return { folder: null, model: null };

                    const model = models.find(
                        (m: any) => m.unique_id === entity.dbt_model,
                    );
                    if (!model) return { folder: null, model: null };

                    return { folder: getModelFolder(model), model };
                }

                // Map data model to Svelte Flow format with metadata
                const entityNodes = (dataModel.entities || []).map((e: any) => {
                    const metadata = getEntityMetadata(e);
                    const entityTags = normalizeTags(e.tags);
                    const hasDbtBinding = Boolean(e.dbt_model);
                    const modelName = metadata.model ? metadata.model.name : e.id;
                    return {
                        id: e.id,
                        type: "entity",
                        position: e.position || { x: 0, y: 0 },
                        zIndex: 10,
                        data: {
                            label: e.label?.trim() || formatModelNameForLabel(modelName.trim(), $labelPrefixes),
                            description: e.description,
                            dbt_model: e.dbt_model,
                            additional_models: e.additional_models,
                            drafted_fields: e.drafted_fields,
                            width: e.width ?? 280,
                            panelHeight: e.panel_height ?? e.panelHeight ?? 200,
                            collapsed: e.collapsed ?? false,
                            folder: metadata.folder,
                            tags: entityTags,
                            _schemaTags: hasDbtBinding ? [] : entityTags,
                            _manifestTags: hasDbtBinding ? entityTags : [],
                            entity_type: e.entity_type,
                            source_system: e.source_system,
                        },
                        parentId: undefined,
                    };
                });

                // Create group nodes if grouping is enabled
                const groupNodes: Node[] = [];
                if ($groupByFolder) {
                    const folderMap = new Map<string, any[]>();

                    entityNodes.forEach((node: any) => {
                        if (node.data.folder) {
                            if (!folderMap.has(node.data.folder)) {
                                folderMap.set(node.data.folder, []);
                            }
                            folderMap.get(node.data.folder)!.push(node);
                        }
                    });

                    const PADDING = 40;
                    const HEADER_HEIGHT = 60;
                    const GROUP_SPACING = 50;

                    const tempGroups: Array<{
                        x: number;
                        y: number;
                        width: number;
                        height: number;
                        node: any;
                    }> = [];

                    folderMap.forEach((children, folderPath) => {
                        if (children.length === 0) return;

                        const groupId = `group-${folderPath.replace(/\//g, "-")}`;

                        const minX = Math.min(...children.map((n) => n.position.x));
                        const minY = Math.min(...children.map((n) => n.position.y));
                        const maxX = Math.max(...children.map((n) => n.position.x + (n.data.width || 280)));
                        const maxY = Math.max(...children.map((n) => n.position.y + (n.data.panelHeight || 200)));

                        let groupX = minX - PADDING;
                        let groupY = minY - PADDING - HEADER_HEIGHT;
                        const groupWidth = maxX - minX + PADDING * 2;
                        const groupHeight = maxY - minY + PADDING * 2 + HEADER_HEIGHT;

                        for (const existing of tempGroups) {
                            const overlapX = groupX < existing.x + existing.width + GROUP_SPACING && groupX + groupWidth + GROUP_SPACING > existing.x;
                            const overlapY = groupY < existing.y + existing.height + GROUP_SPACING && groupY + groupHeight + GROUP_SPACING > existing.y;

                            if (overlapX && overlapY) {
                                groupX = existing.x + existing.width + GROUP_SPACING;
                                if (groupY < existing.y + existing.height + GROUP_SPACING) {
                                    groupY = existing.y + existing.height + GROUP_SPACING;
                                }
                            }
                        }

                        const groupNode = {
                            id: groupId,
                            type: "group",
                            position: { x: groupX, y: groupY },
                            style: `width: ${groupWidth}px; height: ${groupHeight}px;`,
                            zIndex: 1,
                            data: {
                                label: folderPath.split("/").pop() || folderPath,
                                description: `Folder: ${folderPath}`,
                                width: groupWidth,
                                height: groupHeight,
                                collapsed: false,
                            },
                        };

                        tempGroups.push({ x: groupX, y: groupY, width: groupWidth, height: groupHeight, node: groupNode });
                        groupNodes.push(groupNode);

                        children.forEach((child: any) => {
                            child.parentId = groupId;
                            child.position = { x: child.position.x - groupX, y: child.position.y - groupY };
                            child.extent = "parent";
                        });
                    });
                }

                $nodes = [...groupNodes, ...entityNodes] as Node[];
                $edges = aggregateRelationshipsIntoEdges(relationships);

                const layoutCheckNodes = $nodes.filter((n) => n.type === "entity");
                if (layoutCheckNodes.length > 0) {
                    const allAtDefaultPosition = layoutCheckNodes.every((n) => n.position.x === 0 && n.position.y === 0);
                    
                    if (allAtDefaultPosition) {
                        console.log("No saved positions found, applying auto-layout...");
                        $nodes = await applyDagreLayout($nodes, $edges);
                    }
                }

                if (!autoSaveService) {
                    autoSaveService = new AutoSaveService(400);
                    autoSaveService.clearLastSavedState();
                    autoSaveService.saveNow($nodes, $edges);
                }
                lastSyncedState = autoSaveService.getLastSavedState();
                initHistory();
            } catch (e) {
                console.error("Initialization error:", e);
                alert("Failed to initialize. Check backend connection.");
            } finally {
                loading = false;
            }
        })();

        function handleKeydown(e: KeyboardEvent) {
            if ((e.metaKey || e.ctrlKey) && e.key === "z") {
                e.preventDefault();
                if (e.shiftKey) {
                    redo();
                } else {
                    undo();
                }
            }
            if ((e.metaKey || e.ctrlKey) && e.key === "y") {
                e.preventDefault();
                redo();
            }
        }
        const handleBeforeUnload = () => {
            autoSaveService?.flushSync($nodes, $edges);
        };

        window.addEventListener("keydown", handleKeydown);
        window.addEventListener("beforeunload", handleBeforeUnload);
        return () => {
            window.removeEventListener("keydown", handleKeydown);
            window.removeEventListener("beforeunload", handleBeforeUnload);
        };
    });

    $effect(() => {
        if (loading) return;
        
        if (!autoSaveService) {
            autoSaveService = new AutoSaveService(400, (isSaving) => {});
            return;
        }
        
        const currentNodes = $nodes;
        const currentEdges = $edges;
        
        autoSaveService.save(currentNodes, currentEdges);
        
        pushHistory();
    });

    $effect(() => {
        if (loading) return;

        const activeFolder = $folderFilter;
        const activeTags = $tagFilter;
        const models = $dbtModels;

        const currentNodes = untrack(() => $nodes);
        const currentEdges = untrack(() => $edges);

        const updatedNodes = currentNodes.map((node) => {
            if (node.type === "group") {
                return node;
            }

            const primaryModel = models.find((m) => m.unique_id === node.data.dbt_model);
            const additionalModelIds = (node.data?.additional_models as string[]) || [];
            const additionalModels = additionalModelIds.map((id) => models.find((m) => m.unique_id === id)).filter((m): m is DbtModel => m !== undefined);
            const allBoundModels = primaryModel ? [primaryModel, ...additionalModels] : additionalModels;

            let visible = true;

            if (activeFolder.length > 0) {
                if (allBoundModels.length === 0) {
                    visible = false;
                } else {
                    const matchingFolders = allBoundModels.map((m) => getModelFolder(m)).filter((f): f is string => f !== null);
                    visible = visible && matchingFolders.some((folder) => activeFolder.includes(folder));
                }
            }

            if (activeTags.length > 0) {
                const allModelTags = allBoundModels.flatMap((m) => normalizeTags(m.tags));
                const entityTags = normalizeTags(node.data?.tags);
                const nodeTags = [...new Set([...allModelTags, ...entityTags])];

                visible = visible && nodeTags.length > 0 && activeTags.some((tag) => nodeTags.includes(tag));
            }

            return { ...node, hidden: !visible };
        });

        const nodeVisibility = new Map<string, boolean>();
        updatedNodes.forEach((node) => {
            nodeVisibility.set(node.id, !node.hidden);
        });

        const updatedEdges = currentEdges.map((edge) => {
            const sourceVisible = nodeVisibility.get(edge.source) ?? true;
            const targetVisible = nodeVisibility.get(edge.target) ?? true;

            return { ...edge, hidden: !sourceVisible || !targetVisible };
        });

        $nodes = updatedNodes;
        $edges = updatedEdges;
    });
</script>

<svelte:head>
    <link rel="icon" type="image/svg+xml" href={logoHref} />
</svelte:head>

<div class="flex flex-col h-screen overflow-hidden font-sans text-gray-900 bg-gray-50">
    <!-- Header -->
    <header class="h-16 bg-white border-b border-gray-200 flex items-center px-6 justify-between z-20 shadow-sm shrink-0">
        <!-- Brand -->
        <div class="flex items-center gap-3">
            <img src={logoHref} alt="trellis logo" class="w-8 h-8 rounded-lg shadow-sm" />
            <div class="flex flex-col">
                <h1 class="font-bold text-lg text-gray-900 leading-tight tracking-tight">trellis</h1>
                <span class="text-[10px] text-gray-500 font-medium tracking-wider uppercase">Data Model UI</span>
            </div>

            {#if saving}
                <span class="text-xs text-gray-400 animate-pulse ml-2">Saving...</span>
            {/if}
            {#if loading}
                <span class="text-xs text-primary-500 ml-2">Loading...</span>
            {/if}
        </div>

        <!-- View Switcher -->
        <div class="flex bg-gray-100 rounded-lg p-1 border border-gray-200/60 gap-1">
            <a
                href="/canvas"
                class="flex-1 min-w-32 px-4 py-1.5 text-sm rounded-md transition-all duration-200 font-medium flex items-center justify-center gap-2"
                class:bg-white={$page.url.pathname === '/canvas'}
                class:text-primary-600={$page.url.pathname === '/canvas'}
                class:shadow-sm={$page.url.pathname === '/canvas'}
                class:text-gray-500={$page.url.pathname !== '/canvas'}
                class:hover:text-gray-900={$page.url.pathname !== '/canvas'}
            >
                <Icon icon="lucide:layout-dashboard" class="w-3.5 h-3.5" />
                Canvas
            </a>
            {#if exposuresEnabled && hasExposuresData}
                <a
                    href="/exposures"
                    class="flex-1 min-w-32 px-4 py-1.5 text-sm rounded-md transition-all duration-200 font-medium flex items-center justify-center gap-2"
                    class:bg-white={$page.url.pathname === '/exposures'}
                    class:text-primary-600={$page.url.pathname === '/exposures'}
                    class:shadow-sm={$page.url.pathname === '/exposures'}
                    class:text-gray-500={$page.url.pathname !== '/exposures'}
                    class:hover:text-gray-900={$page.url.pathname !== '/exposures'}
                >
                    <Icon icon="mdi:application-export" class="w-3.5 h-3.5" />
                    Exposures
                </a>
            {/if}
            {#if busMatrixEnabled}
                <a
                    href="/bus-matrix"
                    class="flex-1 min-w-32 px-4 py-1.5 text-sm rounded-md transition-all duration-200 font-medium flex items-center justify-center gap-2"
                    class:bg-white={$page.url.pathname === '/bus-matrix'}
                    class:text-primary-600={$page.url.pathname === '/bus-matrix'}
                    class:shadow-sm={$page.url.pathname === '/bus-matrix'}
                    class:text-gray-500={$page.url.pathname !== '/bus-matrix'}
                    class:hover:text-gray-900={$page.url.pathname !== '/bus-matrix'}
                >
                    <Icon icon="mdi:table-large" class="w-3.5 h-3.5" />
                    Bus Matrix
                </a>
            {/if}
            {#if businessEventsEnabled && $modelingStyle === 'dimensional_model'}
                <a
                    href="/business-events"
                    class="flex-1 min-w-32 px-4 py-1.5 text-sm rounded-md transition-all duration-200 font-medium flex items-center justify-center gap-2"
                    class:bg-white={$page.url.pathname === '/business-events'}
                    class:text-primary-600={$page.url.pathname === '/business-events'}
                    class:shadow-sm={$page.url.pathname === '/business-events'}
                    class:text-gray-500={$page.url.pathname !== '/business-events'}
                    class:hover:text-gray-900={$page.url.pathname !== '/business-events'}
                >
                    <Icon icon="lucide:calendar-check" class="w-3.5 h-3.5" />
                    Business Events
                </a>
            {/if}
        </div>

        <!-- Actions -->
        <div class="flex items-center gap-3">
            {#if syncMessage}
                <div class="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-gray-50 border border-gray-200">
                    {#if syncMessage.startsWith("✓")}
                        <div class="w-2 h-2 rounded-full bg-success-500"></div>
                        <span class="text-xs font-medium text-success-700">{syncMessage.substring(2)}</span>
                    {:else if syncMessage.startsWith("✗")}
                        <div class="w-2 h-2 rounded-full bg-danger-500"></div>
                        <span class="text-xs font-medium text-danger-700">{syncMessage.substring(2)}</span>
                    {:else}
                        <span class="text-xs text-gray-600">{syncMessage}</span>
                    {/if}
                </div>
            {/if}

            <div class="h-6 w-px bg-gray-200 mx-1"></div>

            <button
                onclick={() => {
                    // Directly navigate to config page
                    window.location.href = '/config';
                }}
                class="px-2.5 py-1.5 text-xs rounded-md font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 transition-colors flex items-center gap-1.5 shadow-sm"
                title="Go to configuration page"
            >
                <Icon icon="lucide:settings" class="w-3.5 h-3.5" />
                Config info
            </button>

            <button
                onclick={toggleAllEntities}
                disabled={loading}
                class="px-2.5 py-1.5 text-xs rounded-md font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 transition-colors disabled:opacity-50 flex items-center gap-1.5 shadow-sm"
                title={allExpanded ? "Collapse all entities" : "Expand all entities"}
                aria-label={allExpanded ? "Collapse all entities" : "Expand all entities"}
            >
                {#if allExpanded}
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" class="w-3.5 h-3.5">
                        <path d="m7.4 21.308l-.708-.708L12 15.292l5.308 5.308l-.708.708l-4.6-4.6zm4.6-12.6L6.692 3.4l.708-.708l4.6 4.6l4.6-4.6l.708.708z"/>
                    </svg>
                {:else}
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" class="w-3.5 h-3.5">
                        <path d="M12 21.308L6.692 16l.714-.713L12 19.842l4.594-4.555l.714.713zm-4.588-12.6L6.692 8L12 2.692L17.308 8l-.72.708L12 4.158z"/>
                    </svg>
                {/if}
            </button>

            {#if $modelingStyle === "dimensional_model"}
                <button
                    onclick={handleAutoLayout}
                    disabled={loading}
                    class="px-2.5 py-1.5 text-xs rounded-md font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 transition-colors disabled:opacity-50 flex items-center gap-1.5 shadow-sm"
                    title="Arrange entities by fact/dimension positioning"
                >
                    <Icon icon="lucide:wand-2" class="w-3.5 h-3.5" />
                    Auto Layout
                </button>
            {/if}

            <button
                onclick={handleInferFromDbt}
                disabled={syncing || loading}
                class="px-2.5 py-1.5 text-xs rounded-md font-medium text-white bg-primary-600 border border-transparent hover:bg-primary-50 hover:text-primary-700 transition-colors disabled:opacity-50 flex items-center gap-1.5 shadow-sm"
                title="Import relationship tests from dbt yml files"
            >
                <Icon icon="lucide:download" class="w-3.5 h-3.5" />
                Pull from dbt
            </button>

            <button
                onclick={handleSyncDbt}
                disabled={syncing || loading}
                class="px-2.5 py-1.5 text-xs rounded-md font-medium text-white border border-transparent transition-colors disabled:opacity-50 flex items-center gap-1.5 shadow-sm relative"
                class:bg-primary-600={!needsSync}
                class:hover:bg-primary-700={!needsSync}
                class:bg-amber-600={needsSync}
                class:hover:bg-amber-700={needsSync}
                class:animate-pulse={needsSync}
                title={needsSync 
                    ? "⚠️ Changes in data model need to be pushed to dbt schema files" 
                    : "Sync entity & field-definitions and relationship-tests to dbt schema.yml files"}
            >
                {#if syncing}
                    <Icon icon="lucide:loader-2" class="w-3.5 h-3.5 animate-spin" />
                {:else}
                    <Icon icon="lucide:upload" class="w-3.5 h-3.5" />
                {/if}
                Push to dbt
                {#if needsSync && !syncing}
                    <span class="absolute -top-1 -right-1 flex h-2.5 w-2.5">
                        <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                        <span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-500"></span>
                    </span>
                {/if}
            </button>
        </div>
    </header>

    <main class="flex-1 flex overflow-hidden relative">
        <Sidebar width={280} {loading} />
        {@render children()}
    </main>

    {#if lineageEnabled}
        <LineageModal
            open={$lineageModal.open}
            modelId={$lineageModal.modelId}
            onClose={closeLineageModal}
        />
    {/if}

    <ConfigInfoModal
        open={showConfigInfoModal}
        info={configInfo}
        loading={configInfoLoading}
        error={configInfoError}
        onClose={() => (showConfigInfoModal = false)}
        onRetry={handleOpenConfigInfo}
    />

    <IncompleteEntitiesWarningModal
        open={warningModalOpen}
        incompleteEntities={incompleteEntitiesForWarning}
        onConfirm={handleWarningConfirm}
        onCancel={handleWarningCancel}
    />

    <UndescribedAttributesWarningModal
        open={undescribedAttributesModalOpen}
        entitiesWithAttributes={entitiesWithUndescribedAttributes}
        onConfirm={handleUndescribedAttributesConfirm}
        onCancel={handleUndescribedAttributesCancel}
    />

    <DeleteConfirmModal
        open={$deleteConfirmModal.open}
        entityLabel={$deleteConfirmModal.entityLabel}
        onConfirm={() => {
            // Find and delete the entity from the store
            const nodeToDelete = $nodes.find(n => n.data.label === $deleteConfirmModal.entityLabel);
            if (nodeToDelete) {
                nodes.update((list) => list.filter((n) => n.id !== nodeToDelete.id));
                edges.update((list) => list.filter((e) => e.source !== nodeToDelete.id && e.target !== nodeToDelete.id));
            }
            closeDeleteConfirmModal();
        }}
        onCancel={closeDeleteConfirmModal}
    />

    <SourceEditorModal
        open={$sourceEditorModal.open}
        entityLabel={$sourceEditorModal.entityLabel}
        sources={$sourceEditorModal.sources}
        onConfirm={(newSources) => {
            // Update the entity's source systems in the store
            nodes.update((list) =>
                list.map((node) =>
                    node.id === $sourceEditorModal.entityId
                        ? { ...node, data: { ...node.data, source_system: newSources } }
                        : node
                )
            );
            // Trigger an immediate save to persist changes to disk
            // This ensures that when the next modal opens and calls getSourceSystemSuggestions(),
            // it will read the updated data_model.yml file with the new source systems
            autoSaveService?.saveNow($nodes, $edges);
            closeSourceEditorModal();
        }}
        onCancel={closeSourceEditorModal}
    />
</div>
