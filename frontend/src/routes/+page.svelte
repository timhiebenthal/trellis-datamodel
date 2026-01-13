<script lang="ts">
    import { onMount, untrack } from "svelte";
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
    canUndo,
    canRedo,
    folderFilter,
    tagFilter,
    groupByFolder,
        modelingStyle,
        labelPrefixes,
        dimensionPrefixes,
        factPrefixes,
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
    getParallelOffset,
    getModelFolder,
    normalizeTags,
    aggregateRelationshipsIntoEdges,
    mergeRelationshipIntoEdges,
    formatModelNameForLabel,
    getLabelPrefixesFromConfig,
} from "$lib/utils";
    import { applyDagreLayout } from "$lib/layout";
    import Sidebar from "$lib/components/Sidebar.svelte";
    import Canvas from "$lib/components/Canvas.svelte";
    import ExposuresTable from "$lib/components/ExposuresTable.svelte";
    import BusMatrix from "$lib/components/BusMatrix.svelte";
    import ConfigInfoModal from "$lib/components/ConfigInfoModal.svelte";
    import LineageModal from "$lib/components/LineageModal.svelte";
    import IncompleteEntitiesWarningModal from "$lib/components/IncompleteEntitiesWarningModal.svelte";
    import UndescribedAttributesWarningModal from "$lib/components/UndescribedAttributesWarningModal.svelte";
    import { type Node, type Edge } from "@xyflow/svelte";
    import type { ConfigInfo, DbtModel, GuidanceConfig, EntityData, DraftedField } from "$lib/types";
    import Icon from "$lib/components/Icon.svelte";
    import logoHref from "$lib/assets/trellis_squared.svg?url";
    import { lineageModal, closeLineageModal } from "$lib/stores";
    import { AutoSaveService } from "$lib/services/auto-save";
    import { 
        getIncompleteEntities, 
        getEntitiesWithUndescribedAttributes,
        shouldShowValidationModal,
        getValidationSummary
    } from "$lib/services/entity-validation";

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
    let hasExposuresData = $state(false);
    let guidanceConfig = $state<GuidanceConfig>({
        entity_wizard_enabled: true,
        push_warning_enabled: true,
        min_description_length: 10,
        disabled_guidance: [],
    });
    let warningModalOpen = $state(false);
    let incompleteEntitiesForWarning = $state<Node[]>([]);
    let warningModalResolve: ((value: boolean) => void) | null = null;
    let undescribedAttributesModalOpen = $state(false);
    let entitiesWithUndescribedAttributes = $state<Array<{ entityLabel: string; entityId: string; attributeNames: string[] }>>([]);
    let undescribedAttributesResolve: ((value: boolean) => void) | null = null;

    $effect(() => {
        if (!lineageEnabled) {
            closeLineageModal();
        }
        if (!exposuresEnabled || !hasExposuresData) {
            $viewMode = $viewMode === 'exposures' ? 'conceptual' : $viewMode;
        }
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
            // Distribute facts in a grid pattern near center
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
            const angle = (2 * Math.PI * i) / dimensions.length; // Distribute evenly
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
    let sidebarWidth = $state(280);
    let resizingSidebar = $state(false);
    let resizeStartX = 0;
    let resizeStartWidth = 0;
    const MIN_SIDEBAR = 200;
    const MAX_SIDEBAR = 420;

    function onSidebarPointerMove(event: PointerEvent) {
        if (!resizingSidebar) return;
        const delta = event.clientX - resizeStartX;
        sidebarWidth = Math.min(
            MAX_SIDEBAR,
            Math.max(MIN_SIDEBAR, resizeStartWidth + delta),
        );
    }

    function stopSidebarResize() {
        if (!resizingSidebar) return;
        resizingSidebar = false;
        window.removeEventListener("pointermove", onSidebarPointerMove);
        window.removeEventListener("pointerup", stopSidebarResize);
    }

    function startSidebarResize(event: PointerEvent) {
        event.preventDefault();
        resizingSidebar = true;
        resizeStartX = event.clientX;
        resizeStartWidth = sidebarWidth;
        window.addEventListener("pointermove", onSidebarPointerMove);
        window.addEventListener("pointerup", stopSidebarResize, { once: true });
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
                    // Use tags from entity data if present, otherwise empty array
                    const entityTags = normalizeTags(e.tags);
                    const hasDbtBinding = Boolean(e.dbt_model);
                    // Get model name for label formatting (strip prefixes)
                    const modelName = metadata.model ? metadata.model.name : e.id;
                    return {
                        id: e.id,
                        type: "entity",
                        position: e.position || { x: 0, y: 0 },
                        zIndex: 10, // Entities should be above groups (zIndex 1)
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
                            // Treat saved tags as manifest/display tags by default for bound models,
                            // so they don't get written back to schema.yml. Schema tags will be loaded
                            // explicitly via loadSchema().
                            _schemaTags: hasDbtBinding ? [] : entityTags,
                            _manifestTags: hasDbtBinding ? entityTags : [],
                            entity_type: e.entity_type,
                        },
                        parentId: undefined, // Will be set if grouping is enabled
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

                    // Create group nodes for each folder
                    const PADDING = 40;
                    const HEADER_HEIGHT = 60;
                    const GROUP_SPACING = 50; // Minimum spacing between groups

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

                        // Calculate bounding box of children
                        const minX = Math.min(
                            ...children.map((n) => n.position.x),
                        );
                        const minY = Math.min(
                            ...children.map((n) => n.position.y),
                        );
                        const maxX = Math.max(
                            ...children.map(
                                (n) => n.position.x + (n.data.width || 280),
                            ),
                        );
                        const maxY = Math.max(
                            ...children.map(
                                (n) =>
                                    n.position.y + (n.data.panelHeight || 200),
                            ),
                        );

                        let groupX = minX - PADDING;
                        let groupY = minY - PADDING - HEADER_HEIGHT;
                        const groupWidth = maxX - minX + PADDING * 2;
                        const groupHeight =
                            maxY - minY + PADDING * 2 + HEADER_HEIGHT;

                        // Check for overlaps with existing groups and adjust position
                        for (const existing of tempGroups) {
                            const overlapX =
                                groupX <
                                    existing.x +
                                        existing.width +
                                        GROUP_SPACING &&
                                groupX + groupWidth + GROUP_SPACING >
                                    existing.x;
                            const overlapY =
                                groupY <
                                    existing.y +
                                        existing.height +
                                        GROUP_SPACING &&
                                groupY + groupHeight + GROUP_SPACING >
                                    existing.y;

                            if (overlapX && overlapY) {
                                // Move this group to the right of the overlapping group
                                groupX =
                                    existing.x + existing.width + GROUP_SPACING;
                                // If still overlapping vertically, move down
                                if (
                                    groupY <
                                    existing.y + existing.height + GROUP_SPACING
                                ) {
                                    groupY =
                                        existing.y +
                                        existing.height +
                                        GROUP_SPACING;
                                }
                            }
                        }

                        const groupNode = {
                            id: groupId,
                            type: "group",
                            position: { x: groupX, y: groupY },
                            style: `width: ${groupWidth}px; height: ${groupHeight}px;`,
                            zIndex: 1, // Groups should be behind entities
                            data: {
                                label:
                                    folderPath.split("/").pop() || folderPath,
                                description: `Folder: ${folderPath}`,
                                width: groupWidth,
                                height: groupHeight,
                                collapsed: false,
                            },
                        };

                        tempGroups.push({
                            x: groupX,
                            y: groupY,
                            width: groupWidth,
                            height: groupHeight,
                            node: groupNode,
                        });
                        groupNodes.push(groupNode);

                        // Convert children to relative positions and set parent
                        children.forEach((child: any) => {
                            child.parentId = groupId;
                            child.position = {
                                x: child.position.x - groupX,
                                y: child.position.y - groupY,
                            };
                            // Mark as extent parent so it stays within bounds
                            child.extent = "parent";
                        });
                    });
                }

                $nodes = [...groupNodes, ...entityNodes] as Node[];

                // Aggregate relationships by entity pair (deduplicate)
                $edges = aggregateRelationshipsIntoEdges(relationships);

                // Auto-apply layout if all entity nodes are at default position (no saved layout)
                const layoutCheckNodes = $nodes.filter((n) => n.type === "entity");
                if (layoutCheckNodes.length > 0) {
                    const allAtDefaultPosition = layoutCheckNodes.every(
                        (n) => n.position.x === 0 && n.position.y === 0,
                    );
                    
                    if (allAtDefaultPosition) {
                        console.log("No saved positions found, applying auto-layout...");
                        $nodes = await applyDagreLayout($nodes, $edges);
                    }
                }

                // Initialize AutoSave service with loaded state
                if (!autoSaveService) {
                    autoSaveService = new AutoSaveService(400);
                    autoSaveService.clearLastSavedState();
                    autoSaveService.saveNow($nodes, $edges);
                }
                // Initialize as synced since we just loaded from disk
                lastSyncedState = autoSaveService.getLastSavedState();
                initHistory();
            } catch (e) {
                console.error("Initialization error:", e);
                alert("Failed to initialize. Check backend connection.");
            } finally {
                loading = false;
            }
        })();

        // Keyboard shortcut for undo/redo
        function handleKeydown(e: KeyboardEvent) {
            if ((e.metaKey || e.ctrlKey) && e.key === "z") {
                e.preventDefault();
                if (e.shiftKey) {
                    redo();
                } else {
                    undo();
                }
            }
            // Ctrl+Y as alternative redo
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

    // Integrate AutoSave service
    $effect(() => {
        if (loading) return;
        
        // Create AutoSave service on first load
        if (!autoSaveService) {
            autoSaveService = new AutoSaveService(400, (isSaving) => {
                // The `saving` derived state handles this
            });
            return;
        }
        
        // Track node/edge changes so autosave and history run whenever they update
        const currentNodes = $nodes;
        const currentEdges = $edges;
        
        // Save changes via AutoSave service
        autoSaveService.save(currentNodes, currentEdges);
        
        // Push to undo history (only when actual changes occur)
        pushHistory();
    });

    // Apply filters to node visibility
    $effect(() => {
        if (loading) return;

        const activeFolder = $folderFilter;
        const activeTags = $tagFilter;
        const models = $dbtModels; // Dependency on dbtModels

        // Use untrack to read current nodes and edges without creating dependency
        const currentNodes = untrack(() => $nodes);
        const currentEdges = untrack(() => $edges);

        // Build updated nodes array
        const updatedNodes = currentNodes.map((node) => {
            // Skip group nodes
            if (node.type === "group") {
                return node;
            }

            // Find all associated models (primary + additional)
            const primaryModel = models.find(
                (m) => m.unique_id === node.data.dbt_model,
            );
            const additionalModelIds = (node.data?.additional_models as string[]) || [];
            const additionalModels = additionalModelIds
                .map((id) => models.find((m) => m.unique_id === id))
                .filter((m): m is DbtModel => m !== undefined);
            const allBoundModels = primaryModel
                ? [primaryModel, ...additionalModels]
                : additionalModels;

            // Check if node matches filters
            let visible = true;

            if (activeFolder.length > 0) {
                if (allBoundModels.length === 0) {
                    visible = false;
                } else {
                    // Entity is visible if ANY bound model matches the folder filter
                    const matchingFolders = allBoundModels
                        .map((m) => getModelFolder(m))
                        .filter((f): f is string => f !== null);
                    visible =
                        visible &&
                        matchingFolders.some((folder) =>
                            activeFolder.includes(folder),
                        );
                }
            }

            if (activeTags.length > 0) {
                // Combine tags from all bound models (manifest) and entity data (user-added)
                const allModelTags = allBoundModels.flatMap((m) =>
                    normalizeTags(m.tags),
                );
                const entityTags = normalizeTags(node.data?.tags);
                const nodeTags = [...new Set([...allModelTags, ...entityTags])];

                visible =
                    visible &&
                    nodeTags.length > 0 &&
                    activeTags.some((tag) => nodeTags.includes(tag));
            }

            // Return updated node with hidden property
            return {
                ...node,
                hidden: !visible,
            };
        });

        // Create a map of node visibility for quick lookup
        const nodeVisibility = new Map<string, boolean>();
        updatedNodes.forEach((node) => {
            nodeVisibility.set(node.id, !node.hidden);
        });

        // Hide edges where either source or target node is hidden
        const updatedEdges = currentEdges.map((edge) => {
            const sourceVisible = nodeVisibility.get(edge.source) ?? true;
            const targetVisible = nodeVisibility.get(edge.target) ?? true;

            return {
                ...edge,
                hidden: !sourceVisible || !targetVisible,
            };
        });

        // Update the stores
        $nodes = updatedNodes;
        $edges = updatedEdges;
    });
</script>

<div
    class="flex flex-col h-screen overflow-hidden font-sans text-gray-900 bg-gray-50"
>
    <!-- Header -->
    <header
        class="h-16 bg-white border-b border-gray-200 flex items-center px-6 justify-between z-20 shadow-sm shrink-0"
    >
        <!-- Brand -->
        <div class="flex items-center gap-3">
            <img
                src={logoHref}
                alt="trellis logo"
                class="w-8 h-8 rounded-lg shadow-sm"
            />
            <div class="flex flex-col">
                <h1
                    class="font-bold text-lg text-gray-900 leading-tight tracking-tight"
                >
                    trellis
                </h1>
                <span
                    class="text-[10px] text-gray-500 font-medium tracking-wider uppercase"
                    >Data Model UI</span
                >
            </div>

            {#if saving}
                <span class="text-xs text-gray-400 animate-pulse ml-2"
                    >Saving...</span
                >
            {/if}
            {#if loading}
                <span class="text-xs text-primary-500 ml-2">Loading...</span>
            {/if}
        </div>

        <!-- View Switcher -->
        <div
            class="flex bg-gray-100 rounded-lg p-1 border border-gray-200/60"
        >
            <button
                class="px-4 py-1.5 text-sm rounded-md transition-all duration-200 font-medium flex items-center gap-2"
                class:bg-white={$viewMode === "conceptual" || $viewMode === "logical"}
                class:text-primary-600={$viewMode === "conceptual" || $viewMode === "logical"}
                class:shadow-sm={$viewMode === "conceptual" || $viewMode === "logical"}
                class:text-gray-500={$viewMode === "exposures" || $viewMode === "bus_matrix"}
                class:hover:text-gray-900={$viewMode === "exposures" || $viewMode === "bus_matrix"}
                onclick={() => ($viewMode = "conceptual")}
                title="Canvas View"
            >
                <Icon icon="lucide:layout-dashboard" class="w-3.5 h-3.5" />
                Canvas
            </button>
            {#if exposuresEnabled && hasExposuresData}
                <button
                    class="px-4 py-1.5 text-sm rounded-md transition-all duration-200 font-medium flex items-center gap-2"
                    class:bg-white={$viewMode === "exposures"}
                    class:text-primary-600={$viewMode === "exposures"}
                    class:shadow-sm={$viewMode === "exposures"}
                    class:text-gray-500={$viewMode !== "exposures"}
                    class:hover:text-gray-900={$viewMode !== "exposures"}
                    onclick={() => ($viewMode = "exposures")}
                    title="Exposures View"
                >
                    <Icon icon="mdi:application-export" class="w-3.5 h-3.5" />
                    Exposures
                </button>
            {/if}
            {#if busMatrixEnabled}
                <button
                    class="px-4 py-1.5 text-sm rounded-md transition-all duration-200 font-medium flex items-center gap-2"
                    class:bg-white={$viewMode === "bus_matrix"}
                    class:text-primary-600={$viewMode === "bus_matrix"}
                    class:shadow-sm={$viewMode === "bus_matrix"}
                    class:text-gray-500={$viewMode !== "bus_matrix"}
                    class:hover:text-gray-900={$viewMode !== "bus_matrix"}
                    onclick={() => ($viewMode = "bus_matrix")}
                    title="Bus Matrix View"
                >
                    <Icon icon="mdi:table-large" class="w-3.5 h-3.5" />
                    Bus Matrix
                </button>
            {/if}
        </div>

        <!-- Actions -->
        <div class="flex items-center gap-3">
            {#if syncMessage}
                <div
                    class="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-gray-50 border border-gray-200"
                >
                    {#if syncMessage.startsWith("✓")}
                        <div class="w-2 h-2 rounded-full bg-success-500"></div>
                        <span class="text-xs font-medium text-success-700"
                            >{syncMessage.substring(2)}</span
                        >
                    {:else if syncMessage.startsWith("✗")}
                        <div class="w-2 h-2 rounded-full bg-danger-500"></div>
                        <span class="text-xs font-medium text-danger-700"
                            >{syncMessage.substring(2)}</span
                        >
                    {:else}
                        <span class="text-xs text-gray-600">{syncMessage}</span
                        >
                    {/if}
                </div>
            {/if}

            <div class="h-6 w-px bg-gray-200 mx-1"></div>

            <button
                onclick={handleOpenConfigInfo}
                class="px-4 py-2 text-sm rounded-lg font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 transition-colors flex items-center gap-2 shadow-sm"
                title="Show resolved config paths"
            >
                <Icon icon="lucide:info" class="w-4 h-4" />
                Config info
            </button>

            <button
                onclick={toggleAllEntities}
                disabled={loading}
                class="px-4 py-2 text-sm rounded-lg font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 transition-colors disabled:opacity-50 flex items-center gap-2 shadow-sm"
                title={allExpanded ? "Collapse all entities" : "Expand all entities"}
                aria-label={allExpanded ? "Collapse all entities" : "Expand all entities"}
            >
                {#if allExpanded}
                    <!-- Collapse icon: chevrons pointing inward -->
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" class="w-4 h-4">
                        <path d="m7.4 21.308l-.708-.708L12 15.292l5.308 5.308l-.708.708l-4.6-4.6zm4.6-12.6L6.692 3.4l.708-.708l4.6 4.6l4.6-4.6l.708.708z"/>
                    </svg>
                {:else}
                    <!-- Expand icon: chevrons pointing outward -->
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" class="w-4 h-4">
                        <path d="M12 21.308L6.692 16l.714-.713L12 19.842l4.594-4.555l.714.713zm-4.588-12.6L6.692 8L12 2.692L17.308 8l-.72.708L12 4.158z"/>
                    </svg>
                {/if}
                {allExpanded ? "Collapse All" : "Expand All"}
            </button>

            {#if $modelingStyle === "dimensional_model"}
                <button
                    onclick={handleAutoLayout}
                    disabled={loading}
                    class="px-4 py-2 text-sm rounded-lg font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 transition-colors disabled:opacity-50 flex items-center gap-2 shadow-sm"
                    title="Arrange entities by fact/dimension positioning"
                >
                    <Icon icon="lucide:wand-2" class="w-4 h-4" />
                    Auto Layout
                </button>
            {/if}

            <button
                onclick={handleInferFromDbt}
                disabled={syncing || loading}
                class="px-4 py-2 text-sm rounded-lg font-medium text-white bg-primary-600 border border-transparent hover:bg-primary-50 hover:text-primary-700 transition-colors disabled:opacity-50 flex items-center gap-2 shadow-sm"
                title="Import relationship tests from dbt yml files"
            >
                <Icon icon="lucide:download" class="w-4 h-4" />
                Pull from dbt
            </button>

            <button
                onclick={handleSyncDbt}
                disabled={syncing || loading}
                class="px-4 py-2 text-sm rounded-lg font-medium text-white border border-transparent transition-colors disabled:opacity-50 flex items-center gap-2 shadow-sm relative"
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
                    <Icon icon="lucide:loader-2" class="w-4 h-4 animate-spin" />
                {:else}
                    <Icon icon="lucide:upload" class="w-4 h-4" />
                {/if}
                Push to dbt
                {#if needsSync && !syncing}
                    <span class="absolute -top-1 -right-1 flex h-3 w-3">
                        <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                        <span class="relative inline-flex rounded-full h-3 w-3 bg-amber-500"></span>
                    </span>
                {/if}
            </button>
        </div>
    </header>

    <main class="flex-1 flex overflow-hidden relative">
        <Sidebar width={sidebarWidth} {loading} />
        <div
            class="resize-handle h-full"
            class:active={resizingSidebar}
            onpointerdown={startSidebarResize}
        ></div>
        {#if $viewMode === 'exposures'}
            <ExposuresTable {exposuresEnabled} {exposuresDefaultLayout} />
        {:else if $viewMode === 'bus_matrix'}
            <BusMatrix />
        {:else}
            <Canvas guidanceConfig={guidanceConfig} {lineageEnabled} {exposuresEnabled} {hasExposuresData} />
        {/if}
    </main>

    <!-- Render global modals outside SvelteFlow viewport (avoid transform/zoom affecting fixed positioning) -->
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
</div>

<style>
    .resize-handle {
        width: 8px;
        height: 100%;
        cursor: col-resize;
        background: transparent;
        transition: background 0.2s ease;
        pointer-events: auto;
        touch-action: none;
        flex-shrink: 0;
        position: relative;
        z-index: 10;
    }

    .resize-handle:hover,
    .resize-handle.active {
        background: rgba(148, 163, 184, 0.8);
    }
</style>
