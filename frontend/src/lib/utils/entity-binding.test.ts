import { describe, expect, it } from 'vitest';
import type { ModelInfo } from '$lib/types';
import type { Node } from '@xyflow/svelte';
import {
	bindModelToNode,
	buildModelToEntityMap,
	modelShortName,
	remapInferredRelationships,
	renameNode,
	renameNodeInEdges,
} from './entity-binding';

const model: ModelInfo = {
	unique_id: 'model.project.customers',
	name: 'customers',
	schema: 'analytics',
	table: 'customers',
	columns: [],
	description: 'Customer records',
};

function entityNode(data: Record<string, unknown>): Node {
	return {
		id: 'customers',
		type: 'entity',
		position: { x: 0, y: 0 },
		data,
	} as Node;
}

describe('bindModelToNode', () => {
	it('sets the primary model and copies metadata for an unbound entity', () => {
		const result = bindModelToNode(
			entityNode({ label: 'Customers', description: '', tags: ['pii', 'core'] }),
			model,
			{ dimensionPrefixes: [], factPrefixes: [] },
		);

		expect(result.changed).toBe(true);
		expect(result.node.data).toMatchObject({
			model_ref: 'model.project.customers',
			description: 'Customer records',
			ui_tags: ['pii', 'core'],
		});
	});

	it('adds a unique additional model without changing the primary binding', () => {
		const result = bindModelToNode(
			entityNode({
				label: 'Customers',
				model_ref: 'model.project.customers',
				additional_models: ['model.project.customers_history'],
			}),
			{
				...model,
				unique_id: 'model.project.customers_snapshot',
				name: 'customers_snapshot',
			},
		);

		expect(result.changed).toBe(true);
		expect(result.node.data).toMatchObject({
			model_ref: 'model.project.customers',
			additional_models: [
				'model.project.customers_history',
				'model.project.customers_snapshot',
			],
		});
	});

	it('does not duplicate an already-bound model or mutate the node', () => {
		const node = entityNode({
			label: 'Customers',
			model_ref: 'model.project.customers',
			additional_models: ['model.project.customers_history'],
		});

		const result = bindModelToNode(node, {
			...model,
			unique_id: 'model.project.customers_history',
			name: 'customers_history',
		});

		expect(result.changed).toBe(false);
		expect(result.node).toBe(node);
		expect(result.node.data.additional_models).toEqual([
			'model.project.customers_history',
		]);
	});

	it('infers a dimensional entity type from configured prefixes', () => {
		const result = bindModelToNode(
			entityNode({ label: 'Customers' }),
			{ ...model, name: 'dim_customers' },
			{ dimensionPrefixes: ['dim_'], factPrefixes: ['fct_'] },
		);

		expect(result.node.data.entity_type).toBe('dimension');
	});
});

describe('modelShortName', () => {
	it('returns the last dot-separated segment', () => {
		expect(modelShortName('model.project.customers')).toBe('customers');
		expect(modelShortName('model.project.customers.v2')).toBe('v2');
	});

	it('returns ids without dots unchanged', () => {
		expect(modelShortName('customers')).toBe('customers');
	});
});

describe('renameNodeInEdges', () => {
	it('repoints both endpoints and keeps edge ids stable', () => {
		const edges = [
			{ id: 'e1', source: 'old', target: 'b' },
			{ id: 'e2', source: 'a', target: 'old' },
			{ id: 'e3', source: 'a', target: 'b' },
		];
		expect(renameNodeInEdges(edges, 'old', 'new')).toEqual([
			{ id: 'e1', source: 'new', target: 'b' },
			{ id: 'e2', source: 'a', target: 'new' },
			{ id: 'e3', source: 'a', target: 'b' },
		]);
	});
});

describe('renameNode', () => {
	it('renames the matching node and merges the data patch', () => {
		const nodes = [entityNode({ label: 'Old', model_ref: 'x' }), { ...entityNode({ label: 'Other' }), id: 'other' }];
		const result = renameNode(nodes, 'customers', 'clients', { label: 'Clients' });
		expect(result[0].id).toBe('clients');
		expect(result[0].data).toEqual({ label: 'Clients', model_ref: 'x' });
		expect(result[1]).toBe(nodes[1]);
	});
});

describe('buildModelToEntityMap', () => {
	it('maps bound model names (versioned by base name) and entity ids to entities', () => {
		const nodes = [
			{ ...entityNode({ label: 'Orders', model_ref: 'model.p.orders', additional_models: ['model.p.orders_hist.v2'] }), id: 'orders' },
			{ ...entityNode({ label: 'Customers' }), id: 'customers' },
		];
		const map = buildModelToEntityMap(nodes, 'customers', 'customers', ['model.p.customers']);
		expect(map).toEqual({
			orders: 'orders',
			orders_hist: 'orders',
			customers: 'customers',
		});
	});

	it('uses the final id for the renamed current entity', () => {
		const nodes = [{ ...entityNode({ label: 'Clients' }), id: 'clients' }];
		const map = buildModelToEntityMap(nodes, 'new_entity', 'clients', ['model.p.dim_client']);
		expect(map).toEqual({ dim_client: 'clients', clients: 'clients' });
	});
});

describe('remapInferredRelationships', () => {
	const map = { orders: 'orders', dim_client: 'clients', clients: 'clients' };

	it('remaps model names to entity ids and keeps relationships touching the entity', () => {
		const result = remapInferredRelationships(
			[
				{ source: 'dim_client', target: 'orders', type: 'one_to_many' },
				{ source: 'orders', target: 'products', type: 'one_to_many' },
			],
			map,
			'clients',
			['orders', 'clients', 'products'],
		);
		expect(result).toEqual([{ source: 'clients', target: 'orders', type: 'one_to_many' }]);
	});

	it('drops relationships whose other end is not on the canvas', () => {
		const result = remapInferredRelationships(
			[{ source: 'dim_client', target: 'missing', type: 'one_to_many' }],
			map,
			'clients',
			['clients'],
		);
		expect(result).toEqual([]);
	});
});
