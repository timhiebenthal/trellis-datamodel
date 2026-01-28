<script lang="ts">
    import Icon from "@iconify/svelte";

    type Props = {
        processName: string;
        processId?: string;
        size?: "small" | "medium";
        onclick?: () => void;
    };

    let { processName, processId, size = "medium", onclick }: Props = $props();

    const sizeClasses = $derived(
        size === "small" ? "px-1.5 py-0.5 text-xs" : "px-2 py-1 text-xs"
    );
    const iconSize = $derived(size === "small" ? "w-3 h-3" : "w-3.5 h-3.5");
</script>

{#if onclick}
    <button
        onclick={onclick}
        class="inline-flex items-center gap-1.5 bg-indigo-100 text-indigo-700 border border-indigo-300 rounded font-medium hover:opacity-80 transition-opacity {sizeClasses} focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-indigo-400"
        title={processId ? `Process: ${processName} (${processId})` : `Process: ${processName}`}
    >
        <Icon icon="lucide:layers" class={iconSize} />
        <span>{processName}</span>
    </button>
{:else}
    <span
        class="inline-flex items-center gap-1.5 bg-indigo-100 text-indigo-700 border border-indigo-300 rounded font-medium {sizeClasses}"
        title={processId ? `Process: ${processName} (${processId})` : `Process: ${processName}`}
    >
        <Icon icon="lucide:layers" class={iconSize} />
        <span>{processName}</span>
    </span>
{/if}
