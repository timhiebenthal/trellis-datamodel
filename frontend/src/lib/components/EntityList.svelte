<script lang="ts">
	import {
		nodes,
		entityListFilters,
		entitySelection,
		entityListCollapseState,
		bulkEditModal,
		openDeleteConfirmModal,
	} from '$lib/stores';
	import type { Node } from '@xyflow/svelte';
	import type { Entity, EntityData } from '$lib/types';
	import { filterEntities } from '$lib/utils/entity-filtering';
	import { groupEntitiesByDomain } from '$lib/utils/entity-grouping';
	import EntityRow from './EntityRow.svelte';
	import CollapseChevron from './CollapseChevron.svelte';
	import Icon from '@iconify/svelte';

	// Convert nodes to entities for filtering and grouping
	const entities = $derived.by(() => {
		return $nodes
			.filter((node) => node.type === 'entity')
			.map((node) => {
				const data = node.data as unknown as EntityData;
				const entity: Entity = {
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
				return entity;
			});
	});

	// Apply filters to entities
	const filteredEntities = $derived.by(() => {
		return filterEntities(entities, $entityListFilters);
	});

	// Group filtered entities by domain
	const groupedEntities = $derived.by(() => {
		return groupEntitiesByDomain(filteredEntities, $entityListFilters.sortDirection);
	});

	// Sort domain groups: named domains alphabetically, then "Unassigned" last
	const sortedDomainGroups = $derived.by(() => {
		const groups = Array.from(groupedEntities.entries());
		return groups.sort((a, b) => {
			const [domainA] = a;
			const [domainB] = b;

			// "Unassigned" always goes last
			if (domainA === 'Unassigned') return 1;
			if (domainB === 'Unassigned') return -1;

			// Otherwise sort alphabetically
			return domainA.localeCompare(domainB);
		});
	});

	// Selection mode is active when any entities are selected
	const selectionMode = $derived($entitySelection.size > 0);

	// Check if domain is expanded (default: true)
	function isDomainExpanded(domain: string): boolean {
		return $entityListCollapseState[domain] !== false;
	}

	// Toggle domain collapse state
	function toggleDomainCollapse(domain: string) {
		entityListCollapseState.update((state) => ({
			...state,
			[domain]: !isDomainExpanded(domain),
		}));
	}

	// Handle "Select All" checkbox
	function handleSelectAll(e: Event) {
		const checkbox = e.target as HTMLInputElement;
		const newSelection = new Set<string>();

		if (checkbox.checked) {
			// Select all visible filtered entities
			filteredEntities.forEach((entity) => {
				newSelection.add(entity.id);
			});
		}
		// If unchecked, newSelection remains empty (deselect all)

		entitySelection.set(newSelection);
	}

	// Check if all visible entities are selected
	const allSelected = $derived(
		filteredEntities.length > 0 && filteredEntities.every((entity) => $entitySelection.has(entity.id))
	);

	// Check if some (but not all) visible entities are selected
	const someSelected = $derived(
		$entitySelection.size > 0 &&
			!allSelected &&
			filteredEntities.some((entity) => $entitySelection.has(entity.id))
	);

	// Handle bulk edit actions - open modal with selected entities
	function handleBulkEdit() {
		bulkEditModal.set({
			open: true,
			selectedEntityIds: Array.from($entitySelection),
		});
	}

	// Alias for backward compatibility and semantic naming
	const handleBulkAssignDomain = handleBulkEdit;
	const handleBulkAddTags = handleBulkEdit;
	const handleBulkRemoveTags = handleBulkEdit;

	// Handle bulk delete with confirmation modal
	function handleBulkDelete() {
		const selectedIds = Array.from($entitySelection);
		if (selectedIds.length === 0) return;

		const selectedLabel =
			selectedIds.length === 1
				? entities.find((entity) => entity.id === selectedIds[0])?.label ?? 'Entity'
				: `${selectedIds.length} entities`;

		openDeleteConfirmModal(selectedLabel, selectedIds);
	}

	// Clear selection
	function clearSelection() {
		entitySelection.set(new Set());
	}
</script>

<div class="flex flex-col h-full bg-gray-50 w-full">
	<!-- Main Content Area -->
	<div class="flex-1 overflow-y-auto w-full" class:pb-20={selectionMode}>
		<!-- Select All Bar (visible when any entities exist) -->
		{#if filteredEntities.length > 0}
			<div class="bg-white border-b border-gray-200 px-4 py-2 flex items-center gap-3 sticky top-0 z-10">
				<label class="flex items-center gap-2 cursor-pointer select-none">
					<input
						type="checkbox"
						checked={allSelected}
						indeterminate={someSelected}
						onchange={handleSelectAll}
						class="w-4 h-4 rounded border-gray-300 text-primary-600 cursor-pointer"
						title="Select all visible entities"
					/>
					<span class="text-sm font-medium text-gray-700">
						{#if allSelected}
							All {filteredEntities.length} entities selected
						{:else if someSelected}
							{$entitySelection.size} of {filteredEntities.length} entities selected
						{:else}
							Select all
						{/if}
					</span>
				</label>

				{#if selectionMode}
					<button
						onclick={clearSelection}
						class="ml-auto text-sm text-gray-600 hover:text-gray-900 transition-colors"
						title="Clear selection"
					>
						Clear selection
					</button>
				{/if}
			</div>
		{/if}

		<!-- Hierarchical Entity List -->
		{#if entities.length === 0}
			<!-- Empty state: No entities exist -->
			<div class="flex flex-col items-center justify-center py-16 px-4 text-center">
				<div class="text-gray-400 mb-4">
					<Icon icon="lucide:folder-open" class="w-16 h-16" />
				</div>
				<h3 class="text-lg font-semibold text-gray-700 mb-2">No entities yet</h3>
				<p class="text-sm text-gray-500 max-w-md">
					Create entities from the canvas view or generate them from business events to get started.
				</p>
			</div>
		{:else if filteredEntities.length === 0}
			<!-- Zero results: No entities match filters -->
			<div class="flex flex-col items-center justify-center py-16 px-4 text-center">
				<div class="text-gray-400 mb-4">
					<Icon icon="lucide:search-x" class="w-16 h-16" />
				</div>
				<h3 class="text-lg font-semibold text-gray-700 mb-2">No entities match filters</h3>
				<p class="text-sm text-gray-500 max-w-md">
					Try adjusting your search term or filter criteria to see more results.
				</p>
			</div>
		{:else}
			<!-- Domain Groups -->
			{#each sortedDomainGroups as [domain, domainEntities]}
				<div class="mb-4">
					<!-- Domain Header -->
					<button
						onclick={() => toggleDomainCollapse(domain)}
						class="w-full bg-gray-100 border-b border-gray-300 px-4 py-2 flex items-center gap-2 hover:bg-gray-200 transition-all group"
					>
						<!-- Collapse Chevron -->
						<CollapseChevron expanded={isDomainExpanded(domain)} sizeClass="w-4 h-4" />

						<!-- Domain Icon -->
						<div class="text-slate-600">
							<Icon
								icon={domain === 'Unassigned' ? 'lucide:folder-open' : 'lucide:folder'}
								class="w-5 h-5"
							/>
						</div>

					<!-- Domain Name -->
					<span
						class="text-sm font-semibold tracking-wide uppercase"
						class:text-slate-800={domain !== 'Unassigned'}
						class:text-slate-500={domain === 'Unassigned'}
					>
						{domain}
					</span>

						<!-- Entity Count Badge -->
						<span
							class="ml-2 px-2 py-0.5 rounded-full text-xs font-semibold"
							class:bg-slate-200={domain !== 'Unassigned'}
							class:text-slate-700={domain !== 'Unassigned'}
							class:bg-slate-300={domain === 'Unassigned'}
							class:text-slate-600={domain === 'Unassigned'}
						>
							{domainEntities.length} {domainEntities.length === 1 ? 'entity' : 'entities'}
						</span>

						<!-- Expand hint -->
						<span class="ml-auto text-xs text-slate-400 opacity-0 group-hover:opacity-100 transition-opacity">
							{isDomainExpanded(domain) ? 'Collapse' : 'Expand'}
						</span>
					</button>

					<!-- Domain Entities (collapsible) -->
					{#if isDomainExpanded(domain)}
						<div class="bg-white border-b border-gray-200 overflow-hidden">
							{#each domainEntities as entity (entity.id)}
								<EntityRow {entity} />
							{/each}
						</div>
					{/if}
				</div>
			{/each}
		{/if}
	</div>

	<!-- Bulk Action Toolbar (fixed bottom, visible when entities selected) -->
	{#if selectionMode}
		<div
			class="fixed bottom-0 left-0 right-0 bg-primary-600 border-t border-primary-700 shadow-2xl z-50 animate-slide-up"
		>
			<div class="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between gap-4">
				<!-- Selection Count -->
				<div class="flex items-center gap-3">
					<div class="bg-primary-700 rounded-full p-2">
						<Icon icon="lucide:check-square" class="w-5 h-5 text-white" />
					</div>
					<div class="text-white">
						<div class="text-sm font-semibold">
							{$entitySelection.size} {$entitySelection.size === 1 ? 'entity' : 'entities'} selected
						</div>
						<div class="text-xs text-primary-100">Choose an action below</div>
					</div>
				</div>

				<!-- Action Buttons -->
				<div class="flex items-center gap-2">
					<button
						onclick={handleBulkAssignDomain}
						class="inline-flex items-center gap-2 px-4 py-2 bg-white text-primary-700 rounded-lg font-medium hover:bg-primary-50 transition-all shadow-md hover:shadow-lg"
						title="Add domain to selected entities"
					>
						<Icon icon="lucide:tag" class="w-4 h-4" />
						<span>Add Domain</span>
					</button>

					<button
						onclick={handleBulkAddTags}
						class="inline-flex items-center gap-2 px-4 py-2 bg-white text-primary-700 rounded-lg font-medium hover:bg-primary-50 transition-all shadow-md hover:shadow-lg"
						title="Add tags to selected entities"
					>
						<Icon icon="lucide:tags" class="w-4 h-4" />
						<span>Add Tags</span>
					</button>

					<button
						onclick={handleBulkRemoveTags}
						class="inline-flex items-center gap-2 px-4 py-2 bg-white text-primary-700 rounded-lg font-medium hover:bg-primary-50 transition-all shadow-md hover:shadow-lg"
						title="Remove tags from selected entities"
					>
						<Icon icon="lucide:tag-x" class="w-4 h-4" />
						<span>Remove Tags</span>
					</button>

					<button
						onclick={handleBulkDelete}
						class="inline-flex items-center gap-2 px-4 py-2 bg-danger-600 text-white rounded-lg font-medium hover:bg-danger-700 transition-all shadow-md hover:shadow-lg"
						title="Delete selected entities"
					>
						<Icon icon="lucide:trash-2" class="w-4 h-4" />
						<span>Delete</span>
					</button>

					<button
						onclick={clearSelection}
						class="inline-flex items-center gap-2 px-3 py-2 bg-primary-700 text-white rounded-lg hover:bg-primary-800 transition-colors"
						title="Clear selection"
					>
						<Icon icon="lucide:x" class="w-4 h-4" />
					</button>
				</div>
			</div>
		</div>
	{/if}
</div>

<style>
	/* Animate toolbar slide up */
	@keyframes slide-up {
		from {
			transform: translateY(100%);
			opacity: 0;
		}
		to {
			transform: translateY(0);
			opacity: 1;
		}
	}

	.animate-slide-up {
		animation: slide-up 0.3s ease-out;
	}

	/* Indeterminate checkbox state */
	input[type='checkbox']:indeterminate {
		background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 16 16'%3e%3cpath stroke='white' stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M4 8h8'/%3e%3c/svg%3e");
		background-color: currentColor;
		background-size: 100% 100%;
		background-position: center;
		background-repeat: no-repeat;
	}

	/* Smooth transitions for collapse/expand */
	:global(.transition-all) {
		transition-property: all;
		transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
		transition-duration: 200ms;
	}
</style>
