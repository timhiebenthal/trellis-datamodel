import { describe, it, expect } from 'vitest';
import type { Edge, Node } from '@xyflow/svelte';
import type { BusinessEventProcess, EntityData } from '$lib/types';
import {
	addRoleByName,
	buildEntityRelationships,
	buildMaterializeColumns,
	buildSchemaColumnsForSave,
	collectUniqueDomains,
	collectUniqueTags,
	dedupeRolesByName,
	getProcessesForRole,
	hasEntityFormChanges,
	moveItem,
	normalizeDomains,
	removeRoleByName,
	renameRole,
	visibleChips,
	type EntityFormSnapshot
} from './entity-detail';

const node = (id: string, data: Record<string, unknown>): Node =>
	({ id, type: 'entity', position: { x: 0, y: 0 }, data }) as Node;

describe('normalizeDomains', () => {
	it('trims, drops blanks and dedupes', () => {
		expect(normalizeDomains([' Sales ', 'Sales', '', 'Ops'])).toEqual(['Sales', 'Ops']);
	});
	it('falls back to the legacy single domain', () => {
		expect(normalizeDomains([], 'Finance')).toEqual(['Finance']);
		expect(normalizeDomains(undefined, undefined)).toEqual([]);
	});
});

describe('visibleChips', () => {
	const items = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h'];
	it('caps at six unless showing all', () => {
		expect(visibleChips(items, false)).toEqual(['a', 'b', 'c', 'd', 'e', 'f']);
		expect(visibleChips(items, true)).toEqual(items);
	});
});

describe('collectUniqueDomains / collectUniqueTags', () => {
	const nodes = [
		node('1', { domains: ['Sales', ' Ops '], tags: ['b', ' a '] }),
		node('2', { domain: 'Finance', tags: ['a', ''] }),
		node('3', {})
	];
	it('gathers sorted, trimmed domains including legacy `domain`', () => {
		expect(collectUniqueDomains(nodes)).toEqual(['Finance', 'Ops', 'Sales']);
	});
	it('gathers sorted, trimmed tags', () => {
		expect(collectUniqueTags(nodes)).toEqual(['a', 'b']);
	});
});

describe('role helpers', () => {
	it('dedupes case-insensitively by role or label, first wins', () => {
		const roles = [
			{ role: 'Creation Date', source: 'p1' },
			{ role: 'creation date', source: 'p2' },
			{ label: 'Only Label' },
			{ label: 'only label' }
		];
		expect(dedupeRolesByName(roles)).toEqual([roles[0], roles[2]]);
	});

	it('adds a trimmed role, ignores blank input, rejects duplicates', () => {
		expect(addRoleByName([], '  ship_date ')).toEqual([{ role: 'ship_date' }]);
		expect(addRoleByName([], '   ')).toBeNull();
		expect(addRoleByName([{ role: 'x' }], 'x')).toEqual({ error: 'Role "x" already exists' });
	});

	it('renames every entry sharing a name and validates the new name', () => {
		const roles = [{ role: 'a', source: 'p1' }, { role: 'a', source: 'p2' }, { role: 'b' }];
		expect(renameRole(roles, 'a', ' c ')).toEqual([
			{ role: 'c', source: 'p1' },
			{ role: 'c', source: 'p2' },
			{ role: 'b' }
		]);
		expect(renameRole(roles, 'a', 'a')).toEqual(roles);
		expect(renameRole(roles, 'a', '  ')).toEqual({ error: 'Role name cannot be empty' });
		expect(renameRole(roles, 'a', 'b')).toEqual({ error: 'Role "b" already exists' });
	});

	it('removes all entries sharing a name', () => {
		expect(removeRoleByName([{ role: 'a' }, { role: 'a', source: 'p' }, { role: 'b' }], 'a')).toEqual([
			{ role: 'b' }
		]);
	});

	it('finds the processes whose annotations use the dimension in that role', () => {
		const processes = [
			{ id: 'p1', annotations_superset: { when: [{ dimension_id: 'dim', role: 'order_date' }] } },
			{ id: 'p2', annotations_superset: { when: [{ dimension_id: 'dim', role: 'ship_date' }] } },
			{ id: 'p3', annotations_superset: { who: [{ dimension_id: 'other', role: 'order_date' }] } },
			{ id: 'p4' }
		] as unknown as BusinessEventProcess[];
		expect(getProcessesForRole(processes, 'dim', { role: 'order_date' }).map((p) => p.id)).toEqual(['p1']);
	});
});

describe('moveItem', () => {
	it('moves an item without mutating the input', () => {
		const input = ['a', 'b', 'c'];
		expect(moveItem(input, 0, 2)).toEqual(['b', 'c', 'a']);
		expect(moveItem(input, 2, 0)).toEqual(['c', 'a', 'b']);
		expect(input).toEqual(['a', 'b', 'c']);
	});
});

