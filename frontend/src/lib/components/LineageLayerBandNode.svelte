<script lang="ts">
    import type { NodeProps } from "@xyflow/svelte";

    let { data }: NodeProps = $props();

    const label = $derived((data?.label as string) || "");
    const width = $derived((data?.width as number | undefined) ?? 1200);
    const height = $derived((data?.height as number | undefined) ?? 220);
</script>

<!--
  A background "band" node used to visualize lineage layers.
  This node should be created with draggable/selectable disabled and a low zIndex.
-->
<div
    class="rounded-md border border-gray-200 bg-gray-50/60"
    style={`pointer-events: none; width: ${width}px; height: ${height}px;`}
    aria-hidden="true"
>
    <div class="px-3 py-2 text-xs font-medium text-gray-600 select-none">
        {label}
    </div>
</div>


