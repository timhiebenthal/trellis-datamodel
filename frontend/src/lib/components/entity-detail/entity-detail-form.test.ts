import { describe, it, expect, vi, afterEach } from 'vitest';
import type { EntityData } from '$lib/types';
import { EntityDetailForm } from './entity-detail-form.svelte';

const key = (k: string) => {
	const event = new KeyboardEvent('keydown', { key: k, cancelable: true });
	return event;
};

afterEach(() => {
	vi.unstubAllGlobals();
});

describe('EntityDetailForm.reset', () => {
	it('loads entity data and clears transient UI state', () => {
		const form = new EntityDetailForm();
		form.tagInput = 'leftover';
		form.showDeleteConfirm = true;
		form.materializeError = 'boom';
		form.isDirty = true;

		form.reset({
			label: 'Order',
			domain: 'Sales',
			tags: ['t'],
			source_system: ['crm'],
			entity_type: 'fact',
			drafted_fields: [{ name: 'id', datatype: 'int' }]
		} as EntityData);

		expect(form.entityName).toBe('Order');
		expect(form.entityDomains).toEqual(['Sales']);
		expect(form.entityTags).toEqual(['t']);
		expect(form.entitySourceSystems).toEqual(['crm']);
		expect(form.entityType).toBe('fact');
		expect(form.editableDraftedFields).toEqual([{ name: 'id', datatype: 'int' }]);
		expect(form.tagInput).toBe('');
		expect(form.showDeleteConfirm).toBe(false);
		expect(form.materializeError).toBe('');
		expect(form.isDirty).toBe(false);
	});

	it('defaults missing fields', () => {
		const form = new EntityDetailForm();
		form.reset({} as EntityData);
		expect(form.entityName).toBe('');
		expect(form.entityType).toBe('unclassified');
		expect(form.entityRoles).toEqual([]);
	});
});

describe('EntityDetailForm chip inputs', () => {
	it('adds a trimmed tag on Enter and clears the input; ignores duplicates', () => {
		const form = new EntityDetailForm();
		form.tagInput = ' pii ';
		const enter = key('Enter');
		form.handleTagInputKeydown(enter);
		expect(enter.defaultPrevented).toBe(true);
		expect(form.entityTags).toEqual(['pii']);
		expect(form.tagInput).toBe('');

		form.tagInput = 'pii';
		form.addTag();
		expect(form.entityTags).toEqual(['pii']);
		expect(form.tagInput).toBe('pii');

		form.removeTag('pii');
		expect(form.entityTags).toEqual([]);
	});

	it('adds and removes domains', () => {
		const form = new EntityDetailForm();
		form.domainInput = 'Sales';
		form.handleDomainInputKeydown(key('Enter'));
		expect(form.entityDomains).toEqual(['Sales']);
		form.removeDomain('Sales');
		expect(form.entityDomains).toEqual([]);
	});

	it('navigates and picks source suggestions with the keyboard', () => {
		const form = new EntityDetailForm();
		form.sourceSuggestions = ['CRM', 'ERP', 'Shop'];
		form.handleSourceInputFocus();
		expect(form.showSourceSuggestions).toBe(true);

		form.sourceInput = 'r';
		expect(form.filteredSourceSuggestions).toEqual(['CRM', 'ERP']);

		form.handleSourceInputKeydown(key('ArrowDown'));
		form.handleSourceInputKeydown(key('ArrowDown'));
		expect(form.activeSourceSuggestionIndex).toBe(1);
		form.handleSourceInputKeydown(key('ArrowUp'));
		form.handleSourceInputKeydown(key('ArrowDown'));

		form.handleSourceInputKeydown(key('Enter'));
		expect(form.entitySourceSystems).toEqual(['ERP']);
		expect(form.showSourceSuggestions).toBe(false);
		expect(form.sourceInput).toBe('');
		expect(form.activeSourceSuggestionIndex).toBe(0);
	});

	it('adds the typed source on Enter when suggestions are hidden, and Escape hides them', () => {
		const form = new EntityDetailForm();
		form.sourceSuggestions = ['CRM'];
		form.showSourceSuggestions = true;
		const escape = key('Escape');
		form.handleSourceInputKeydown(escape);
		expect(form.showSourceSuggestions).toBe(false);
		expect(escape.defaultPrevented).toBe(true);

		form.sourceInput = 'Billing';
		form.handleSourceInputKeydown(key('Enter'));
		expect(form.entitySourceSystems).toEqual(['Billing']);
	});

	it('hides suggestions 200ms after blur', () => {
		vi.useFakeTimers();
		try {
			const form = new EntityDetailForm();
			form.showSourceSuggestions = true;
			form.handleSourceInputBlur();
			vi.advanceTimersByTime(199);
			expect(form.showSourceSuggestions).toBe(true);
			vi.advanceTimersByTime(1);
			expect(form.showSourceSuggestions).toBe(false);
		} finally {
			vi.useRealTimers();
		}
	});
});

