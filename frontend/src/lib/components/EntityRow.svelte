<script lang="ts">
	import Icon from "@iconify/svelte";
	import type { Entity } from "$lib/types";
	import { entityDetailModal, entitySelection } from "$lib/stores";
	import DomainBadge from "./DomainBadge.svelte";

	type Props = {
		entity: Entity;
		selectionMode?: boolean;
	};

	let { entity, selectionMode = false }: Props = $props();

	// Determine entity type icon
	const typeIcon = $derived(() => {
		if (entity.entity_type === "dimension") {
			return "lucide:list";
		} else if (entity.entity_type === "fact") {
			return "lucide:bar-chart-3";
		} else {
			return "lucide:help-circle";
		}
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

	// Handle row click (open detail modal if not in selection mode)
	function handleRowClick() {
		if (!selectionMode) {
			entityDetailModal.set({ open: true, entityId: entity.id });
		}
	}

	// Get visible tags (max 3, +N more if overflow)
	const { visibleTags, hiddenCount } = $derived.by(() => {
		const tags = entity.tags || [];
		const visible = tags.slice(0, 3);
		const hidden = Math.max(0, tags.length - 3);
		return { visibleTags: visible, hiddenCount: hidden };
	});
</script>

<div
	class="bg-white border-b border-gray-200 px-4 py-2 flex items-center gap-3 hover:bg-gray-50 transition-colors cursor-pointer group"
	role="row"
	on:click={handleRowClick}
	on:keydown={(e) => e.key === "Enter" && handleRowClick()}
	tabindex="0"
>
	<!-- Checkbox (visible only in selection mode) -->
	{#if selectionMode}
		<input
			type="checkbox"
			checked={isSelected}
			on:change={handleCheckboxToggle}
			class="w-4 h-4 rounded border-gray-300 text-blue-600 cursor-pointer flex-shrink-0"
			title="Select entity"
		/>
	{/if}

	<!-- Entity Icon -->
	<div
		class="flex-shrink-0"
		class:text-green-600={entity.entity_type === "dimension"}
		class:text-blue-600={entity.entity_type === "fact"}
		class:text-gray-600={entity.entity_type !== "dimension" && entity.entity_type !== "fact"}
	>
		<Icon icon={typeIcon()} class="w-5 h-5" />
	</div>

	<!-- Entity Info (name, type, domain, tags) - Horizontal Layout -->
	<div class="flex-1 min-w-0 flex items-center gap-3">
		<!-- Entity name -->
		<span class="text-sm font-semibold text-slate-800 truncate min-w-[200px]">
			{entity.label}
		</span>

		<!-- Type badge -->
		<span
			class="inline-flex items-center gap-1 px-2 py-0.5 rounded border text-xs font-medium whitespace-nowrap flex-shrink-0 {typeBadgeColor()}"
		>
			{typeLabel()}
		</span>

		<!-- Domain badge (if present) -->
		{#if entity.domain}
			<div class="flex-shrink-0">
				<DomainBadge domain={entity.domain} size="small" />
			</div>
		{/if}

		<!-- Tags as compact chips -->
		{#if visibleTags.length > 0 || hiddenCount > 0}
			<div class="flex items-center gap-1.5 flex-wrap">
				{#each visibleTags as tag}
					<span
						class="inline-flex items-center px-2 py-0.5 rounded-full bg-gray-200 text-gray-700 text-[11px] font-medium whitespace-nowrap"
						title={tag}
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
	</div>

	<!-- Right side action hint (visible on hover in non-selection mode) -->
	{#if !selectionMode}
		<div class="flex-shrink-0 text-gray-400 group-hover:text-gray-600 transition-colors">
			<Icon icon="lucide:chevron-right" class="w-4 h-4" />
		</div>
	{/if}
</div>
