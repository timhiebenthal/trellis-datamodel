<script lang="ts">
    import { normalizeTags } from '$lib/utils';

    let { tags = [], canEdit = true, isBatchMode = false, onUpdate }: {
        tags?: string[];
        canEdit?: boolean;
        isBatchMode?: boolean;
        onUpdate: (newTags: string[]) => void;
    } = $props();

    let tagInput = $state('');
    let showTagInput = $state(false);

    let normalizedTags = $derived(normalizeTags(tags));

    function handleAddTag(tag: string) {
        const trimmed = tag.trim();
        if (!trimmed) return;

        if (normalizedTags.includes(trimmed)) return;

        const newTags = [...normalizedTags, trimmed];
        onUpdate(newTags);
        tagInput = '';
    }

    function handleRemoveTag(tag: string) {
        const newTags = normalizedTags.filter((t) => t !== tag);
        onUpdate(newTags);
    }

    function handleTagInputKeydown(e: KeyboardEvent) {
        if (e.key === 'Enter') {
            e.preventDefault();
            if (tagInput.trim()) {
                handleAddTag(tagInput);
            }
        } else if (e.key === 'Escape') {
            tagInput = '';
            showTagInput = false;
        } else if (e.key === ',') {
            e.preventDefault();
            const parts = tagInput.split(',');
            parts.forEach((part) => {
                if (part.trim()) {
                    handleAddTag(part.trim());
                }
            });
            tagInput = '';
        }
    }

    function handleTagInputBlur() {
        if (tagInput.trim()) {
            handleAddTag(tagInput);
        }
        showTagInput = false;
    }

    function handleInputFocus() {
        showTagInput = true;
    }
</script>

<div class="tag-editor flex flex-wrap gap-1">
    {#each normalizedTags as tag}
        <div
            class="tag flex items-center gap-1 px-2 py-0.5 bg-blue-50 text-blue-700 text-xs rounded group"
        >
            {tag}
            {#if canEdit}
                <button
                    onmousedown={(e) => e.preventDefault()}
                    onclick={() => handleRemoveTag(tag)}
                    class="opacity-0 group-hover:opacity-100 transition-opacity text-blue-500 hover:text-blue-700 focus:opacity-100 focus:outline-none"
                    title={isBatchMode ? 'Remove tag from all selected' : 'Remove tag'}
                    aria-label={isBatchMode ? `Remove ${tag} tag from all selected` : `Remove ${tag} tag`}
                >
                    <svg xmlns="http://www.w3.org/2000/svg" class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            {/if}
        </div>
    {/each}

    {#if canEdit}
        {#if showTagInput}
            <input
                type="text"
                bind:value={tagInput}
                onkeydown={handleTagInputKeydown}
                onblur={handleTagInputBlur}
                placeholder={isBatchMode ? 'Enter tag for all selected (comma or Enter)' : 'Enter tag (comma or Enter to add)'}
                class="tag-input w-full min-w-[120px] max-w-[200px] px-1.5 py-0.5 text-[10px] text-gray-800 bg-white border border-blue-200 rounded focus:outline-none focus:ring-1 focus:ring-blue-400"
                aria-label="Add new tag"
            />
        {:else}
            <button
                onmousedown={(e) => e.preventDefault()}
                onclick={() => {
                    showTagInput = true;
                    // Focus the input on next tick after it's rendered
                    setTimeout(() => {
                        const input = document.querySelector('.tag-input') as HTMLInputElement;
                        if (input) input.focus();
                    }, 0);
                }}
                class="px-2 py-0.5 bg-blue-50 text-blue-500 text-xs rounded hover:bg-blue-100 transition-colors focus:outline-none focus:ring-1 focus:ring-blue-400"
                title="Add tag"
                aria-label="Add new tag"
            >
                <svg xmlns="http://www.w3.org/2000/svg" class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4" />
                </svg>
            </button>
        {/if}
    {/if}
</div>

<style>
    .tag-editor :global(.tag-input) {
        /* Ensure input doesn't cause layout shifts */
        box-sizing: border-box;
    }
</style>
