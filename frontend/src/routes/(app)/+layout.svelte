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
    frameworkModels,
    viewMode,
    configStatus,
    initHistory,
    pushHistory,
    undo,
    redo,
    folderFilter,
    domainFilter,
    tagFilter,
    canvasFiltersInitialized,
    groupByFolder,
    entitySelection,
        modelingStyle,
        labelPrefixes,
        dimensionPrefixes,
        factPrefixes,
        sourceColors,
        activeFramework,
    } from "$lib/stores";
    import {
        getManifest,
        getDataModel,
        getConfigStatus,
        getConfigInfo,
        inferRelationships,
        getExposures,
        reconcileDbt,
    } from "$lib/api";
import { getModelFolder } from "$lib/utils/folder-utils";
import { aggregateRelationshipsIntoEdges } from "$lib/utils/relationship-edges";
import { getLabelPrefixesFromConfig } from "$lib/utils/model-naming";
import { nextExpandCollapseState } from "$lib/utils/expand-collapse";
import { readModelRef } from "$lib/utils/entity-compat";
import { buildEntityNodes, groupEntityNodesByFolder, smartPositionNodes } from "$lib/utils/canvas-nodes";
import { matchesCanvasFilters } from "$lib/utils/canvas-filtering";
import { isFeatureAvailable, getFrameworkCopy } from "$lib/utils/framework-display";
    import { applyDagreLayout } from "$lib/layout";
    import Sidebar from "$lib/components/Sidebar.svelte";
    import ConfigInfoModal from "$lib/components/ConfigInfoModal.svelte";
    import LineageModal from "$lib/components/LineageModal.svelte";
    import IncompleteEntitiesWarningModal from "$lib/components/IncompleteEntitiesWarningModal.svelte";
    import UndescribedAttributesWarningModal from "$lib/components/UndescribedAttributesWarningModal.svelte";
    import SourceEditorModal from "$lib/components/SourceEditorModal.svelte";
    import DeleteConfirmModal from "$lib/components/DeleteConfirmModal.svelte";
    import EntityDetailModal from "$lib/components/EntityDetailModal.svelte";
    import Toolbar from "$lib/components/Toolbar.svelte";
    import { getEntityIdFromPath } from "$lib/utils/entity-list-route";
    import { type Node, type Edge } from "@xyflow/svelte";
    import type { ConfigInfo, EntityNodeData, GroupFlowNode, GuidanceConfig } from "$lib/types";
    import { isEntityNode } from "$lib/types";
    import Icon from "$lib/components/Icon.svelte";
    import { entityDetailModal, lineageModal, closeLineageModal, sourceEditorModal, closeSourceEditorModal, deleteConfirmModal, closeDeleteConfirmModal } from "$lib/stores";
    import { AutoSaveService } from "$lib/services/auto-save";
    import { createBootLoader } from "$lib/boot-loader";
    import {
        failBootPhase,
        finishBootPhase,
        emitBootSummary,
        startBootPhase,
    } from "$lib/boot-diagnostics";
    import {
        buildBootGraphIndex,
        transformBootGraph,
        type BootGraphIndex,
    } from "$lib/utils/boot-graph";
    import { pushToFramework, pullFromFramework, type SyncStatus, type UndescribedEntity } from "$lib/services/canvas-sync";
    import { createConfirmGate } from "$lib/services/confirm-gate";

    let { children } = $props();

    let loading = $state(true);
    let syncing = $state(false);
    let syncMessage = $state<string | null>(null);
    
    // AutoSave service instance
    let autoSaveService: AutoSaveService | null = null;
    let lastSyncedState = $state("");
    let needsSync = $state(false);
    let saving = $state(false);
    let bootGraphIndex: BootGraphIndex | null = null;

    // Framework-aware wording for the pull/push controls, sourced from the same
    // branding module the sidebar header uses.
    let frameworkCopy = $derived(getFrameworkCopy($activeFramework));

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
    let unconfiguredCanvas = $state(true);
    let navigationConfigLoaded = $state(false);
    let lineageEnabled = $state(false);
    let exposuresEnabled = $state(false);
    let exposuresDefaultLayout = $state<'dashboards-as-rows' | 'entities-as-rows'>('dashboards-as-rows');
    let busMatrixEnabled = $state(false);
    let businessEventsEnabled = $state(false);
    let metricsEnabled = $state(false);
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
    const loadingStore = writable(loading);
    setContext('guidanceConfig', guidanceConfigStore);
    setContext('lineageEnabled', lineageEnabledStore);
    setContext('exposuresEnabled', exposuresEnabledStore);
    setContext('hasExposuresData', hasExposuresDataStore);
    setContext('loading', loadingStore);

    // Provide autoSaveService to child components (for EntityDetailModal)
    const autoSaveServiceContext = $state<{ current: AutoSaveService | null }>({ current: null });
    setContext('autoSaveService', autoSaveServiceContext);

    let warningModalOpen = $state(false);
    let incompleteEntitiesForWarning = $state<Node[]>([]);
    const incompleteEntitiesGate = createConfirmGate();
    let undescribedAttributesModalOpen = $state(false);
    let entitiesWithUndescribedAttributes = $state<UndescribedEntity[]>([]);
    const undescribedAttributesGate = createConfirmGate();

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
        } else if (currentPath === '/entity-list') {
            // Entity list view doesn't change viewMode - maintains current mode
        }
    });

    // Keep entity-list detail routes and the global detail modal in sync.
    $effect(() => {
        const entityId = getEntityIdFromPath($page.url.pathname);

        if (entityId === null) {
            if ($page.url.pathname === '/entity-list' && $entityDetailModal.open) {
                entityDetailModal.set({ open: false, entityId: null });
            }
            return;
        }

        const entityExists = $nodes.some((node) => node.type === 'entity' && node.id === entityId);
        if (entityExists) {
            if (!$entityDetailModal.open || $entityDetailModal.entityId !== entityId) {
                entityDetailModal.set({ open: true, entityId });
            }
        } else if (!loading && $entityDetailModal.open) {
            entityDetailModal.set({ open: false, entityId: null });
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
        loadingStore.set(loading);
    });

    // Show warning modal for incomplete entities and wait for user decision
    function showIncompleteEntitiesWarning(incompleteEntities: Node[]): Promise<boolean> {
        incompleteEntitiesForWarning = incompleteEntities;
        const decision = incompleteEntitiesGate.request();
        warningModalOpen = true;
        return decision;
    }

    function closeIncompleteEntitiesWarning(proceed: boolean) {
        warningModalOpen = false;
        incompleteEntitiesGate.settle(proceed);
    }

    // Show warning modal for undescribed attributes and wait for user decision
    function showUndescribedAttributesWarning(entities: UndescribedEntity[]): Promise<boolean> {
        entitiesWithUndescribedAttributes = entities;
        const decision = undescribedAttributesGate.request();
        undescribedAttributesModalOpen = true;
        return decision;
    }

    function closeUndescribedAttributesWarning(proceed: boolean) {
        undescribedAttributesModalOpen = false;
        undescribedAttributesGate.settle(proceed);
    }

    // Show a toolbar status line and clear it after its timeout.
    function flashSyncMessage(status: SyncStatus) {
        syncMessage = status.message;
        setTimeout(() => {
            syncMessage = null;
        }, status.clearAfterMs);
    }

    async function handleSyncDbt() {
        syncing = true;
        syncMessage = null;
        try {
            const outcome = await pushToFramework({
                nodes: $nodes,
                pushWarningEnabled: guidanceConfig.push_warning_enabled,
                confirmIncomplete: showIncompleteEntitiesWarning,
                confirmUndescribed: showUndescribedAttributesWarning,
            });
            if (!outcome) return;
            // Mark current state as synced
            if (outcome.ok && autoSaveService) {
                lastSyncedState = autoSaveService.getLastSavedState();
            }
            flashSyncMessage(outcome);
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
                lineageEnabled = isFeatureAvailable(info.lineage_enabled, info.capabilities, 'lineage');
                exposuresEnabled = isFeatureAvailable(info.exposures_enabled, info.capabilities, 'exposures');
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
            const outcome = await pullFromFramework({
                getGraph: () => ({
                    nodes: $nodes,
                    edges: $edges,
                    models: $frameworkModels,
                    labelPrefixes: $labelPrefixes,
                }),
                noRelationshipsMessage: frameworkCopy.noRelationshipsMessage,
            });
            if (outcome.nodes) $nodes = outcome.nodes;
            if (outcome.edges) $edges = outcome.edges;
            flashSyncMessage(outcome);
        } finally {
            syncing = false;
        }
    }

    async function handleAutoLayout() {
        if (loading) return;

        const entityNodes = $nodes.filter(isEntityNode);
        if (entityNodes.length === 0) return;

        // If dimensional modeling is enabled, use smart positioning
        if ($modelingStyle === "dimensional_model") {
            $nodes = smartPositionNodes($nodes, entityNodes);
        } else {
            // Use dagre layout for entity modeling
            const layoutedNodes = await applyDagreLayout($nodes, $edges);
            $nodes = layoutedNodes;
        }
        // fitView prop on Canvas will automatically adjust the view
    }

    // Expand/Collapse all entities toggle
    const STORAGE_KEY = "trellis_all_expanded";
    let allExpanded = $state(true);
    let stateApplied = $state(false);
    let hasPersistedCollapsePreference = $state(false);
    let collapsePreferenceLoaded = $state(false);

    // Restore state from localStorage on mount
    onMount(() => {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved !== null) {
            hasPersistedCollapsePreference = true;
            allExpanded = saved === "true";
        }
        collapsePreferenceLoaded = true;
    });


    // Watch for nodes changes and apply persisted state once when nodes are first loaded
    $effect(() => {
        const currentNodes = $nodes;
        const entityNodes = currentNodes.filter((n) => n.type === "entity");
        if (entityNodes.length > 0 && collapsePreferenceLoaded && navigationConfigLoaded && !stateApplied) {
            // A fresh, unconfigured project starts in a conceptual, collapsed
            // Canvas. An explicit local preference always wins for collapse.
            if (unconfiguredCanvas) {
                $viewMode = "conceptual";
                if (!hasPersistedCollapsePreference) {
                    allExpanded = false;
                }
            }
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
        // Derive the action from what is actually rendered, not from the
        // persisted toggle flag: if the flag and the canvas ever desync, a
        // blind toggle would appear to do nothing.
        allExpanded = nextExpandCollapseState($nodes);
        applyExpandCollapseState(allExpanded);
        // Persist to localStorage
        localStorage.setItem(STORAGE_KEY, String(allExpanded));
        // Save immediately using AutoSave service
        autoSaveService?.saveNow($nodes, $edges);
    }

    function hasExplicitCanvasEntitySubset(): boolean {
        if ($page.url.pathname !== "/canvas") return false;
        const entities = $page.url.searchParams.get("entities");
        return entities !== null && entities.split(",").some((id) => id.trim().length > 0);
    }
    
    onMount(() => {
        (async () => {
            const corePhase = startBootPhase("core-publish");
            try {
                let releaseRelationshipInference!: () => void;
                const corePublished = new Promise<void>((resolve) => {
                    releaseRelationshipInference = resolve;
                });
                const boot = createBootLoader({
                    getConfigStatus,
                    getConfigInfo,
                    getManifest,
                    reconcile: reconcileDbt,
                    getDataModel,
                    getExposures: async () => {
                        const phase = startBootPhase("exposures");
                        try {
                            const result = await getExposures();
                            finishBootPhase(phase);
                            return result;
                        } catch (error) {
                            failBootPhase(phase, error);
                            throw error;
                        }
                    },
                    inferRelationships: async () => {
                        await corePublished;
                        const phase = startBootPhase("relationship-inference");
                        try {
                            const result = await inferRelationships();
                            finishBootPhase(phase);
                            return result;
                        } catch (error) {
                            failBootPhase(phase, error);
                            throw error;
                        }
                    },
                });
                const { status, config: info, models, dataModel } = await boot.core;
                $configStatus = status;
                unconfiguredCanvas =
                    !status.config_present ||
                    status.data_model_exists === false ||
                    Boolean(status.error);

                // Load Config Info (includes guidance config and Canvas defaults).
                configInfo = info;
                const hasCanvasNavigationConfig =
                    info?.start_page === 'entity-list' ||
                    (info?.canvas_default_filters?.domains?.length ?? 0) > 0 ||
                    (info?.canvas_default_filters?.tags?.length ?? 0) > 0;
                unconfiguredCanvas = unconfiguredCanvas || !hasCanvasNavigationConfig;
                navigationConfigLoaded = true;
                if (!$canvasFiltersInitialized) {
                    domainFilter.set([...(info?.canvas_default_filters?.domains ?? [])]);
                    tagFilter.set([...(info?.canvas_default_filters?.tags ?? [])]);
                    canvasFiltersInitialized.set(true);
                }
                if (info?.guidance) {
                    guidanceConfig = info.guidance;
                }
                lineageEnabled = isFeatureAvailable(info?.lineage_enabled, info?.capabilities, 'lineage');
                exposuresEnabled = isFeatureAvailable(info?.exposures_enabled, info?.capabilities, 'exposures');
                exposuresDefaultLayout = info?.exposures_default_layout ?? 'dashboards-as-rows';
                busMatrixEnabled = info?.bus_matrix_enabled ?? false;
                businessEventsEnabled = info?.business_events_enabled ?? false;
                metricsEnabled = info?.metrics_enabled ?? false;
                $modelingStyle = info?.modeling_style ?? 'entity_model';
                $activeFramework = info?.framework ?? 'dbt-core';
                $labelPrefixes = getLabelPrefixesFromConfig(info ?? null);
                dimensionPrefixes.set(info?.dimension_prefix ?? []);
                factPrefixes.set(info?.fact_prefix ?? []);

                $frameworkModels = models;

                void boot.optional.exposures.then((exposuresData) => {
                    hasExposuresData = (exposuresData?.exposures?.length ?? 0) > 0;
                });

                // Load source_colors from canvas_layout.yml
                if (dataModel.source_colors) {
                    $sourceColors = dataModel.source_colors;
                }

                // If no relationships in data model, try to infer from dbt yml files
                let relationships = dataModel.relationships || [];

                // Map data model to Svelte Flow format with metadata
                const entityNodes = buildEntityNodes(dataModel.entities || [], models, $labelPrefixes);

                // Create group nodes if grouping is enabled
                const groupNodes: GroupFlowNode[] = $groupByFolder ? groupEntityNodesByFolder(entityNodes) : [];

                $nodes = [...groupNodes, ...entityNodes];
                $edges = aggregateRelationshipsIntoEdges(relationships);
                bootGraphIndex = buildBootGraphIndex({
                    models,
                    entities: dataModel.entities || [],
                    nodes: $nodes,
                });
                const coreGraph = transformBootGraph(bootGraphIndex, $edges);
                $nodes = coreGraph.nodes as Node[];
                $edges = coreGraph.edges as Edge[];

                if (!autoSaveService) {
                    autoSaveService = new AutoSaveService(400);
                    autoSaveServiceContext.current = autoSaveService;
                }
                autoSaveService.initializeBaseline($nodes, $edges);
                lastSyncedState = autoSaveService.getLastSavedState();
                initHistory();
                finishBootPhase(corePhase);
                loading = false;
                releaseRelationshipInference();
                setTimeout(() => {
                    autoSaveService?.initializeBaseline($nodes, $edges);
                    lastSyncedState = autoSaveService?.getLastSavedState() ?? lastSyncedState;
                });

                if (relationships.length === 0) {
                    setTimeout(() => {
                        void boot.optional.relationships.then((inferred) => {
                            if (inferred.length > 0) {
                                relationships = inferred;
                                $edges = aggregateRelationshipsIntoEdges(relationships);
                            }
                        });
                    });
                }

                const layoutCheckNodes = $nodes.filter((n) => n.type === "entity");
                const allAtDefaultPosition =
                    layoutCheckNodes.length > 0 &&
                    layoutCheckNodes.every((n) => n.position.x === 0 && n.position.y === 0);
                let deferredLayout: Promise<void> = Promise.resolve();
                if (allAtDefaultPosition) {
                    const layoutPhase = startBootPhase("elk-layout");
                    deferredLayout = new Promise((resolve) => {
                        setTimeout(() => {
                            void applyDagreLayout($nodes, $edges)
                                .then((layoutedNodes) => {
                                    if (layoutedNodes !== $nodes) {
                                        $nodes = layoutedNodes;
                                    }
                                    return new Promise<void>((resolve) => {
                                        setTimeout(() => {
                                            autoSaveService?.initializeBaseline($nodes, $edges);
                                            lastSyncedState =
                                                autoSaveService?.getLastSavedState() ?? lastSyncedState;
                                            finishBootPhase(layoutPhase);
                                            resolve();
                                        });
                                    });
                                })
                                .catch((error) => {
                                    return new Promise<void>((resolve) => {
                                        setTimeout(() => {
                                            failBootPhase(layoutPhase, error);
                                            autoSaveService?.initializeBaseline($nodes, $edges);
                                            lastSyncedState =
                                                autoSaveService?.getLastSavedState() ?? lastSyncedState;
                                            resolve();
                                        });
                                    });
                                })
                                .finally(resolve);
                        });
                    });
                }
                setTimeout(() => {
                    void Promise.allSettled([
                        boot.optional.exposures,
                        boot.optional.relationships,
                        deferredLayout,
                    ]).then(() => emitBootSummary());
                });
            } catch (e) {
                failBootPhase(corePhase, e);
                console.error(e);
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
            autoSaveServiceContext.current = autoSaveService;
            return;
        }
        
        const currentNodes = $nodes;
        const currentEdges = $edges;
        autoSaveService.save(currentNodes, currentEdges);
        
        pushHistory();
    });

    $effect(() => {
        if (loading || !bootGraphIndex) return;

        const activeFolder = $folderFilter;
        const activeDomains = $domainFilter;
        const activeTags = $tagFilter;
        const explicitEntityIds = hasExplicitCanvasEntitySubset()
            ? new Set(($page.url.searchParams.get("entities") ?? "").split(",").filter((id) => id.trim()))
            : null;

        const currentNodes = untrack(() => $nodes);
        const currentEdges = untrack(() => $edges);
        const filtering =
            activeFolder.length > 0 ||
            activeDomains.length > 0 ||
            activeTags.length > 0;

        if (!filtering) {
            const hasHiddenState =
                currentNodes.some((node) => node.hidden) || currentEdges.some((edge) => edge.hidden);
            if (!hasHiddenState) return;

            $nodes = currentNodes.map((node) => (node.hidden ? { ...node, hidden: false } : node));
            $edges = currentEdges.map((edge) => (edge.hidden ? { ...edge, hidden: false } : edge));
            return;
        }

        const visibleNodeIds = new Set<string>();
        for (const node of bootGraphIndex.nodes) {
            if (node.type === "group") {
                visibleNodeIds.add(node.id);
                continue;
            }

            const entity = bootGraphIndex.entitiesById.get(node.id);
            if (!entity) {
                visibleNodeIds.add(node.id);
                continue;
            }

            const modelIds = [
                readModelRef(entity),
                ...(entity.additional_models ?? []),
            ].filter((modelId): modelId is string => Boolean(modelId));
            const boundModels = modelIds
                .map((modelId) => bootGraphIndex?.modelsById.get(modelId))
                .filter((model): model is NonNullable<typeof model> => model !== undefined);

            let visible = explicitEntityIds?.has(node.id) ?? true;

            if (!explicitEntityIds?.has(node.id) && activeFolder.length > 0) {
                if (boundModels.length === 0) {
                    visible = false;
                } else {
                    const matchingFolders = boundModels
                        .map((model) => getModelFolder(model))
                        .filter((folder): folder is string => folder !== null);
                    visible = visible && matchingFolders.some((folder) => activeFolder.includes(folder));
                }
            }

            if (!explicitEntityIds?.has(node.id)) {
                visible = visible && matchesCanvasFilters(
                    // bootGraphIndex.nodes is untyped Node[]; only entity nodes reach here.
                    node.data as EntityNodeData,
                    {
                        selectedDomains: activeDomains,
                        selectedTags: activeTags,
                    },
                    boundModels,
                );
            }

            if (visible) visibleNodeIds.add(node.id);
        }

        const transformed = transformBootGraph(bootGraphIndex, currentEdges, { visibleNodeIds });
        const visibleIds = new Set(transformed.nodes.map((node) => node.id));
        const updatedNodes = currentNodes.map((node) => {
            if (node.type === "group") return node;
            const hidden = !visibleIds.has(node.id);
            return node.hidden === hidden ? node : { ...node, hidden };
        });
        const updatedEdges = currentEdges.map((edge) => {
            const hidden =
                !visibleIds.has(edge.source) || !visibleIds.has(edge.target);
            return edge.hidden === hidden ? edge : { ...edge, hidden };
        });

        if (updatedNodes.some((node, index) => node !== currentNodes[index])) {
            $nodes = updatedNodes;
        }
        if (updatedEdges.some((edge, index) => edge !== currentEdges[index])) {
            $edges = updatedEdges;
        }
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
                <span class="text-xs text-primary-500 ml-2" data-testid="app-loading">Loading...</span>
            {:else}
                <span data-testid="app-ready" class="sr-only"></span>
            {/if}
        </div>

        <!-- View Switcher -->
        <div class="flex bg-gray-100 rounded-lg p-1 border border-gray-200/60 gap-1">
            {#if businessEventsEnabled}
                <a
                    href="/business-events"
                    class="flex-1 min-w-32 px-4 py-1.5 text-sm rounded-md transition-all duration-200 font-medium flex items-center justify-center gap-2 whitespace-nowrap"
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
            <a
                href="/canvas"
                class="flex-1 min-w-32 px-4 py-1.5 text-sm rounded-md transition-all duration-200 font-medium flex items-center justify-center gap-2 whitespace-nowrap"
                class:bg-white={$page.url.pathname === '/canvas'}
                class:text-primary-600={$page.url.pathname === '/canvas'}
                class:shadow-sm={$page.url.pathname === '/canvas'}
                class:text-gray-500={$page.url.pathname !== '/canvas'}
                class:hover:text-gray-900={$page.url.pathname !== '/canvas'}
            >
                <Icon icon="lucide:layout-dashboard" class="w-3.5 h-3.5" />
                Canvas
            </a>
            <a
                href="/entity-list"
                class="flex-1 min-w-32 px-4 py-1.5 text-sm rounded-md transition-all duration-200 font-medium flex items-center justify-center gap-2 whitespace-nowrap"
                class:bg-white={$page.url.pathname === '/entity-list'}
                class:text-primary-600={$page.url.pathname === '/entity-list'}
                class:shadow-sm={$page.url.pathname === '/entity-list'}
                class:text-gray-500={$page.url.pathname !== '/entity-list'}
                class:hover:text-gray-900={$page.url.pathname !== '/entity-list'}
            >
                <Icon icon="lucide:list-tree" class="w-3.5 h-3.5" />
                Entity List
            </a>
            {#if metricsEnabled}
                <a
                    href="/metrics-tree"
                    class="flex-1 min-w-32 px-4 py-1.5 text-sm rounded-md transition-all duration-200 font-medium flex items-center justify-center gap-2 whitespace-nowrap"
                    class:bg-white={$page.url.pathname === '/metrics-tree'}
                    class:text-primary-600={$page.url.pathname === '/metrics-tree'}
                    class:shadow-sm={$page.url.pathname === '/metrics-tree'}
                    class:text-gray-500={$page.url.pathname !== '/metrics-tree'}
                    class:hover:text-gray-900={$page.url.pathname !== '/metrics-tree'}
                >
                    <Icon icon="lucide:git-branch" class="w-3.5 h-3.5" />
                    Metric Tree
                </a>
            {/if}
            {#if exposuresEnabled && hasExposuresData}
                <a
                    href="/exposures"
                    class="flex-1 min-w-32 px-4 py-1.5 text-sm rounded-md transition-all duration-200 font-medium flex items-center justify-center gap-2 whitespace-nowrap"
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
                    class="flex-1 min-w-32 px-4 py-1.5 text-sm rounded-md transition-all duration-200 font-medium flex items-center justify-center gap-2 whitespace-nowrap"
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
        </div>

        <Toolbar
            {syncMessage}
            {loading}
            {syncing}
            {needsSync}
            {allExpanded}
            showAutoLayout={$modelingStyle === "dimensional_model"}
            {frameworkCopy}
            onToggleAll={toggleAllEntities}
            onAutoLayout={handleAutoLayout}
            onPull={handleInferFromDbt}
            onPush={handleSyncDbt}
        />
    </header>

    <main class="flex-1 flex overflow-hidden relative">
        {#if !$page.url.pathname.startsWith('/metrics-tree')}
            <Sidebar width={280} {loading} trellisVersion={configInfo?.trellis_version ?? null} />
        {/if}
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
        onConfirm={() => closeIncompleteEntitiesWarning(true)}
        onCancel={() => closeIncompleteEntitiesWarning(false)}
    />

    <UndescribedAttributesWarningModal
        open={undescribedAttributesModalOpen}
        entitiesWithAttributes={entitiesWithUndescribedAttributes}
        onConfirm={() => closeUndescribedAttributesWarning(true)}
        onCancel={() => closeUndescribedAttributesWarning(false)}
    />

    <DeleteConfirmModal
        open={$deleteConfirmModal.open}
        entityLabel={$deleteConfirmModal.entityLabel}
        entityCount={$deleteConfirmModal.entityIds.length}
        onConfirm={() => {
            const idsToDelete = new Set($deleteConfirmModal.entityIds);
            if (idsToDelete.size > 0) {
                nodes.update((list) => list.filter((n) => !idsToDelete.has(n.id)));
                edges.update((list) =>
                    list.filter((e) => !idsToDelete.has(e.source) && !idsToDelete.has(e.target))
                );
                entitySelection.update((selection) => {
                    const nextSelection = new Set(selection);
                    idsToDelete.forEach((id) => nextSelection.delete(id));
                    return nextSelection;
                });
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

    <EntityDetailModal />
</div>
