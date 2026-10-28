<script lang="ts">
	import Icon from "@iconify/svelte";
	import { goto } from "$app/navigation";
	import type { Entity, ModelInfo } from "$lib/types";
	import { entityDetailModal, entitySelection, modelingStyle, activeFramework } from "$lib/stores";
	import DomainBadge from "./DomainBadge.svelte";
	import { readModelRef } from "$lib/utils/entity-compat";
	import { bindEntityToModel } from "$lib/utils/entity-binding";
	import { getEntityDetailPath } from "$lib/utils/entity-list-route";
	import { getFrameworkCopy, formatModelHint } from "$lib/utils/framework-display";
import { getEntityTypeStyle } from "$lib/utils/entity-type-style";
	import { SEVEN_W_LABELS, SEVEN_W_BADGE_CLASSES } from "$lib/utils/seven-ws";

	type Props = {
		entity: Entity;
	};

	let { entity }: Props = $props();

	// Determine entity type icon
	const typeStyle = $derived(getEntityTypeStyle(entity.entity_type));
	const typeIcon = $derived($modelingStyle === 'dimensional_model' ? typeStyle.icon : "lucide:box");

	// 7Ws annotation type badge (for dimensions)
	const annotationTypeLabel = $derived(() => {
		if (!entity.annotation_type) return null;
		return SEVEN_W_LABELS[entity.annotation_type] || null;
	});

	const annotationTypeColor = $derived(() => {
		if (!entity.annotation_type) return '';
		return SEVEN_W_BADGE_CLASSES[entity.annotation_type] || '';
	});

	// Check if entity is selected
	const isSelected = $derived($entitySelection.has(entity.id));

	// Handle checkbox toggle
	function handleCheckboxToggle(e: Event) {
		e.stopPropagation();
		const checkbox = e.target as HTMLInputElement;
		const newSelection = new Set($entitySelection);

		if (checkbox.checked) {
			newSelection.add(entity.id);
		} else {
			newSelection.delete(entity.id);
		}

		entitySelection.set(newSelection);
	}

	// Handle row click (open detail modal)
	function handleRowClick() {
		entityDetailModal.set({ open: true, entityId: entity.id });
		void goto(getEntityDetailPath(entity.id));
	}

	let isDragOver = $state(false);

	function handleModelDragOver(event: DragEvent) {
		event.preventDefault();
		event.stopPropagation();
		isDragOver = true;
		if (event.dataTransfer) {
			event.dataTransfer.dropEffect = "copy";
		}
	}

	function handleModelDragEnter(event: DragEvent) {
		event.preventDefault();
		event.stopPropagation();
		isDragOver = true;
	}

	function handleModelDragLeave(event: DragEvent) {
		const currentTarget = event.currentTarget as HTMLElement;
		const relatedTarget = event.relatedTarget;
		if (relatedTarget instanceof HTMLElement && currentTarget.contains(relatedTarget)) {
			return;
		}
		isDragOver = false;
	}

	function handleModelDrop(event: DragEvent) {
		event.preventDefault();
		event.stopPropagation();
		isDragOver = false;

		const json = event.dataTransfer?.getData("application/model-ref");
		if (!json) return;

		try {
			const model = JSON.parse(json) as ModelInfo;
			if (model.unique_id) {
				bindEntityToModel(entity.id, model);
			}
		} catch (error) {
			console.warn("Could not bind dropped model:", error);
		}
	}

	// Get visible tags (max 3, +N more if overflow)
	const { visibleTags, hiddenCount } = $derived.by(() => {
		const tags = entity.tags || [];
		const visible = tags.slice(0, 3);
		const hidden = Math.max(0, tags.length - 3);
		return { visibleTags: visible, hiddenCount: hidden };
	});

	// Get visible domains (max 2, +N more if overflow)
	const { visibleDomains, hiddenDomainCount } = $derived.by(() => {
		const rawDomains = Array.isArray(entity.domains) && entity.domains.length > 0
			? entity.domains
			: entity.domain
				? [entity.domain]
				: [];
		const cleaned = rawDomains.map((domain) => domain.trim()).filter(Boolean);
		const unique = Array.from(new Set(cleaned));
		const visible = unique.slice(0, 2);
		const hidden = Math.max(0, unique.length - 2);
		return { visibleDomains: visible, hiddenDomainCount: hidden };
	});

	// Get roles (for dimensions only)
	const entityRoles = $derived.by(() => {
		if (entity.entity_type !== 'dimension') return [];
		return (entity as any).roles || [];
	});

	// Bound model reference (prefers new `model_ref`, falls back to legacy `dbt_model`)
	const boundModelRef = $derived(readModelRef(entity));
	const frameworkCopy = $derived(getFrameworkCopy($activeFramework));
</script>

