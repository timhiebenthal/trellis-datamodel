<script lang="ts">
	import Icon from '@iconify/svelte';
	import type { Node } from '@xyflow/svelte';
	import { nodes, edges, modelingStyle } from '$lib/stores';
	import type { EntityData, OriginEntry } from '$lib/types';
	import type { MergedField } from '$lib/utils/merged-fields';
	import { exportEntityToExcel } from '$lib/utils/excel-export';
	import { formatEntityAsMarkdown } from '$lib/utils/markdown-export';
	import type { getFrameworkCopy } from '$lib/utils/framework-display';
	import type { EntityDetailForm } from './entity-detail-form.svelte';

	let {
		form,
		entity,
		mergedFields,
		frameworkCopy,
		onCancel,
		onSave,
		onConfirmDelete
	}: {
		form: EntityDetailForm;
		entity: Node;
		mergedFields: MergedField[];
		frameworkCopy: ReturnType<typeof getFrameworkCopy>;
		onCancel: () => void;
		onSave: () => void;
		onConfirmDelete: () => void;
	} = $props();

	let isExporting = $state(false);
	let isCopyingMarkdown = $state(false);

	function handleDelete() {
		form.showDeleteConfirm = true;
	}

	function cancelDelete() {
		form.showDeleteConfirm = false;
	}

	function buildExportAttributes(): Array<{ name: string; type: string; description?: string; origin?: OriginEntry[] }> {
		const attributes = mergedFields.map((f) => ({
			name: f.name,
			type: f.datatype ?? '',
			description: f.description ?? '',
			origin: f.originRefs,
		}));
		return attributes;
	}

	async function handleExportToExcel() {
		if (!entity) return;

		isExporting = true;
		try {
			// Extract entity ID from the current entity
			const entityId = entity.id;

			// Call export function with all required data
			exportEntityToExcel(
				entity.data as unknown as EntityData,
				buildExportAttributes(),
				$edges,
				$nodes,
				entityId,
				$modelingStyle === 'dimensional_model',
				frameworkCopy.modelColumnLabel
			);

			// Success - file downloads automatically
		} catch (error) {
			console.error('Export failed:', error);
			alert(`Failed to export entity: ${error instanceof Error ? error.message : 'Unknown error'}`);
		} finally {
			isExporting = false;
		}
	}

	async function handleCopyAsMarkdown() {
		if (!entity) return;
		isCopyingMarkdown = true;
		try {
			const entityId = entity.id;
			const exportAttributes = buildExportAttributes();
			const markdown = formatEntityAsMarkdown(
				entity.data as unknown as EntityData,
				exportAttributes,
				$edges,
				$nodes,
				entityId,
				$modelingStyle === 'dimensional_model',
				frameworkCopy.modelColumnLabel
			);
			await navigator.clipboard.writeText(markdown);

			// Show success message
			form.showMarkdownSuccess = true;
			setTimeout(() => {
				form.showMarkdownSuccess = false;
			}, 3000);
		} catch (error) {
			console.error('Copy failed:', error);
			alert(`Failed to copy: ${error instanceof Error ? error.message : 'Unknown error'}`);
		} finally {
			isCopyingMarkdown = false;
			form.showExportDropdown = false;
		}
	}
</script>

<!-- Footer Actions -->
<div
	class="px-8 py-5 border-t border-gray-200 bg-gray-50/80"
