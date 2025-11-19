<script lang="ts">
    import { Handle, Position, useSvelteFlow, type NodeProps } from '@xyflow/svelte';
    import { viewMode, dbtModels, nodes, edges } from '$lib/stores';
    import type { DbtModel } from '$lib/types';

    type $$Props = NodeProps;

    let { data, id } = $props<$$Props>();
    
    const { updateNodeData } = useSvelteFlow();
    
    // Reactive binding check
    let boundModelName = $derived(data.dbt_model as string | undefined);
    let isBound = $derived(!!boundModelName);
    let isCollapsed = $derived(data.collapsed ?? false);
    const DEFAULT_WIDTH = 280;
    const DEFAULT_PANEL_HEIGHT = 200;
    const MIN_WIDTH = 220;
    const MAX_WIDTH = 560;
    const MIN_PANEL_HEIGHT = 120;
    const MAX_PANEL_HEIGHT = 480;
    let nodeWidth = $derived(data.width ?? DEFAULT_WIDTH);
    let columnPanelHeight = $derived(data.panelHeight ?? DEFAULT_PANEL_HEIGHT);

    
    // Find model details by unique_id (e.g. "model.elmo.entity_booking")
    let modelDetails = $derived(
        isBound ? $dbtModels.find(m => m.unique_id === boundModelName) : null
    );

    function generateSlug(label: string, currentId: string): string {
        // Convert to lowercase and replace spaces/special chars with underscores
        let slug = label.toLowerCase()
            .replace(/[^a-z0-9]+/g, '_')
            .replace(/^_+|_+$/g, ''); // trim leading/trailing underscores
        
        // If empty after cleaning, use a default
        if (!slug) slug = 'entity';
        
        // Ensure uniqueness by checking existing node IDs (excluding current node)
        let finalSlug = slug;
        let counter = 1;
        while ($nodes.some(node => node.id === finalSlug && node.id !== currentId)) {
            finalSlug = `${slug}_${counter}`;
            counter++;
        }
        
        return finalSlug;
    }
    
    function updateLabel(e: Event) {
        const label = (e.target as HTMLInputElement).value;
        // Just update the label without changing ID (for real-time typing)
        updateNodeData(id, { label });
    }
    
    function updateIdFromLabel(e: Event) {
        // Called on blur - update the ID based on final label
        const label = (e.target as HTMLInputElement).value;
        const newId = generateSlug(label, id);
        
        // If ID changes, update the node and all relationships
        if (newId !== id) {
            // Update all edges that reference this node
            $edges = $edges.map(edge => {
                let updatedEdge = { ...edge };
                if (edge.source === id) {
                    updatedEdge.source = newId;
                }
                if (edge.target === id) {
                    updatedEdge.target = newId;
                }
                // Update edge ID if it was based on source-target pattern
                if (updatedEdge.source !== edge.source || updatedEdge.target !== edge.target) {
                    updatedEdge.id = `e${updatedEdge.source}-${updatedEdge.target}`;
                }
                return updatedEdge;
            });
            
            // Update the node itself with new ID
            $nodes = $nodes.map(node => {
                if (node.id === id) {
                    return { ...node, id: newId, data: { ...node.data, label } };
                }
                return node;
            });
        }
    }
    
    function updateDescription(e: Event) {
        const description = (e.target as HTMLTextAreaElement).value;
        updateNodeData(id, { description });
    }

    let isDragOver = $state(false);

    function onDrop(event: DragEvent) {
        event.preventDefault();
        event.stopPropagation(); // Stop bubbling to canvas
        event.stopImmediatePropagation();
        isDragOver = false;
        
        const json = event.dataTransfer?.getData('application/dbt-model');
        if (!json) return;
        const model: DbtModel = JSON.parse(json);
        
        // Store the full unique_id (e.g. "model.elmo.entity_booking")
        const updates: Record<string, unknown> = { dbt_model: model.unique_id };
        const hasDescription = (data.description || '').trim().length > 0;
        if (!hasDescription && (model.description || '').trim().length > 0) {
            updates.description = model.description;
        }
        
        updateNodeData(id, updates);
    }
    
    function onDragOver(event: DragEvent) {
        event.preventDefault(); // Essential to allow drop
        if (event.dataTransfer) {
            event.dataTransfer.dropEffect = 'copy';
        }
    }
    
    function onDragEnter(event: DragEvent) {
        event.preventDefault();
        isDragOver = true;
    }

    function onDragLeave(event: DragEvent) {
        isDragOver = false;
    }

    function startDimensionResize(event: PointerEvent, type: 'width' | 'height') {
        event.stopPropagation();
        event.preventDefault();

        const startX = event.clientX;
        const startY = event.clientY;
        const initialWidth = nodeWidth;
        const initialHeight = columnPanelHeight;

        function onMove(moveEvent: PointerEvent) {
            if (type === 'width') {
                const delta = moveEvent.clientX - startX;
                const next = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, initialWidth + delta));
                updateNodeData(id, { width: next });
            } else {
                const delta = moveEvent.clientY - startY;
                const next = Math.min(MAX_PANEL_HEIGHT, Math.max(MIN_PANEL_HEIGHT, initialHeight + delta));
                updateNodeData(id, { panelHeight: next });
            }
        }

        function onUp() {
            window.removeEventListener('pointermove', onMove);
            window.removeEventListener('pointerup', onUp);
        }

        window.addEventListener('pointermove', onMove);
        window.addEventListener('pointerup', onUp);
    }
    
    function unbind() {
        updateNodeData(id, { dbt_model: null });
    }
    
    function toggleCollapse(event: MouseEvent) {
        // Only toggle if clicking on the header background, not on the input
        if ((event.target as HTMLElement).tagName === 'INPUT') {
            return;
        }
        updateNodeData(id, { collapsed: !isCollapsed });
    }