<div
	class="bg-white border-b border-gray-200 px-4 py-2 flex items-center gap-3 hover:bg-gray-50 transition-colors cursor-pointer group"
	class:ring-2={isDragOver}
	class:ring-primary-300={isDragOver}
	class:bg-primary-50={isDragOver}
	class:border-primary-400={isDragOver}
	role="row"
	onclick={handleRowClick}
	onkeydown={(e) => e.key === "Enter" && handleRowClick()}
	ondragenter={handleModelDragEnter}
	ondragover={handleModelDragOver}
	ondragleave={handleModelDragLeave}
	ondrop={handleModelDrop}
	tabindex="0"
>
	<!-- Checkbox (always visible for selection) -->
	<input
		type="checkbox"
		checked={isSelected}
		onchange={handleCheckboxToggle}
		onclick={(e) => e.stopPropagation()}
		class="w-4 h-4 rounded border-gray-300 text-primary-600 cursor-pointer flex-shrink-0"
		title="Select entity"
	/>

	<!-- Entity Icon -->
	<div
		class="flex-shrink-0 {$modelingStyle === 'dimensional_model' ? typeStyle.iconClass : 'text-slate-500'}"
	>
		<Icon icon={typeIcon} class="w-5 h-5" />
	</div>

	<!-- Entity Info (name, type, domain, tags) - Horizontal Layout -->
	<div class="flex-1 min-w-0 flex items-center gap-3">
		<!-- Entity name -->
		<span class="text-sm font-semibold text-slate-800 truncate min-w-[200px]">
			{entity.label}
		</span>

		<!-- dbt build status badge — reserved slot so later badges stay aligned whether or not the entity is bound. Uses the same check icon/color as the "Bound" filter in the sidebar for consistency. -->
		<span
			class="flex-shrink-0 inline-flex items-center justify-center w-4 text-primary-600"
			title={boundModelRef ? formatModelHint(frameworkCopy.builtHint, boundModelRef.split('.').pop() ?? '') : undefined}
		>
			{#if boundModelRef}
				<Icon icon="lucide:check" class="h-3.5 w-3.5" aria-hidden="true" />
			{/if}
		</span>

		<!-- Type badge (only visible in dimensional modeling) -->
		{#if $modelingStyle === 'dimensional_model'}
			<span
				class="inline-flex items-center gap-1 px-2 py-0.5 rounded border text-xs font-medium whitespace-nowrap flex-shrink-0 {typeStyle.badge}"
				title={`Entity Type: ${typeStyle.label}`}
			>
				{typeStyle.label}
			</span>
		{/if}

		<!-- 7Ws annotation badge (dimensional modeling only) -->
		{#if $modelingStyle === 'dimensional_model' && annotationTypeLabel()}
			<span
				class="inline-flex items-center px-2 py-0.5 rounded border text-xs font-medium whitespace-nowrap flex-shrink-0 {annotationTypeColor()}"
				title="Annotation Type: {annotationTypeLabel()}"
			>
				{annotationTypeLabel()}
			</span>
		{/if}

		<!-- Domain badges (if present) -->
		{#if visibleDomains.length > 0}
			<div class="flex items-center gap-1.5 flex-shrink-0">
				{#each visibleDomains as domain}
					<DomainBadge {domain} size="small" />
				{/each}
				{#if hiddenDomainCount > 0}
					<span
						class="inline-flex items-center px-2 py-0.5 rounded-full bg-gray-200 text-gray-700 text-[11px] font-medium whitespace-nowrap"
						title={`${hiddenDomainCount} more domain${hiddenDomainCount === 1 ? "" : "s"}`}
					>
						+{hiddenDomainCount}
					</span>
				{/if}
			</div>
		{/if}

		<!-- Tags as compact chips -->
		{#if visibleTags.length > 0 || hiddenCount > 0}
			<div class="flex items-center gap-1.5 flex-wrap">
				{#each visibleTags as tag}
					<span
						class="inline-flex items-center px-2 py-0.5 rounded-full bg-gray-200 text-gray-700 text-[11px] font-medium whitespace-nowrap"
						title={`Tag: ${tag}`}
					>
						{tag}
					</span>
				{/each}

				{#if hiddenCount > 0}
					<span
						class="inline-flex items-center px-2 py-0.5 rounded-full bg-gray-300 text-gray-700 text-[11px] font-medium whitespace-nowrap"
						title={`${hiddenCount} more tag${hiddenCount === 1 ? "" : "s"}`}
					>
						+{hiddenCount}
					</span>
				{/if}
			</div>
		{/if}

		<!-- Roles (for dimensions only) -->
		{#if entityRoles.length > 0}
			<div class="flex items-center gap-1.5 flex-shrink-0">
				<span class="text-[10px] text-gray-500 uppercase tracking-wide font-semibold">Roles:</span>
				<span class="text-[11px] text-gray-600 font-medium truncate max-w-[200px]" title={entityRoles.join(', ')}>
					{entityRoles.join(', ')}
				</span>
			</div>
		{/if}
	</div>

	<!-- Right side action hint (visible on hover) -->
	<div class="flex-shrink-0 text-gray-400 group-hover:text-gray-600 transition-colors">
		<Icon icon="lucide:chevron-right" class="w-4 h-4" />
	</div>
</div>
