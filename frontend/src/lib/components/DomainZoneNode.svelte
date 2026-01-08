<script lang="ts">
    import { useSvelteFlow, type NodeProps } from "@xyflow/svelte";
    import { nodes } from "$lib/stores";
    import Icon from "@iconify/svelte";

    let { data, id, selected }: NodeProps = $props();

    const { updateNodeData } = useSvelteFlow();
    let isCollapsed = $derived(data.collapsed ?? false);

    // Resize constants
    const DEFAULT_WIDTH = 400;
    const DEFAULT_HEIGHT = 300;
    const MIN_WIDTH = 300;
    const MAX_WIDTH = 1400;
    const MIN_HEIGHT = 200;
    const MAX_HEIGHT = 1000;
    let nodeWidth: number = $derived((data.width as number | undefined) ?? DEFAULT_WIDTH);
    let nodeHeight: number = $derived((data.height as number | undefined) ?? DEFAULT_HEIGHT);

    function startDimensionResize(
        event: PointerEvent,
        type: "width" | "height"
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
                    Math.max(MIN_WIDTH, initialWidth + delta)
                );
                updateNodeData(id, { width: next, manuallyResized: true });
            } else {
                const delta = moveEvent.clientY - startY;
                const next = Math.min(
                    MAX_HEIGHT,
                    Math.max(MIN_HEIGHT, initialHeight + delta)
                );
                updateNodeData(id, { height: next, manuallyResized: true });
            }

            // Force nodes store update to trigger edge recalculation
            $nodes = $nodes.map(n => n.parentId === id ? { ...n } : n);
        }

        function onUp() {
            window.removeEventListener("pointermove", onMove);
            window.removeEventListener("pointerup", onUp);
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
        const edges = $nodes[0]?.__svelte_flow_edges || [];
        edges = edges.map(e => {
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

    // Get domain color or use default
    let domainColor = $derived(data.color || "#8b5cf6");
</script>

{#if isCollapsed}
    <!-- Compact badge when collapsed -->
    <div
        class="inline-flex items-center gap-1.5 px-2 py-1 border rounded cursor-pointer transition-colors text-xs shadow-sm"
        style={`background-color: ${domainColor}20; border-color: ${domainColor}60;`}
        onclick={toggleCollapse}
        onkeydown={handleCollapseKeydown}
        role="button"
        tabindex="0"
    >
        <Icon icon="lucide:chevron-right" class="w-3 h-3" style="color: {domainColor};" />
        <Icon icon="lucide:layers" class="w-3 h-3" style="color: {domainColor};" />
        <span class="font-medium">{data.label || id}</span>
        <span class="px-1 rounded text-[10px]" style="background-color: {domainColor}60;">{childCount}</span>
    </div>
{:else}
    <!-- Full container when expanded -->
    <div
        class="domain-zone-node rounded-xl border relative"
        style={`width:${nodeWidth}px; height:${nodeHeight}px; background-color: ${domainColor}10; border-color: ${domainColor}40;`}
    >
        <div
            class="flex items-center gap-2 px-4 py-3.5 cursor-pointer hover:opacity-80 transition-opacity rounded-t-xl"
            style="background-color: {domainColor}30;"
            onclick={toggleCollapse}
            onkeydown={handleCollapseKeydown}
            role="button"
            tabindex="0"
        >
            <Icon icon="lucide:chevron-down" class="w-4 h-4" style="color: {domainColor};" />
            <Icon icon="lucide:layers" class="w-4 h-4" style="color: {domainColor};" />
            <span class="font-bold text-base" style="color: {domainColor};">{data.label || id}</span>
            <span class="px-2 py-1 rounded text-xs font-medium" style="background-color: {domainColor}60; color: {domainColor};">{childCount}</span>
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
    :global(.svelte-flow__node-domain-zone) {
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
        background: rgba(139, 92, 246, 0.3);
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

