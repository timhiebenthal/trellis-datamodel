<script lang="ts">
    type Props = {
        // 'entity' = entity_model compact form, 'dimension' = dimensional_model form with hint
        variant: 'entity' | 'dimension';
        name: string;
        loading: boolean;
        onSubmit: () => void;
        onCancel: () => void;
    };

    let { variant, name = $bindable(), loading, onSubmit, onCancel }: Props = $props();
</script>

{#if variant === 'entity'}
    <div class="mt-2 space-y-1 border-l-2 border-blue-200 pl-3">
        <label class="text-xs font-medium text-gray-600">Create new entity</label>
        <div class="flex items-center gap-2">
            <input
                type="text"
                bind:value={name}
                placeholder="e.g., Employee, Project"
                class="flex-1 px-2 py-1 border border-gray-300 rounded text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                disabled={loading}
                onkeydown={(e) => {
                    if (e.key === 'Enter') onSubmit();
                    else if (e.key === 'Escape') onCancel();
                }}
            />
            <button type="button" onclick={onSubmit} disabled={!name.trim() || loading} class="px-2 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed">Create</button>
            <button type="button" onclick={onCancel} class="px-2 py-1 bg-gray-200 text-gray-700 rounded text-xs hover:bg-gray-300" disabled={loading}>Cancel</button>
        </div>
    </div>
{:else}
    <!-- Create new dimension inline -->
    <div class="space-y-2">
        <label class="text-xs font-medium text-gray-600">
            Create new dimension
        </label>
        <div class="flex items-center gap-2">
            <input
                type="text"
                bind:value={name}
                placeholder="e.g., Employee, Date, Location"
                class="flex-1 px-2 py-1 border border-gray-300 rounded text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
                disabled={loading}
                onkeydown={(e) => {
                    if (e.key === 'Enter') {
                        onSubmit();
                    } else if (e.key === 'Escape') {
                        onCancel();
                    }
                }}
            />
            <button
                type="button"
                onclick={onSubmit}
                disabled={!name.trim() || loading}
                class="px-2 py-1 bg-blue-600 text-white rounded text-xs hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
                Create
            </button>
            <button
                type="button"
                onclick={onCancel}
                class="px-2 py-1 bg-gray-200 text-gray-700 rounded text-xs hover:bg-gray-300"
                disabled={loading}
            >
                Cancel
            </button>
        </div>
        <p class="text-xs text-gray-500 italic">
            Press Enter to create, Escape to cancel
        </p>
    </div>
{/if}
