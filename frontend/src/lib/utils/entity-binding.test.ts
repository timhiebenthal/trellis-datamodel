import { describe, expect, it } from 'vitest';
import type { ModelInfo } from '$lib/types';
import type { Node } from '@xyflow/svelte';
import { bindModelToNode } from './entity-binding';

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
			entityNode({ label: 'Customers', description: '' }),
			model,
			{ dimensionPrefixes: [], factPrefixes: [] },
		);

		expect(result.changed).toBe(true);
		expect(result.node.data).toMatchObject({
			model_ref: 'model.project.customers',
			description: 'Customer records',
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
