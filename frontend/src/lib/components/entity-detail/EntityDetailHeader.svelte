<script lang="ts">
	import Icon from '@iconify/svelte';
	import { frameworkModels, modelingStyle } from '$lib/stores';
	import type { AnnotationType, ModelInfo } from '$lib/types';
	import { getEntityTypeStyle } from '$lib/utils/entity-type-style';
	import { SEVEN_W_TYPES, SEVEN_W_LABELS, SEVEN_W_BADGE_CLASSES } from '$lib/utils/seven-ws';
	import type { getFrameworkCopy } from '$lib/utils/framework-display';
	import ModelBindingPicker from '../ModelBindingPicker.svelte';
	import type { EntityDetailForm } from './entity-detail-form.svelte';

	let {
		form,
		boundModels,
		frameworkCopy,
		onClose,
		onModelSelect
	}: {
		form: EntityDetailForm;
		boundModels: string[];
		frameworkCopy: ReturnType<typeof getFrameworkCopy>;
		onClose: () => void;
		onModelSelect: (model: ModelInfo) => void;
	} = $props();

	// Annotation type options for dimensions
	const annotationTypes: { value: AnnotationType; label: string; color: string }[] = SEVEN_W_TYPES.map(
		(value) => ({ value, label: SEVEN_W_LABELS[value], color: SEVEN_W_BADGE_CLASSES[value] })
	);
</script>

<!-- Header with primary accent -->
<div
	class="relative px-8 pt-8 pb-6 bg-gray-50"
