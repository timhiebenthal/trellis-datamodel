<script lang="ts">
	import { entityListFilters, nodes, edges, modelingStyle } from '$lib/stores';
	import type { EntityData } from '$lib/types';
	import { exportDataModelToExcel } from '$lib/utils/excel-export';
	import Icon from '@iconify/svelte';

	interface Props {
		filteredCount: number;
		totalCount: number;
	}

	let { filteredCount, totalCount }: Props = $props();

	let searchTermLocal = $state($entityListFilters.searchTerm);
	let searchDebounceTimeout: ReturnType<typeof setTimeout> | null = null;
	let lastSyncedSearchTerm = $entityListFilters.searchTerm;

	// Extract unique domains from entity nodes
	let allDomains = $derived.by(() => {
		const domains = new Set<string>();
		$nodes.forEach((node) => {
			if (node.type === 'entity') {
				const data = node.data as unknown as EntityData;
				const domainList = Array.isArray(data.domains) && data.domains.length > 0
					? data.domains
					: data.domain
						? [data.domain]
						: [];
				domainList.forEach((domain) => {
					if (domain && domain.trim()) {
						domains.add(domain.trim());
					}
				});
			}
		});
		return Array.from(domains).sort();
	});

	// Extract unique tags from entity nodes
	let allTags = $derived.by(() => {
		const tags = new Set<string>();
		$nodes.forEach((node) => {
			if (node.type === 'entity') {
				const data = node.data as unknown as EntityData;
				if (data.tags && Array.isArray(data.tags)) {
					data.tags.forEach((tag) => tags.add(tag));
				}
			}
		});
		return Array.from(tags).sort();
	});

	// Handle search input with debounce
	function handleSearchInput(value: string) {
		searchTermLocal = value;

		if (searchDebounceTimeout) {
			clearTimeout(searchDebounceTimeout);
		}

		searchDebounceTimeout = setTimeout(() => {
			entityListFilters.update((filters) => ({
				...filters,
				searchTerm: value,
			}));
		}, 300);
	}

	// Handle domain filter toggle
	function toggleDomain(domain: string) {
		entityListFilters.update((filters) => {
			const domains = [...filters.selectedDomains];
			if (domains.includes(domain)) {
				return {
					...filters,
					selectedDomains: domains.filter((d) => d !== domain),
				};
			} else {
				return {
					...filters,
					selectedDomains: [...domains, domain],
				};
			}
		});
	}

	// Remove domain from filter
	function removeDomain(domain: string) {
		entityListFilters.update((filters) => ({
			...filters,
			selectedDomains: filters.selectedDomains.filter((d) => d !== domain),
		}));
	}

	// Handle tag filter toggle
	function toggleTag(tag: string) {
		entityListFilters.update((filters) => {
			const tags = [...filters.selectedTags];
			if (tags.includes(tag)) {
				return {
					...filters,
					selectedTags: tags.filter((t) => t !== tag),
				};
			} else {
				return {
					...filters,
					selectedTags: [...tags, tag],
				};
			}
		});
	}

	// Remove tag from filter
	function removeTag(tag: string) {
		entityListFilters.update((filters) => ({
			...filters,
			selectedTags: filters.selectedTags.filter((t) => t !== tag),
		}));
	}

	function handleExportDataModel() {
		exportDataModelToExcel($nodes, $edges, $modelingStyle === 'dimensional_model');
	}

	function toggleEntityType(type: 'dimension' | 'fact' | 'unclassified') {
		entityListFilters.update((filters) => {
			const types = [...filters.selectedEntityTypes];
			if (types.includes(type)) {
				return { ...filters, selectedEntityTypes: types.filter((t) => t !== type) };
			} else {
				return { ...filters, selectedEntityTypes: [...types, type] };
			}
		});
	}

	function removeEntityType(type: 'dimension' | 'fact' | 'unclassified') {
		entityListFilters.update((filters) => ({
			...filters,
			selectedEntityTypes: filters.selectedEntityTypes.filter((t) => t !== type),
		}));
	}

	function toggleBuildStatus(status: 'bound' | 'unbound') {
		entityListFilters.update((filters) => {
			const statuses = [...filters.selectedBuildStatus];
			if (statuses.includes(status)) {
				return { ...filters, selectedBuildStatus: statuses.filter((s) => s !== status) };
			} else {
				return { ...filters, selectedBuildStatus: [...statuses, status] };
			}
		});
	}

	function removeBuildStatus(status: 'bound' | 'unbound') {
		entityListFilters.update((filters) => ({
			...filters,
			selectedBuildStatus: filters.selectedBuildStatus.filter((s) => s !== status),
		}));
	}

	function toggleSortDirection() {
		entityListFilters.update((filters) => ({
			...filters,
			sortDirection: filters.sortDirection === 'asc' ? 'desc' : 'asc',
		}));
	}

	function toggleGroupByEntityType() {
		entityListFilters.update((filters) => ({ ...filters, groupByEntityType: !filters.groupByEntityType }));
	}

	// Clear all filters
	function clearAllFilters() {
		searchTermLocal = '';
		entityListFilters.update((filters) => ({
			searchTerm: '',
			selectedDomains: [],
			selectedTags: [],
			selectedEntityTypes: [],
			selectedBuildStatus: [],
			sortDirection: filters.sortDirection,
			groupByEntityType: filters.groupByEntityType,
		}));
	}

	// Sync local search term when store changes externally
	$effect(() => {
		const storeSearchTerm = $entityListFilters.searchTerm;
		if (storeSearchTerm !== lastSyncedSearchTerm) {
			lastSyncedSearchTerm = storeSearchTerm;
			if (searchTermLocal !== storeSearchTerm) {
				searchTermLocal = storeSearchTerm;
			}
		}
	});
