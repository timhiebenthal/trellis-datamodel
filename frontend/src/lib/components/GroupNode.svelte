<script lang="ts">
    import {
        Handle,
        Position,
        useSvelteFlow,
        type NodeProps,
    } from "@xyflow/svelte";
    import { nodes, edges } from "$lib/stores";
    import Icon from "@iconify/svelte";

    let { data, id, selected }: NodeProps = $props();

    const { updateNodeData } = useSvelteFlow();
    let isCollapsed = $derived(data.collapsed ?? false);

    // Resize constants
    const DEFAULT_WIDTH = 300;
    const DEFAULT_HEIGHT = 200;
    const MIN_WIDTH = 200;
    const MAX_WIDTH = 1200;
    const MIN_HEIGHT = 150;
    const MAX_HEIGHT = 900;
    let nodeWidth: number = $derived((data.width as number | undefined) ?? DEFAULT_WIDTH);
    let nodeHeight: number = $derived((data.height as number | undefined) ?? DEFAULT_HEIGHT);

    function startDimensionResize(
        event: PointerEvent,
        type: "width" | "height",
    ) {
        event.stopPropagation();
        event.preventDefault();

        // Mark as manually resized to prevent auto-resize from overriding
        updateNodeData(id, { manuallyResized: true });

        const startX = event.clientX;
        const startY = event.clientY;
        const initialWidth = nodeWidth;
        const initialHeight = nodeHeight;

        function onMove(moveEvent: PointerEvent) {
            if (type === "width") {
                const delta = moveEvent.clientX - startX;
                const next = Math.min(
                    MAX_WIDTH,
                    Math.max(MIN_WIDTH, initialWidth + delta),
                );
                updateNodeData(id, { width: next, manuallyResized: true });
            } else {
                const delta = moveEvent.clientY - startY;
                const next = Math.min(
                    MAX_HEIGHT,
                    Math.max(MIN_HEIGHT, initialHeight + delta),
                );
                updateNodeData(id, { height: next, manuallyResized: true });
            }
            
            // Force nodes store update to trigger edge recalculation
            // Touch child nodes to ensure edges re-render
            $nodes = $nodes.map(n => n.parentId === id ? { ...n } : n);
        }

        function onUp() {
            window.removeEventListener("pointermove", onMove);
            window.removeEventListener("pointerup", onUp);
            // Final update to ensure edges are correct
            $nodes = [...$nodes];
        }

        window.addEventListener("pointermove", onMove);
        window.addEventListener("pointerup", onUp);
    }

    function toggleCollapse() {
        const newCollapsed = !isCollapsed;
        updateNodeData(id, { collapsed: newCollapsed });
        
        // Get child node IDs
        const childIds = new Set($nodes.filter(n => n.parentId === id).map(n => n.id));
        
        // Hide/show child nodes
        $nodes = $nodes.map(n => {
            if (n.parentId === id) {
                return { ...n, hidden: newCollapsed };
            }
            return n;
        });
        
        // Hide/show edges connected to child nodes
        $edges = $edges.map(e => {
            if (childIds.has(e.source) || childIds.has(e.target)) {
                return { ...e, hidden: newCollapsed };
            }
            return e;
        });
    }

    function handleCollapseKeydown(event: KeyboardEvent) {
        if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            toggleCollapse();
        }
    }

    // Count children
    let childCount = $derived(
        $nodes.filter(n => n.parentId === id).length
    );
</script>

{#if isCollapsed}
    <!-- Compact badge when collapsed -->
    <div
        class="inline-flex items-center gap-1.5 px-2 py-1 bg-gray-200 hover:bg-gray-300 border border-gray-300 rounded cursor-pointer transition-colors text-xs shadow-sm"
        onclick={toggleCollapse}
        onkeydown={handleCollapseKeydown}
        role="button"
        tabindex="0"
    >
        <Icon icon="lucide:chevron-right" class="w-3 h-3 text-gray-600" />
        <Icon icon="lucide:folder" class="w-3 h-3 text-gray-600" />
        <span class="font-medium text-gray-800">{data.label || id}</span>
        <span class="text-gray-700 bg-gray-300 px-1 rounded text-[10px]">{childCount}</span>
    </div>
{:else}
    <!-- Full container when expanded -->
    <div
        class="group-node rounded-xl bg-gray-200/50 border border-gray-300 relative"
        style={`width:${nodeWidth}px; height:${nodeHeight}px;`}
    >
        <div
            class="flex items-center gap-2 px-4 py-3.5 cursor-pointer hover:bg-gray-200/70 transition-colors rounded-t-xl"
            onclick={toggleCollapse}
            onkeydown={handleCollapseKeydown}
            role="button"
            tabindex="0"
        >
            <Icon icon="lucide:chevron-down" class="w-4 h-4 text-gray-600" />
            <Icon icon="lucide:folder" class="w-4 h-4 text-gray-600" />
            <span class="font-bold text-base text-gray-800">{data.label || id}</span>
            <span class="text-gray-700 bg-gray-300/80 px-2 py-1 rounded text-xs font-medium">{childCount}</span>
        </div>
        <div
            class="width-resize-handle"
            onpointerdown={(event) => startDimensionResize(event, "width")}
            title="Drag to resize width"
        ></div>
        <div
            class="height-resize-handle"
            onpointerdown={(event) => startDimensionResize(event, "height")}
            title="Drag to resize height"
        ></div>
    </div>
{/if}

<style>
    /* Override Svelte Flow's default node wrapper border */
    :global(.svelte-flow__node-group) {
        border: none !important;
        background: transparent !important;
        box-shadow: none !important;
        width: auto !important;
        height: auto !important;
    }

    .width-resize-handle {
        position: absolute;
        top: 0;
        right: -3px;
        width: 6px;
        height: 100%;
        cursor: ew-resize;
        border-radius: 999px;
        z-index: 10;
        pointer-events: auto;
    }

    .width-resize-handle:hover,
    .height-resize-handle:hover {
        background: rgba(38, 166, 154, 0.2);
    }

    .height-resize-handle {
        position: absolute;
        bottom: -3px;
        left: 0;
        width: 100%;
        height: 6px;
        cursor: ns-resize;
        border-radius: 999px;
        z-index: 10;
        pointer-events: auto;
    }
</style>
