<script lang="ts">
	import Icon from '@iconify/svelte';
	import type { EntityRelationshipRow } from '$lib/utils/entity-detail';

	let {
		relationships,
		onOpenRelatedEntity
	}: {
		relationships: EntityRelationshipRow[];
		onOpenRelatedEntity: (entityId: string) => void;
	} = $props();
</script>

<!-- Relationships (read-only, click an entity to navigate) -->
<div>
	<label class="block text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wide">
		Relationships ({relationships.length})
	</label>
	<div class="space-y-2">
	{#each relationships as rel (rel.edgeId)}
		<div class="px-3.5 py-2.5 bg-white border border-gray-200 rounded-lg shadow-2xs hover:border-gray-300 transition-colors">
			<div class="flex items-center gap-2 flex-wrap">
				<Icon
					icon={rel.isOutgoing ? 'lucide:arrow-right' : 'lucide:arrow-left'}
					class="w-4 h-4 text-gray-400 shrink-0"
				/>
				<button
					type="button"
					onclick={() => onOpenRelatedEntity(rel.relatedId)}
					class="text-sm font-semibold text-primary-700 hover:text-primary-900 hover:underline focus:outline-none focus:ring-2 focus:ring-primary-500 rounded"
				>
					{rel.relatedName}
				</button>
				<span class="text-xs text-gray-500 font-medium">
					({rel.cardinality}, {rel.isOutgoing ? 'Outgoing' : 'Incoming'})
				</span>
			</div>
			{#if rel.keys}
				<div class="mt-1 ml-6 font-mono text-xs text-gray-600">{rel.keys}</div>
			{:else if rel.label}
				<div class="mt-1 ml-6 text-xs text-gray-500 italic">{rel.label}</div>
			{/if}
		</div>
	{/each}
	</div>
</div>
