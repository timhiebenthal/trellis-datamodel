<script lang="ts">
	import Icon from '@iconify/svelte';
	import Modal from './Modal.svelte';
	import { nodes, edges, entityDetailModal, pushHistory, frameworkModels, activeFramework } from '$lib/stores';
	import { getSourceSystemSuggestions, getBusinessEventProcesses, updateModelSchema, getModelSchema } from '$lib/api';
	import type { EntityData, ModelInfo } from '$lib/types';
	import { mergeFields } from '$lib/utils/merged-fields';
	import type { MergedField } from '$lib/utils/merged-fields';
	import { computeUiTagsAfterEdit } from '$lib/utils/entity-tags';
	import { readModelRef, readFrameworkTags } from '$lib/utils/entity-compat';
	import { bindEntityToModel } from '$lib/utils/entity-binding';
	import { getEntityDetailPath, isEntityDetailPath } from '$lib/utils/entity-list-route';
	import {
		buildEntityRelationships,
		buildSchemaColumnsForSave,
		hasEntityFormChanges,
		normalizeDomains
	} from '$lib/utils/entity-detail';
	import { getContext } from 'svelte';
	import { page } from '$app/stores';
	import type { AutoSaveService } from '$lib/services/auto-save';
	import { getFrameworkCopy, getFrameworkDisplay } from '$lib/utils/framework-display';
	import { goto } from '$app/navigation';
	import { EntityDetailForm } from './entity-detail/entity-detail-form.svelte';
	import EntityDetailHeader from './entity-detail/EntityDetailHeader.svelte';
	import EntityMetaPanel from './entity-detail/EntityMetaPanel.svelte';
	import EntityRolesSection from './entity-detail/EntityRolesSection.svelte';
	import EntityFieldsEditor from './entity-detail/EntityFieldsEditor.svelte';
	import EntityRelationshipsList from './entity-detail/EntityRelationshipsList.svelte';
	import EntityDetailFooter from './entity-detail/EntityDetailFooter.svelte';

	// Get autoSaveService from parent context (set in +layout.svelte)
	const autoSaveServiceContext = getContext<{ current: AutoSaveService | null }>('autoSaveService');

	// Modal-local form + UI state shared with the section components
	const form = new EntityDetailForm();

	let frameworkCopy = $derived(getFrameworkCopy($activeFramework));
	let frameworkDisplay = $derived(getFrameworkDisplay($activeFramework));

	// Current entity data
	let currentEntity = $derived.by(() => {
		if (!$entityDetailModal.open || !$entityDetailModal.entityId) return null;
		return $nodes.find((n) => n.id === $entityDetailModal.entityId) || null;
	});

	// Read-only relationships for the current entity, derived from the edges that touch it.
	let entityRelationships = $derived(buildEntityRelationships(currentEntity?.id, $edges, $nodes));

	// Check if entity is bound to dbt model
	let isBoundEntity = $derived.by(() => {
		if (!currentEntity) return false;
		const data = currentEntity.data as unknown as EntityData;
		return !!readModelRef(data ?? {});
	});

	// Look up the bound dbt model
	let boundModel = $derived(
		currentEntity
			? $frameworkModels.find((m) => m.unique_id === readModelRef((currentEntity?.data as unknown as EntityData) ?? {})) ?? null
			: null,
	);

	// Merged field list: dbt columns first, then drafted fields that don't collide
	let mergedFields = $derived<MergedField[]>(mergeFields(boundModel?.columns, form.editableDraftedFields));

	// Bound dbt models
	let boundModels = $derived.by(() => {
		if (!currentEntity) return [];

		const data = currentEntity.data as unknown as EntityData;
		const models: string[] = [];

		const modelRef = readModelRef(data ?? {});
		if (modelRef) {
			models.push(modelRef);
		}

		if (data?.additional_models) {
			models.push(...data.additional_models);
		}

		return models;
	});

	function handleModelSelect(model: ModelInfo) {
		if (!currentEntity) return;
		form.bindingError = '';
		const changed = bindEntityToModel(currentEntity.id, model);
		if (!changed) {
			form.bindingError = 'This model is already bound to the entity.';
		}
	}

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

		form.reset(entity.data as unknown as EntityData);
	});

	// Load source system suggestions when modal opens
	$effect(() => {
		if ($entityDetailModal.open) {
			loadSourceSuggestions();
			loadProcesses();
		}
	});

	// Load live descriptions from schema.yml when a bound entity modal opens.
	// The manifest lags behind schema.yml by a dbt compile; reading directly gives
	// the user the current description without requiring a recompile.
	$effect(() => {
		if ($entityDetailModal.open && isBoundEntity && boundModel) {
			loadLiveSchemaDescriptions(boundModel.name, boundModel.version ?? undefined);
		}
	});

	async function loadLiveSchemaDescriptions(modelName: string, version: number | undefined) {
		try {
			const schema = await getModelSchema(modelName, version);
			if (!schema) return;
			const map = new Map<string, string>();
			for (const col of schema.columns ?? []) {
				if (col.name && col.description != null) {
					map.set(col.name, col.description);
				}
			}
			form.liveSchemaDescriptions = map;
		} catch {
			// Non-fatal: fall back to manifest descriptions already in editableDraftedFields
		}
	}

	async function loadSourceSuggestions() {
		try {
			form.sourceSuggestions = await getSourceSystemSuggestions();
		} catch (error) {
			console.error('Failed to load source system suggestions:', error);
			form.sourceSuggestions = [];
		}
	}

	async function loadProcesses() {
		try {
			form.processes = await getBusinessEventProcesses();
		} catch (error) {
			console.error('Failed to load business event processes:', error);
			form.processes = [];
		}
	}

	function navigateToProcess(processId: string) {
		// Close modal
		void closeModal({ navigateToList: false });
		// Navigate to business events view with process highlighted/filtered
		goto(`/business-events?process=${processId}`);
	}

	// Clear annotation type when changing away from dimension
	$effect(() => {
		if (form.entityType !== 'dimension' && form.annotationType !== undefined) {
			form.annotationType = undefined;
		}
	});

	// Track changes for dirty state
	$effect(() => {
		if (!currentEntity) return;

		form.isDirty = hasEntityFormChanges(currentEntity.data as unknown as EntityData, {
			entityName: form.entityName,
			entityDescription: form.entityDescription,
			entityDomains: form.entityDomains,
			entityTags: form.entityTags,
			entitySourceSystems: form.entitySourceSystems,
			sourceInput: form.sourceInput,
			entityType: form.entityType,
			annotationType: form.annotationType,
			entityRoles: form.entityRoles,
			materializedEditCount: form.materializedDescriptionEdits.size,
			editableDraftedFields: form.editableDraftedFields
		});
	});

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			if (form.show7WsDropdown) {
				form.show7WsDropdown = false;
			} else if (form.showExportDropdown) {
				form.showExportDropdown = false;
			} else if (form.showDeleteConfirm) {
				form.showDeleteConfirm = false;
			} else if (form.deletingRoleName !== null) {
				form.deletingRoleName = null;
			} else {
				handleCancel();
			}
		} else if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
			handleSave();
		}
	}

	function handleModalContentClick(event: MouseEvent) {
		// Close dropdowns when clicking outside of them
		const target = event.target as HTMLElement;
		const annotationDropdown = target.closest('.annotation-dropdown-container');
		if (!annotationDropdown && form.show7WsDropdown) {
			form.show7WsDropdown = false;
		}

		const exportDropdown = target.closest('.export-dropdown-container');
		if (!exportDropdown && form.showExportDropdown) {
			form.showExportDropdown = false;
		}
	}

	async function handleSave() {
		if (!currentEntity || !form.entityName.trim()) return;
		if (form.sourceInput.trim().length > 0) {
			form.addSourceSystem();
		}

		const normalizedDomains = normalizeDomains(form.entityDomains);
		const primaryDomain = normalizedDomains[0];

		// Update the node in the store
		nodes.update((n) => {
			return n.map((node) => {
				if (node.id === currentEntity.id) {
					// The modal's node is an entity node; the store is untyped `Node[]`.
					const entityData = (node.data ?? {}) as EntityData;
					const isBound = Boolean(readModelRef(entityData));
					// Bound entities: `tags` is a computed display union and reconcile-owned
					// `dbt_tags` is read-only — an edit here only ever changes `ui_tags`.
					// Unbound entities: `tags` remains the single freely-editable field.
					const tagFields = isBound
						? { ui_tags: (() => {
								const uiTags = computeUiTagsAfterEdit(readFrameworkTags(entityData), form.entityTags);
								return uiTags.length > 0 ? uiTags : undefined;
							})() }
						: { tags: form.entityTags.length > 0 ? form.entityTags : undefined };
					return {
						...node,
						data: {
							...node.data,
							label: form.entityName.trim(),
							description: form.entityDescription.trim() || undefined,
							domains: normalizedDomains.length > 0 ? normalizedDomains : undefined,
							domain: primaryDomain || undefined,
							...tagFields,
							source_system:
								form.entitySourceSystems.length > 0 ? form.entitySourceSystems : undefined,
							entity_type: form.entityType,
							annotation_type: form.entityType === 'dimension' ? form.annotationType : undefined,
							roles: form.entityType === 'dimension' && form.entityRoles.length > 0 ? form.entityRoles : undefined,
							drafted_fields:
								form.editableDraftedFields.length > 0
									? form.editableDraftedFields
									: undefined
						}
					};
				}
				return node;
			});
		});

		// If any materialized description edits, write them to schema.yml.
		// Baseline is the live schema.yml content (lag-free); user edits overlay on top.
		if (isBoundEntity && boundModel && form.materializedDescriptionEdits.size > 0) {
			try {
				// Priority: user's staged edit > live schema.yml value > manifest value
				const allCols = buildSchemaColumnsForSave(
					boundModel.columns,
					form.materializedDescriptionEdits,
					form.liveSchemaDescriptions
				);
				await updateModelSchema(boundModel.name, boundModel.version ?? undefined, allCols);
				// Re-read schema.yml so liveSchemaDescriptions reflects the saved state
				await loadLiveSchemaDescriptions(boundModel.name, boundModel.version ?? undefined);
				form.materializedDescriptionEdits = new Map();
			} catch (e: unknown) {
				const msg = e instanceof Error ? e.message : 'Failed to save descriptions to schema.yml';
				console.error('Schema update failed:', msg);
				// Surface the error so the user can retry — do not roll back the canvas save
				form.materializeError = msg;
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

	function handleCancel() {
		if (form.isDirty) {
			const confirmed = confirm('You have unsaved changes. Are you sure you want to cancel?');
			if (!confirmed) return;
		}
		closeModal();
	}

	function confirmDelete() {
		if (!currentEntity) return;

		// Remove all relationships that reference the deleted entity.
		edges.update((edgeList) =>
			edgeList.filter(
				(edge) => edge.source !== currentEntity.id && edge.target !== currentEntity.id
			)
		);

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

	async function closeModal(options: { navigateToList?: boolean } = {}) {
		if (options.navigateToList !== false && isEntityDetailPath($page.url.pathname)) {
			await goto('/entity-list');
		}
		entityDetailModal.set({ open: false, entityId: null });
	}

	// Navigate the modal to a related entity. Warns on unsaved changes, mirroring handleCancel.
	async function openRelatedEntity(entityId: string) {
		if (!entityId || entityId === currentEntity?.id) return;
		if (form.isDirty) {
			const confirmed = confirm('You have unsaved changes. Switch entities without saving?');
			if (!confirmed) return;
		}

		if (isEntityDetailPath($page.url.pathname)) {
			await goto(getEntityDetailPath(entityId));
		}
		entityDetailModal.set({ open: true, entityId });
	}
</script>

{#if $entityDetailModal.open && currentEntity}
	<!-- Escape is handled by handleKeydown: it closes open dropdowns/confirms before the modal. -->
	<Modal
		onClose={handleCancel}
		closeOnEscape={false}
		class="relative bg-white rounded-xl shadow-2xl w-full mx-4 max-h-[90vh] overflow-hidden"
		style="max-width: 1400px; border: 1px solid rgba(209, 213, 219, 0.3);"
		labelledBy="entity-detail-modal-title"
		onkeydown={handleKeydown}
		onclick={handleModalContentClick}
	>
		<EntityDetailHeader
			{form}
			{boundModels}
			{frameworkCopy}
			onClose={handleCancel}
			onModelSelect={handleModelSelect}
		/>

		<!-- Success Message -->
		{#if form.showMarkdownSuccess}
			<div class="mx-8 mt-4 px-4 py-3 bg-green-50 border-2 border-green-200 rounded-lg flex items-center gap-3 animate-fade-in">
				<Icon icon="lucide:check-circle" class="w-5 h-5 text-green-600 flex-shrink-0" />
				<span class="text-sm font-medium text-green-800">Entity copied to clipboard as Markdown!</span>
			</div>
		{/if}

		<!-- Scrollable Content -->
		<div class="px-8 py-6 overflow-y-auto" style="max-height: calc(90vh - 220px);">
			<div class="space-y-4">
				<EntityMetaPanel {form} />

				{#if form.entityType === 'dimension'}
					<EntityRolesSection
						{form}
						entityId={currentEntity?.id || ''}
						onNavigateToProcess={navigateToProcess}
					/>
				{/if}

				<EntityFieldsEditor
					{form}
					{mergedFields}
					{isBoundEntity}
					{boundModel}
					{frameworkCopy}
					{frameworkDisplay}
				/>

				{#if entityRelationships.length > 0}
					<EntityRelationshipsList
						relationships={entityRelationships}
						onOpenRelatedEntity={openRelatedEntity}
					/>
				{/if}
			</div>
		</div>

		<EntityDetailFooter
			{form}
			entity={currentEntity}
			{mergedFields}
			{frameworkCopy}
			onCancel={handleCancel}
			onSave={handleSave}
			onConfirmDelete={confirmDelete}
		/>

		<!-- Delete Role Confirmation Modal -->
	{#if form.deletingRoleName !== null}
		<div class="absolute inset-0 bg-gray-900/50 flex items-center justify-center z-10 rounded-xl">
			<div class="bg-white rounded-lg shadow-xl p-6 max-w-md mx-4 border-2 border-red-200">
				<div class="flex items-start gap-3 mb-4">
					<Icon icon="lucide:alert-triangle" class="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
					<div>
						<h3 class="text-lg font-bold text-gray-900 mb-1">Remove Role?</h3>
						<p class="text-sm text-gray-600">
							Are you sure you want to remove the role <span class="font-semibold text-gray-900">"{form.deletingRoleName}"</span>?
						</p>
					</div>
				</div>
					<div class="flex gap-2 justify-end">
						<button
							onclick={form.cancelDeleteRole}
							class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border-2 border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
						>
							Cancel
						</button>
						<button
							onclick={form.deleteRole}
							class="px-4 py-2 text-sm font-bold text-white bg-red-600 rounded-lg hover:bg-red-700 transition-colors"
						>
							Remove Role
						</button>
					</div>
				</div>
			</div>
		{/if}
	</Modal>
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
