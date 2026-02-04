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
	<!-- Backdrop with dramatic blur -->
	<div
		class="fixed inset-0 bg-gradient-to-br from-slate-900/90 via-slate-800/85 to-slate-900/90 backdrop-blur-md z-50 flex items-center justify-center"
		onclick={handleBackdropClick}
		onkeydown={handleKeydown}
		role="dialog"
		tabindex="-1"
		aria-modal="true"
		aria-labelledby="bulk-edit-modal-title"
	>
		<!-- Modal Container with geometric design -->
		<div
			class="bg-white rounded-lg shadow-2xl w-full mx-4 max-h-[90vh] overflow-hidden max-w-3xl border border-slate-200"
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
			<div class="p-6 overflow-y-auto max-h-[calc(90vh-180px)] space-y-6">
				<!-- Entity Preview -->
				<div class="bg-slate-50 rounded-lg p-4 border border-slate-200">
					<div class="flex items-center gap-2 mb-3">
						<Icon icon="lucide:layers" class="w-4 h-4 text-slate-600" />
						<h3 class="text-sm font-semibold text-slate-900">Selected Entities</h3>
					</div>
					<div class="space-y-1.5">
						{#each previewEntities as entity}
							<div
								class="flex items-center gap-2 text-sm px-3 py-2 bg-white rounded border border-slate-200"
							>
								<div class="w-1.5 h-1.5 bg-teal-500 rounded-full"></div>
								<span class="font-medium text-slate-700 flex-1">{entity.label}</span>
								{#if entity.domain}
									<span
										class="text-xs px-2 py-0.5 bg-slate-100 text-slate-600 rounded-full font-medium"
									>
										{entity.domain}
									</span>
								{/if}
							</div>
						{/each}
						{#if overflowCount > 0}
							<div class="text-sm text-slate-500 px-3 py-2 italic">
								...and {overflowCount} more {overflowCount === 1 ? 'entity' : 'entities'}
							</div>
						{/if}
					</div>
				</div>

				<!-- Domain Assignment -->
				<div class="space-y-3">
					<div class="flex items-center gap-2">
						<Icon icon="lucide:folder" class="w-5 h-5 text-slate-700" />
						<label for="bulk-domain-select" class="text-sm font-semibold text-slate-900">
							Assign Domain
						</label>
					</div>
					<select
						id="bulk-domain-select"
						bind:value={selectedDomain}
						class="w-full px-4 py-2.5 border-2 border-slate-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-teal-500 disabled:bg-slate-100 disabled:cursor-not-allowed font-medium text-slate-900 bg-white"
						disabled={processing}
					>
						<option value="">— No change —</option>
						{#each allDomains as domain}
							<option value={domain}>{domain}</option>
						{/each}
					</select>
					<p class="text-xs text-slate-500 pl-1">
						Select a domain to assign to all selected entities
					</p>
				</div>

				<!-- Add Tags Section -->
				<div class="space-y-3">
					<div class="flex items-center gap-2">
						<Icon icon="lucide:plus-circle" class="w-5 h-5 text-emerald-600" />
						<h3 class="text-sm font-semibold text-slate-900">Add Tags</h3>
					</div>

					<!-- New tag input -->
					<div class="flex gap-2">
						<input
							type="text"
							bind:value={newTagInput}
							onkeydown={handleNewTagKeydown}
							placeholder="Type new tag name..."
							class="flex-1 px-4 py-2 border-2 border-slate-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 disabled:bg-slate-100 text-sm font-medium"
							disabled={processing}
						/>
						<button
							onclick={handleAddNewTag}
							disabled={!newTagInput.trim() || processing}
							class="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium text-sm flex items-center gap-2 shadow-sm"
						>
							<Icon icon="lucide:plus" class="w-4 h-4" />
							Add
						</button>
					</div>

					<!-- Existing tags to add -->
					{#if allTags.length > 0}
						<div class="bg-slate-50 rounded-lg p-4 border border-slate-200">
							<p class="text-xs text-slate-600 mb-3 font-medium">Or select from existing tags:</p>
							<div class="flex flex-wrap gap-2">
								{#each allTags as tag}
									<button
										onclick={() => toggleTagToAdd(tag)}
										class="px-3 py-1.5 text-sm rounded-lg border-2 transition-all font-medium {tagsToAdd.includes(
											tag
										)
											? 'bg-emerald-100 border-emerald-500 text-emerald-800'
											: 'bg-white border-slate-300 text-slate-700 hover:border-emerald-400'}"
										disabled={processing}
									>
										{#if tagsToAdd.includes(tag)}
											<Icon icon="lucide:check" class="w-3 h-3 inline-block mr-1" />
										{/if}
										{tag}
									</button>
								{/each}
							</div>
						</div>
					{/if}

					<!-- Selected tags to add -->
					{#if tagsToAdd.length > 0}
						<div class="bg-emerald-50 rounded-lg p-4 border-2 border-emerald-200">
							<p class="text-xs text-emerald-700 mb-2 font-semibold">Will be added:</p>
							<div class="flex flex-wrap gap-2">
								{#each tagsToAdd as tag}
									<span
										class="px-3 py-1 text-sm bg-emerald-600 text-white rounded-full font-medium flex items-center gap-1.5 shadow-sm"
									>
										{tag}
										<button
											onclick={() => toggleTagToAdd(tag)}
											class="hover:bg-emerald-700 rounded-full p-0.5"
											disabled={processing}
										>
											<Icon icon="lucide:x" class="w-3 h-3" />
										</button>
									</span>
								{/each}
							</div>
						</div>
					{/if}
				</div>

				<!-- Remove Tags Section -->
				{#if commonTags.length > 0}
					<div class="space-y-3">
						<div class="flex items-center gap-2">
							<Icon icon="lucide:minus-circle" class="w-5 h-5 text-rose-600" />
							<h3 class="text-sm font-semibold text-slate-900">Remove Tags</h3>
						</div>

						<div class="bg-slate-50 rounded-lg p-4 border border-slate-200">
							<p class="text-xs text-slate-600 mb-3 font-medium">
								Tags common to all selected entities:
							</p>
							<div class="flex flex-wrap gap-2">
								{#each commonTags as tag}
									<button
										onclick={() => toggleTagToRemove(tag)}
										class="px-3 py-1.5 text-sm rounded-lg border-2 transition-all font-medium {tagsToRemove.includes(
											tag
										)
											? 'bg-rose-100 border-rose-500 text-rose-800'
											: 'bg-white border-slate-300 text-slate-700 hover:border-rose-400'}"
										disabled={processing}
									>
										{#if tagsToRemove.includes(tag)}
											<Icon icon="lucide:check" class="w-3 h-3 inline-block mr-1" />
										{/if}
										{tag}
									</button>
								{/each}
							</div>
						</div>

						<!-- Selected tags to remove -->
						{#if tagsToRemove.length > 0}
							<div class="bg-rose-50 rounded-lg p-4 border-2 border-rose-200">
								<p class="text-xs text-rose-700 mb-2 font-semibold">Will be removed:</p>
								<div class="flex flex-wrap gap-2">
									{#each tagsToRemove as tag}
										<span
											class="px-3 py-1 text-sm bg-rose-600 text-white rounded-full font-medium flex items-center gap-1.5 shadow-sm"
										>
											{tag}
											<button
												onclick={() => toggleTagToRemove(tag)}
												class="hover:bg-rose-700 rounded-full p-0.5"
												disabled={processing}
											>
												<Icon icon="lucide:x" class="w-3 h-3" />
											</button>
										</span>
									{/each}
								</div>
							</div>
						{/if}
					</div>
				{:else}
					<div class="bg-slate-50 rounded-lg p-4 border border-slate-200">
						<p class="text-sm text-slate-600 flex items-center gap-2">
							<Icon icon="lucide:info" class="w-4 h-4" />
							No tags are common to all selected entities
						</p>
					</div>
				{/if}

				<!-- Progress Indicator (shown for 50+ entities) -->
				{#if processing && selectedCount >= 50}
					<div class="bg-teal-50 rounded-lg p-4 border-2 border-teal-200">
						<div class="flex items-center gap-3">
							<Icon icon="lucide:loader-2" class="w-5 h-5 text-teal-600 animate-spin" />
							<div class="flex-1">
								<p class="text-sm font-semibold text-teal-900">Processing bulk operation...</p>
								<p class="text-xs text-teal-700 mt-1">
									Updating {selectedCount} entities
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
