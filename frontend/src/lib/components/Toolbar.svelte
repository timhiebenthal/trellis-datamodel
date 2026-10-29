<script lang="ts">
    import Icon from "$lib/components/Icon.svelte";
    import type { FrameworkCopy } from "$lib/utils/framework-display";

    let {
        syncMessage,
        loading,
        syncing,
        needsSync,
        allExpanded,
        showAutoLayout,
        frameworkCopy,
        onToggleAll,
        onAutoLayout,
        onPull,
        onPush,
    }: {
        syncMessage: string | null;
        loading: boolean;
        syncing: boolean;
        needsSync: boolean;
        allExpanded: boolean;
        showAutoLayout: boolean;
        frameworkCopy: FrameworkCopy;
        onToggleAll: () => void;
        onAutoLayout: () => void;
        onPull: () => void;
        onPush: () => void;
    } = $props();
</script>

<!-- Actions -->
<div class="flex items-center gap-3">
    {#if syncMessage}
        <div class="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-gray-50 border border-gray-200">
            {#if syncMessage.startsWith("✓")}
                <div class="w-2 h-2 rounded-full bg-success-500"></div>
                <span class="text-xs font-medium text-success-700">{syncMessage.substring(2)}</span>
            {:else if syncMessage.startsWith("✗")}
                <div class="w-2 h-2 rounded-full bg-danger-500"></div>
                <span class="text-xs font-medium text-danger-700">{syncMessage.substring(2)}</span>
            {:else}
                <span class="text-xs text-gray-600">{syncMessage}</span>
            {/if}
        </div>
    {/if}

    <div class="h-6 w-px bg-gray-200 mx-1"></div>

    <button
        onclick={() => {
            // Directly navigate to config page
            window.location.href = '/config';
        }}
        class="px-2.5 py-1.5 text-xs rounded-md font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 transition-colors flex items-center gap-1.5 shadow-sm"
        title="Go to configuration page"
    >
        <Icon icon="lucide:settings" class="w-3.5 h-3.5" />
        Config info
    </button>

    <button
        onclick={onToggleAll}
        disabled={loading}
        class="px-2.5 py-1.5 text-xs rounded-md font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 transition-colors disabled:opacity-50 flex items-center gap-1.5 shadow-sm"
        title={allExpanded ? "Collapse all entities" : "Expand all entities"}
        aria-label={allExpanded ? "Collapse all entities" : "Expand all entities"}
    >
        {#if allExpanded}
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" class="w-3.5 h-3.5">
                <path d="m7.4 21.308l-.708-.708L12 15.292l5.308 5.308l-.708.708l-4.6-4.6zm4.6-12.6L6.692 3.4l.708-.708l4.6 4.6l4.6-4.6l.708.708z"/>
            </svg>
        {:else}
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" class="w-3.5 h-3.5">
                <path d="M12 21.308L6.692 16l.714-.713L12 19.842l4.594-4.555l.714.713zm-4.588-12.6L6.692 8L12 2.692L17.308 8l-.72.708L12 4.158z"/>
            </svg>
        {/if}
    </button>

    {#if showAutoLayout}
        <button
            onclick={onAutoLayout}
            disabled={loading}
            class="px-2.5 py-1.5 text-xs rounded-md font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 transition-colors disabled:opacity-50 flex items-center gap-1.5 shadow-sm"
            title="Arrange entities by fact/dimension positioning"
        >
            <Icon icon="lucide:wand-2" class="w-3.5 h-3.5" />
            Auto Layout
        </button>
    {/if}

    <button
        onclick={onPull}
        disabled={syncing || loading}
        class="px-2.5 py-1.5 text-xs rounded-md font-medium text-white bg-primary-600 border border-transparent hover:bg-primary-50 hover:text-primary-700 transition-colors disabled:opacity-50 flex items-center gap-1.5 shadow-sm"
        title={frameworkCopy.pullTooltip}
    >
        <Icon icon="lucide:download" class="w-3.5 h-3.5" />
        {frameworkCopy.pullLabel}
    </button>

    <button
        onclick={onPush}
        disabled={syncing || loading}
        class="px-2.5 py-1.5 text-xs rounded-md font-medium text-white border border-transparent transition-colors disabled:opacity-50 flex items-center gap-1.5 shadow-sm relative"
        class:bg-primary-600={!needsSync}
        class:hover:bg-primary-700={!needsSync}
        class:bg-amber-600={needsSync}
        class:hover:bg-amber-700={needsSync}
        class:animate-pulse={needsSync}
        title={needsSync
            ? frameworkCopy.pushDirtyTooltip
            : frameworkCopy.pushCleanTooltip}
    >
        {#if syncing}
            <Icon icon="lucide:loader-2" class="w-3.5 h-3.5 animate-spin" />
        {:else}
            <Icon icon="lucide:upload" class="w-3.5 h-3.5" />
        {/if}
        {frameworkCopy.pushLabel}
        {#if needsSync && !syncing}
            <span class="absolute -top-1 -right-1 flex h-2.5 w-2.5">
                <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                <span class="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-500"></span>
            </span>
        {/if}
    </button>
</div>
