<script lang="ts">
    import { BaseEdge, getBezierPath, type EdgeProps } from "@xyflow/svelte";
    import { METRIC_ACCENT } from "$lib/utils/metric-graph";

    let {
        selected = false,
        sourceX,
        sourceY,
        targetX,
        targetY,
        sourcePosition,
        targetPosition,
        markerEnd,
    }: EdgeProps = $props();

    // A claim about direction, not a formula: no label, no cardinality, just an
    // arrow from the driver onto the metric it moves.
    const [path] = $derived(
        getBezierPath({
            sourceX,
            sourceY,
            sourcePosition,
            targetX,
            targetY,
            targetPosition,
        }),
    );

    const strokeStyle = $derived(
        selected
            ? `stroke: ${METRIC_ACCENT}; stroke-width: 2.5;`
            : `stroke: #c4b5fd; stroke-width: 1.75;`,
    );
</script>

<BaseEdge path={path} {markerEnd} style={strokeStyle} class="metric-influence-edge" />
