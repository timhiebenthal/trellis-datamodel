<script lang="ts">
    import {
        Handle,
        Position,
        type NodeProps,
    } from "@xyflow/svelte";
    import { nodes, edges } from "$lib/stores";
    import Icon from "@iconify/svelte";

    let { data, id, selected }: NodeProps = $props();

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

        // `$nodes` is the source of truth: Canvas re-derives its bound
        // `displayNodes` from `$nodes` on every change, so a size written to the
        // display store alone is reverted before the reverse sync can copy it back
        // (#140). Mark as manually resized so the auto-fit pass leaves it alone.
        $nodes = $nodes.map(n => n.id === id
            ? { ...n, data: { ...n.data, manuallyResized: true } }
            : n);

        const startX = event.clientX;
        const startY = event.clientY;
        const initialWidth = nodeWidth;
        const initialHeight = nodeHeight;

        function onMove(moveEvent: PointerEvent) {
            let next: number;
            if (type === "width") {
                const delta = moveEvent.clientX - startX;
                next = Math.min(
                    MAX_WIDTH,
                    Math.max(MIN_WIDTH, initialWidth + delta),
                );
            } else {
                const delta = moveEvent.clientY - startY;
                next = Math.min(
                    MAX_HEIGHT,
                    Math.max(MIN_HEIGHT, initialHeight + delta),
                );
            }

            // Write the new size into `$nodes` in the same pass as the child
            // touches, otherwise the re-derivation drops it (#140).
            $nodes = $nodes.map(n => {
                if (n.id === id) {
                    return {
                        ...n,
                        data: {
                            ...n.data,
                            ...(type === "width" ? { width: next } : { height: next }),
                            manuallyResized: true,
                        },
                    };
                }
                // Force nodes store update to trigger edge recalculation
                // Touch child nodes to ensure edges re-render
                if (n.parentId === id) {
                    return { ...n };
                }
                return n;
            });
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
        // Derive the current state from $nodes (the source of truth) so a stale
        // prop can never invert the toggle.
        const currentCollapsed =
            $nodes.find(n => n.id === id)?.data?.collapsed ?? isCollapsed;
        const newCollapsed = !currentCollapsed;

        // Get child node IDs
        const childIds = new Set($nodes.filter(n => n.parentId === id).map(n => n.id));

        // Persist the group's own collapsed state and hide/show children in a
        // single $nodes pass, since $nodes is re-derived into the display store.
        $nodes = $nodes.map(n => {
            if (n.id === id) {
                return { ...n, data: { ...n.data, collapsed: newCollapsed } };
            }
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
        class="group-node rounded-xl border border-primary-600/10 bg-primary-500/[0.03] shadow-[inset_0_1px_0_0_rgba(255,255,255,0.4)] relative"
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
            class="width-resize-handle nodrag nopan"
            onpointerdown={(event) => startDimensionResize(event, "width")}
            title="Drag to resize width"
        ></div>
        <div
            class="height-resize-handle nodrag nopan"
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
