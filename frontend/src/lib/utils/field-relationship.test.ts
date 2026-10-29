import { describe, expect, it } from 'vitest';
import type { Edge } from '@xyflow/svelte';
import type { ModelInfo } from '$lib/types';
import {
	assignFieldsToEdge,
	findGenericEdge,
	hasFieldEdge,
	inferGreenfieldRelationshipType,
	resolveActiveModel,
} from './field-relationship';

const models = [
	{ unique_id: 'model.p.orders', name: 'orders', version: null },
	{ unique_id: 'model.p.orders_hist', name: 'orders_hist', version: 2 },
] as ModelInfo[];

describe('resolveActiveModel', () => {
	it('prefers the ephemeral active model', () => {
		expect(
			resolveActiveModel(
				{ label: 'O', model_ref: 'model.p.orders', _activeModelName: 'orders_hist', _activeModelVersion: 2 },
				models,
			),
		).toEqual({ name: 'orders_hist', version: 2 });
	});

	it('falls back to the primary, then the first additional model', () => {
		expect(resolveActiveModel({ label: 'O', model_ref: 'model.p.orders' }, models)).toBe(models[0]);
		expect(resolveActiveModel({ label: 'O', additional_models: ['model.p.orders_hist'] }, models)).toBe(
			models[1],
		);
	});

	it('returns null for unbound or unknown models', () => {
		expect(resolveActiveModel(undefined, models)).toBeNull();
		expect(resolveActiveModel({ label: 'O', model_ref: 'model.p.unknown' }, models)).toBeNull();
	});
});

const edges: Edge[] = [
	{ id: 'linked', source: 'a', target: 'b', data: { source_field: 'id', target_field: 'a_id' } },
	{ id: 'generic', source: 'b', target: 'c', data: {} },
];

describe('hasFieldEdge', () => {
	it('matches only the exact field pair in the same direction', () => {
		expect(hasFieldEdge(edges, 'a', 'b', 'id', 'a_id')).toBe(true);
		expect(hasFieldEdge(edges, 'b', 'a', 'id', 'a_id')).toBe(false);
		expect(hasFieldEdge(edges, 'a', 'b', 'id', 'other')).toBe(false);
	});
});

describe('findGenericEdge', () => {
	it('finds a field-less edge in either direction', () => {
		expect(findGenericEdge(edges, 'c', 'b')?.id).toBe('generic');
		expect(findGenericEdge(edges, 'a', 'b')).toBeUndefined();
	});
});

describe('assignFieldsToEdge', () => {
	it('sets fields and the drag direction on the given edge only', () => {
		const result = assignFieldsToEdge(edges, 'generic', 'c', 'b', 'b_id', 'id');
		expect(result[0]).toBe(edges[0]);
		expect(result[1]).toEqual({
			id: 'generic',
			source: 'c',
			target: 'b',
			data: { source_field: 'b_id', target_field: 'id' },
		});
	});
});

describe('inferGreenfieldRelationshipType', () => {
	it('is many_to_one only for fact -> dimension', () => {
		expect(inferGreenfieldRelationshipType('fact', 'dimension')).toBe('many_to_one');
		expect(inferGreenfieldRelationshipType('dimension', 'fact')).toBe('one_to_many');
		expect(inferGreenfieldRelationshipType('unclassified', 'unclassified')).toBe('one_to_many');
	});
});
