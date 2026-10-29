<script lang="ts">
	import Icon from '@iconify/svelte';
	import { nodes } from '$lib/stores';
	import {
		CHIP_DISPLAY_LIMIT as chipDisplayLimit,
		collectUniqueDomains,
		collectUniqueTags,
		visibleChips
	} from '$lib/utils/entity-detail';
	import type { EntityDetailForm } from './entity-detail-form.svelte';

	let { form }: { form: EntityDetailForm } = $props();

	// Suggestions drawn from the domains/tags already used on the canvas
	let uniqueDomains = $derived(collectUniqueDomains($nodes));
	let uniqueTags = $derived(collectUniqueTags($nodes));
</script>

<!-- Entity Name and Domain - Side by Side -->
<div class="grid grid-cols-2 gap-4">
	<!-- Entity Name -->
	<div>
		<label for="entity-name" class="block text-xs font-semibold text-gray-700 mb-1.5 uppercase tracking-wide">
			Entity Name *
		</label>
		<input
			id="entity-name"
			type="text"
			bind:value={form.entityName}
			class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm shadow-2xs focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all text-gray-900 font-medium"
			placeholder="e.g., Customer, Order, Product"
			required
		/>
	</div>

	<!-- Domains -->
	<div>
		<label class="block text-xs font-semibold text-gray-700 mb-1.5 uppercase tracking-wide">
			Domains
		</label>
		<div class="flex flex-wrap items-center gap-1.5 min-h-[38px] p-1.5 border border-gray-300 rounded-lg bg-white shadow-2xs hover:border-gray-400 focus-within:border-primary-500 focus-within:ring-2 focus-within:ring-primary-500/20 transition-all">
			{#each visibleChips(form.entityDomains, form.showAllDomains) as domain}
				<span class="inline-flex items-center gap-1 px-2 py-0.5 bg-purple-50 text-purple-700 text-xs rounded-md border border-purple-200 font-medium shadow-3xs">
					{domain}
					<button
						type="button"
						onclick={() => form.removeDomain(domain)}
						class="text-purple-500 hover:text-purple-800 focus:outline-none"
						aria-label="Remove {domain}"
					>
						<Icon icon="lucide:x" class="w-2.5 h-2.5" />
					</button>
				</span>
			{/each}
			<input
				type="text"
				list="domain-suggestions"
				bind:value={form.domainInput}
				onkeydown={form.handleDomainInputKeydown}
				class="flex-1 min-w-[80px] px-2 py-1 text-xs border-0 bg-transparent focus:outline-none focus:ring-0 text-gray-900 placeholder-gray-400"
				placeholder="Type and press Enter"
				aria-label="Add domain"
			/>
			{#if form.entityDomains.length > chipDisplayLimit}
				<button
					type="button"
					class="shrink-0 px-2 py-0.5 text-[11px] font-semibold text-purple-700 hover:text-purple-900 hover:bg-purple-50 rounded-full border border-purple-200/70 transition-colors"
					onclick={() => (form.showAllDomains = !form.showAllDomains)}
				>
					{form.showAllDomains ? 'Show less' : `+${form.entityDomains.length - chipDisplayLimit} more`}
				</button>
			{/if}
		</div>
		<datalist id="domain-suggestions">
			{#each uniqueDomains as domain}
				<option value={domain}></option>
			{/each}
		</datalist>
	</div>
</div>

<div>
	<label for="entity-description" class="block text-xs font-semibold text-gray-700 mb-1.5 uppercase tracking-wide">
		Description
	</label>
	<textarea
		id="entity-description"
		bind:value={form.entityDescription}
		rows="3"
		class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm shadow-2xs focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all text-gray-900 resize-y"
		placeholder="Description..."
	></textarea>
</div>

<!-- Tags and Source Systems - Side by Side -->
<div class="grid grid-cols-2 gap-4">
	<!-- Tags -->
	<div>
		<label class="block text-xs font-semibold text-gray-700 mb-1.5 uppercase tracking-wide">Tags</label>
		<div class="flex flex-wrap items-center gap-1.5 min-h-[38px] p-1.5 border border-gray-300 rounded-lg bg-white shadow-2xs hover:border-gray-400 focus-within:border-primary-500 focus-within:ring-2 focus-within:ring-primary-500/20 transition-all">
			{#each visibleChips(form.entityTags, form.showAllTags) as tag}
				<span class="inline-flex items-center gap-1 px-2 py-0.5 bg-primary-50 text-primary-700 text-xs rounded-md border border-primary-200/80 font-medium shadow-3xs">
					{tag}
					<button
						type="button"
						onclick={() => form.removeTag(tag)}
						class="text-primary-500 hover:text-primary-800 focus:outline-none"
						aria-label="Remove {tag}"
					>
						<Icon icon="lucide:x" class="w-2.5 h-2.5" />
					</button>
				</span>
			{/each}
			<input
				type="text"
				list="tag-suggestions"
				bind:value={form.tagInput}
				onkeydown={form.handleTagInputKeydown}
				class="flex-1 min-w-[80px] px-2 py-1 text-xs border-0 bg-transparent focus:outline-none focus:ring-0 text-gray-900 placeholder-gray-400"
				placeholder="Type and press Enter"
				aria-label="Add tag"
			/>
			{#if form.entityTags.length > chipDisplayLimit}
				<button
					type="button"
					class="shrink-0 px-2 py-0.5 text-[11px] font-semibold text-primary-700 hover:text-primary-900 hover:bg-primary-50 rounded-full border border-primary-200/70 transition-colors"
					onclick={() => (form.showAllTags = !form.showAllTags)}
				>
					{form.showAllTags ? 'Show less' : `+${form.entityTags.length - chipDisplayLimit} more`}
				</button>
			{/if}
		</div>
		<datalist id="tag-suggestions">
			{#each uniqueTags as tag}
				<option value={tag}></option>
			{/each}
		</datalist>
	</div>

	<!-- Source Systems -->
	<div>
		<label class="block text-xs font-semibold text-gray-700 mb-1.5 uppercase tracking-wide">
			Source Systems
		</label>
		<div class="flex flex-wrap items-center gap-1.5 min-h-[38px] p-1.5 border border-gray-300 rounded-lg bg-white shadow-2xs hover:border-gray-400 focus-within:border-primary-500 focus-within:ring-2 focus-within:ring-primary-500/20 transition-all">
			{#each visibleChips(form.entitySourceSystems, form.showAllSourceSystems) as source}
				<span class="inline-flex items-center gap-1 px-2 py-0.5 bg-gray-100 text-gray-700 text-xs rounded-md border border-gray-200 font-medium shadow-3xs">
					{source}
					<button
						type="button"
						onclick={() => form.removeSourceSystem(source)}
						class="text-gray-500 hover:text-gray-800 focus:outline-none"
						aria-label="Remove {source}"
					>
						<Icon icon="lucide:x" class="w-2.5 h-2.5" />
					</button>
				</span>
			{/each}
			<input
				type="text"
				bind:value={form.sourceInput}
				onkeydown={form.handleSourceInputKeydown}
				onfocus={form.handleSourceInputFocus}
				onblur={form.handleSourceInputBlur}
				oninput={form.handleSourceInput}
				class="flex-1 min-w-[80px] px-2 py-1 text-xs border-0 bg-transparent focus:outline-none focus:ring-0 text-gray-900 placeholder-gray-400"
				placeholder="Type and press Enter"
				aria-label="Add source system"
			/>
			{#if form.entitySourceSystems.length > chipDisplayLimit}
				<button
					type="button"
					class="shrink-0 px-2 py-0.5 text-[11px] font-semibold text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-full border border-gray-300 transition-colors"
					onclick={() => (form.showAllSourceSystems = !form.showAllSourceSystems)}
				>
					{form.showAllSourceSystems ? 'Show less' : `+${form.entitySourceSystems.length - chipDisplayLimit} more`}
				</button>
			{/if}
		</div>
		{#if form.showSourceSuggestions && form.filteredSourceSuggestions.length > 0}
			<div class="mt-2 border border-gray-200 rounded-lg bg-white max-h-48 overflow-y-auto shadow-lg">
				{#each form.filteredSourceSuggestions as suggestion, index}
					<button
						class="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 focus:bg-gray-50 focus:outline-none {index === form.activeSourceSuggestionIndex ? 'bg-gray-50' : ''}"
						onmousedown={(e) => e.preventDefault()}
						onclick={() => form.selectSourceSuggestion(suggestion)}
						aria-label="Add {suggestion}"
					>
						{suggestion}
						{#if form.entitySourceSystems.includes(suggestion)}
							<span class="ml-2 text-xs text-gray-400">(added)</span>
						{/if}
					</button>
				{/each}
			</div>
		{/if}
	</div>
</div>
