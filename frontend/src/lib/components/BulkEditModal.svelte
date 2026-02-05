<script lang="ts">
	import Icon from '@iconify/svelte';
	import { bulkEditModal, entitySelection, nodes } from '$lib/stores';
	import type { EntityData } from '$lib/types';
	import { bulkAssignDomain, bulkAddTags, bulkRemoveTags } from '$lib/utils/bulk-operations';

	type Props = {
		open: boolean;
		onClose: () => void;
	};

	let { open, onClose }: Props = $props();

	// Get selected entities from nodes
	const selectedEntities = $derived.by(() => {
		const selectedIds = $bulkEditModal.selectedEntityIds;
		return $nodes
			.filter((node) => node.type === 'entity' && selectedIds.includes(node.id))
			.map((node) => {
				const data = node.data as unknown as EntityData;
				return {
					id: node.id,
					label: data.label,
					domain: data.domain,
					tags: data.tags || [],
				};
			});
	});

	// Count of selected entities
	const selectedCount = $derived(selectedEntities.length);

	// Get all unique domains from all nodes for dropdown
	const allDomains = $derived.by(() => {
		const domains = new Set<string>();
		$nodes
			.filter((node) => node.type === 'entity')
			.forEach((node) => {
				const data = node.data as unknown as EntityData;
				const domain = data.domain;
				if (domain) {
					domains.add(domain);
				}
			});
		return Array.from(domains).sort();
	});

	// Get all unique tags from all nodes
	const allTags = $derived.by(() => {
		const tags = new Set<string>();
		$nodes
			.filter((node) => node.type === 'entity')
			.forEach((node) => {
				const data = node.data as unknown as EntityData;
				const nodeTags = data.tags || [];
				nodeTags.forEach((tag) => tags.add(tag));
			});
		return Array.from(tags).sort();
	});

	// Get common tags (tags that appear in ALL selected entities)
	const commonTags = $derived.by(() => {
		if (selectedEntities.length === 0) return [];

		// Start with tags from first entity
		const firstEntityTags = new Set(selectedEntities[0].tags);

		// Intersect with tags from all other entities
		for (let i = 1; i < selectedEntities.length; i++) {
			const entityTags = new Set(selectedEntities[i].tags);
			// Keep only tags that exist in current entity
			firstEntityTags.forEach((tag) => {
				if (!entityTags.has(tag)) {
					firstEntityTags.delete(tag);
				}
			});
		}

		return Array.from(firstEntityTags).sort();
	});

	// Form state
	let selectedDomain = $state<string>('');
	let tagsToAdd = $state<string[]>([]);
	let tagsToRemove = $state<string[]>([]);
	let newTagInput = $state('');
	let processing = $state(false);

	// Whether any operations are selected
	const hasOperations = $derived(selectedDomain !== '' || tagsToAdd.length > 0 || tagsToRemove.length > 0);

	// Reset form when modal opens/closes
	$effect(() => {
		if (open) {
			selectedDomain = '';
			tagsToAdd = [];
			tagsToRemove = [];
			newTagInput = '';
			processing = false;
		}
	});

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape' && !processing) {
			handleClose();
		}
	}

	function handleBackdropClick(event: MouseEvent) {
		if (event.target === event.currentTarget && !processing) {
			handleClose();
		}
	}

	function handleClose() {
		if (!processing) {
			onClose();
		}
	}

	function toggleTagToAdd(tag: string) {
		if (tagsToAdd.includes(tag)) {
			tagsToAdd = tagsToAdd.filter((t) => t !== tag);
		} else {
			tagsToAdd = [...tagsToAdd, tag];
		}
	}

	function toggleTagToRemove(tag: string) {
		if (tagsToRemove.includes(tag)) {
			tagsToRemove = tagsToRemove.filter((t) => t !== tag);
		} else {
			tagsToRemove = [...tagsToRemove, tag];
		}
	}

	function handleAddNewTag() {
		const trimmed = newTagInput.trim();
		if (trimmed && !tagsToAdd.includes(trimmed)) {
			tagsToAdd = [...tagsToAdd, trimmed];
			newTagInput = '';
		}
	}

	function handleNewTagKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			event.preventDefault();
			handleAddNewTag();
		}
	}

	function handleApplyChanges() {
		if (!hasOperations || processing) return;

		processing = true;

		try {
			const entityIds = selectedEntities.map((e) => e.id);

			// Apply domain assignment
			if (selectedDomain) {
				bulkAssignDomain(entityIds, selectedDomain);
			}

			// Apply tag additions
			if (tagsToAdd.length > 0) {
				bulkAddTags(entityIds, tagsToAdd);
			}

			// Apply tag removals
			if (tagsToRemove.length > 0) {
				bulkRemoveTags(entityIds, tagsToRemove);
			}

			// Clear selection and close modal
			entitySelection.set(new Set());
			onClose();
		} catch (error) {
			console.error('Error applying bulk changes:', error);
		} finally {
			processing = false;
		}
	}

	// Show up to 10 entities in preview, with overflow message
	const previewEntities = $derived(selectedEntities.slice(0, 10));
	const overflowCount = $derived(Math.max(0, selectedEntities.length - 10));