describe('buildEntityRelationships', () => {
	const nodes = [node('lead', { label: 'Lead' }), node('ir', { label: 'Invoice Recipient' })];
	const edges = [
		{
			id: 'e1',
			source: 'ir',
			target: 'lead',
			data: { type: 'one_to_many', label: 'customer' }
		},
		{ id: 'e2', source: 'lead', target: 'missing' },
		{ id: 'e3', source: 'x', target: 'y' }
	] as Edge[];

	it('returns nothing without an entity id', () => {
		expect(buildEntityRelationships(undefined, edges, nodes)).toEqual([]);
	});

	it('lists touching edges with direction, names and cardinality', () => {
		const rows = buildEntityRelationships('lead', edges, nodes);
		expect(rows.map((r) => [r.edgeId, r.relatedId, r.relatedName, r.isOutgoing])).toEqual([
			['e1', 'ir', 'Invoice Recipient', false],
			['e2', 'missing', 'missing', true]
		]);
		expect(rows[0].cardinality).toBe('1:N');
		expect(rows[0].label).toBe('customer');
		expect(rows[1].label).toBe('');
	});
});

describe('hasEntityFormChanges', () => {
	const data: EntityData = {
		label: 'Customer',
		description: 'desc',
		domains: ['Sales'],
		tags: ['b', 'a'],
		source_system: ['crm'],
		entity_type: 'dimension',
		annotation_type: 'who',
		roles: [{ role: 'buyer' }],
		drafted_fields: [{ name: 'id', datatype: 'int' }]
	} as EntityData;

	const pristine = (): EntityFormSnapshot => ({
		entityName: 'Customer',
		entityDescription: 'desc',
		entityDomains: ['Sales'],
		entityTags: ['a', 'b'],
		entitySourceSystems: ['crm'],
		sourceInput: '',
		entityType: 'dimension',
		annotationType: 'who',
		entityRoles: [{ role: 'buyer' }],
		materializedEditCount: 0,
		editableDraftedFields: [{ name: 'id', datatype: 'int' }]
	});

	it('is clean when the form matches the data (order-insensitive tags)', () => {
		expect(hasEntityFormChanges(data, pristine())).toBe(false);
	});

	it.each([
		['entityName', 'Client'],
		['entityDescription', ''],
		['entityDomains', ['Ops']],
		['entityTags', ['a']],
		['entitySourceSystems', []],
		['sourceInput', ' erp '],
		['entityType', 'fact'],
		['annotationType', undefined],
		['entityRoles', []],
		['materializedEditCount', 1],
		['editableDraftedFields', []]
	] as const)('is dirty when %s changes', (key, value) => {
		const form = { ...pristine(), [key]: value } as EntityFormSnapshot;
		expect(hasEntityFormChanges(data, form)).toBe(true);
	});

	it('ignores a whitespace-only pending source input', () => {
		expect(hasEntityFormChanges(data, { ...pristine(), sourceInput: '   ' })).toBe(false);
	});

	it('sorts the form tag/source arrays in place (preserved chip-order side effect)', () => {
		// Tags equal the stored set (so evaluation reaches the source comparison).
		const form = { ...pristine(), entityTags: ['b', 'a'], entitySourceSystems: ['y', 'b'] };
		hasEntityFormChanges(data, form);
		expect(form.entityTags).toEqual(['a', 'b']);
		expect(form.entitySourceSystems).toEqual(['b', 'y']);
	});
});

describe('schema column builders', () => {
	const columns = [
		{ name: 'id', type: 'int', description: 'manifest id' },
		{ name: 'name', type: 'text' },
		{ name: 'created_at', type: 'timestamp', description: 'manifest created' }
	];

	it('resolves descriptions as staged edit > live schema.yml > manifest > empty', () => {
		const edits = new Map([['id', 'edited id']]);
		const live = new Map([['id', 'live id'], ['created_at', 'live created']]);
		expect(buildSchemaColumnsForSave(columns, edits, live)).toEqual([
			{ name: 'id', data_type: 'int', description: 'edited id' },
			{ name: 'name', data_type: 'text', description: '' },
			{ name: 'created_at', data_type: 'timestamp', description: 'live created' }
		]);
		expect(buildSchemaColumnsForSave(undefined, edits, live)).toEqual([]);
	});

	it('appends the draft, defaulting unknown datatypes to text', () => {
		expect(buildMaterializeColumns(columns.slice(0, 2), { name: 'new_col', datatype: 'unknown' })).toEqual([
			{ name: 'id', data_type: 'int', description: 'manifest id' },
			{ name: 'name', data_type: 'text', description: '' },
			{ name: 'new_col', data_type: 'text', description: '' }
		]);
		expect(
			buildMaterializeColumns(undefined, { name: 'amt', datatype: 'float', description: 'Amount' })
		).toEqual([{ name: 'amt', data_type: 'float', description: 'Amount' }]);
	});
});