>
	{#if !form.showDeleteConfirm}
		<div class="flex items-center justify-between gap-4">
			<button
				onclick={handleDelete}
				class="px-3.5 py-2 text-xs font-semibold text-red-700 bg-red-50/80 border border-red-200 rounded-lg hover:bg-red-100 hover:border-red-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-all flex items-center gap-1.5 shadow-3xs"
			>
				<Icon icon="lucide:trash-2" class="w-3.5 h-3.5" />
				Delete Entity
			</button>

			<div class="flex gap-2.5">
				<div class="relative export-dropdown-container">
					<button
						onclick={() => (form.showExportDropdown = !form.showExportDropdown)}
						disabled={isExporting}
						class="px-3.5 py-2 text-xs font-semibold text-primary-700 bg-primary-50/80 border border-primary-200 rounded-lg hover:bg-primary-100 hover:border-primary-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 transition-all flex items-center gap-1.5 disabled:opacity-50 disabled:cursor-not-allowed shadow-3xs"
						aria-label="Export options"
					>
						{#if isExporting}
							<Icon icon="lucide:loader-2" class="w-3.5 h-3.5 animate-spin" />
						{:else}
							<Icon icon="lucide:download" class="w-3.5 h-3.5" />
						{/if}
						Export
						<Icon icon="lucide:chevron-down" class="w-3 h-3 transition-transform {form.showExportDropdown ? 'rotate-180' : ''}" />
					</button>

					<!-- Dropdown Menu -->
					{#if form.showExportDropdown}
						<div class="absolute bottom-full mb-2 right-0 bg-white border border-gray-200 rounded-lg shadow-xl overflow-hidden min-w-[200px] z-10 animate-fade-in">
							<button
								onclick={() => {
									handleExportToExcel();
									form.showExportDropdown = false;
								}}
								class="w-full px-3.5 py-2 text-left text-xs font-medium text-gray-700 hover:bg-gray-50 transition-colors flex items-center gap-2 whitespace-nowrap"
							>
								<Icon icon="lucide:file-spreadsheet" class="w-4 h-4 text-green-600" />
								Download as Excel
							</button>
							<button
								onclick={() => { handleCopyAsMarkdown(); }}
								disabled={isCopyingMarkdown}
								class="w-full px-3.5 py-2 text-left text-xs font-medium text-gray-700 hover:bg-gray-50 transition-colors flex items-center gap-2 whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed border-t border-gray-100"
							>
								{#if isCopyingMarkdown}
									<Icon icon="lucide:loader-2" class="w-4 h-4 animate-spin text-primary-600" />
								{:else}
									<Icon icon="lucide:clipboard-copy" class="w-4 h-4 text-primary-600" />
								{/if}
								Copy as Markdown
							</button>
						</div>
					{/if}
				</div>

				<button
					onclick={onCancel}
					class="px-4 py-2 text-xs font-semibold text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-400 transition-all shadow-3xs"
				>
					Cancel
				</button>
				<button
					onclick={onSave}
					disabled={!form.isDirty || !form.entityName.trim()}
					class="px-4 py-2 text-xs font-bold text-white bg-primary-600 hover:bg-primary-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 transition-all flex items-center gap-1.5 shadow-2xs disabled:opacity-50 disabled:cursor-not-allowed"
				>
					<Icon icon="lucide:save" class="w-3.5 h-3.5" />
					Save Changes
				</button>
			</div>
		</div>
	{:else}
		<!-- Delete Confirmation -->
		<div
			class="flex items-center justify-between p-3.5 bg-red-50 border border-red-200 rounded-lg shadow-2xs"
		>
			<div class="flex items-center gap-2.5">
				<Icon icon="lucide:alert-triangle" class="w-4 h-4 text-red-600 shrink-0" />
				<span class="text-xs font-medium text-red-900"
					>Are you sure you want to delete this entity? This action cannot be undone.</span
				>
			</div>
			<div class="flex gap-2">
				<button
					onclick={cancelDelete}
					class="px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
				>
					Cancel
				</button>
				<button
					onclick={onConfirmDelete}
					class="px-3 py-1.5 text-xs font-bold text-white bg-red-600 rounded-md hover:bg-red-700 transition-colors"
				>
					Delete
				</button>
			</div>
		</div>
	{/if}
</div>

<style>
	@keyframes fade-in {
		from {
			opacity: 0;
			transform: translateY(-10px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	.animate-fade-in {
		animation: fade-in 0.3s ease-out;
	}
</style>
