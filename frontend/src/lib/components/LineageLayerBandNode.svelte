<script lang="ts">
    import type { NodeProps } from "@xyflow/svelte";

    let { data }: NodeProps = $props();

    const label = $derived((data?.label as string) || "");
    const width = $derived((data?.width as number | undefined) ?? 100000);
    const height = $derived((data?.height as number | undefined) ?? 220);
    // labelX aligns the text with the start of your actual nodes
    const labelX = $derived((data?.labelX as number) ?? 0);
</script>

<!--
  A background "band" node used to visualize lineage layers.
  This node should be created with draggable/selectable disabled and a low zIndex.
  Uses infinite width to create seamless horizontal strips across the canvas.
-->
<div
    class="border-y border-primary-600/10 bg-primary-500/[0.03] shadow-[inset_0_1px_0_0_rgba(255,255,255,0.4)]"
    style={`pointer-events: none; width: ${width}px; height: ${height}px;`}
    aria-hidden="true"
>
    <!-- Technical Label -->
    <div class="pt-4 select-none" style={`padding-left: ${labelX}px`}>
        <span class="text-[10px] font-bold text-primary-700/50 uppercase tracking-[0.3em]">
            {label}
        </span>
    </div>
</div>