</script>

{#if open}
	<!-- Backdrop -->
	<div
		class="fixed inset-0 bg-gray-900/85 backdrop-blur-md z-50 flex items-center justify-center"
		onclick={handleBackdropClick}
		onkeydown={handleKeydown}
		role="dialog"
		tabindex="-1"
		aria-modal="true"
		aria-labelledby="bulk-edit-modal-title"
	>
		<!-- Modal Container with geometric design - Wider for attributes -->
		<div
			class="bg-white rounded-lg shadow-2xl w-full mx-4 max-h-[90vh] overflow-hidden max-w-5xl border border-slate-200"
			role="document"
			tabindex="-1"
		>
			<!-- Header with primary accent -->
			<div class="relative overflow-hidden">
				<!-- Solid background -->
				<div class="absolute inset-0 bg-primary-600"></div>
				<div
					class="absolute inset-0 opacity-10"
					style="background-image: repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(255,255,255,0.1) 10px, rgba(255,255,255,0.1) 20px);"
				></div>

				<div class="relative px-6 py-5 flex items-center justify-between">
					<div class="flex items-center gap-4">
						<div
							class="w-12 h-12 bg-white/20 backdrop-blur-sm rounded-lg flex items-center justify-center border border-white/30"
						>
							<Icon icon="lucide:edit-3" class="w-6 h-6 text-white" />
						</div>
						<div>
							<h2 id="bulk-edit-modal-title" class="text-xl font-bold text-white tracking-tight">
								Bulk Edit Entities
							</h2>
							<p class="text-sm text-teal-50 font-medium mt-0.5">
								{selectedCount} {selectedCount === 1 ? 'entity' : 'entities'} selected
							</p>
						</div>
					</div>
					<button
						class="p-2 rounded-lg hover:bg-white/20 text-white transition-colors border border-transparent hover:border-white/30"
						onclick={handleClose}
						aria-label="Close"
						disabled={processing}
					>
						<Icon icon="lucide:x" class="w-5 h-5" />
					</button>
				</div>
			</div>

			<!-- Content -->
			<div class="p-6 overflow-y-auto max-h-[calc(90vh-180px)] space-y-5">
				<!-- Entity Preview - Compact -->
				<div class="bg-slate-50 rounded-lg p-3 border border-slate-200">
					<div class="flex items-center gap-2 mb-2">
						<Icon icon="lucide:layers" class="w-4 h-4 text-slate-600" />
						<h3 class="text-xs font-semibold text-slate-900 uppercase tracking-wide">
							Selected Entities
						</h3>
					</div>
					<div class="flex flex-wrap gap-1.5">
						{#each previewEntities as entity}
							<span
								class="inline-flex items-center gap-1.5 text-xs px-2.5 py-1 bg-white rounded-md border border-slate-200 font-medium text-slate-700"
							>
								<div class="w-1 h-1 bg-teal-500 rounded-full"></div>
								{entity.label}
								{#if entity.domain}
									<span class="text-[10px] px-1.5 py-0.5 bg-slate-100 text-slate-600 rounded">
										{entity.domain}
									</span>
								{/if}
							</span>
						{/each}
						{#if overflowCount > 0}
							<span class="text-xs text-slate-500 px-2 py-1 italic">
								+{overflowCount} more
							</span>
						{/if}
					</div>
				</div>

				<!-- Domain Assignment - Compact -->
				<div>
					<label for="bulk-domain-select" class="flex items-center gap-1.5 text-xs font-semibold text-slate-900 mb-2 uppercase tracking-wide">
						<Icon icon="lucide:folder" class="w-4 h-4 text-slate-700" />
						Domain
					</label>
					<select
						id="bulk-domain-select"
						bind:value={selectedDomain}
						class="w-full px-3 py-2 border-2 border-slate-300 rounded-lg text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-teal-500 disabled:bg-slate-100 disabled:cursor-not-allowed font-medium text-slate-900 bg-white"
						disabled={processing}
					>
						<option value="">— No change —</option>
						{#each allDomains as domain}
							<option value={domain}>{domain}</option>
						{/each}
					</select>
				</div>

				<!-- Add Tags Section - Compact -->
				<div class="space-y-2">
					<label class="flex items-center gap-1.5 text-xs font-semibold text-slate-900 uppercase tracking-wide">
						<Icon icon="lucide:plus-circle" class="w-4 h-4 text-emerald-600" />
						Add Tags
					</label>

					<!-- New tag input - compact -->
					<div class="flex gap-2">
						<input
							type="text"
							bind:value={newTagInput}
							onkeydown={handleNewTagKeydown}
							placeholder="Type new tag..."
							class="flex-1 px-3 py-1.5 border-2 border-slate-300 rounded-lg text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 disabled:bg-slate-100 font-medium"
							disabled={processing}
						/>
						<button
							onclick={handleAddNewTag}
							disabled={!newTagInput.trim() || processing}
							class="px-3 py-1.5 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium text-sm flex items-center gap-1.5 shadow-sm"
						>
							<Icon icon="lucide:plus" class="w-3.5 h-3.5" />
							Add
						</button>
					</div>

					<!-- Existing tags to add - compact chips -->
					{#if allTags.length > 0}
						<div class="bg-slate-50 rounded-lg p-2.5 border border-slate-200">
							<p class="text-[10px] text-slate-600 mb-2 font-medium uppercase tracking-wide">Select existing:</p>
							<div class="flex flex-wrap gap-1.5">
								{#each allTags as tag}
									<button
										onclick={() => toggleTagToAdd(tag)}
										class="px-2 py-1 text-xs rounded-md border transition-all font-medium {tagsToAdd.includes(
											tag
										)
											? 'bg-emerald-100 border-emerald-500 text-emerald-800'
											: 'bg-white border-slate-300 text-slate-700 hover:border-emerald-400'}"
										disabled={processing}
									>
										{#if tagsToAdd.includes(tag)}
											<Icon icon="lucide:check" class="w-2.5 h-2.5 inline-block mr-0.5" />
										{/if}
										{tag}
									</button>
								{/each}
							</div>
						</div>
					{/if}

					<!-- Selected tags to add - compact -->
					{#if tagsToAdd.length > 0}
						<div class="bg-emerald-50 rounded-lg p-2.5 border border-emerald-200">
							<p class="text-[10px] text-emerald-700 mb-1.5 font-semibold uppercase tracking-wide">Will add:</p>
							<div class="flex flex-wrap gap-1.5">
								{#each tagsToAdd as tag}
									<span
										class="px-2 py-0.5 text-xs bg-emerald-600 text-white rounded-md font-medium flex items-center gap-1 shadow-sm"
									>
										{tag}
										<button
											onclick={() => toggleTagToAdd(tag)}
											class="hover:bg-emerald-700 rounded p-0.5"
											disabled={processing}
										>
											<Icon icon="lucide:x" class="w-2.5 h-2.5" />
										</button>
									</span>
								{/each}
							</div>
						</div>
					{/if}
				</div>

				<!-- Remove Tags Section - Compact -->
				{#if commonTags.length > 0}
					<div class="space-y-2">
						<label class="flex items-center gap-1.5 text-xs font-semibold text-slate-900 uppercase tracking-wide">
							<Icon icon="lucide:minus-circle" class="w-4 h-4 text-rose-600" />
							Remove Tags
						</label>

						<div class="bg-slate-50 rounded-lg p-2.5 border border-slate-200">
							<p class="text-[10px] text-slate-600 mb-2 font-medium uppercase tracking-wide">
								Common tags:
							</p>
							<div class="flex flex-wrap gap-1.5">
								{#each commonTags as tag}
									<button
										onclick={() => toggleTagToRemove(tag)}
										class="px-2 py-1 text-xs rounded-md border transition-all font-medium {tagsToRemove.includes(
											tag
										)
											? 'bg-rose-100 border-rose-500 text-rose-800'
											: 'bg-white border-slate-300 text-slate-700 hover:border-rose-400'}"
										disabled={processing}
									>
										{#if tagsToRemove.includes(tag)}
											<Icon icon="lucide:check" class="w-2.5 h-2.5 inline-block mr-0.5" />
										{/if}
										{tag}
									</button>
								{/each}
							</div>
						</div>

						<!-- Selected tags to remove - compact -->
						{#if tagsToRemove.length > 0}
							<div class="bg-rose-50 rounded-lg p-2.5 border border-rose-200">
								<p class="text-[10px] text-rose-700 mb-1.5 font-semibold uppercase tracking-wide">Will remove:</p>
								<div class="flex flex-wrap gap-1.5">
									{#each tagsToRemove as tag}
										<span
											class="px-2 py-0.5 text-xs bg-rose-600 text-white rounded-md font-medium flex items-center gap-1 shadow-sm"
										>
											{tag}
											<button
												onclick={() => toggleTagToRemove(tag)}
												class="hover:bg-rose-700 rounded p-0.5"
												disabled={processing}
											>
												<Icon icon="lucide:x" class="w-2.5 h-2.5" />
											</button>
										</span>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				{:else}
					<div class="bg-slate-50 rounded-lg p-2.5 border border-slate-200">
						<p class="text-xs text-slate-600 flex items-center gap-1.5">
							<Icon icon="lucide:info" class="w-3.5 h-3.5" />
							No common tags
						</p>
					</div>
				{/if}

				<!-- Progress Indicator (shown for 50+ entities) - Compact -->
				{#if processing && selectedCount >= 50}
					<div class="bg-teal-50 rounded-lg p-2.5 border border-teal-200">
						<div class="flex items-center gap-2">
							<Icon icon="lucide:loader-2" class="w-4 h-4 text-teal-600 animate-spin" />
							<div class="flex-1">
								<p class="text-xs font-semibold text-teal-900">
									Processing {selectedCount} entities...
								</p>
							</div>
						</div>
					</div>
				{/if}
			</div>

			<!-- Footer Actions -->
			<div class="px-6 py-4 bg-slate-50 border-t border-slate-200 flex justify-end gap-3">
				<button
					onclick={handleClose}
					class="px-5 py-2.5 text-sm font-semibold text-slate-700 bg-white border-2 border-slate-300 rounded-lg hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-slate-500 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
					disabled={processing}
				>
					Cancel
				</button>
				<button
					onclick={handleApplyChanges}
					class="px-5 py-2.5 text-sm font-semibold text-white bg-primary-600 hover:bg-primary-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-md"
					disabled={!hasOperations || processing}
				>
					{#if processing}
						<Icon icon="lucide:loader-2" class="w-4 h-4 animate-spin" />
						<span>Processing...</span>
					{:else}
						<Icon icon="lucide:check" class="w-4 h-4" />
						<span>Apply Changes</span>
					{/if}
				</button>
			</div>
		</div>
	</div>
{/if}
