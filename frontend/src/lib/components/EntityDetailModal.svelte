<script lang="ts">
	import Icon from '@iconify/svelte';
	import { nodes, edges, entityDetailModal, pushHistory, dbtModels } from '$lib/stores';
	import { getSourceSystemSuggestions, getBusinessEventProcesses } from '$lib/api';
	import type { EntityData, AnnotationType, DraftedField, BusinessEventProcess, AnnotationEntry, EntityRole } from '$lib/types';
	import type { Node } from '@xyflow/svelte';
	import { getContext } from 'svelte';
	import type { AutoSaveService } from '$lib/services/auto-save';
	import { exportEntityToExcel } from '$lib/utils/excel-export';
	import { formatEntityAsMarkdown } from '$lib/utils/markdown-export';
	import { goto } from '$app/navigation';

	// Get autoSaveService from parent context (set in +layout.svelte)
	const autoSaveServiceContext = getContext<{ current: AutoSaveService | null }>('autoSaveService');

	// Local state for form fields
	let entityName = $state('');
	let entityDomains = $state<string[]>([]);
	let entityTags = $state<string[]>([]);
	let entitySourceSystems = $state<string[]>([]);
	let entityType = $state<'dimension' | 'fact' | 'unclassified'>('unclassified');
	let annotationType = $state<AnnotationType | undefined>(undefined);
	let entityDescription = $state('');
	let tagInput = $state('');
	let domainInput = $state('');
	let sourceInput = $state('');
	let sourceSuggestions = $state<string[]>([]);
	let showSourceSuggestions = $state(false);
	let activeSourceSuggestionIndex = $state(0);
	let filteredSourceSuggestions = $derived(
		sourceSuggestions.filter((s) =>
			s.toLowerCase().includes(sourceInput.toLowerCase())
		)
	);
	let showDeleteConfirm = $state(false);
	let isDirty = $state(false);
	let show7WsDropdown = $state(false);
	let isExporting = $state(false);
	let showExportDropdown = $state(false);
	let isCopyingMarkdown = $state(false);
	let showMarkdownSuccess = $state(false);

	// Role management state
	let entityRoles = $state<EntityRole[]>([]);
	let roleInput = $state('');
	let editingRoleIndex = $state<number | null>(null);
	let editingRoleValue = $state('');
	let deletingRoleIndex = $state<number | null>(null);
	let autoRoles = $derived(entityRoles.filter(r => r.source));
	
	// Process linking state
	let processes = $state<BusinessEventProcess[]>([]);
	let expandedRoles = $state<Set<string>>(new Set());

	function normalizeDomains(domains?: string[], domain?: string): string[] {
		const list = Array.isArray(domains) && domains.length > 0 ? domains : domain ? [domain] : [];
		return Array.from(new Set(list.map((item) => item.trim()).filter(Boolean)));
	}

	// Get available domains from existing entities
	let uniqueDomains = $derived.by(() => {
		const domains = new Set<string>();
		$nodes.forEach((node) => {
			const data = node.data as unknown as EntityData;
			const domainList = Array.isArray(data.domains) && data.domains.length > 0
				? data.domains
				: data.domain
					? [data.domain]
					: [];
			domainList.forEach((domain) => {
				if (domain && domain.trim()) {
					domains.add(domain.trim());
				}
			});
		});
		return Array.from(domains).sort();
	});

	// Get available tags from existing entities
	let uniqueTags = $derived.by(() => {
		const tags = new Set<string>();
		$nodes.forEach((node) => {
			const nodeTags = (node.data as unknown as EntityData)?.tags || [];
			nodeTags.forEach((tag) => {
				if (tag && tag.trim()) {
					tags.add(tag.trim());
				}
			});
		});
		return Array.from(tags).sort();
	});

	// Current entity data
	let currentEntity = $derived.by(() => {
		if (!$entityDetailModal.open || !$entityDetailModal.entityId) return null;
		return $nodes.find((n) => n.id === $entityDetailModal.entityId) || null;
	});

	// Entity attributes (from dbt model or drafted fields)
	let entityAttributes = $derived.by(() => {
		if (!currentEntity) return [];

		const data = currentEntity.data as unknown as EntityData;
		const dbtModelId = data?.dbt_model;
		const draftedFields = data?.drafted_fields || [];

		// If bound to dbt model, get columns from dbtModels store
		if (dbtModelId) {
			const model = $dbtModels.find((m) => m.unique_id === dbtModelId);
			if (model && model.columns) {
				return model.columns.map((col) => ({
					name: col.name,
					type: col.type || 'unknown',
					description: ''
				}));
			}
		}

		// Otherwise, show drafted fields
		return draftedFields.map((field) => ({
			name: field.name,
			type: field.datatype || 'unknown',
			description: field.description || ''
		}));
	});

	// Check if entity is bound to dbt model (attributes are read-only if bound)
	let isBoundEntity = $derived.by(() => {
		if (!currentEntity) return false;
		const data = currentEntity.data as unknown as EntityData;
		return !!data?.dbt_model;
	});

	// Editable drafted fields state
	let editableDraftedFields = $state<DraftedField[]>([]);

	// Initialize editable drafted fields when modal opens
	$effect(() => {
		if ($entityDetailModal.open && currentEntity && !isBoundEntity) {
			const data = currentEntity.data as unknown as EntityData;
			editableDraftedFields = [...(data?.drafted_fields || [])];
		}
	});

	function updateDraftedField(index: number, updates: Partial<DraftedField>) {
		editableDraftedFields = editableDraftedFields.map((field, i) =>
			i === index ? { ...field, ...updates } : field
		);
	}

	function addDraftedField() {
		editableDraftedFields = [
			...editableDraftedFields,
			{ name: '', datatype: 'text', description: '' }
		];
	}

	function deleteDraftedField(index: number) {
		editableDraftedFields = editableDraftedFields.filter((_, i) => i !== index);
	}

	// Bound dbt models
	let boundModels = $derived.by(() => {
		if (!currentEntity) return [];

		const data = currentEntity.data as unknown as EntityData;
		const models: string[] = [];

		if (data?.dbt_model) {
			models.push(data.dbt_model);
		}

		if (data?.additional_models) {
			models.push(...data.additional_models);
		}

		return models;
	});

	// Initialize form when modal opens
	$effect(() => {
		if ($entityDetailModal.open && currentEntity) {
			const data = currentEntity.data as unknown as EntityData;
			entityName = data.label || '';
			entityDescription = data.description || '';
			entityDomains = normalizeDomains(data.domains, data.domain);
			entityTags = [...(data.tags || [])];
			entitySourceSystems = [...(data.source_system || [])];
			entityType = data.entity_type || 'unclassified';
			annotationType = data.annotation_type;
			entityRoles = [...((data as any).roles || [])];
			tagInput = '';
			domainInput = '';
			sourceInput = '';
			roleInput = '';
			editingRoleIndex = null;
			editingRoleValue = '';
			deletingRoleIndex = null;
			sourceSuggestions = [];
			showSourceSuggestions = false;
			activeSourceSuggestionIndex = 0;
			showDeleteConfirm = false;
			isDirty = false;
		}
	});

	// Load source system suggestions when modal opens
	$effect(() => {
		if ($entityDetailModal.open) {
			loadSourceSuggestions();
			loadProcesses();
		}
	});

	async function loadSourceSuggestions() {
		try {
			sourceSuggestions = await getSourceSystemSuggestions();
		} catch (error) {
			console.error('Failed to load source system suggestions:', error);
			sourceSuggestions = [];
		}
	}

	async function loadProcesses() {
		try {
			processes = await getBusinessEventProcesses();
		} catch (error) {
			console.error('Failed to load business event processes:', error);
			processes = [];
		}
	}

	function getProcessesForRole(dimensionId: string, role: EntityRole): BusinessEventProcess[] {
		const roleName = role.role;
		return processes.filter(proc => {
			if (!proc.annotations_superset) return false;
			return Object.values(proc.annotations_superset).some((annotations: AnnotationEntry[]) =>
				annotations.some((ann: AnnotationEntry) =>
					ann.dimension_id === dimensionId && ann.role === roleName
				)
			);
		});
	}

	function toggleRoleExpansion(role: EntityRole) {
		const roleName = role.role || '';
		if (expandedRoles.has(roleName)) {
			expandedRoles.delete(roleName);
		} else {
			expandedRoles.add(roleName);
		}
		expandedRoles = new Set(expandedRoles); // Trigger reactivity
	}

	function navigateToProcess(processId: string) {
		// Close modal
		closeModal();
		// Navigate to business events view with process highlighted/filtered
		goto(`/business-events?process=${processId}`);
	}

	// Clear annotation type when changing away from dimension
	$effect(() => {
		if (entityType !== 'dimension' && annotationType !== undefined) {
			annotationType = undefined;
		}
	});

	// Track changes for dirty state
	$effect(() => {
		if (!currentEntity) return;

		const data = currentEntity.data as unknown as EntityData;
		const initialDomains = normalizeDomains(data.domains, data.domain);
		const nextDomains = normalizeDomains(entityDomains);
		const hasChanges =
			entityName !== (data.label || '') ||
			entityDescription !== (data.description || '') ||
			JSON.stringify(nextDomains.sort()) !== JSON.stringify(initialDomains.sort()) ||
			JSON.stringify(entityTags.sort()) !== JSON.stringify([...(data.tags || [])].sort()) ||
			JSON.stringify(entitySourceSystems.sort()) !==
				JSON.stringify([...(data.source_system || [])].sort()) ||
			sourceInput.trim().length > 0 ||
			entityType !== (data.entity_type || 'unclassified') ||
			annotationType !== data.annotation_type ||
			JSON.stringify(entityRoles.sort()) !== JSON.stringify([...((data as any).roles || [])].sort()) ||
			(!isBoundEntity &&
				JSON.stringify(editableDraftedFields) !==
					JSON.stringify(data?.drafted_fields || []));

		isDirty = hasChanges;
	});

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			if (show7WsDropdown) {
				show7WsDropdown = false;
			} else if (showExportDropdown) {
				showExportDropdown = false;
			} else if (showDeleteConfirm) {
				showDeleteConfirm = false;
			} else if (deletingRoleIndex !== null) {
				deletingRoleIndex = null;
			} else {
				handleCancel();
			}
		} else if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
			handleSave();
		}
	}

	function handleBackdropClick(event: MouseEvent) {
		if (event.target === event.currentTarget) {
			handleCancel();
		}
	}

	function handleModalContentClick(event: MouseEvent) {
		// Close dropdowns when clicking outside of them
		const target = event.target as HTMLElement;
		const annotationDropdown = target.closest('.annotation-dropdown-container');
		if (!annotationDropdown && show7WsDropdown) {
			show7WsDropdown = false;
		}

		const exportDropdown = target.closest('.export-dropdown-container');
		if (!exportDropdown && showExportDropdown) {
			showExportDropdown = false;
		}
	}

	function addTag() {
		const trimmed = tagInput.trim();
		if (trimmed && !entityTags.includes(trimmed)) {
			entityTags = [...entityTags, trimmed];
			tagInput = '';
		}
	}

	function removeTag(tag: string) {
		entityTags = entityTags.filter((t) => t !== tag);
	}

	function handleTagInputKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			event.preventDefault();
			addTag();
		}
	}

	function addDomain() {
		const trimmed = domainInput.trim();
		if (trimmed && !entityDomains.includes(trimmed)) {
			entityDomains = [...entityDomains, trimmed];
			domainInput = '';
		}
	}

	function removeDomain(domain: string) {
		entityDomains = entityDomains.filter((d) => d !== domain);
	}

	function handleDomainInputKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			event.preventDefault();
			addDomain();
		}
	}

	function addSourceSystem(source = sourceInput) {
		const trimmed = source.trim();
		if (trimmed && !entitySourceSystems.includes(trimmed)) {
			entitySourceSystems = [...entitySourceSystems, trimmed];
			sourceInput = '';
		}
	}

	function removeSourceSystem(source: string) {
		entitySourceSystems = entitySourceSystems.filter((s) => s !== source);
	}

	function handleSourceInputKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape' && showSourceSuggestions) {
			showSourceSuggestions = false;
			event.preventDefault();
		} else if (event.key === 'Enter') {
			if (showSourceSuggestions && filteredSourceSuggestions.length > 0) {
				event.preventDefault();
				selectSourceSuggestion(filteredSourceSuggestions[activeSourceSuggestionIndex]);
			} else {
				event.preventDefault();
				addSourceSystem();
			}
		} else if (event.key === 'ArrowDown' && showSourceSuggestions) {
			event.preventDefault();
			activeSourceSuggestionIndex = Math.min(
				activeSourceSuggestionIndex + 1,
				filteredSourceSuggestions.length - 1
			);
		} else if (event.key === 'ArrowUp' && showSourceSuggestions) {
			event.preventDefault();
			activeSourceSuggestionIndex = Math.max(activeSourceSuggestionIndex - 1, 0);
		} else if (event.key === 'Tab' && showSourceSuggestions && filteredSourceSuggestions.length > 0) {
			event.preventDefault();
			selectSourceSuggestion(filteredSourceSuggestions[activeSourceSuggestionIndex]);
		}
	}

	function handleSourceInputFocus() {
		showSourceSuggestions = true;
		activeSourceSuggestionIndex = 0;
	}

	function handleSourceInputBlur() {
		setTimeout(() => {
			showSourceSuggestions = false;
		}, 200);
	}

	function handleSourceInput() {
		showSourceSuggestions = true;
		activeSourceSuggestionIndex = 0;
	}

	function selectSourceSuggestion(suggestion: string) {
		addSourceSystem(suggestion);
		showSourceSuggestions = false;
		sourceInput = '';
		activeSourceSuggestionIndex = 0;
	}

	// Role management functions
	function addRole() {
		const trimmed = roleInput.trim();
		if (!trimmed) return;

		if (entityRoles.some(r => r.role === trimmed)) {
			alert(`Role "${trimmed}" already exists`);
			return;
		}

		entityRoles = [...entityRoles, { role: trimmed }];
		roleInput = '';
	}

	function handleRoleInputKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			event.preventDefault();
			addRole();
		}
	}

	function startEditingRole(index: number) {
		editingRoleIndex = index;
		editingRoleValue = entityRoles[index].role || '';
	}

	function saveEditingRole() {
		if (editingRoleIndex === null) return;

		const trimmed = editingRoleValue.trim();
		if (!trimmed) {
			alert('Role name cannot be empty');
			return;
		}

		// Check for duplicates (excluding the current role being edited)
		const duplicate = entityRoles.find((role, idx) => idx !== editingRoleIndex && role.role === trimmed);
		if (duplicate) {
			alert(`Role "${trimmed}" already exists`);
			return;
		}

		entityRoles = entityRoles.map((role, idx) =>
			idx === editingRoleIndex ? { ...role, role: trimmed } : role
		);
		editingRoleIndex = null;
		editingRoleValue = '';
	}

	function cancelEditingRole() {
		editingRoleIndex = null;
		editingRoleValue = '';
	}

	function handleEditRoleKeydown(event: KeyboardEvent) {
		if (event.key === 'Enter') {
			event.preventDefault();
			saveEditingRole();
		} else if (event.key === 'Escape') {
			event.preventDefault();
			cancelEditingRole();
		}
	}

	function confirmDeleteRole(index: number) {
		deletingRoleIndex = index;
	}

	function deleteRole() {
		if (deletingRoleIndex === null) return;
		entityRoles = entityRoles.filter((_, idx) => idx !== deletingRoleIndex);
		deletingRoleIndex = null;
	}

	function cancelDeleteRole() {
		deletingRoleIndex = null;
	}

	function handleSave() {
		if (!currentEntity || !entityName.trim()) return;
		if (sourceInput.trim().length > 0) {
			addSourceSystem();
		}

		const normalizedDomains = normalizeDomains(entityDomains);
		const primaryDomain = normalizedDomains[0];

		// Update the node in the store
		nodes.update((n) => {
			return n.map((node) => {
				if (node.id === currentEntity.id) {
					return {
						...node,
						data: {
							...node.data,
							label: entityName.trim(),
							description: entityDescription.trim() || undefined,
							domains: normalizedDomains.length > 0 ? normalizedDomains : undefined,
							domain: primaryDomain || undefined,
							tags: entityTags.length > 0 ? entityTags : undefined,
							source_system:
								entitySourceSystems.length > 0 ? entitySourceSystems : undefined,
							entity_type: entityType,
							annotation_type: entityType === 'dimension' ? annotationType : undefined,
							roles: entityType === 'dimension' && entityRoles.length > 0 ? entityRoles : undefined,
							drafted_fields:
								!isBoundEntity && editableDraftedFields.length > 0
									? editableDraftedFields
									: undefined
						}
					};
				}
				return node;
			});
		});

		// Push to history for undo/redo
		pushHistory();

		// Trigger auto-save
		if (autoSaveServiceContext?.current) {
			autoSaveServiceContext.current.saveNow($nodes, $edges);
		}

		// Close modal
		closeModal();
	}

	function handleCancel() {
		if (isDirty) {
			const confirmed = confirm('You have unsaved changes. Are you sure you want to cancel?');
			if (!confirmed) return;
		}
		closeModal();
	}

	function handleDelete() {
		showDeleteConfirm = true;
	}

	function confirmDelete() {
		if (!currentEntity) return;

		// Remove node from store
		nodes.update((n) => n.filter((node) => node.id !== currentEntity.id));

		// Push to history
		pushHistory();

		// Trigger auto-save
		if (autoSaveServiceContext?.current) {
			autoSaveServiceContext.current.saveNow($nodes, $edges);
		}

		// Close modal
		closeModal();
	}

	function cancelDelete() {
		showDeleteConfirm = false;
	}


	async function handleExportToExcel() {
		if (!currentEntity) return;

		isExporting = true;
		try {
			// Extract entity ID from currentEntity
			const entityId = currentEntity.id;

			// Call export function with all required data
			exportEntityToExcel(
				currentEntity.data as unknown as EntityData,
				entityAttributes,
				$edges,
				$nodes,
				entityId
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
		if (!currentEntity) return;
		isCopyingMarkdown = true;
		try {
			const entityId = currentEntity.id;
			const markdown = formatEntityAsMarkdown(
				currentEntity.data as unknown as EntityData,
				entityAttributes,
				$edges,
				$nodes,
				entityId
			);
			await navigator.clipboard.writeText(markdown);
			
			// Show success message
			showMarkdownSuccess = true;
			setTimeout(() => {
				showMarkdownSuccess = false;
			}, 3000);
		} catch (error) {
			console.error('Copy failed:', error);
			alert(`Failed to copy: ${error instanceof Error ? error.message : 'Unknown error'}`);
		} finally {
			isCopyingMarkdown = false;
			showExportDropdown = false;
		}
	}

	function closeModal() {
		$entityDetailModal = { open: false, entityId: null };
	}

	// Annotation type options for dimensions
	const annotationTypes: { value: AnnotationType; label: string; color: string }[] = [
		{ value: 'who', label: 'Who', color: 'bg-blue-100 text-blue-800 border-blue-200' },
		{ value: 'what', label: 'What', color: 'bg-purple-100 text-purple-800 border-purple-200' },
		{ value: 'when', label: 'When', color: 'bg-green-100 text-green-800 border-green-200' },
		{ value: 'where', label: 'Where', color: 'bg-yellow-100 text-yellow-800 border-yellow-200' },
		{ value: 'how', label: 'How', color: 'bg-orange-100 text-orange-800 border-orange-200' },
		{ value: 'why', label: 'Why', color: 'bg-red-100 text-red-800 border-red-200' },
		{
			value: 'how_many',
			label: 'How Many',
			color: 'bg-indigo-100 text-indigo-800 border-indigo-200'
		}
	];
</script>

{#if $entityDetailModal.open && currentEntity}
	<!-- Backdrop -->
	<div
		class="fixed inset-0 z-50 flex items-center justify-center backdrop-blur-sm bg-gray-900/85"
		onclick={handleBackdropClick}
		onkeydown={handleKeydown}
		role="dialog"
		tabindex="-1"
		aria-modal="true"
		aria-labelledby="entity-detail-modal-title"
	>
		<!-- Modal Container -->
		<div
			class="relative bg-white rounded-xl shadow-2xl w-full mx-4 max-h-[90vh] overflow-hidden"
			style="max-width: 1400px; border: 1px solid rgba(209, 213, 219, 0.3);"
			role="document"
			tabindex="-1"
			onclick={handleModalContentClick}
		>
			<!-- Header with primary accent -->
			<div
				class="relative px-8 pt-8 pb-6 bg-gray-50"
			>
				<div
					class="absolute top-0 left-0 right-0 h-1 bg-primary-600"
				></div>

				<div class="flex items-start justify-between">
					<div class="flex-1">
						<h2
							id="entity-detail-modal-title"
							class="text-2xl font-bold text-gray-900 mb-2"
							style="letter-spacing: -0.02em;"
						>
							Entity Details
						</h2>
						<p class="text-sm text-gray-600">
							{entityType === 'dimension' ? 'Dimension' : entityType === 'fact' ? 'Fact' : 'Unclassified'} entity
						</p>
					</div>
					<button
						class="p-2 rounded-lg hover:bg-gray-200 text-gray-500 transition-colors"
						onclick={handleCancel}
						aria-label="Close"
					>
						<Icon icon="lucide:x" class="w-5 h-5" />
					</button>
				</div>
			</div>

			<!-- Success Message -->
			{#if showMarkdownSuccess}
				<div class="mx-8 mt-4 px-4 py-3 bg-green-50 border-2 border-green-200 rounded-lg flex items-center gap-3 animate-fade-in">
					<Icon icon="lucide:check-circle" class="w-5 h-5 text-green-600 flex-shrink-0" />
					<span class="text-sm font-medium text-green-800">Entity copied to clipboard as Markdown!</span>
				</div>
			{/if}

			<!-- Scrollable Content -->
			<div class="px-8 py-6 overflow-y-auto" style="max-height: calc(90vh - 220px);">
				<div class="space-y-4">
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
								bind:value={entityName}
								class="w-full px-3 py-2 border-2 border-gray-200 rounded-lg text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all text-gray-900 font-medium"
								placeholder="e.g., Customer, Order, Product"
								required
							/>
						</div>

					<!-- Domains -->
					<div>
						<label class="block text-xs font-semibold text-gray-700 mb-1.5 uppercase tracking-wide">
							Domains
						</label>
						<div class="flex flex-wrap gap-1.5 min-h-[44px] p-2 border-2 border-gray-200 rounded-lg bg-gray-50">
							{#each entityDomains as domain}
								<span class="inline-flex items-center gap-1 px-2 py-0.5 bg-purple-50 text-purple-700 text-xs rounded-md border border-purple-200 font-medium">
									{domain}
									<button
										type="button"
										onclick={() => removeDomain(domain)}
										class="text-purple-600 hover:text-purple-900 focus:outline-none"
										aria-label="Remove {domain}"
									>
										<Icon icon="lucide:x" class="w-2.5 h-2.5" />
									</button>
								</span>
							{/each}
							<input
								type="text"
								list="domain-suggestions"
								bind:value={domainInput}
								onkeydown={handleDomainInputKeydown}
								class="flex-1 min-w-[80px] px-2 py-1 text-xs border-0 bg-transparent focus:outline-none focus:ring-0"
								placeholder="Type and press Enter"
							/>
						</div>
						<datalist id="domain-suggestions">
							{#each uniqueDomains as domain}
								<option value={domain} />
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
							bind:value={entityDescription}
							rows="3"
							class="w-full px-3 py-2 border-2 border-gray-200 rounded-lg text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all text-gray-900 resize-y"
							placeholder="Description..."
						></textarea>
					</div>

					<!-- Entity Type and 7Ws - Same Row -->
					<div class="grid grid-cols-2 gap-4">
						<!-- Entity Type - Compact Chips -->
						<div>
							<label class="block text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wide">Entity Type</label>
							<div class="flex gap-2">
								<button
									type="button"
									class="px-3 py-1.5 rounded-md border-2 transition-all text-sm font-medium {entityType === 'dimension'
										? 'bg-green-50 border-green-500 text-green-700'
										: 'bg-white border-gray-200 text-gray-700 hover:border-gray-300 hover:bg-gray-50'}"
									onclick={() => (entityType = 'dimension')}
								>
									<Icon icon="lucide:list" class="w-4 h-4 inline-block mr-1" />
									Dimension
								</button>
								<button
									type="button"
									class="px-3 py-1.5 rounded-md border-2 transition-all text-sm font-medium {entityType === 'fact'
										? 'bg-blue-50 border-blue-500 text-blue-700'
										: 'bg-white border-gray-200 text-gray-700 hover:border-gray-300 hover:bg-gray-50'}"
									onclick={() => (entityType = 'fact')}
								>
									<Icon icon="lucide:bar-chart-3" class="w-4 h-4 inline-block mr-1" />
									Fact
								</button>
								<button
									type="button"
									class="px-3 py-1.5 rounded-md border-2 transition-all text-sm font-medium {entityType === 'unclassified'
										? 'bg-gray-50 border-gray-500 text-gray-700'
										: 'bg-white border-gray-200 text-gray-700 hover:border-gray-300'}"
									onclick={() => (entityType = 'unclassified')}
								>
									<Icon icon="lucide:circle-help" class="w-4 h-4 inline-block mr-1" />
									Unclassified
								</button>
							</div>
						</div>

						<!-- Annotation Type (7Ws) - Chip/Badge style for dimensions only -->
						{#if entityType === 'dimension'}
							<div class="relative annotation-dropdown-container">
								<label class="block text-xs font-semibold text-gray-700 mb-2 uppercase tracking-wide">
									Annotation Type (7Ws)
								</label>
								<!-- Selected chip/badge or placeholder -->
								<button
									type="button"
									class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border transition-all text-xs font-medium hover:opacity-80 {annotationType
										? annotationTypes.find((a) => a.value === annotationType)?.color + ' border-current'
										: 'bg-gray-100 border-gray-300 text-gray-500 hover:bg-gray-200'}"
									onclick={() => (show7WsDropdown = !show7WsDropdown)}
								>
									{#if annotationType}
										<span>
											{annotationTypes.find((a) => a.value === annotationType)?.label}
										</span>
									{:else}
										<span>Select 7W...</span>
									{/if}
									<Icon
										icon="lucide:chevron-down"
										class="w-3 h-3 transition-transform {show7WsDropdown ? 'rotate-180' : ''}"
									/>
								</button>

								<!-- Dropdown menu -->
								{#if show7WsDropdown}
									<div
										class="absolute z-10 mt-1 left-0 bg-white border-2 border-gray-200 rounded-lg shadow-lg overflow-hidden min-w-[160px]"
									>
										<div class="max-h-60 overflow-y-auto">
											{#each annotationTypes.filter((opt) => opt.value !== 'how_many') as option}
												<button
													type="button"
													class="w-full px-3 py-2 text-left text-sm font-medium transition-colors hover:bg-gray-50 flex items-center gap-2 {annotationType === option.value
														? option.color
														: 'text-gray-700'}"
													onclick={() => {
														annotationType = option.value;
														show7WsDropdown = false;
													}}
												>
													{#if annotationType === option.value}
														<Icon icon="lucide:check" class="w-4 h-4" />
													{:else}
														<span class="w-4"></span>
													{/if}
													{option.label}
												</button>
											{/each}
											<button
												type="button"
												class="w-full px-3 py-2 text-left text-sm font-medium transition-colors hover:bg-gray-50 flex items-center gap-2 border-t border-gray-200 {annotationType === undefined
													? 'bg-gray-50 text-gray-700'
													: 'text-gray-500'}"
												onclick={() => {
													annotationType = undefined;
													show7WsDropdown = false;
												}}
											>
												{#if annotationType === undefined}
													<Icon icon="lucide:check" class="w-4 h-4" />
												{:else}
													<span class="w-4"></span>
												{/if}
												None
											</button>
										</div>
									</div>
								{/if}
							</div>
						{/if}
					</div>

					<!-- Tags and Source Systems - Side by Side -->
					<div class="grid grid-cols-2 gap-4">
						<!-- Tags -->
						<div>
							<label class="block text-xs font-semibold text-gray-700 mb-1.5 uppercase tracking-wide">Tags</label>
							<div class="flex flex-wrap gap-1.5 min-h-[44px] p-2 border-2 border-gray-200 rounded-lg bg-gray-50">
								{#each entityTags as tag}
									<span class="inline-flex items-center gap-1 px-2 py-0.5 bg-primary-50 text-primary-700 text-xs rounded-md border border-primary-200 font-medium">
										{tag}
										<button
											type="button"
											onclick={() => removeTag(tag)}
											class="text-primary-600 hover:text-primary-900 focus:outline-none"
											aria-label="Remove {tag}"
										>
											<Icon icon="lucide:x" class="w-2.5 h-2.5" />
										</button>
									</span>
								{/each}
								<input
									type="text"
									list="tag-suggestions"
									bind:value={tagInput}
									onkeydown={handleTagInputKeydown}
									class="flex-1 min-w-[80px] px-2 py-1 text-xs border-0 bg-transparent focus:outline-none focus:ring-0"
									placeholder="Type and press Enter"
								/>
							</div>
							<datalist id="tag-suggestions">
								{#each uniqueTags as tag}
									<option value={tag} />
								{/each}
							</datalist>
						</div>

						<!-- Source Systems -->
						<div>
							<label class="block text-xs font-semibold text-gray-700 mb-1.5 uppercase tracking-wide">
								Source Systems
							</label>
							<div class="flex flex-wrap gap-1.5 min-h-[44px] p-2 border-2 border-gray-200 rounded-lg bg-gray-50">
								{#each entitySourceSystems as source}
									<span class="inline-flex items-center gap-1 px-2 py-0.5 bg-gray-100 text-gray-700 text-xs rounded-md border border-gray-300 font-medium">
										{source}
										<button
											type="button"
											onclick={() => removeSourceSystem(source)}
											class="text-gray-600 hover:text-gray-900 focus:outline-none"
											aria-label="Remove {source}"
										>
											<Icon icon="lucide:x" class="w-2.5 h-2.5" />
										</button>
									</span>
								{/each}
								<input
									type="text"
									bind:value={sourceInput}
									onkeydown={handleSourceInputKeydown}
									onfocus={handleSourceInputFocus}
									onblur={handleSourceInputBlur}
									oninput={handleSourceInput}
									class="flex-1 min-w-[80px] px-2 py-1 text-xs border-0 bg-transparent focus:outline-none focus:ring-0"
									placeholder="Type and press Enter"
								/>
							</div>
							{#if showSourceSuggestions && filteredSourceSuggestions.length > 0}
								<div class="mt-2 border border-gray-200 rounded-lg bg-white max-h-48 overflow-y-auto">
									{#each filteredSourceSuggestions as suggestion, index}
										<button
											class="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 focus:bg-gray-50 focus:outline-none {index === activeSourceSuggestionIndex ? 'bg-gray-50' : ''}"
											onmousedown={(e) => e.preventDefault()}
											onclick={() => selectSourceSuggestion(suggestion)}
											aria-label="Add {suggestion}"
										>
											{suggestion}
											{#if entitySourceSystems.includes(suggestion)}
												<span class="ml-2 text-xs text-gray-400">(added)</span>
											{/if}
										</button>
									{/each}
								</div>
							{/if}
						</div>
					</div>

					<!-- Role aliases (read-only auto-generated) -->
					{#if entityType === 'dimension' && autoRoles.length > 0}
						<div>
							<label class="block text-xs font-semibold text-gray-700 mb-1.5 uppercase tracking-wide">
								Role aliases
							</label>
							<div class="space-y-1">
								{#each autoRoles as role}
									<div class="flex items-center gap-1.5 text-sm text-gray-600">
										<span class="w-1.5 h-1.5 rounded-full bg-blue-400 flex-shrink-0"></span>
										<span class="font-medium text-gray-800">{role.label || role.role}</span>
										{#if role.role && role.label}
											<span class="text-gray-400">({role.role})</span>
										{/if}
										{#if role.source}
											<span class="text-gray-400">·</span>
											<span class="text-gray-500 text-xs">{role.source}</span>
										{/if}
									</div>
								{/each}
							</div>
						</div>
					{/if}

					<!-- Roles (for dimensions only) -->
					{#if entityType === 'dimension'}
						<div>
							<div class="flex items-center gap-2 mb-3">
								<label class="block text-sm font-semibold text-gray-700">
									Roles ({entityRoles.length})
								</label>
								<button
									type="button"
									class="text-gray-400 hover:text-gray-600 transition-colors"
									title="Role-playing dimensions: Track different contextual uses of the same dimension (e.g., 'order_date', 'ship_date', 'delivery_date' for a Date dimension)"
								>
									<Icon icon="lucide:info" class="w-4 h-4" />
								</button>
							</div>

							{#if entityRoles.length === 0 && !roleInput}
								<!-- Empty state -->
								<div class="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center bg-gray-50">
									<Icon icon="lucide:users" class="w-8 h-8 text-gray-400 mx-auto mb-2" />
									<p class="text-sm text-gray-600 mb-1">No roles defined for this dimension</p>
									<p class="text-xs text-gray-500">Roles track different contextual uses (e.g., order_date, ship_date)</p>
								</div>
							{:else}
								<!-- Role list -->
								<div class="border-2 border-gray-200 rounded-lg overflow-hidden">
									{#if entityRoles.length > 0}
										<div class="divide-y divide-gray-200">
											{#each entityRoles as role, index}
												<div class="border-b border-gray-200 last:border-b-0">
													<!-- Role header -->
													<div class="px-4 py-3 hover:bg-gray-50 transition-colors group flex items-center justify-between">
														<div class="flex items-center gap-2 flex-1">
															<button
																type="button"
																onclick={() => toggleRoleExpansion(role)}
																class="text-gray-400 hover:text-gray-600 transition-colors"
																title={expandedRoles.has(role.role || '') ? 'Collapse processes' : 'Expand to see processes'}
															>
																<Icon
																	icon={expandedRoles.has(role.role || '') ? 'lucide:chevron-down' : 'lucide:chevron-right'}
																	class="w-4 h-4"
																/>
															</button>

															{#if editingRoleIndex === index}
																<!-- Edit mode -->
																<input
																	type="text"
																	bind:value={editingRoleValue}
																	onkeydown={handleEditRoleKeydown}
																	onblur={saveEditingRole}
																	class="flex-1 px-3 py-1.5 border-2 border-blue-500 rounded-lg text-sm font-medium text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
																	placeholder="e.g., order_date, ship_date"
																	autofocus
																/>
															{:else}
																<!-- View mode -->
																<button
																	type="button"
																	onclick={() => startEditingRole(index)}
																	class="flex-1 text-left px-2 py-1 text-sm font-medium text-gray-900 hover:text-blue-600 transition-colors rounded"
																	title="Click to edit"
																>
																	{role.role}
																</button>
																<span class="text-xs text-gray-500">
																	({getProcessesForRole(currentEntity?.id || '', role).length} processes)
																</span>
															{/if}
														</div>

														<div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
															<button
																type="button"
																onclick={() => startEditingRole(index)}
																class="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
																title="Edit role"
															>
																<Icon icon="lucide:pencil" class="w-4 h-4" />
															</button>
															<button
																type="button"
																onclick={() => confirmDeleteRole(index)}
																class="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
																title="Delete role"
															>
																<Icon icon="lucide:trash-2" class="w-4 h-4" />
															</button>
														</div>
													</div>

													<!-- Expandable process list -->
													{#if expandedRoles.has(role.role || '')}
														<div class="px-4 pb-3 pl-12 bg-gray-50">
															{#each getProcessesForRole(currentEntity?.id || '', role) as process}
																<button
																	type="button"
																	onclick={() => navigateToProcess(process.id)}
																	class="block w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-white hover:text-blue-600 rounded transition-colors mb-1 last:mb-0"
																>
																	<div class="flex items-center gap-2">
																		<Icon icon="lucide:workflow" class="w-4 h-4" />
																		<span>{process.name}</span>
																		<span class="text-xs text-gray-500">({process.event_ids.length} events)</span>
																	</div>
																</button>
															{/each}

															{#if getProcessesForRole(currentEntity?.id || '', role).length === 0}
																<p class="text-xs text-gray-500 italic px-3 py-2">
																	No processes use this role yet
																</p>
															{/if}
														</div>
													{/if}
												</div>
											{/each}
										</div>
									{/if}
								</div>
							{/if}

							<!-- Add role input -->
							<div class="mt-3 flex gap-2">
								<input
									type="text"
									bind:value={roleInput}
									onkeydown={handleRoleInputKeydown}
									class="flex-1 px-3 py-2 border-2 border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
									placeholder="e.g., Sales Agent, Manager, Team Lead"
								/>
								<button
									type="button"
									onclick={addRole}
									disabled={!roleInput.trim()}
									class="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-all flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
								>
									<Icon icon="lucide:plus" class="w-4 h-4" />
									Add Role
								</button>
							</div>
						</div>
					{/if}

					<!-- Attributes -->
					{#if isBoundEntity}
						<!-- Read-only attributes for bound entities -->
						{#if entityAttributes.length > 0}
							<div>
								<label class="block text-sm font-semibold text-gray-700 mb-3">
									Attributes ({entityAttributes.length}) - Read Only
								</label>
								<div class="border-2 border-gray-200 rounded-lg overflow-hidden">
									<table class="w-full text-sm">
										<thead class="bg-gray-100">
											<tr>
												<th class="px-4 py-2 text-left font-semibold text-gray-700">Name</th>
												<th class="px-4 py-2 text-left font-semibold text-gray-700">Type</th>
												<th class="px-4 py-2 text-left font-semibold text-gray-700"
													>Description</th
												>
											</tr>
										</thead>
										<tbody class="divide-y divide-gray-200">
											{#each entityAttributes as attr}
												<tr class="hover:bg-gray-50">
													<td class="px-4 py-2 font-medium text-gray-900">{attr.name}</td>
													<td class="px-4 py-2 text-gray-600 font-mono text-xs"
														>{attr.type}</td
													>
													<td class="px-4 py-2 text-gray-600"
														>{attr.description || '—'}</td
													>
												</tr>
											{/each}
										</tbody>
									</table>
								</div>
								<p class="mt-2 text-xs text-gray-500 italic">
									Attributes are managed in the dbt schema file. Edit them on the canvas in logical
									view.
								</p>
							</div>
						{/if}
					{:else}
						<!-- Editable attributes for unbound entities -->
						<div>
							<label class="block text-sm font-semibold text-gray-700 mb-3">
								Attributes ({editableDraftedFields.length})
							</label>
							<div class="border-2 border-gray-200 rounded-lg overflow-hidden">
								{#if editableDraftedFields.length > 0}
									<!-- Header row -->
									<div class="bg-gray-100 px-3 py-2 grid grid-cols-12 gap-2 text-xs font-semibold text-gray-700">
										<div class="col-span-3">Name</div>
										<div class="col-span-2">Type</div>
										<div class="col-span-6">Description</div>
										<div class="col-span-1"></div>
									</div>
									<!-- Attribute rows -->
									<div class="divide-y divide-gray-200">
										{#each editableDraftedFields as field, index}
											<div class="px-3 py-2 hover:bg-gray-50 group">
												<div class="grid grid-cols-12 gap-2 items-center">
													<!-- Name (narrower) -->
													<div class="col-span-3">
														<input
															type="text"
															value={field.name}
															oninput={(e) =>
																updateDraftedField(index, {
																	name: (e.target as HTMLInputElement).value
																})}
															class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium text-sm"
															placeholder="attribute_name"
														/>
													</div>
													<!-- Type -->
													<div class="col-span-2">
														<select
															value={field.datatype}
															onchange={(e) =>
																updateDraftedField(index, {
																	datatype: (e.target as HTMLSelectElement)
																		.value as any
																})}
															class="w-full px-2 py-2 border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 text-xs font-mono uppercase text-gray-600"
														>
															<option value="text">text</option>
															<option value="int">int</option>
															<option value="float">float</option>
															<option value="bool">bool</option>
															<option value="date">date</option>
															<option value="timestamp">timestamp</option>
														</select>
													</div>
													<!-- Description (wider) -->
													<div class="col-span-6">
														<input
															type="text"
															value={field.description || ''}
															oninput={(e) =>
																updateDraftedField(index, {
																	description: (e.target as HTMLInputElement).value
																})}
															class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
															placeholder="Description (optional)"
														/>
													</div>
													<!-- Delete button -->
													<div class="col-span-1 flex justify-end">
														<button
															type="button"
															onclick={() => deleteDraftedField(index)}
															class="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
															title="Delete attribute"
														>
															<Icon icon="lucide:trash-2" class="w-4 h-4" />
														</button>
													</div>
												</div>
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
								onclick={addDraftedField}
								class="mt-3 w-full px-4 py-2.5 text-sm font-medium text-blue-700 bg-blue-50 border-2 border-blue-200 rounded-lg hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-all flex items-center justify-center gap-2"
							>
								<Icon icon="lucide:plus" class="w-4 h-4" />
								Add Attribute
							</button>
						</div>
					{/if}

					<!-- Bound dbt Models (Read-only) -->
					{#if boundModels.length > 0}
						<div>
							<label class="block text-sm font-semibold text-gray-700 mb-3">
								Bound dbt Models ({boundModels.length})
							</label>
							<div class="space-y-2">
							{#each boundModels as model}
								<div
									class="px-4 py-3 bg-primary-50 border border-primary-200 rounded-lg"
								>
									<div class="flex items-center gap-2">
										<Icon icon="lucide:layers" class="w-4 h-4 text-primary-600" />
										<span class="font-mono text-sm text-gray-900">{model}</span>
									</div>
								</div>
							{/each}
							</div>
						</div>
					{/if}
				</div>
			</div>

			<!-- Footer Actions -->
			<div
				class="px-8 py-6 border-t-2 border-gray-100 bg-gray-50"
			>
				{#if !showDeleteConfirm}
					<div class="flex items-center justify-between gap-4">
						<button
							onclick={handleDelete}
							class="px-4 py-2.5 text-sm font-medium text-red-700 bg-red-50 border-2 border-red-200 rounded-lg hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-all flex items-center gap-2"
						>
							<Icon icon="lucide:trash-2" class="w-4 h-4" />
							Delete Entity
						</button>

						<div class="flex gap-3">
							<div class="relative export-dropdown-container">
								<button
									onclick={() => (showExportDropdown = !showExportDropdown)}
									disabled={isExporting}
									class="px-5 py-2.5 text-sm font-medium text-primary-700 bg-primary-50 border-2 border-primary-200 rounded-lg hover:bg-primary-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 transition-all flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
									aria-label="Export options"
								>
									{#if isExporting}
										<Icon icon="lucide:loader-2" class="w-4 h-4 animate-spin" />
									{:else}
										<Icon icon="lucide:download" class="w-4 h-4" />
									{/if}
									Export
									<Icon icon="lucide:chevron-down" class="w-3 h-3 transition-transform {showExportDropdown ? 'rotate-180' : ''}" />
								</button>

								<!-- Dropdown Menu -->
								{#if showExportDropdown}
									<div class="absolute bottom-full mb-2 right-0 bg-white border-2 border-gray-200 rounded-lg shadow-lg overflow-hidden min-w-[200px] z-10">
										<button
											onclick={() => {
												handleExportToExcel();
												showExportDropdown = false;
											}}
											class="w-full px-4 py-2.5 text-left text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors flex items-center gap-2 whitespace-nowrap"
										>
											<Icon icon="lucide:file-spreadsheet" class="w-4 h-4 text-green-600" />
											Download as Excel
										</button>
										<button
											onclick={() => { handleCopyAsMarkdown(); }}
											disabled={isCopyingMarkdown}
											class="w-full px-4 py-2.5 text-left text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors flex items-center gap-2 whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed"
										>
											{#if isCopyingMarkdown}
												<Icon icon="lucide:loader-2" class="w-4 h-4 animate-spin text-blue-600" />
											{:else}
												<Icon icon="lucide:clipboard-copy" class="w-4 h-4 text-blue-600" />
											{/if}
											Copy as Markdown
										</button>
									</div>
								{/if}
							</div>

							<button
								onclick={handleCancel}
								class="px-5 py-2.5 text-sm font-medium text-gray-700 bg-white border-2 border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 transition-all"
							>
								Cancel
							</button>
							<button
								onclick={handleSave}
								disabled={!isDirty || !entityName.trim()}
								class="px-5 py-2.5 text-sm font-bold text-white bg-primary-600 hover:bg-primary-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 transition-all flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
							>
								<Icon icon="lucide:save" class="w-4 h-4" />
								Save Changes
							</button>
						</div>
					</div>
				{:else}
					<!-- Delete Confirmation -->
					<div
						class="flex items-center justify-between p-4 bg-red-50 border-2 border-red-300 rounded-lg"
					>
						<div class="flex items-center gap-3">
							<Icon icon="lucide:alert-triangle" class="w-5 h-5 text-red-600" />
							<span class="text-sm font-medium text-red-900"
								>Are you sure you want to delete this entity? This action cannot be undone.</span
							>
						</div>
						<div class="flex gap-2">
							<button
								onclick={cancelDelete}
								class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
							>
								Cancel
							</button>
							<button
								onclick={confirmDelete}
								class="px-4 py-2 text-sm font-bold text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
							>
								Delete
							</button>
						</div>
					</div>
				{/if}
			</div>

			<!-- Delete Role Confirmation Modal -->
			{#if deletingRoleIndex !== null}
				<div class="absolute inset-0 bg-gray-900/50 flex items-center justify-center z-10 rounded-xl">
					<div class="bg-white rounded-lg shadow-xl p-6 max-w-md mx-4 border-2 border-red-200">
						<div class="flex items-start gap-3 mb-4">
							<Icon icon="lucide:alert-triangle" class="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
							<div>
								<h3 class="text-lg font-bold text-gray-900 mb-1">Remove Role?</h3>
								<p class="text-sm text-gray-600">
									Are you sure you want to remove the role <span class="font-semibold text-gray-900">"{entityRoles[deletingRoleIndex]}"</span>?
								</p>
							</div>
						</div>
						<div class="flex gap-2 justify-end">
							<button
								onclick={cancelDeleteRole}
								class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border-2 border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
							>
								Cancel
							</button>
							<button
								onclick={deleteRole}
								class="px-4 py-2 text-sm font-bold text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
							>
								Remove Role
							</button>
						</div>
					</div>
				</div>
			{/if}
		</div>
	</div>
{/if}

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
