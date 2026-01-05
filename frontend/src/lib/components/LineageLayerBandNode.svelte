<script lang="ts">
    import type { NodeProps } from "@xyflow/svelte";

    let { data }: NodeProps = $props();

    const label = $derived((data?.label as string) || "");
    const width = $derived((data?.width as number | undefined) ?? 100000);
    const height = $derived((data?.height as number | undefined) ?? 220);
    // labelX aligns the text with the start of your actual nodes
    const labelX = $derived((data?.labelX as number) ?? 0);
    
    const isUnassigned = $derived(label === "Unassigned");
    
    const bandClasses = $derived(
        `border-y shadow-[inset_0_1px_0_0_rgba(255,255,255,0.4)] ${
            isUnassigned
                ? "border-gray-300/20 bg-gray-100/30"
                : "border-primary-600/10 bg-primary-500/[0.03]"
        }`
    );
    
    const labelClasses = $derived(
        `text-[10px] font-bold uppercase tracking-[0.3em] ${
            isUnassigned ? "text-gray-500/60" : "text-primary-700/50"
        }`
    );
</script>

<!--
  A background "band" node used to visualize lineage layers.
  This node should be created with draggable/selectable disabled and a low zIndex.
  Uses infinite width to create seamless horizontal strips across the canvas.
-->
<div
    class={bandClasses}
    style={`pointer-events: none; width: ${width}px; height: ${height}px;`}
    aria-hidden="true"
>
    <!-- Technical Label -->
    <div class="pt-4 select-none" style={`padding-left: ${labelX}px`}>
        <span class={labelClasses}>
            {label}
        </span>
    </div>
</div>


