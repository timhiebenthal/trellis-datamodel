<script lang="ts">
	import Icon from '@iconify/svelte';
	import { nodes, edges, entityDetailModal, pushHistory, dbtModels, modelingStyle, configStatus } from '$lib/stores';
	import { getSourceSystemSuggestions, getBusinessEventProcesses, updateModelSchema, getManifest } from '$lib/api';
	import type { EntityData, AnnotationType, DraftedField, BusinessEventProcess, AnnotationEntry, EntityRole, ModelSchemaColumn } from '$lib/types';
	import { mergeFields } from '$lib/utils/merged-fields';
	import type { MergedField } from '$lib/utils/merged-fields';
	import type { Node } from '@xyflow/svelte';
	import { getContext } from 'svelte';
	import type { AutoSaveService } from '$lib/services/auto-save';
	import { exportEntityToExcel } from '$lib/utils/excel-export';
	import { formatEntityAsMarkdown } from '$lib/utils/markdown-export';
	import { goto } from '$app/navigation';
	import DropIndicator from './DropIndicator.svelte';

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
	let editingRoleName = $state<string | null>(null);
	let editingRoleValue = $state('');
	let deletingRoleName = $state<string | null>(null);
	let autoRoles = $derived(entityRoles.filter(r => r.source));
	// Deduplicate roles by name for display (multiple entries can exist per role when sourced from different processes)
	// Case-insensitive: "Creation Date" and "creation date" should be treated as the same role
	// Use role.role or role.label (some entries only have label, no role field)
	let uniqueEntityRoles = $derived.by(() => {
		const seen = new Set<string>();
		return entityRoles.filter(role => {
			const key = (role.role || role.label || '').toLowerCase();
			if (seen.has(key)) return false;
			seen.add(key);
			return true;
		});
	});
	
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

	// Check if entity is bound to dbt model
	let isBoundEntity = $derived.by(() => {
		if (!currentEntity) return false;
		const data = currentEntity.data as unknown as EntityData;
		return !!data?.dbt_model;
	});

	// Look up the bound dbt model
	let boundModel = $derived(
		currentEntity
			? $dbtModels.find((m) => m.unique_id === (currentEntity?.data as unknown as EntityData)?.dbt_model) ?? null
			: null,
	);

	// Editable drafted fields state
	let editableDraftedFields = $state<DraftedField[]>([]);

	// Pending description edits for materialized (dbt) columns — written to schema.yml on save
	let materializedDescriptionEdits = $state<Map<string, string>>(new Map());

	// Feedback banners for materialize action
	let materializeWarnings = $state<string[]>([]);
	let materializeError = $state('');

	// Merged field list: dbt columns first, then drafted fields that don't collide
	let mergedFields = $derived<MergedField[]>(mergeFields(boundModel?.columns, editableDraftedFields));

	// Export-friendly shape for Excel/Markdown export helpers
	let entityAttributes = $derived(
		mergedFields.map((f) => ({
			name: f.name,
			type: f.datatype || 'unknown',
			description: f.origin === 'dbt'
				? (materializedDescriptionEdits.get(f.name) ?? f.description ?? '')
				: (f.description ?? ''),
			origin: f.origin === 'dbt' ? undefined : (editableDraftedFields[f.draftIndex]?.origin),
		})),
	);

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
			const fields = [...editableDraftedFields];
			const [moved] = fields.splice(dragIndex, 1);
			fields.splice(index, 0, moved);
			editableDraftedFields = fields;
			isDirty = true;
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

	// Full form sync only when opening the modal or switching entities — not when
	// currentEntity gets a new object reference after manifest refresh / autosave
	// (otherwise materialize banners and in-progress edits are wiped).
	let lastModalFormEntityId: string | null = null;
	$effect(() => {
		const open = $entityDetailModal.open;
		const entity = currentEntity;

		if (!open) {
			lastModalFormEntityId = null;
			return;
		}
		if (!entity) return;
		if (lastModalFormEntityId === entity.id) return;
		lastModalFormEntityId = entity.id;

		const data = entity.data as unknown as EntityData;
		editableDraftedFields = [...(data?.drafted_fields || [])];
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
		editingRoleName = null;
		editingRoleValue = '';
		deletingRoleName = null;
		sourceSuggestions = [];
		showSourceSuggestions = false;
		activeSourceSuggestionIndex = 0;
		showDeleteConfirm = false;
		isDirty = false;
		materializedDescriptionEdits = new Map();
		materializeWarnings = [];
		materializeError = '';
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
			materializedDescriptionEdits.size > 0 ||
			JSON.stringify(editableDraftedFields) !==
				JSON.stringify(data?.drafted_fields || []);

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
			} else if (deletingRoleName !== null) {
				deletingRoleName = null;
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

	function startEditingRole(role: EntityRole) {
		editingRoleName = role.role || '';
		editingRoleValue = role.role || '';
	}

	function saveEditingRole() {
		if (editingRoleName === null) return;

		const trimmed = editingRoleValue.trim();
		if (!trimmed) {
			alert('Role name cannot be empty');
			return;
		}

		// Check for duplicates (excluding the role being edited)
		if (trimmed !== editingRoleName && entityRoles.some(r => r.role === trimmed)) {
			alert(`Role "${trimmed}" already exists`);
			return;
		}

		// Update all entries that share this role name (e.g. sourced from different processes)
		entityRoles = entityRoles.map(r =>
			r.role === editingRoleName ? { ...r, role: trimmed } : r
		);
		editingRoleName = null;
		editingRoleValue = '';
	}

	function cancelEditingRole() {
		editingRoleName = null;
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

	function confirmDeleteRole(roleName: string) {
		deletingRoleName = roleName;
	}

	function deleteRole() {
		if (deletingRoleName === null) return;
		// Remove all entries sharing this role name
		entityRoles = entityRoles.filter(r => r.role !== deletingRoleName);
		deletingRoleName = null;
	}

	function cancelDeleteRole() {
		deletingRoleName = null;
	}

	async function handleSave() {
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
								editableDraftedFields.length > 0
									? editableDraftedFields
									: undefined
						}
					};
				}
				return node;
			});
		});

		// If any materialized description edits, write them to schema.yml
		if (isBoundEntity && boundModel && materializedDescriptionEdits.size > 0) {
			try {
				const columns: ModelSchemaColumn[] = (boundModel.columns ?? []).map((c) => ({
					name: c.name,
					data_type: c.type,
					description: materializedDescriptionEdits.get(c.name) ?? (c as any).description ?? '',
				}));
				await updateModelSchema(boundModel.name, boundModel.version ?? undefined, columns);
				const models = await getManifest();
				dbtModels.set(models);
				materializedDescriptionEdits = new Map();
			} catch (e: unknown) {
				const msg = e instanceof Error ? e.message : 'Failed to save descriptions to schema.yml';
				console.error('Schema update failed:', msg);
				// Surface the error so the user can retry — do not roll back the canvas save
				materializeError = msg;
			}
		}

		// Push to history for undo/redo
		pushHistory();

		// Trigger auto-save
		if (autoSaveServiceContext?.current) {
			autoSaveServiceContext.current.saveNow($nodes, $edges);
		}

		// Close modal
		closeModal();
	}

	async function materializeDraft(draftIndex: number) {
		if (!boundModel) return;
		const draft = editableDraftedFields[draftIndex];
		if (!draft) return;
		materializeError = '';
		try {
			const columns: ModelSchemaColumn[] = [
				...(boundModel.columns ?? []).map((c) => ({
					name: c.name,
					data_type: c.type,
					description: (c as any).description ?? '',
				})),
				{
					name: draft.name,
					data_type: draft.datatype && draft.datatype !== 'unknown' ? draft.datatype : 'text',
					description: draft.description ?? '',
				},
			];
			await updateModelSchema(boundModel.name, boundModel.version ?? undefined, columns);
			const warning = `Column '${draft.name}' added to schema.yml. You still need to add it to the SQL in ${boundModel.name}.sql.`;
			materializeWarnings = materializeWarnings.includes(warning)
				? materializeWarnings
				: [...materializeWarnings, warning];
			// Remove from drafts — it's now materialized in schema.yml
			editableDraftedFields = editableDraftedFields.filter((_, i) => i !== draftIndex);
			// Refresh manifest so auto-promotion runs
			const models = await getManifest();
			dbtModels.set(models);
		} catch (e: unknown) {
			materializeError = e instanceof Error ? e.message : 'Failed to materialize field';
		}
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


	// Build legacy attributes shape from mergedFields for export helpers
	function buildExportAttributes(): Array<{ name: string; type: string; description?: string; origin?: string }> {
		const attributes = mergedFields.map((f) => ({
			name: f.name,
			type: f.datatype ?? '',
			description: f.description ?? '',
			origin: f.origin === 'dbt'
				? (boundModel?.unique_id ?? 'dbt')
				: (editableDraftedFields[f.draftIndex]?.origin ?? ''),
		}));
		return attributes;
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
				buildExportAttributes(),
				$edges,
				$nodes,
				entityId,
				$modelingStyle === 'dimensional_model'
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
			const exportAttributes = buildExportAttributes();
			const markdown = formatEntityAsMarkdown(
				currentEntity.data as unknown as EntityData,
				exportAttributes,
				$edges,
				$nodes,
				entityId,
				$modelingStyle === 'dimensional_model'
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
							{entityName || 'Entity'} Details
						</h2>
						{#if $modelingStyle === 'dimensional_model'}
							<p class="text-sm text-gray-600">
								{entityType === 'dimension' ? 'Dimension' : entityType === 'fact' ? 'Fact' : 'Unclassified'} entity
							</p>
						{/if}
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

					<!-- Entity Type and 7Ws (dimensional modeling only) -->
					{#if $modelingStyle === 'dimensional_model'}
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
					{/if}

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
								Roles ({uniqueEntityRoles.length})
							</label>
								<button
									type="button"
									class="text-gray-400 hover:text-gray-600 transition-colors"
									title="Role-playing dimensions: Track different contextual uses of the this dimension (e.g. 'date' can become 'order_date', 'ship_date', 'delivery_date')"
								>
									<Icon icon="lucide:info" class="w-4 h-4" />
								</button>
							</div>

							{#if uniqueEntityRoles.length === 0 && !roleInput}
								<!-- Empty state -->
								<p class="text-xs text-gray-400 italic">No roles defined for this dimension. Use this functionality if this entity 'slips' into different roles and functions.</p>
							{:else}
								<!-- Role list -->
								<div class="border-2 border-gray-200 rounded-lg overflow-hidden">
									{#if uniqueEntityRoles.length > 0}
										<div class="divide-y divide-gray-200">
											{#each uniqueEntityRoles as role}
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

															{#if editingRoleName === role.role}
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
																	onclick={() => startEditingRole(role)}
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
																onclick={() => startEditingRole(role)}
																class="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded transition-colors"
																title="Edit role"
															>
																<Icon icon="lucide:pencil" class="w-4 h-4" />
															</button>
															<button
																type="button"
																onclick={() => confirmDeleteRole(role.role || '')}
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
									placeholder="e.g. Employee = Sales Agent, Manager, Team Lead, ..."
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

					<!-- Attributes (merged dbt + drafted) -->
					<div>
						<label class="block text-sm font-semibold text-gray-700 mb-3">
							Attributes ({mergedFields.length})
							{#if isBoundEntity}<span class="font-normal text-xs text-gray-400 ml-1">— dbt columns are read-only</span>{/if}
						</label>

						{#if materializeWarnings.length > 0}
							<div class="mb-3 px-3 py-2 bg-amber-50 border border-amber-300 text-amber-800 text-sm rounded-lg flex items-start gap-2">
								<Icon icon="lucide:alert-triangle" class="w-4 h-4 mt-0.5 shrink-0" />
								<div class="space-y-1">
									{#each materializeWarnings as warning}
										<div>{warning}</div>
									{/each}
								</div>
								<button onclick={() => (materializeWarnings = [])} class="ml-auto text-amber-600 hover:text-amber-800" aria-label="Dismiss warning">
									<Icon icon="lucide:x" class="w-4 h-4" />
								</button>
							</div>
						{/if}
						{#if materializeError}
							<div class="mb-3 px-3 py-2 bg-red-50 border border-red-300 text-red-800 text-sm rounded-lg">{materializeError}</div>
						{/if}

						<div class="border-2 border-gray-200 rounded-lg overflow-hidden">
							{#if mergedFields.length > 0}
								<!-- Header -->
								<div class="bg-gray-100 px-3 py-2 grid grid-cols-12 gap-2 text-xs font-semibold text-gray-700">
									<div class="col-span-2">Name</div>
									<div class="col-span-1">Type</div>
									<div class="col-span-6">Description</div>
									<div class="col-span-2">Origin</div>
									<div class="col-span-1"></div>
								</div>
								<div class="divide-y divide-gray-200">
								{#each mergedFields as field (field.origin === 'draft' ? `draft-${field.draftIndex}` : `dbt-${field.name}`)}
								<div
									class="relative px-3 py-2 hover:bg-gray-50 group transition-colors"
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
														oninput={(e) => updateDraftedField(field.draftIndex, { name: (e.target as HTMLInputElement).value })}
														class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium text-sm"
														placeholder="attribute_name"
													/>
													</div>
												{:else}
														<input
															type="text"
															value={field.name}
															readonly
															class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium text-sm bg-gray-50 cursor-default"
															placeholder="attribute_name"
														/>
													{/if}
												</div>
												<!-- Type -->
												<div class="col-span-1">
													{#if field.origin === 'dbt'}
														<span class="px-1 py-2 text-xs font-mono uppercase text-gray-500">{field.datatype ?? '—'}</span>
													{:else}
						<select
														value={field.datatype}
														onchange={(e) => updateDraftedField(field.draftIndex, { datatype: (e.target as HTMLSelectElement).value as any })}
														class="w-full px-1 py-2 border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 text-xs font-mono uppercase text-gray-600"
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
														value={materializedDescriptionEdits.get(field.name) ?? field.description ?? ''}
														oninput={(e) => {
															const map = new Map(materializedDescriptionEdits);
															map.set(field.name, (e.target as HTMLInputElement).value);
															materializedDescriptionEdits = map;
														}}
														class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
														placeholder="Description (optional)"
													/>
												{:else}
													<input
														type="text"
														value={field.description ?? ''}
														oninput={(e) => updateDraftedField(field.draftIndex, { description: (e.target as HTMLInputElement).value })}
														class="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
														placeholder="Description (optional)"
													/>
													{/if}
												</div>
												<!-- Origin label -->
												<div class="col-span-2 text-xs text-gray-400 font-mono truncate" title={field.origin === 'dbt' ? ($configStatus?.framework === 'bruin' ? 'Defined in Bruin asset' : 'dbt model') : 'drafted'}>
													{#if field.origin === 'dbt'}
														<span
															class="inline-flex items-center"
															aria-label={$configStatus?.framework === 'bruin' ? `Defined in Bruin asset '${boundModel?.name ?? ''}'` : `Materialized in dbt model '${boundModel?.name ?? ''}'`}
															title={$configStatus?.framework === 'bruin' ? `Defined in Bruin asset '${boundModel?.name ?? ''}'` : `Materialized in dbt model '${boundModel?.name ?? ''}'`}
														>
															<Icon icon={$configStatus?.framework === 'bruin' ? 'lucide:database' : 'simple-icons:dbt'} class="h-3.5 w-3.5 text-gray-400 opacity-70" aria-hidden="true" />
														</span>
													{:else}
													<input
														type="text"
														value={editableDraftedFields[field.draftIndex]?.origin ?? ''}
														oninput={(e) => updateDraftedField(field.draftIndex, { origin: (e.target as HTMLInputElement).value })}
														class="w-full px-2 py-2 border border-gray-300 rounded-lg text-xs text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
														placeholder="Origin"
															aria-label={`Drafted in Trellis — not yet materialized in dbt. Use the materialize button in this row's Actions column to write into ${boundModel?.name ?? ''}'s schema.yml.`}
															title={`Drafted in Trellis — not yet materialized in dbt. Use the materialize button in this row's Actions column to write into ${boundModel?.name ?? ''}'s schema.yml.`}
														/>
													{/if}
												</div>
										<!-- Actions -->
										<div class="col-span-1 flex justify-end gap-1 items-center">
											{#if field.origin === 'draft'}
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
														onclick={() => deleteDraftedField(field.draftIndex)}
														class="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
														title="Delete attribute"
													>
														<Icon icon="lucide:trash-2" class="w-4 h-4" />
													</button>
												{/if}
											</div>
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
							onclick={addDraftedField}
							class="mt-3 w-full px-4 py-2.5 text-sm font-medium text-blue-700 bg-blue-50 border-2 border-blue-200 rounded-lg hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-all flex items-center justify-center gap-2"
						>
							<Icon icon="lucide:plus" class="w-4 h-4" />
							Add Attribute
						</button>
					</div>

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
		{#if deletingRoleName !== null}
			<div class="absolute inset-0 bg-gray-900/50 flex items-center justify-center z-10 rounded-xl">
				<div class="bg-white rounded-lg shadow-xl p-6 max-w-md mx-4 border-2 border-red-200">
					<div class="flex items-start gap-3 mb-4">
						<Icon icon="lucide:alert-triangle" class="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
						<div>
							<h3 class="text-lg font-bold text-gray-900 mb-1">Remove Role?</h3>
							<p class="text-sm text-gray-600">
								Are you sure you want to remove the role <span class="font-semibold text-gray-900">"{deletingRoleName}"</span>?
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
