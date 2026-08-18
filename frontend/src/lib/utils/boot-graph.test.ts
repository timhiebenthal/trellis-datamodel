import { describe, expect, it } from 'vitest';
import type { Edge, Node } from '@xyflow/svelte';
import type { Entity, ModelInfo } from '$lib/types';
import {
	buildBootGraphIndex,
	transformBootGraph,
	type BootGraphNodeData,
} from './boot-graph';

const models: ModelInfo[] = [
	{
		unique_id: 'model.project.customer',
		name: 'customer',
		version: 1,
		schema: 'analytics',
		table: 'customer',
		columns: [],
	},
	{
		unique_id: 'model.project.order',
		name: 'order',
		version: null,
		schema: 'analytics',
		table: 'order',
		columns: [],
	},
];

const entities: Entity[] = [
	{
		id: 'customer',
		label: 'Customer',
		model_ref: 'model.project.customer',
		additional_models: ['model.project.order'],
		position: { x: 0, y: 0 },
	},
	{
		id: 'order',
		label: 'Order',
		model_ref: 'model.project.order',
		position: { x: 100, y: 100 },
	},
	{
		id: 'unbound',
		label: 'Unbound',
		position: { x: 200, y: 200 },
	},
];

function makeNode(id: string): Node<BootGraphNodeData> {
	return {
		id,
		type: 'entity',
		position: { x: 0, y: 0 },
		data: { label: id },
	};
}

const nodes = entities.map(({ id }) => makeNode(id));
const edges: Edge[] = [
	{ id: 'customer-order', source: 'customer', target: 'order' },
	{ id: 'order-unbound', source: 'order', target: 'unbound' },
];

describe('boot graph helpers', () => {
	it('builds model, entity, and node lookup maps in one pass', () => {
		const index = buildBootGraphIndex({
			models,
			entities,
			nodes,
			activeModelIds: new Map([['customer', 'model.project.order']]),
		});

		expect(index.modelsById.get('model.project.customer')).toBe(models[0]);
		expect(index.entitiesById.get('customer')).toBe(entities[0]);
		expect(index.nodesById.get('customer')).toBe(nodes[0]);
		expect(index.modelsById.size).toBe(2);
		expect(index.entitiesById.size).toBe(3);
		expect(index.nodesById.size).toBe(3);
	});

	it('keeps active-model metadata in a dedicated index, outside node data', () => {
		const index = buildBootGraphIndex({
			models,
			entities,
			nodes,
			activeModelIds: new Map([['customer', 'model.project.order']]),
		});

		expect(index.activeModelsByNodeId.get('customer')).toEqual({
			id: 'model.project.order',
			name: 'order',
			version: null,
		});
		expect(index.nodesById.get('customer')?.data).toEqual({ label: 'customer' });
		expect(index.nodesById.get('customer')?.data).not.toHaveProperty('_activeModelId');
	});

	it('returns original node and edge references when filters are inactive', () => {
		const index = buildBootGraphIndex({ models, entities, nodes });
		const result = transformBootGraph(index, edges);

		expect(result.nodes).toBe(nodes);
		expect(result.edges).toBe(edges);
		expect(result.nodes[0]).toBe(nodes[0]);
		expect(result.edges[0]).toBe(edges[0]);
	});

	it('rewrites only nodes and edges affected by an active-model change', () => {
		const index = buildBootGraphIndex({ models, entities, nodes });
		const result = transformBootGraph(index, edges, {
			activeModelIds: new Map([['customer', 'model.project.order']]),
		});

		expect(result.nodes[0]).not.toBe(nodes[0]);
		expect(result.nodes[1]).toBe(nodes[1]);
		expect(result.nodes[2]).toBe(nodes[2]);
		expect(result.edges[0]).not.toBe(edges[0]);
		expect(result.edges[1]).toBe(edges[1]);
		expect(result.nodes[0].data).toEqual(nodes[0].data);
		expect(result.activeModelsByNodeId.get('customer')?.id).toBe('model.project.order');
	});

	it('rewrites only visible nodes and edges when filters change', () => {
		const index = buildBootGraphIndex({ models, entities, nodes });
		const result = transformBootGraph(index, edges, {
			visibleNodeIds: new Set(['customer', 'order']),
		});

		expect(result.nodes).toEqual([nodes[0], nodes[1]]);
		expect(result.nodes[0]).toBe(nodes[0]);
		expect(result.nodes[1]).toBe(nodes[1]);
		expect(result.edges).toEqual([edges[0]]);
		expect(result.edges[0]).toBe(edges[0]);
	});
});
