<script lang="ts">
	import Icon from '@iconify/svelte';
	import { frameworkModels } from '$lib/stores';
	import type { ModelInfo } from '$lib/types';
	import { getModelFolder } from '$lib/utils';

	type Props = {
		selectedModelIds?: string[];
		onSelect: (model: ModelInfo) => void;
		disabled?: boolean;
	};

	let {
		selectedModelIds = [],
		onSelect,
		disabled = false,
	}: Props = $props();

	let isOpen = $state(false);
	let searchTerm = $state('');
	let containerRef = $state<HTMLDivElement>();
	let searchInput = $state<HTMLInputElement>();

	let filteredGroups = $derived.by(() => {
		const query = searchTerm.trim().toLowerCase();
		const groups = new Map<string, ModelInfo[]>();

		for (const model of $frameworkModels) {
			const matches =
				!query ||
				model.name.toLowerCase().includes(query) ||
				model.unique_id.toLowerCase().includes(query);
			if (!matches) continue;

			const group = getModelFolder(model) ?? 'Uncategorized';
			const models = groups.get(group) ?? [];
			models.push(model);
			groups.set(group, models);
		}

		return Array.from(groups.entries())
			.sort(([left], [right]) => left.localeCompare(right))
			.map(([label, models]) => ({
				label,
				models: models.sort((left, right) => left.name.localeCompare(right.name)),
			}));
	});

	$effect(() => {
		function handleClickOutside(event: MouseEvent) {
			if (containerRef && !containerRef.contains(event.target as Node)) {
				isOpen = false;
			}
		}

		if (isOpen) {
			document.addEventListener('click', handleClickOutside);
			queueMicrotask(() => searchInput?.focus());
		}

		return () => document.removeEventListener('click', handleClickOutside);
	});

	function openPicker() {
		if (disabled) return;
		isOpen = !isOpen;
		if (!isOpen) searchTerm = '';
	}

	function selectModel(model: ModelInfo) {
		if (selectedModelIds.includes(model.unique_id)) return;
		onSelect(model);
		isOpen = false;
		searchTerm = '';
	}

	function handleSearchKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			event.preventDefault();
			isOpen = false;
			searchTerm = '';
		}
	}
</script>

<div
	class="relative"
	bind:this={containerRef}
	role="presentation"
	onclick={(event) => event.stopPropagation()}
	onkeydown={(event) => event.stopPropagation()}
>
	<button
		type="button"
		class="inline-flex items-center gap-1.5 rounded-lg border border-primary-200 bg-primary-50/80 px-3 py-1.5 text-xs font-semibold text-primary-700 shadow-3xs transition-colors hover:border-primary-300 hover:bg-primary-100 disabled:cursor-not-allowed disabled:opacity-50"
		onclick={openPicker}
		disabled={disabled}
		aria-label="Bind model"
		aria-expanded={isOpen}
		aria-haspopup="dialog"
	>
		<Icon icon="lucide:link" class="h-3.5 w-3.5" />
		<span>Bind model</span>
		<Icon icon="lucide:chevron-down" class="h-3 w-3 transition-transform {isOpen ? 'rotate-180' : ''}" />
	</button>

	{#if isOpen}
		<div
			class="absolute right-0 top-full z-50 mt-1.5 w-80 overflow-hidden rounded-lg border border-gray-200 bg-white shadow-xl ring-1 ring-black/5"
			role="dialog"
			aria-label="Select model to bind"
		>
			<div class="border-b border-gray-100 p-2">
				<div class="relative">
					<Icon icon="lucide:search" class="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400" />
					<input
						bind:this={searchInput}
						type="search"
						value={searchTerm}
						oninput={(event) => (searchTerm = (event.target as HTMLInputElement).value)}
						onkeydown={handleSearchKeydown}
						class="w-full rounded-md border border-gray-200 py-1.5 pl-8 pr-2 text-xs text-gray-900 outline-none transition-colors focus:border-primary-400 focus:ring-2 focus:ring-primary-500/20"
						placeholder="Search models..."
						aria-label="Search models"
					/>
				</div>
			</div>

			<div class="max-h-72 overflow-y-auto py-1">
				{#if filteredGroups.length === 0}
					<div class="px-3 py-6 text-center text-xs text-gray-500">
						No models match your search.
					</div>
				{:else}
					{#each filteredGroups as group}
						<div class="border-b border-gray-100 last:border-b-0">
							<div class="bg-gray-50/80 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-gray-500">
								{group.label}
							</div>
							{#each group.models as model}
								{@const isSelected = selectedModelIds.includes(model.unique_id)}
								<button
									type="button"
									class="flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-xs transition-colors {isSelected
										? 'cursor-not-allowed bg-gray-50 text-gray-400'
										: 'text-gray-800 hover:bg-primary-50 hover:text-primary-700'}"
									onclick={() => selectModel(model)}
									disabled={isSelected}
									aria-label={`${model.name}${isSelected ? ' Already bound' : ''}`}
								>
									<span class="min-w-0">
										<span class="block truncate font-medium">{model.name}</span>
										<span class="block truncate font-mono text-[10px] text-gray-400">{model.unique_id}</span>
									</span>
									{#if isSelected}
										<span class="flex shrink-0 items-center gap-1 text-[10px] font-semibold text-gray-400">
											<Icon icon="lucide:check" class="h-3.5 w-3.5" />
											Already bound
										</span>
									{:else}
										<Icon icon="lucide:plus" class="h-3.5 w-3.5 shrink-0 text-primary-500" />
									{/if}
								</button>
							{/each}
						</div>
					{/each}
				{/if}
			</div>
		</div>
	{/if}
</div>
