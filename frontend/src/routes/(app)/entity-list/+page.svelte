<script lang="ts">
	import { nodes, entityListFilters, bulkEditModal } from '$lib/stores';
	import type { EntityData } from '$lib/types';
	import { filterEntities } from '$lib/utils/entity-filtering';
	import EntityList from '$lib/components/EntityList.svelte';
	import EntityListFilters from '$lib/components/EntityListFilters.svelte';
	import BulkEditModal from '$lib/components/BulkEditModal.svelte';
	import Icon from '@iconify/svelte';

	// Convert nodes to entities for count calculation
	const entities = $derived.by(() => {
		return $nodes
			.filter((node) => node.type === 'entity')
			.map((node) => {
				const data = node.data as unknown as EntityData;
				return {
					id: node.id,
					label: data.label,
					description: data.description,
					dbt_model: data.dbt_model,
					additional_models: data.additional_models,
					drafted_fields: data.drafted_fields,
					position: node.position,
					width: data.width,
					panel_height: data.panelHeight,
					collapsed: data.collapsed,
					tags: data.tags,
					entity_type: data.entity_type,
					annotation_type: data.annotation_type,
					source_system: data.source_system,
					domain: data.domain,
					domains: data.domains,
				};
			});
	});

	// Calculate filtered count
	const filteredCount = $derived(filterEntities(entities, $entityListFilters).length);
	const totalCount = $derived(entities.length);

	// Handle modal close
	function handleCloseBulkEditModal() {
		bulkEditModal.set({ open: false, selectedEntityIds: [] });
	}
</script>

<svelte:head>
	<title>trellis - Entity List</title>
	<meta name="description" content="Browse and manage entities in list view" />
</svelte:head>

<div class="flex flex-col h-full bg-gray-50 w-full">
	<!-- Header -->
	<div class="bg-white border-b border-gray-200 px-6 py-4 w-full">
		<div class="max-w-7xl mx-auto">
			<div class="flex items-center gap-3">
				<Icon icon="lucide:list" class="w-6 h-6 text-gray-700" />
				<h1 class="text-2xl font-bold text-gray-900">Entity List</h1>
			</div>
			<p class="text-sm text-gray-600 mt-1">
				Browse and manage entities organized by domain
			</p>
		</div>
	</div>

	<!-- Content -->
	<div class="flex-1 overflow-hidden flex flex-col w-full">
		<!-- Filters Section -->
		<div class="bg-white border-b border-gray-200 w-full">
			<div class="max-w-7xl mx-auto">
				<EntityListFilters {filteredCount} {totalCount} />
			</div>
		</div>

		<!-- List Section -->
		<div class="flex-1 overflow-auto w-full">
			<div class="max-w-7xl mx-auto h-full">
				<EntityList />
			</div>
		</div>
	</div>
</div>

<!-- Bulk Edit Modal -->
<BulkEditModal open={$bulkEditModal.open} onClose={handleCloseBulkEditModal} />

<style>
	:global(body) {
		overflow: hidden;
	}
</style>
