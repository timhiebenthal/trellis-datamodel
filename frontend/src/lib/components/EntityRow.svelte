<script lang="ts">
	import Icon from "@iconify/svelte";
	import type { Entity } from "$lib/types";
	import { entityDetailModal, entitySelection, modelingStyle } from "$lib/stores";
	import DomainBadge from "./DomainBadge.svelte";
	import { readModelRef } from "$lib/utils/entity-compat";

	type Props = {
		entity: Entity;
	};

	let { entity }: Props = $props();

	// Determine entity type icon
	const typeIcon = $derived(() => {
		if ($modelingStyle === 'dimensional_model') {
			if (entity.entity_type === "dimension") {
				return "lucide:list";
			} else if (entity.entity_type === "fact") {
				return "lucide:bar-chart-3";
			} else {
				return "lucide:help-circle";
			}
		}
		return "lucide:box";
	});

	// Type label
	const typeLabel = $derived(() => {
		if (entity.entity_type === "dimension") {
			return "Dimension";
		} else if (entity.entity_type === "fact") {
			return "Fact";
		} else {
			return "Unclassified";
		}
	});

	// Type badge color
	const typeBadgeColor = $derived(() => {
		if (entity.entity_type === "dimension") {
			return "bg-green-100 text-green-700 border-green-300";
		} else if (entity.entity_type === "fact") {
			return "bg-blue-100 text-blue-700 border-blue-300";
		} else {
			return "bg-gray-100 text-gray-700 border-gray-300";
		}
	});

	// 7Ws annotation type badge (for dimensions)
	const annotationTypeLabel = $derived(() => {
		if (!entity.annotation_type) return null;
		const typeMap: Record<string, string> = {
			who: 'Who',
			what: 'What',
			when: 'When',
			where: 'Where',
			how: 'How',
			why: 'Why',
			how_many: 'How Many'
		};
		return typeMap[entity.annotation_type] || null;
	});

	const annotationTypeColor = $derived(() => {
		if (!entity.annotation_type) return '';
		const colorMap: Record<string, string> = {
			who: 'bg-blue-100 text-blue-800 border-blue-200',
			what: 'bg-purple-100 text-purple-800 border-purple-200',
			when: 'bg-green-100 text-green-800 border-green-200',
			where: 'bg-yellow-100 text-yellow-800 border-yellow-200',
			how: 'bg-orange-100 text-orange-800 border-orange-200',
			why: 'bg-red-100 text-red-800 border-red-200',
			how_many: 'bg-indigo-100 text-indigo-800 border-indigo-200'
		};
		return colorMap[entity.annotation_type] || '';
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
</script>

<div
	class="bg-white border-b border-gray-200 px-4 py-2 flex items-center gap-3 hover:bg-gray-50 transition-colors cursor-pointer group"
	role="row"
	onclick={handleRowClick}
	onkeydown={(e) => e.key === "Enter" && handleRowClick()}
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
		class="flex-shrink-0"
		class:text-green-600={$modelingStyle === 'dimensional_model' && entity.entity_type === "dimension"}
		class:text-blue-600={$modelingStyle === 'dimensional_model' && entity.entity_type === "fact"}
		class:text-gray-600={$modelingStyle === 'dimensional_model' && entity.entity_type !== "dimension" && entity.entity_type !== "fact"}
		class:text-slate-500={$modelingStyle !== 'dimensional_model'}
	>
		<Icon icon={typeIcon()} class="w-5 h-5" />
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
			title={boundModelRef ? `Built with dbt: ${boundModelRef.split('.').pop()}` : undefined}
		>
			{#if boundModelRef}
				<Icon icon="lucide:check" class="h-3.5 w-3.5" aria-hidden="true" />
			{/if}
		</span>

		<!-- Type badge (only visible in dimensional modeling) -->
		{#if $modelingStyle === 'dimensional_model'}
			<span
				class="inline-flex items-center gap-1 px-2 py-0.5 rounded border text-xs font-medium whitespace-nowrap flex-shrink-0 {typeBadgeColor()}"
				title={`Entity Type: ${typeLabel()}`}
			>
				{typeLabel()}
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
