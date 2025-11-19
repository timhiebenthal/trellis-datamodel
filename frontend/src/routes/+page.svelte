<script lang="ts">
import { onMount } from 'svelte';
import { nodes, edges, dbtModels, viewMode } from '$lib/stores';
import { getManifest, getOntology, saveOntology } from '$lib/api';
import Sidebar from '$lib/components/Sidebar.svelte';
import Canvas from '$lib/components/Canvas.svelte';
import { type Node, type Edge } from '@xyflow/svelte';

let loading = $state(true);
let saving = $state(false);
let lastSavedState = "";
let sidebarWidth = $state(280);
let resizingSidebar = $state(false);
let resizeStartX = 0;
let resizeStartWidth = 0;
const MIN_SIDEBAR = 200;
const MAX_SIDEBAR = 420;

function onSidebarPointerMove(event: PointerEvent) {
    if (!resizingSidebar) return;
    const delta = event.clientX - resizeStartX;
    sidebarWidth = Math.min(MAX_SIDEBAR, Math.max(MIN_SIDEBAR, resizeStartWidth + delta));
}

function stopSidebarResize() {
    if (!resizingSidebar) return;
    resizingSidebar = false;
    window.removeEventListener('pointermove', onSidebarPointerMove);
    window.removeEventListener('pointerup', stopSidebarResize);
}

function startSidebarResize(event: PointerEvent) {
    event.preventDefault();
    resizingSidebar = true;
    resizeStartX = event.clientX;
    resizeStartWidth = sidebarWidth;
    window.addEventListener('pointermove', onSidebarPointerMove);
    window.addEventListener('pointerup', stopSidebarResize, { once: true });
}

    onMount(async () => {
        try {
            // Load Manifest
            const models = await getManifest();
            $dbtModels = models;
            
            // Load Ontology
            const ontology = await getOntology();
            
            // Map ontology to Svelte Flow format
            $nodes = (ontology.entities || []).map((e: any) => ({
                id: e.id,
                type: 'entity',
                position: e.position || { x: 0, y: 0 },
                data: {
                    label: e.label,
                    description: e.description,
                    dbt_model: e.dbt_model,
                    width: e.width ?? 280,
                    panelHeight: e.panel_height ?? e.panelHeight ?? 200
                }
            })) as Node[];
            
            $edges = (ontology.relationships || []).map((r: any) => ({
                id: `e${r.source}-${r.target}`,
                source: r.source,
                target: r.target,
                type: 'custom',
                data: {
                    label: r.label || '',
                    type: r.type || 'one_to_many'
                }
            })) as Edge[];
            
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
        
        const state = JSON.stringify({ nodes: currentNodes, edges: currentEdges });
        if (state === lastSavedState) return;

        clearTimeout(timeout);
        saving = true;
        timeout = setTimeout(async () => {
            try {
                // Convert back to ontology format
                const ontology = {
                    version: 0.1,
                    entities: currentNodes.map(n => ({
                        id: n.id,
                        label: n.data.label,
                        description: n.data.description,
                        dbt_model: n.data.dbt_model,
                        position: n.position,
                        width: n.data?.width,
                        panel_height: n.data?.panelHeight
                    })),
                    relationships: currentEdges.map(e => ({
                        source: e.source,
                        target: e.target,
                        label: (e.data?.label as string) || '',
                        type: (e.data?.type as string) || 'one_to_many'
                    }))
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
</script>

<div class="flex flex-col h-screen overflow-hidden font-sans text-gray-900">
    <!-- Header -->
    <header class="h-14 bg-white border-b flex items-center px-6 justify-between z-20 shadow-sm shrink-0">
        <div class="flex items-center gap-4">
            <div class="font-bold text-xl text-gray-800 flex items-center gap-2">
                 📦 dbt Ontology
            </div>
             {#if saving}
                <span class="text-xs text-gray-400 animate-pulse">Saving changes...</span>
             {/if}
             {#if loading}
                <span class="text-xs text-blue-400">Loading...</span>
             {/if}
        </div>
        
        <div class="flex bg-gray-100 rounded p-1 border border-gray-200">
            <button 
                class="px-4 py-1.5 text-sm rounded transition-all duration-200 font-medium"
                class:bg-white={$viewMode === 'concept'}
                class:shadow-sm={$viewMode === 'concept'}
                class:text-blue-600={$viewMode === 'concept'}
                class:text-gray-600={$viewMode !== 'concept'}
                onclick={() => $viewMode = 'concept'}
            >
                Conceptual
            </button>
            <button 
                class="px-4 py-1.5 text-sm rounded transition-all duration-200 font-medium"
                class:bg-white={$viewMode === 'physical'}
                class:shadow-sm={$viewMode === 'physical'}
                class:text-blue-600={$viewMode === 'physical'}
                class:text-gray-600={$viewMode !== 'physical'}
                onclick={() => $viewMode = 'physical'}
            >
                Physical
            </button>
        </div>
    </header>
    
    <main class="flex-1 flex overflow-hidden relative">
        <Sidebar width={sidebarWidth} />
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