</script>

<div 
    class="rounded-md border-2 bg-white shadow-sm transition-all hover:shadow-md relative"
    class:border-green-500={isBound}
    class:border-blue-500={isDragOver}
    class:border-gray-300={!isBound && !isDragOver}
    class:ring-2={isDragOver}
    class:ring-blue-200={isDragOver}
    style={`width:${nodeWidth}px`}
    ondrop={onDrop}
    ondragover={onDragOver}
    ondragenter={onDragEnter}
    ondragleave={onDragLeave}
    role="presentation"
>
    <Handle type="target" position={Position.Top} class="!bg-gray-400 !w-3 !h-3" />
    
    <!-- Header -->
    <div 
        class="p-2 border-b border-gray-100 bg-gray-50 rounded-t-md flex justify-between items-center cursor-pointer hover:bg-gray-100 transition-colors"
        onclick={toggleCollapse}
        title={isCollapsed ? "Click to expand" : "Click to collapse"}
    >
        <div class="flex items-center gap-1 flex-1 min-w-0">
            <span class="text-gray-500 text-xs flex-shrink-0 select-none transition-transform" style={`transform: rotate(${isCollapsed ? 0 : 90}deg)`}>
                ▶
            </span>
            <input 
                value={data.label} 
                oninput={updateLabel}
                onblur={updateIdFromLabel}
                onclick={(e) => e.stopPropagation()}
                class="font-bold bg-transparent w-full focus:outline-none focus:bg-white focus:ring-1 focus:ring-blue-300 rounded px-1 text-sm"
                placeholder="Entity Name"
            />
        </div>
        {#if isBound}
            <div class="w-2 h-2 rounded-full bg-green-500 ml-2 flex-shrink-0" title="Bound to {boundModelName}"></div>
        {/if}
    </div>

    <!-- Body -->
    {#if !isCollapsed}
    <div class="p-2">
        {#if $viewMode === 'physical' && isBound && modelDetails}
            <div class="text-xs">
                <div class="font-mono text-gray-600 mb-2 bg-gray-100 p-1 rounded break-all">
                    {modelDetails.schema}.{modelDetails.table}
                </div>
                {#if modelDetails.materialization}
                    <div class="mb-2 text-gray-500">
                        <span class="font-medium">Materialization:</span> 
                        <span class="ml-1 px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded text-[10px] font-semibold uppercase">
                            {modelDetails.materialization}
                        </span>
                    </div>
                {/if}
                <div class="overflow-y-auto border rounded bg-gray-50 p-1 scrollbar-thin" style={`max-height:${columnPanelHeight}px`}>
                    {#each modelDetails.columns as col}
                        <div class="flex justify-between py-1 border-b border-gray-200 last:border-0">
                            <span class="font-medium text-gray-700 truncate pr-2" title={col.name}>{col.name}</span>
                            <span class="text-gray-400 text-[10px] uppercase">{col.type}</span>
                        </div>
                    {/each}
                </div>
                <button 
                    class="mt-2 w-full text-xs text-red-500 hover:bg-red-50 p-1 rounded border border-red-100 transition-colors"
                    onclick={unbind}
                >
                    Unbind Model
                </button>
            </div>
        {:else}
            <!-- Concept View -->
             <textarea 
                value={data.description || ''} 
                oninput={updateDescription}
                class="w-full text-xs text-gray-600 resize-y min-h-[60px] focus:outline-none focus:bg-gray-50 focus:ring-1 focus:ring-blue-300 rounded p-1"
                placeholder="Description..."
            ></textarea>
            {#if isBound}
                 <div class="mt-2 text-xs text-green-600 flex items-center justify-between bg-green-50 p-1 rounded border border-green-100">
                    <span class="truncate font-medium" title={boundModelName}>🔗 {boundModelName}</span>
                    <button onclick={unbind} class="text-red-400 hover:text-red-600 ml-1 px-1">×</button>
                 </div>
            {:else}
                <div class="mt-2 text-[10px] text-gray-400 text-center border border-dashed border-gray-300 rounded p-2 bg-gray-50 pointer-events-none">
                    Drag dbt model here
                </div>
            {/if}
        {/if}
    </div>
    {/if}

    <Handle type="source" position={Position.Bottom} class="!bg-gray-400 !w-3 !h-3" />

    <div 
        class="width-resize-handle"
        onpointerdown={(event) => startDimensionResize(event, 'width')}
        title="Drag to resize width"
    ></div>

    {#if $viewMode === 'physical'}
        <div 
            class="height-resize-handle"
            onpointerdown={(event) => startDimensionResize(event, 'height')}
            title="Drag to show more columns"
        ></div>
    {/if}
</div>

<style>
    .width-resize-handle {
        position: absolute;
        top: 0;
        right: -3px;
        width: 6px;
        height: 100%;
        cursor: col-resize;
        border-radius: 999px;
    }

    .width-resize-handle:hover,
    .height-resize-handle:hover {
        background: rgba(59, 130, 246, 0.3);
    }

    .height-resize-handle {
        position: absolute;
        bottom: -3px;
        left: 0;
        width: 100%;
        height: 6px;
        cursor: row-resize;
        border-radius: 999px;
    }
</style>