describe('EntityDetailForm roles', () => {
	it('adds roles and alerts on duplicates', () => {
		const alert = vi.fn();
		vi.stubGlobal('alert', alert);
		const form = new EntityDetailForm();
		form.roleInput = 'order_date';
		form.handleRoleInputKeydown(key('Enter'));
		expect(form.entityRoles).toEqual([{ role: 'order_date' }]);
		expect(form.roleInput).toBe('');

		form.roleInput = 'order_date';
		form.addRole();
		expect(alert).toHaveBeenCalledWith('Role "order_date" already exists');
		expect(form.roleInput).toBe('order_date');
	});

	it('renames via the edit input and cancels with Escape', () => {
		const form = new EntityDetailForm();
		form.entityRoles = [{ role: 'a', source: 'p1' }, { role: 'a', source: 'p2' }];
		form.startEditingRole({ role: 'a' });
		expect(form.editingRoleName).toBe('a');
		form.editingRoleValue = 'b';
		form.handleEditRoleKeydown(key('Enter'));
		expect(form.entityRoles.map((r) => r.role)).toEqual(['b', 'b']);
		expect(form.editingRoleName).toBeNull();

		form.startEditingRole({ role: 'b' });
		form.editingRoleValue = 'zzz';
		form.handleEditRoleKeydown(key('Escape'));
		expect(form.editingRoleName).toBeNull();
		expect(form.entityRoles.map((r) => r.role)).toEqual(['b', 'b']);
	});

	it('keeps editing when the new name is invalid', () => {
		vi.stubGlobal('alert', vi.fn());
		const form = new EntityDetailForm();
		form.entityRoles = [{ role: 'a' }];
		form.startEditingRole({ role: 'a' });
		form.editingRoleValue = ' ';
		form.saveEditingRole();
		expect(form.editingRoleName).toBe('a');
	});

	it('deletes a role only after confirmation', () => {
		const form = new EntityDetailForm();
		form.entityRoles = [{ role: 'a' }, { role: 'b' }];
		form.confirmDeleteRole('a');
		expect(form.deletingRoleName).toBe('a');
		form.cancelDeleteRole();
		expect(form.entityRoles).toHaveLength(2);

		form.confirmDeleteRole('a');
		form.deleteRole();
		expect(form.entityRoles).toEqual([{ role: 'b' }]);
		expect(form.deletingRoleName).toBeNull();
	});

	it('derives auto (sourced) roles and unique roles', () => {
		const form = new EntityDetailForm();
		form.entityRoles = [{ role: 'x', source: 'p1' }, { role: 'X', source: 'p2' }, { role: 'y' }];
		expect(form.autoRoles).toHaveLength(2);
		expect(form.uniqueEntityRoles.map((r) => r.role)).toEqual(['x', 'y']);
	});

	it('toggles role expansion', () => {
		const form = new EntityDetailForm();
		form.toggleRoleExpansion({ role: 'x' });
		expect(form.expandedRoles.has('x')).toBe(true);
		form.toggleRoleExpansion({ role: 'x' });
		expect(form.expandedRoles.has('x')).toBe(false);
	});
});

describe('EntityDetailForm drafted fields', () => {
	it('adds, updates and deletes drafted fields', () => {
		const form = new EntityDetailForm();
		form.addDraftedField();
		expect(form.editableDraftedFields).toEqual([{ name: '', datatype: 'text', description: '' }]);
		form.updateDraftedField(0, { name: 'amount', datatype: 'float' });
		expect(form.editableDraftedFields[0]).toEqual({ name: 'amount', datatype: 'float', description: '' });
		form.deleteDraftedField(0);
		expect(form.editableDraftedFields).toEqual([]);
	});

	it('stages materialized description edits in a fresh map', () => {
		const form = new EntityDetailForm();
		const before = form.materializedDescriptionEdits;
		form.setMaterializedDescription('id', 'The id');
		expect(form.materializedDescriptionEdits).not.toBe(before);
		expect(form.materializedDescriptionEdits.get('id')).toBe('The id');
	});
});
