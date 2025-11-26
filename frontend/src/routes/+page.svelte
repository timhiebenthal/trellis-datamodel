<script lang="ts">
    import { onMount } from "svelte";
    import {
        nodes,
        edges,
        dbtModels,
        viewMode,
        configStatus,
    } from "$lib/stores";
    import {
        getManifest,
        getOntology,
        saveOntology,
        getConfigStatus,
        inferRelationships,
        syncDbtTests,
    } from "$lib/api";
    import Sidebar from "$lib/components/Sidebar.svelte";
    import Canvas from "$lib/components/Canvas.svelte";
    import { type Node, type Edge } from "@xyflow/svelte";

    let loading = $state(true);
    let saving = $state(false);
    let syncing = $state(false);
    let syncMessage = $state<string | null>(null);
    let lastSavedState = "";

    function getParallelOffset(index: number): number {
        if (index === 0) return 0;
        const level = Math.ceil(index / 2);
        const offset = level * 20;
        return index % 2 === 1 ? offset : -offset;
    }
    
    async function handleSyncDbt() {
        syncing = true;
        syncMessage = null;
        try {
            const result = await syncDbtTests();
            syncMessage = `✓ ${result.message}`;
            setTimeout(() => { syncMessage = null; }, 3000);
        } catch (e) {
            syncMessage = `✗ ${e instanceof Error ? e.message : 'Sync failed'}`;
            setTimeout(() => { syncMessage = null; }, 5000);
        } finally {
            syncing = false;
        }
    }

    async function handleInferFromDbt() {
        syncing = true;
        syncMessage = "Inferring...";
        try {
            const inferred = await inferRelationships();
            if (inferred.length > 0) {
                let addedCount = 0;
                const newEdges = [...$edges];
                
                inferred.forEach((r: any) => {
                    const exists = newEdges.some(e => 
                        e.source === r.source && 
                        e.target === r.target && 
                        e.data?.source_field === r.source_field &&
                        e.data?.target_field === r.target_field
                    );
                    
                    if (!exists) {
                        const parallelEdges = newEdges.filter(e => 
                             (e.source === r.source && e.target === r.target) ||
                             (e.source === r.target && e.target === r.source)
                        );
                        const currentCount = parallelEdges.length;
                        
                        const baseId = `e${r.source}-${r.target}`;
                        const edgeId = `${baseId}-${Date.now()}-${currentCount}`; 
                        
                        newEdges.push({
                            id: edgeId,
                            source: r.source,
                            target: r.target,
                            type: "custom",
                            data: {
                                label: r.label || "",
                                type: r.type || "one_to_many",
                                source_field: r.source_field,
                                target_field: r.target_field,
                                label_dx: r.label_dx || 0,
                                label_dy: r.label_dy || 0,
                                parallelOffset: getParallelOffset(currentCount),
                            },
                        });
                        addedCount++;
                    }
                });
                
                if (addedCount > 0) {
                    $edges = newEdges;
                    syncMessage = `✓ Added ${addedCount} new`;
                    setTimeout(() => { syncMessage = null; }, 3000);
                } else {
                    syncMessage = "No new found";
                    setTimeout(() => { syncMessage = null; }, 3000);
                }
            } else {
                syncMessage = "No relationships in dbt";
                setTimeout(() => { syncMessage = null; }, 3000);
            }
        } catch (e) {
            console.error(e);
            syncMessage = "✗ Failed to infer";
            setTimeout(() => { syncMessage = null; }, 5000);
        } finally {
            syncing = false;
        }
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

    onMount(async () => {
        try {
            // Check Config Status
            const status = await getConfigStatus();
            $configStatus = status;

            // Load Manifest
            const models = await getManifest();
            $dbtModels = models;

            // Load Ontology
            const ontology = await getOntology();

            // If no relationships in ontology, try to infer from dbt yml files
            let relationships = ontology.relationships || [];
            if (relationships.length === 0) {
                console.log("No relationships found in ontology, attempting to infer from dbt yml files...");
                const inferred = await inferRelationships();
                if (inferred.length > 0) {
                    relationships = inferred;
                    console.log(`Inferred ${inferred.length} relationships from dbt yml files`);
                }
            }

            // Map ontology to Svelte Flow format
            $nodes = (ontology.entities || []).map((e: any) => ({
                id: e.id,
                type: "entity",
                position: e.position || { x: 0, y: 0 },
                data: {
                    label: e.label,
                    description: e.description,
                    dbt_model: e.dbt_model,
                    drafted_fields: e.drafted_fields,
                    width: e.width ?? 280,
                    panelHeight: e.panel_height ?? e.panelHeight ?? 200,
                    collapsed: e.collapsed ?? false,
                },
            })) as Node[];

            const edgeCounts = new Map<string, number>();
            $edges = relationships.map((r: any) => {
                const pairKey =
                    r.source < r.target ? `${r.source}-${r.target}` : `${r.target}-${r.source}`;
                const currentCount = edgeCounts.get(pairKey) ?? 0;
                edgeCounts.set(pairKey, currentCount + 1);

                const baseId = `e${r.source}-${r.target}`;
                let edgeId = `${baseId}-${currentCount}`;
                if (currentCount === 0) edgeId = baseId;

                return {
                    id: edgeId,
                    source: r.source,
                    target: r.target,
                    type: "custom",
                    data: {
                        label: r.label || "",
                        type: r.type || "one_to_many",
                        source_field: r.source_field,
                        target_field: r.target_field,
                        label_dx: r.label_dx || 0,
                        label_dy: r.label_dy || 0,
                        parallelOffset: getParallelOffset(currentCount),
                    },
                };
            }) as Edge[];

            lastSavedState = JSON.stringify({ nodes: $nodes, edges: $edges });
        } catch (e) {
            console.error("Initialization error:", e);
            alert("Failed to initialize. Check backend connection.");
        } finally {
            loading = false;
        }
    });

    // Auto-save logic
    let timeout: ReturnType<typeof setTimeout>;

    $effect(() => {
        if (loading) return;

        // Track dependencies
        const currentNodes = $nodes;
        const currentEdges = $edges;

        const state = JSON.stringify({
            nodes: currentNodes,
            edges: currentEdges,
        });
        if (state === lastSavedState) return;

        clearTimeout(timeout);
        saving = true;
        timeout = setTimeout(async () => {
            try {
                // Convert back to ontology format
                const ontology = {
                    version: 0.1,
                    entities: currentNodes.map((n) => ({
                        id: n.id,
                        label: n.data.label,
                        description: n.data.description,
                        dbt_model: n.data.dbt_model,
                        drafted_fields: n.data?.drafted_fields,
                        position: n.position,
                        width: n.data?.width,
                        panel_height: n.data?.panelHeight,
                        collapsed: n.data?.collapsed ?? false,
                    })),
                    relationships: currentEdges.map((e) => ({
                        source: e.source,
                        target: e.target,
                        label: (e.data?.label as string) || "",
                        type: (e.data?.type as string) || "one_to_many",
                        source_field: e.data?.source_field,
                        target_field: e.data?.target_field,
                        label_dx: e.data?.label_dx,
                        label_dy: e.data?.label_dy,
                    })),
                };

                await saveOntology(ontology);
                lastSavedState = state;
            } catch (e) {
                console.error("Save failed", e);
            } finally {
                saving = false;
            }
        }, 1000); // 1s debounce
    });

    // Auto-expand entities when switching to physical view
    $effect(() => {
        if ($viewMode === "physical") {
            // Only update nodes if there are actually collapsed ones
            const hasCollapsed = $nodes.some(
                (node) => node.data?.collapsed === true,
            );
            if (hasCollapsed) {
                $nodes = $nodes.map((node) => ({
                    ...node,
                    data: {
                        ...node.data,
                        collapsed: false,
                    },
                }));
            }
        }
    });
</script>

<div class="flex flex-col h-screen overflow-hidden font-sans text-gray-900">
    <!-- Header -->
    <header
        class="h-14 bg-white border-b flex items-center px-6 justify-between z-20 shadow-sm shrink-0"
    >
        <div class="flex items-center gap-4">
            <div
                class="font-bold text-xl text-gray-800 flex items-center gap-2"
            >
                📦 dbt Ontology
            </div>
            {#if saving}
                <span class="text-xs text-gray-400 animate-pulse"
                    >Saving changes...</span
                >
            {/if}
            {#if loading}
                <span class="text-xs text-blue-400">Loading...</span>
            {/if}
        </div>

        <div class="flex bg-gray-100 rounded p-1 border border-gray-200">
            <button
                class="px-4 py-1.5 text-sm rounded transition-all duration-200 font-medium"
                class:bg-white={$viewMode === "concept"}
                class:shadow-sm={$viewMode === "concept"}
                class:text-blue-600={$viewMode === "concept"}
                class:text-gray-600={$viewMode !== "concept"}
                onclick={() => ($viewMode = "concept")}
            >
                Conceptual
            </button>
            <button
                class="px-4 py-1.5 text-sm rounded transition-all duration-200 font-medium"
                class:bg-white={$viewMode === "physical"}
                class:shadow-sm={$viewMode === "physical"}
                class:text-blue-600={$viewMode === "physical"}
                class:text-gray-600={$viewMode !== "physical"}
                onclick={() => ($viewMode = "physical")}
            >
                Physical
            </button>
        </div>
        
        <div class="flex items-center gap-3">
            {#if syncMessage}
                <span class="text-xs" class:text-green-600={syncMessage.startsWith('✓')} class:text-red-600={syncMessage.startsWith('✗')}>
                    {syncMessage}
                </span>
            {/if}
            <button
                onclick={handleInferFromDbt}
                disabled={syncing || loading}
                class="px-4 py-1.5 text-sm rounded font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                title="Import relationship tests from dbt yml files"
            >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 8V7a3 3 0 00-3-3H7a3 3 0 00-3 3v1m4 4l4-4m0 0l4 4m-4-4v12" />
                </svg>
                Pull from dbt
            </button>
            <button
                onclick={handleSyncDbt}
                disabled={syncing || loading}
                class="px-4 py-1.5 text-sm rounded font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                title="Sync relationship tests to dbt yml files"
            >
                <svg class={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Push to dbt
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
        <Canvas />
    </main>
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