</script>

<div class="py-4">
	<!-- Search and Results Row -->
	<div class="flex items-center justify-between mb-4 gap-4">
		<!-- Search Input -->
		<div class="relative flex-1 max-w-sm">
			<div class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none">
				<Icon icon="lucide:search" class="w-4 h-4" />
			</div>
			<input
				type="text"
				placeholder="Search by entity name..."
				value={searchTermLocal}
				onchange={(e) => handleSearchInput(e.currentTarget.value)}
				oninput={(e) => handleSearchInput(e.currentTarget.value)}
				class="inline-input w-full pl-9 pr-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-primary-600 focus:border-primary-600"
			/>
		</div>

		<div class="flex flex-wrap items-center gap-2 shrink-0">
			<!-- Result Count Badge -->
			<div class="flex items-center gap-2 px-3 py-1.5 bg-gray-50 border border-gray-200 rounded-md text-sm text-gray-600">
				<span class="font-medium text-gray-900">{filteredCount}</span>
				<span class="text-gray-500">/</span>
				<span class="text-gray-600">{totalCount}</span>
				<span class="text-gray-500">entities</span>
			</div>

			<button
				type="button"
				onclick={handleExportDataModel}
				class="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 bg-white border border-gray-300 rounded-md hover:bg-gray-50 hover:border-gray-400 transition-colors"
				title="Download all entities as one Excel file (one tab per entity)"
			>
				<Icon icon="lucide:download" class="w-4 h-4" />
				<span>Export Data Model</span>
			</button>

			<!-- Clear Filters Button -->
			{#if $entityListFilters.searchTerm || $entityListFilters.selectedDomains.length > 0 || $entityListFilters.selectedTags.length > 0 || $entityListFilters.selectedEntityTypes.length > 0 || $entityListFilters.selectedBuildStatus.length > 0}
				<button
					type="button"
					onclick={clearAllFilters}
					class="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 bg-white border border-gray-300 rounded-md hover:bg-gray-50 hover:border-gray-400 transition-colors"
					title="Clear all filters"
				>
					<Icon icon="lucide:x" class="w-4 h-4" />
					<span>Clear</span>
				</button>
			{/if}
		</div>
	</div>

	<!-- Filters Row -->
	<div class="flex items-center justify-between gap-4 flex-wrap">
		<div class="flex flex-wrap items-center gap-4">
			<!-- Domain Filter -->
			{#if allDomains.length > 0}
				<div class="flex items-center gap-2">
					<span class="text-xs text-gray-600">Domain:</span>

					<!-- Selected domains as chips -->
					{#if $entityListFilters.selectedDomains.length > 0}
						<div class="flex flex-wrap gap-1">
							{#each $entityListFilters.selectedDomains as domain}
								<span
									class="inline-flex items-center gap-1.5 px-2 py-1 bg-primary-100 text-primary-700 rounded text-xs font-medium border border-primary-200"
								>
									{domain}
									<button
										onclick={() => removeDomain(domain)}
										class="text-primary-600 hover:text-primary-900 transition-colors"
										title="Remove {domain}"
									>
										<Icon icon="lucide:x" class="w-3 h-3" />
									</button>
								</span>
							{/each}
						</div>
					{/if}

					<!-- Domain dropdown -->
					<div class="relative">
						<select
							value=""
							onchange={(e) => {
								const val = e.currentTarget.value;
								if (val) {
									toggleDomain(val);
									e.currentTarget.value = '';
								}
							}}
							class="pl-2 pr-7 py-1.5 text-xs border border-gray-300 rounded bg-white focus:outline-none focus:ring-1 focus:ring-primary-600 focus:border-primary-600 appearance-none cursor-pointer"
						>
							<option value="" disabled selected>
								{$entityListFilters.selectedDomains.length > 0 ? 'Add domain...' : 'All'}
							</option>
							{#each allDomains as domain}
								<option
									value={domain}
									disabled={$entityListFilters.selectedDomains.includes(domain)}
								>
									{domain}
								</option>
							{/each}
						</select>
						<div class="absolute right-1.5 top-1/2 -translate-y-1/2 pointer-events-none text-gray-400">
							<Icon icon="lucide:chevron-down" class="w-3 h-3" />
						</div>
					</div>
				</div>
			{/if}

			<!-- Tag Filter -->
			{#if allTags.length > 0}
				<div class="flex items-center gap-2">
					<span class="text-xs text-gray-600">Tag:</span>

					<!-- Selected tags as chips -->
					{#if $entityListFilters.selectedTags.length > 0}
						<div class="flex flex-wrap gap-1">
							{#each $entityListFilters.selectedTags as tag}
								<span
									class="inline-flex items-center gap-1.5 px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs font-medium border border-gray-300"
								>
									{tag}
									<button
										onclick={() => removeTag(tag)}
										class="text-gray-600 hover:text-gray-900 transition-colors"
										title="Remove {tag}"
									>
										<Icon icon="lucide:x" class="w-3 h-3" />
									</button>
								</span>
							{/each}
						</div>
					{/if}

					<!-- Tag dropdown -->
					<div class="relative">
						<select
							value=""
							disabled={allTags.length === 0}
							onchange={(e) => {
								const val = e.currentTarget.value;
								if (val) {
									toggleTag(val);
									e.currentTarget.value = '';
								}
							}}
							class="pl-2 pr-7 py-1.5 text-xs border border-gray-300 rounded bg-white focus:outline-none focus:ring-1 focus:ring-primary-600 focus:border-primary-600 appearance-none cursor-pointer disabled:bg-gray-50 disabled:text-gray-400 disabled:cursor-not-allowed"
						>
							<option value="" disabled selected>
								{allTags.length === 0 ? 'No tags' : $entityListFilters.selectedTags.length > 0 ? 'Add tag...' : 'All'}
							</option>
							{#each allTags as tag}
								<option
									value={tag}
									disabled={$entityListFilters.selectedTags.includes(tag)}
								>
									{tag}
								</option>
							{/each}
						</select>
						<div class="absolute right-1.5 top-1/2 -translate-y-1/2 pointer-events-none text-gray-400">
							<Icon icon="lucide:chevron-down" class="w-3 h-3" />
						</div>
					</div>
				</div>
			{/if}

			<!-- Type Filter -->
			<div class="flex items-center gap-2">
				<span class="text-xs text-gray-600">Type:</span>

				<!-- Selected types as chips -->
				{#if $entityListFilters.selectedEntityTypes.length > 0}
					<div class="flex flex-wrap gap-1">
						{#each $entityListFilters.selectedEntityTypes as type}
							{@const typeLabel = type === 'dimension' ? 'Dimension' : type === 'fact' ? 'Fact' : 'Unclassified'}
							{@const typeClass = type === 'dimension' ? 'bg-green-100 text-green-700 border-green-200' : type === 'fact' ? 'bg-blue-100 text-blue-700 border-blue-200' : 'bg-gray-100 text-gray-700 border-gray-300'}
							<span class="inline-flex items-center gap-1.5 px-2 py-1 rounded text-xs font-medium border {typeClass}">
								{typeLabel}
								<button
									onclick={() => removeEntityType(type)}
									class="hover:opacity-75 transition-opacity"
									title="Remove {typeLabel}"
								>
									<Icon icon="lucide:x" class="w-3 h-3" />
								</button>
							</span>
						{/each}
					</div>
				{/if}

				<!-- Type dropdown -->
				<div class="relative">
					<select
						value=""
						onchange={(e) => {
							const val = e.currentTarget.value as 'dimension' | 'fact' | 'unclassified';
							if (val) {
								toggleEntityType(val);
								e.currentTarget.value = '';
							}
						}}
						class="pl-2 pr-7 py-1.5 text-xs border border-gray-300 rounded bg-white focus:outline-none focus:ring-1 focus:ring-primary-600 focus:border-primary-600 appearance-none cursor-pointer"
					>
						<option value="" disabled selected>
							{$entityListFilters.selectedEntityTypes.length > 0 ? 'Add type...' : 'All'}
						</option>
						<option value="dimension" disabled={$entityListFilters.selectedEntityTypes.includes('dimension')}>Dimension</option>
						<option value="fact" disabled={$entityListFilters.selectedEntityTypes.includes('fact')}>Fact</option>
						<option value="unclassified" disabled={$entityListFilters.selectedEntityTypes.includes('unclassified')}>Unclassified</option>
					</select>
					<div class="absolute right-1.5 top-1/2 -translate-y-1/2 pointer-events-none text-gray-400">
						<Icon icon="lucide:chevron-down" class="w-3 h-3" />
					</div>
				</div>
			</div>

			<!-- Built Filter -->
			<div class="flex items-center gap-2">
				<span class="text-xs text-gray-600 inline-flex items-center gap-1">
					Built:
					<span class="inline-flex items-center gap-0.5 text-gray-400" title="Entities with this mark are already built with dbt">
						(<Icon icon="lucide:check" class="w-3 h-3 text-primary-600" /> = built with dbt)
					</span>
				</span>

				<!-- Selected build statuses as chips -->
				{#if $entityListFilters.selectedBuildStatus.length > 0}
					<div class="flex flex-wrap gap-1">
						{#each $entityListFilters.selectedBuildStatus as status}
							{@const statusLabel = status === 'bound' ? 'Bound' : 'Unbound'}
							<span
								class="inline-flex items-center gap-1.5 px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs font-medium border border-gray-300"
							>
								{statusLabel}
								<button
									onclick={() => removeBuildStatus(status)}
									class="text-gray-600 hover:text-gray-900 transition-colors"
									title="Remove {statusLabel}"
								>
									<Icon icon="lucide:x" class="w-3 h-3" />
								</button>
							</span>
						{/each}
					</div>
				{/if}

				<!-- Built dropdown -->
				<div class="relative">
					<select
						value=""
						data-testid="build-status-select"
						onchange={(e) => {
							const val = e.currentTarget.value as 'bound' | 'unbound';
							if (val) {
								toggleBuildStatus(val);
								e.currentTarget.value = '';
							}
						}}
						class="pl-2 pr-7 py-1.5 text-xs border border-gray-300 rounded bg-white focus:outline-none focus:ring-1 focus:ring-primary-600 focus:border-primary-600 appearance-none cursor-pointer"
					>
						<option value="" disabled selected>
							{$entityListFilters.selectedBuildStatus.length > 0 ? 'Add status...' : 'All'}
						</option>
						<option value="bound" disabled={$entityListFilters.selectedBuildStatus.includes('bound')}>Bound</option>
						<option value="unbound" disabled={$entityListFilters.selectedBuildStatus.includes('unbound')}>Unbound</option>
					</select>
					<div class="absolute right-1.5 top-1/2 -translate-y-1/2 pointer-events-none text-gray-400">
						<Icon icon="lucide:chevron-down" class="w-3 h-3" />
					</div>
				</div>
			</div>

			<!-- Group By Type Checkbox -->
			<label class="flex items-center gap-2 cursor-pointer select-none">
				<input
					type="checkbox"
					checked={$entityListFilters.groupByEntityType}
					onchange={toggleGroupByEntityType}
					class="w-3.5 h-3.5 rounded border-gray-300 text-primary-600 cursor-pointer"
				/>
				<span class="text-xs text-gray-600">Group by type</span>
			</label>
		</div>

		<!-- Sort Direction Toggle -->
		<div class="flex items-center gap-2 shrink-0">
			<span class="text-xs text-gray-600">Sort:</span>
			<button
				type="button"
				onclick={toggleSortDirection}
				class="inline-flex items-center gap-1 px-2 py-1.5 text-xs border border-gray-300 rounded bg-white hover:bg-gray-50 transition-colors font-medium text-gray-700"
				title="Toggle sort direction"
			>
				<Icon icon={$entityListFilters.sortDirection === 'asc' ? 'lucide:arrow-up-a-z' : 'lucide:arrow-down-z-a'} class="w-3.5 h-3.5" />
				{$entityListFilters.sortDirection === 'asc' ? 'A–Z' : 'Z–A'}
			</button>
		</div>
	</div>
</div>

<style>
	:global(.inline-input) {
		transition: all 0.2s ease;
	}

	:global(.inline-input:focus) {
		box-shadow: 0 0 0 3px rgba(20, 184, 166, 0.1);
	}
</style>
