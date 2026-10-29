import type { AnnotationType, BusinessEventProcess, DraftedField, EntityData, EntityRole } from '$lib/types';
import { addTag as appendUnique, removeTag as removeFrom } from '$lib/utils/entity-tags';
import {
	addRoleByName,
	dedupeRolesByName,
	normalizeDomains,
	removeRoleByName,
	renameRole
} from '$lib/utils/entity-detail';

/**
 * Modal-local state for EntityDetailModal: the editable form values plus the UI
 * flags (dropdowns, confirms, disclosures) that the modal's keyboard/click handlers
 * and its child sections share. One instance per mounted modal.
 *
 * Handlers are arrow-function fields so they can be passed straight to `on*` props.
 */
export class EntityDetailForm {
	// Form values
	entityName = $state('');
	entityDomains = $state<string[]>([]);
	entityTags = $state<string[]>([]);
	entitySourceSystems = $state<string[]>([]);
	entityType = $state<'dimension' | 'fact' | 'unclassified'>('unclassified');
	annotationType = $state<AnnotationType | undefined>(undefined);
	entityDescription = $state('');
	entityRoles = $state<EntityRole[]>([]);
	editableDraftedFields = $state<DraftedField[]>([]);

	// Pending description edits for materialized (dbt) columns — written to schema.yml on save
	materializedDescriptionEdits = $state<Map<string, string>>(new Map());
	// Live descriptions read directly from schema.yml (lag-free, not from manifest).
	// Loaded on modal open for bound entities; used as baseline when displaying and saving.
	liveSchemaDescriptions = $state<Map<string, string>>(new Map());

	// Chip inputs
	tagInput = $state('');
	domainInput = $state('');
	sourceInput = $state('');
	sourceSuggestions = $state<string[]>([]);
	showSourceSuggestions = $state(false);
	activeSourceSuggestionIndex = $state(0);
	showAllDomains = $state(false);
	showAllTags = $state(false);
	showAllSourceSystems = $state(false);
	filteredSourceSuggestions = $derived(
		this.sourceSuggestions.filter((s) => s.toLowerCase().includes(this.sourceInput.toLowerCase()))
	);

	// Roles
	roleInput = $state('');
	editingRoleName = $state<string | null>(null);
	editingRoleValue = $state('');
	deletingRoleName = $state<string | null>(null);
	showRolesSection = $state(false);
	processes = $state<BusinessEventProcess[]>([]);
	expandedRoles = $state<Set<string>>(new Set());
	autoRoles = $derived(this.entityRoles.filter((r) => r.source));
	uniqueEntityRoles = $derived(dedupeRolesByName(this.entityRoles));

	// Modal UI flags
	showDeleteConfirm = $state(false);
	isDirty = $state(false);
	show7WsDropdown = $state(false);
	showExportDropdown = $state(false);
	showMarkdownSuccess = $state(false);

	// Feedback banners for materialize / binding actions
	materializeWarnings = $state<string[]>([]);
	materializeError = $state('');
	bindingError = $state('');

	/** Load `data` into the form and reset all transient UI state (write-only). */
	reset(data: EntityData) {
		this.editableDraftedFields = [...(data?.drafted_fields || [])];
		this.entityName = data.label || '';
		this.entityDescription = data.description || '';
		this.entityDomains = normalizeDomains(data.domains, data.domain);
		this.entityTags = [...(data.tags || [])];
		this.entitySourceSystems = [...(data.source_system || [])];
		this.entityType = data.entity_type || 'unclassified';
		this.annotationType = data.annotation_type;
		this.entityRoles = [...(data.roles || [])];
		this.tagInput = '';
		this.domainInput = '';
		this.sourceInput = '';
		this.roleInput = '';
		this.editingRoleName = null;
		this.editingRoleValue = '';
		this.deletingRoleName = null;
		this.sourceSuggestions = [];
		this.showSourceSuggestions = false;
		this.activeSourceSuggestionIndex = 0;
		this.showDeleteConfirm = false;
		this.showAllDomains = false;
		this.showAllTags = false;
		this.showAllSourceSystems = false;
		this.showRolesSection = false;
		this.isDirty = false;
		this.materializedDescriptionEdits = new Map();
		this.liveSchemaDescriptions = new Map();
		this.materializeWarnings = [];
		this.materializeError = '';
		this.bindingError = '';
	}

	// --- Tags -------------------------------------------------------------

	addTag = () => {
		const next = appendUnique(this.entityTags, this.tagInput);
		if (next) {
			this.entityTags = next;
			this.tagInput = '';
		}
	};

	removeTag = (tag: string) => {
		this.entityTags = removeFrom(this.entityTags, tag);
	};

	handleTagInputKeydown = (event: KeyboardEvent) => {
		if (event.key === 'Enter') {
			event.preventDefault();
			this.addTag();
		}
	};

	// --- Domains ----------------------------------------------------------

	addDomain = () => {
		const next = appendUnique(this.entityDomains, this.domainInput);
		if (next) {
			this.entityDomains = next;
			this.domainInput = '';
		}
	};

	removeDomain = (domain: string) => {
		this.entityDomains = removeFrom(this.entityDomains, domain);
	};

	handleDomainInputKeydown = (event: KeyboardEvent) => {
		if (event.key === 'Enter') {
			event.preventDefault();
			this.addDomain();
		}
	};

