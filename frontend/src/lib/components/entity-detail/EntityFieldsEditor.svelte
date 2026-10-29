<script lang="ts">
	import Icon from '@iconify/svelte';
	import { frameworkModels } from '$lib/stores';
	import { updateModelSchema, getManifest } from '$lib/api';
	import type { DraftedField, ModelInfo } from '$lib/types';
	import type { MergedField } from '$lib/utils/merged-fields';
	import { buildMaterializeColumns, moveItem } from '$lib/utils/entity-detail';
	import { formatModelHint } from '$lib/utils/framework-display';
	import type { getFrameworkCopy, getFrameworkDisplay } from '$lib/utils/framework-display';
	import DropIndicator from '../DropIndicator.svelte';
	import type { EntityDetailForm } from './entity-detail-form.svelte';

	let {
		form,
		mergedFields,
		isBoundEntity,
		boundModel,
		frameworkCopy,
		frameworkDisplay
	}: {
		form: EntityDetailForm;
		mergedFields: MergedField[];
		isBoundEntity: boolean;
		boundModel: ModelInfo | null;
		frameworkCopy: ReturnType<typeof getFrameworkCopy>;
		frameworkDisplay: ReturnType<typeof getFrameworkDisplay>;
	} = $props();

	// Drag-to-reorder state for drafted fields
	let lastMouseDownTarget: HTMLElement | null = null;
	let dragIndex = $state<number | null>(null);
	let dropIndex = $state<number | null>(null);
	let dropPosition = $state<'before' | 'after' | null>(null);

	function onAttributeDragStart(index: number, e: DragEvent) {
		const mouseDownTag = lastMouseDownTarget?.tagName ?? null;
		if (mouseDownTag === 'INPUT' || mouseDownTag === 'SELECT' || mouseDownTag === 'TEXTAREA') {
			e.preventDefault();
			return;
		}
		e.dataTransfer!.effectAllowed = 'move';
		// Defer state update so browser captures drag image before DOM changes
		setTimeout(() => {
			dragIndex = index;
			dropIndex = null;
			dropPosition = null;
		}, 0);
	}

	function onAttributeDragOver(index: number, e: DragEvent) {
		if (dragIndex === null || dragIndex === index) return;
		e.preventDefault();
		e.dataTransfer!.dropEffect = 'move';
		dropIndex = index;
		dropPosition = dragIndex < index ? 'after' : 'before';
	}

	function onAttributeDrop(index: number, e: DragEvent) {
		e.preventDefault();
		if (dragIndex !== null && dragIndex !== index) {
			form.editableDraftedFields = moveItem(form.editableDraftedFields, dragIndex, index);
			form.isDirty = true;
		}
		dragIndex = null;
		dropIndex = null;
		dropPosition = null;
	}

	function onAttributeDragEnd() {
		dragIndex = null;
		dropIndex = null;
		dropPosition = null;
	}

	async function materializeDraft(draftIndex: number) {
		if (!boundModel) return;
		const draft = form.editableDraftedFields[draftIndex];
		if (!draft) return;
		form.materializeError = '';
		try {
			const columns = buildMaterializeColumns(boundModel.columns, draft);
			await updateModelSchema(boundModel.name, boundModel.version ?? undefined, columns);
			const warning = `Column '${draft.name}' added to schema.yml. You still need to add it to the SQL in ${boundModel.name}.sql.`;
			form.materializeWarnings = form.materializeWarnings.includes(warning)
				? form.materializeWarnings
				: [...form.materializeWarnings, warning];
			// Remove from drafts — it's now materialized in schema.yml
			form.editableDraftedFields = form.editableDraftedFields.filter((_, i) => i !== draftIndex);
			// Refresh manifest so auto-promotion runs
			const models = await getManifest();
			frameworkModels.set(models);
		} catch (e: unknown) {
			form.materializeError = e instanceof Error ? e.message : 'Failed to materialize field';
		}
	}
</script>