>
	<div
		class="absolute top-0 left-0 right-0 h-1 bg-primary-600"
	></div>

	<div class="flex items-start justify-between">
		<div class="flex-1">
			<p class="mb-1 text-[11px] font-bold uppercase tracking-[0.16em] text-primary-700">
				Entity details
			</p>
			<h2
				id="entity-detail-modal-title"
				class="text-3xl font-bold text-gray-900"
				style="letter-spacing: -0.02em;"
			>
				{form.entityName || 'Entity'}
			</h2>
		</div>
		<button
			class="p-2 rounded-lg hover:bg-gray-200 text-gray-500 transition-colors"
			onclick={onClose}
			aria-label="Close"
		>
			<Icon icon="lucide:x" class="w-5 h-5" />
		</button>
	</div>

	<div class="mt-4 flex flex-wrap items-center gap-2.5" data-testid="entity-context">
		{#if $modelingStyle === 'dimensional_model'}
			<div class="flex flex-wrap items-center gap-1.5 bg-white px-2 py-1 rounded-lg border border-gray-200 shadow-sm" role="group" aria-label="Entity type">
				<span class="text-[11px] font-semibold text-gray-500 px-1">Type</span>
				<button
					type="button"
					aria-pressed={form.entityType === 'dimension'}
					class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border transition-all text-xs font-medium {form.entityType === 'dimension'
						? 'bg-green-100 border-green-300 text-green-800 shadow-xs'
						: 'bg-white border-transparent text-gray-600 hover:bg-gray-100'}"
					onclick={() => (form.entityType = 'dimension')}
				>
					<Icon icon={getEntityTypeStyle('dimension').icon} class="w-3.5 h-3.5 {form.entityType === 'dimension' ? getEntityTypeStyle('dimension').iconClass : 'text-gray-500'}" />
					Dimension
				</button>
				<button
					type="button"
					aria-pressed={form.entityType === 'fact'}
					class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border transition-all text-xs font-medium {form.entityType === 'fact'
						? 'bg-blue-100 border-blue-300 text-blue-800 shadow-xs'
						: 'bg-white border-transparent text-gray-600 hover:bg-gray-100'}"
					onclick={() => (form.entityType = 'fact')}
				>
					<Icon icon={getEntityTypeStyle('fact').icon} class="w-3.5 h-3.5 {form.entityType === 'fact' ? getEntityTypeStyle('fact').iconClass : 'text-gray-500'}" />
					Fact
				</button>
				<button
					type="button"
					aria-pressed={form.entityType === 'unclassified'}
					class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border transition-all text-xs font-medium {form.entityType === 'unclassified'
						? 'bg-gray-100 border-gray-300 text-gray-800 shadow-xs'
						: 'bg-white border-transparent text-gray-600 hover:bg-gray-100'}"
					onclick={() => (form.entityType = 'unclassified')}
				>
					<Icon icon={getEntityTypeStyle('unclassified').icon} class="w-3.5 h-3.5 {getEntityTypeStyle('unclassified').iconClass}" />
					Unclassified
				</button>
			</div>

			{#if form.entityType === 'dimension'}
				<div class="relative annotation-dropdown-container flex items-center gap-1.5 bg-white px-2 py-1 rounded-lg border border-gray-200 shadow-sm">
					<span class="text-[11px] font-semibold text-gray-500 px-1">7Ws</span>
					<button
						type="button"
						aria-label="Annotation type"
						class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md border transition-all text-xs font-medium hover:opacity-90 {form.annotationType
							? annotationTypes.find((a) => a.value === form.annotationType)?.color + ' border-current shadow-xs'
							: 'bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100'}"
						onclick={() => (form.show7WsDropdown = !form.show7WsDropdown)}
					>
						{form.annotationType ? annotationTypes.find((a) => a.value === form.annotationType)?.label : 'Select 7W...'}
						<Icon icon="lucide:chevron-down" class="w-3 h-3 transition-transform {form.show7WsDropdown ? 'rotate-180' : ''}" />
					</button>

					{#if form.show7WsDropdown}
						<div class="absolute z-20 top-full mt-1.5 left-0 bg-white border border-gray-200 rounded-lg shadow-xl overflow-hidden min-w-[170px] animate-fade-in">
							<div class="max-h-60 overflow-y-auto py-1">
								{#each annotationTypes.filter((opt) => opt.value !== 'how_many') as option}
									<button
										type="button"
										class="w-full px-3 py-1.5 text-left text-xs font-medium transition-colors hover:bg-gray-50 flex items-center gap-2 {form.annotationType === option.value
											? option.color
											: 'text-gray-700'}"
										onclick={() => {
											form.annotationType = option.value;
											form.show7WsDropdown = false;
										}}
									>
										{#if form.annotationType === option.value}
											<Icon icon="lucide:check" class="w-3.5 h-3.5" />
										{:else}
											<span class="w-3.5"></span>
										{/if}
										{option.label}
									</button>
								{/each}
								<button
									type="button"
									class="w-full px-3 py-1.5 text-left text-xs font-medium transition-colors hover:bg-gray-50 flex items-center gap-2 border-t border-gray-100 text-gray-500"
									onclick={() => {
										form.annotationType = undefined;
										form.show7WsDropdown = false;
									}}
								>
									{#if form.annotationType === undefined}
										<Icon icon="lucide:check" class="w-3.5 h-3.5" />
									{:else}
										<span class="w-3.5"></span>
									{/if}
									None
								</button>
							</div>
						</div>
					{/if}
				</div>
			{/if}
		{/if}

		<div class="flex min-w-0 flex-1 flex-wrap items-center gap-2" data-testid="model-binding-controls">
			{#if boundModels.length > 0}
				<div class="flex min-w-0 flex-1 flex-wrap items-center gap-2 rounded-lg border border-primary-200 bg-primary-50/80 px-3 py-1.5 shadow-sm" data-testid="bound-model-summary">
					<div class="flex items-center gap-1.5 shrink-0 text-primary-700">
						<Icon icon="lucide:layers" class="h-4 w-4 shrink-0 text-primary-600" />
						<span class="text-xs font-semibold">
							{frameworkCopy.boundModelsHeading} ({boundModels.length})
						</span>
					</div>
					{#each boundModels as model}
						<span class="max-w-full truncate rounded-md border border-primary-200/70 bg-white px-2 py-0.5 font-mono text-xs text-primary-900 shadow-2xs font-medium" title={model}>
							{model}
						</span>
					{/each}
				</div>
			{/if}
			{#if $frameworkModels.length > 0}
				<ModelBindingPicker
					selectedModelIds={boundModels}
					onSelect={onModelSelect}
				/>
			{/if}
			{#if form.bindingError}
				<span class="text-xs text-danger-700" role="alert">{form.bindingError}</span>
			{/if}
		</div>
	</div>
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