	// --- Source systems ---------------------------------------------------

	addSourceSystem = (source = this.sourceInput) => {
		const next = appendUnique(this.entitySourceSystems, source);
		if (next) {
			this.entitySourceSystems = next;
			this.sourceInput = '';
		}
	};

	removeSourceSystem = (source: string) => {
		this.entitySourceSystems = removeFrom(this.entitySourceSystems, source);
	};

	handleSourceInputKeydown = (event: KeyboardEvent) => {
		if (event.key === 'Escape' && this.showSourceSuggestions) {
			this.showSourceSuggestions = false;
			event.preventDefault();
		} else if (event.key === 'Enter') {
			if (this.showSourceSuggestions && this.filteredSourceSuggestions.length > 0) {
				event.preventDefault();
				this.selectSourceSuggestion(this.filteredSourceSuggestions[this.activeSourceSuggestionIndex]);
			} else {
				event.preventDefault();
				this.addSourceSystem();
			}
		} else if (event.key === 'ArrowDown' && this.showSourceSuggestions) {
			event.preventDefault();
			this.activeSourceSuggestionIndex = Math.min(
				this.activeSourceSuggestionIndex + 1,
				this.filteredSourceSuggestions.length - 1
			);
		} else if (event.key === 'ArrowUp' && this.showSourceSuggestions) {
			event.preventDefault();
			this.activeSourceSuggestionIndex = Math.max(this.activeSourceSuggestionIndex - 1, 0);
		} else if (
			event.key === 'Tab' &&
			this.showSourceSuggestions &&
			this.filteredSourceSuggestions.length > 0
		) {
			event.preventDefault();
			this.selectSourceSuggestion(this.filteredSourceSuggestions[this.activeSourceSuggestionIndex]);
		}
	};

	handleSourceInputFocus = () => {
		this.showSourceSuggestions = true;
		this.activeSourceSuggestionIndex = 0;
	};

	handleSourceInputBlur = () => {
		setTimeout(() => {
			this.showSourceSuggestions = false;
		}, 200);
	};

	handleSourceInput = () => {
		this.showSourceSuggestions = true;
		this.activeSourceSuggestionIndex = 0;
	};

	selectSourceSuggestion = (suggestion: string) => {
		this.addSourceSystem(suggestion);
		this.showSourceSuggestions = false;
		this.sourceInput = '';
		this.activeSourceSuggestionIndex = 0;
	};

	// --- Roles ------------------------------------------------------------

	addRole = () => {
		const result = addRoleByName(this.entityRoles, this.roleInput);
		if (result === null) return;
		if ('error' in result) {
			alert(result.error);
			return;
		}
		this.entityRoles = result;
		this.roleInput = '';
	};

	handleRoleInputKeydown = (event: KeyboardEvent) => {
		if (event.key === 'Enter') {
			event.preventDefault();
			this.addRole();
		}
	};

	startEditingRole = (role: EntityRole) => {
		this.editingRoleName = role.role || '';
		this.editingRoleValue = role.role || '';
	};

	saveEditingRole = () => {
		if (this.editingRoleName === null) return;
		const result = renameRole(this.entityRoles, this.editingRoleName, this.editingRoleValue);
		if ('error' in result) {
			alert(result.error);
			return;
		}
		this.entityRoles = result;
		this.editingRoleName = null;
		this.editingRoleValue = '';
	};

	cancelEditingRole = () => {
		this.editingRoleName = null;
		this.editingRoleValue = '';
	};

	handleEditRoleKeydown = (event: KeyboardEvent) => {
		if (event.key === 'Enter') {
			event.preventDefault();
			this.saveEditingRole();
		} else if (event.key === 'Escape') {
			event.preventDefault();
			this.cancelEditingRole();
		}
	};

	confirmDeleteRole = (roleName: string) => {
		this.deletingRoleName = roleName;
	};

	deleteRole = () => {
		if (this.deletingRoleName === null) return;
		this.entityRoles = removeRoleByName(this.entityRoles, this.deletingRoleName);
		this.deletingRoleName = null;
	};

	cancelDeleteRole = () => {
		this.deletingRoleName = null;
	};

	toggleRoleExpansion = (role: EntityRole) => {
		const roleName = role.role || '';
		if (this.expandedRoles.has(roleName)) {
			this.expandedRoles.delete(roleName);
		} else {
			this.expandedRoles.add(roleName);
		}
		this.expandedRoles = new Set(this.expandedRoles); // Trigger reactivity
	};

	// --- Drafted fields ---------------------------------------------------

	updateDraftedField = (index: number, updates: Partial<DraftedField>) => {
		this.editableDraftedFields = this.editableDraftedFields.map((field, i) =>
			i === index ? { ...field, ...updates } : field
		);
	};

	addDraftedField = () => {
		this.editableDraftedFields = [
			...this.editableDraftedFields,
			{ name: '', datatype: 'text', description: '' }
		];
	};

	deleteDraftedField = (index: number) => {
		this.editableDraftedFields = this.editableDraftedFields.filter((_, i) => i !== index);
	};

	setMaterializedDescription = (columnName: string, value: string) => {
		const map = new Map(this.materializedDescriptionEdits);
		map.set(columnName, value);
		this.materializedDescriptionEdits = map;
	};
}