<!-- Attributes (merged dbt + drafted) -->
<div>
	<label class="block text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wide">
		Attributes ({mergedFields.length})
		{#if isBoundEntity}<span class="font-normal normal-case text-xs text-gray-400 ml-1">{frameworkCopy.materializedColumnsNote}</span>{/if}
	</label>

	{#if form.materializeWarnings.length > 0}
		<div class="mb-3 px-3 py-2 bg-amber-50 border border-amber-300 text-amber-800 text-sm rounded-lg flex items-start gap-2 shadow-2xs">
			<Icon icon="lucide:alert-triangle" class="w-4 h-4 mt-0.5 shrink-0 text-amber-600" />
			<div class="space-y-1">
				{#each form.materializeWarnings as warning}
					<div>{warning}</div>
				{/each}
			</div>
			<button onclick={() => (form.materializeWarnings = [])} class="ml-auto text-amber-600 hover:text-amber-800" aria-label="Dismiss warning">
				<Icon icon="lucide:x" class="w-4 h-4" />
			</button>
		</div>
	{/if}
	{#if form.materializeError}
		<div class="mb-3 px-3 py-2 bg-red-50 border border-red-300 text-red-800 text-sm rounded-lg shadow-2xs">{form.materializeError}</div>
	{/if}

	<div class="border border-gray-200 rounded-lg overflow-hidden shadow-2xs bg-white">
		{#if mergedFields.length > 0}
			<!-- Header -->
			<div class="bg-gray-50/90 border-b border-gray-200 px-3.5 py-2.5 grid grid-cols-12 gap-2 text-xs font-semibold text-gray-600 uppercase tracking-wider">
				<div class="col-span-2">Name</div>
				<div class="col-span-1">Type</div>
				<div class="col-span-6">Description</div>
				<div class="col-span-3">Origin</div>
			</div>
			<div class="divide-y divide-gray-100">
			{#each mergedFields as field (field.origin === 'draft' ? `draft-${field.draftIndex}` : `dbt-${field.name}`)}
			<div
				class="relative px-3.5 py-2 hover:bg-primary-50/20 group transition-colors odd:bg-white even:bg-gray-50/30"
				data-testid={`merged-field-row-${field.name}`}
				draggable={field.origin === 'draft'}
				ondragstart={field.origin === 'draft' ? (e) => onAttributeDragStart(field.draftIndex, e) : undefined}
				ondragover={field.origin === 'draft' ? (e) => onAttributeDragOver(field.draftIndex, e) : undefined}
				ondrop={field.origin === 'draft' ? (e) => onAttributeDrop(field.draftIndex, e) : undefined}
				ondragend={field.origin === 'draft' ? onAttributeDragEnd : undefined}
				style={field.origin === 'draft' && dragIndex === field.draftIndex ? 'opacity: 0.5;' : ''}
				onmousedown={field.origin === 'draft' ? (e) => { lastMouseDownTarget = e.target as HTMLElement; } : undefined}
			>
				<div class="grid grid-cols-12 gap-2 items-center">
					<!-- Name -->
					<div class="col-span-2">
						{#if field.origin === 'draft'}
							<div class="flex items-center gap-1">
								<Icon icon="lucide:grip-vertical" class="w-4 h-4 text-gray-300 cursor-grab active:cursor-grabbing shrink-0" />
								<input
									type="text"
									value={field.name}
									oninput={(e) => form.updateDraftedField(field.draftIndex, { name: (e.target as HTMLInputElement).value })}
									class="w-full px-2.5 py-1.5 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 font-medium text-sm text-gray-900 bg-white"
									placeholder="attribute_name"
								/>
							</div>
						{:else}
							<input
								type="text"
								value={field.name}
								readonly
								class="w-full px-2.5 py-1.5 border border-gray-200 rounded-md focus:outline-none font-medium text-sm bg-gray-50/80 text-gray-700 cursor-default"
								placeholder="attribute_name"
							/>
						{/if}
					</div>
					<!-- Type -->
					<div class="col-span-1">
						{#if field.origin === 'dbt'}
							<span class="px-1 py-1.5 text-xs font-mono uppercase text-gray-500 font-semibold">{field.datatype ?? '—'}</span>
						{:else}
							<select
								value={field.datatype}
								onchange={(e) => form.updateDraftedField(field.draftIndex, { datatype: (e.target as HTMLSelectElement).value as DraftedField['datatype'] })}
								class="w-full px-1.5 py-1.5 border border-gray-300 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 text-xs font-mono uppercase text-gray-700 font-medium cursor-pointer"
							>
								<option value="text">text</option>
								<option value="int">int</option>
								<option value="float">float</option>
								<option value="bool">bool</option>
								<option value="date">date</option>
								<option value="timestamp">timestamp</option>
							</select>
						{/if}
					</div>
					<!-- Description (editable for both origins) -->
					<div class="col-span-6">
						{#if field.origin === 'dbt'}
							<input
								type="text"
								value={form.materializedDescriptionEdits.get(field.name) ?? form.liveSchemaDescriptions.get(field.name) ?? field.description ?? ''}
								oninput={(e) => form.setMaterializedDescription(field.name, (e.target as HTMLInputElement).value)}
								class="w-full px-2.5 py-1.5 border border-gray-200 hover:border-gray-300 rounded-md text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 bg-white placeholder-gray-400"
								placeholder="Description (optional)"
							/>
						{:else}
							<input
								type="text"
								value={field.description ?? ''}
								oninput={(e) => form.updateDraftedField(field.draftIndex, { description: (e.target as HTMLInputElement).value })}
								class="w-full px-2.5 py-1.5 border border-gray-300 hover:border-gray-400 rounded-md text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 bg-white placeholder-gray-400"
								placeholder="Description (optional)"
							/>
						{/if}
					</div>
					<!-- Origin (read-only) -->
					<div class={field.origin === 'dbt' ? "col-span-3 text-xs text-gray-600 font-mono space-y-0.5" : "col-span-2 text-xs text-gray-600 font-mono space-y-0.5"}>
						{#if field.origin === 'dbt'}
							<span
								class="inline-flex items-center text-gray-400"
								aria-label={formatModelHint(frameworkCopy.materializedHint, `'${boundModel?.name ?? ''}'`)}
								title={formatModelHint(frameworkCopy.materializedHint, `'${boundModel?.name ?? ''}'`)}
							>
								<img
									src={frameworkDisplay.icon}
									alt={frameworkDisplay.alt}
									class="h-3.5 w-3.5 opacity-70"
									aria-hidden="true"
								/>
							</span>
						{/if}
						{#if field.originRefs?.length}
							{#each field.originRefs as entry (JSON.stringify(entry))}
								{#each Object.entries(entry) as [originKey, originValue]}
									<div
										class="truncate text-gray-500 text-[11px]"
										data-testid="origin-entry"
										title={originKey ? `${originKey}: ${originValue}` : originValue}
									>
										{originKey ? `${originKey}: ${originValue}` : originValue}
									</div>
								{/each}
							{/each}
						{/if}
					</div>
					<!-- Actions -->
					{#if field.origin === 'draft'}
						<div class="col-span-1 flex justify-end gap-1 items-center">
							{#if isBoundEntity && boundModel}
								<button
									type="button"
									onclick={() => materializeDraft(field.draftIndex)}
									class="p-1.5 text-primary-600 hover:text-primary-800 hover:bg-primary-50 rounded transition-colors"
									aria-label={`Materialize ${field.name} into ${boundModel.name}'s schema.yml`}
									title={`Write to ${boundModel.name}'s schema.yml`}
								>
									<Icon icon="lucide:arrow-up-to-line" class="w-3.5 h-3.5" />
								</button>
							{/if}
							<button
								type="button"
								onclick={() => form.deleteDraftedField(field.draftIndex)}
								class="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors"
								title="Delete attribute"
							>
								<Icon icon="lucide:trash-2" class="w-3.5 h-3.5" />
							</button>
						</div>
					{/if}
				</div>
				{#if field.origin === 'draft' && dropIndex === field.draftIndex && dropPosition !== null}
					<DropIndicator position={dropPosition} />
				{/if}
			</div>
			{/each}
			</div>
		{:else}
			<div class="p-6 text-center text-gray-400 text-sm italic">
				No attributes defined
			</div>
		{/if}
	</div>

	<button
		type="button"
		onclick={form.addDraftedField}
		class="mt-3 w-full px-4 py-2 text-xs font-semibold text-primary-700 bg-primary-50/70 border border-dashed border-primary-300 rounded-lg hover:bg-primary-100/70 hover:border-primary-400 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 transition-all flex items-center justify-center gap-2 shadow-3xs"
	>
		<Icon icon="lucide:plus" class="w-4 h-4" />
		Add Attribute
	</button>
</div>
