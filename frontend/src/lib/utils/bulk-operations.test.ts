import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
	bulkAssignDomain,
	bulkAddTags,
	bulkRemoveTags,
	bulkDeleteEntities,
} from './bulk-operations';
import { nodes as nodesStore, edges as edgesStore, entitySelection } from '$lib/stores';
import { get } from 'svelte/store';
import type { Node, Edge } from '@xyflow/svelte';

// Mock pushHistory
vi.mock('$lib/stores', async () => {
	const actual = await vi.importActual('$lib/stores');
	return {
		...actual,
		pushHistory: vi.fn(),
	};
});

describe('bulk-operations', () => {
	// Helper to create entity node
	const createEntityNode = (
		id: string,
		label: string,
		domain?: string,
		tags?: string[]
	): Node => ({
		id,
		type: 'entity',
		position: { x: 0, y: 0 },
		data: {
			label,
			domain,
			tags,
			entity_type: 'dimension',
			attributes: [],
		},
	});

	// Helper to create edge
	const createEdge = (id: string, source: string, target: string): Edge => ({
		id,
		source,
		target,
	});

	beforeEach(() => {
		// Reset stores before each test
		nodesStore.set([]);
		edgesStore.set([]);
		entitySelection.set(new Set());
		vi.clearAllMocks();
	});

	describe('bulkAssignDomain', () => {
		it('should assign domain to multiple entities', () => {
			const nodes = [
				createEntityNode('1', 'Customer'),
				createEntityNode('2', 'Order'),
				createEntityNode('3', 'Product'),
			];
			nodesStore.set(nodes);

			bulkAssignDomain(['1', '2'], 'Sales');

			const updatedNodes = get(nodesStore);
			expect(updatedNodes[0].data.domain).toBe('Sales');
			expect(updatedNodes[1].data.domain).toBe('Sales');
			expect(updatedNodes[2].data.domain).toBeUndefined();
		});

		it('should only update entity nodes, not other node types', () => {
			const nodes = [
				createEntityNode('1', 'Customer'),
				{ id: '2', type: 'process', position: { x: 0, y: 0 }, data: {} },
				createEntityNode('3', 'Product'),
			];
			nodesStore.set(nodes);

			bulkAssignDomain(['1', '2', '3'], 'Sales');

			const updatedNodes = get(nodesStore);
			expect(updatedNodes[0].data.domain).toBe('Sales');
			expect(updatedNodes[1].data.domain).toBeUndefined(); // Process node unchanged
			expect(updatedNodes[2].data.domain).toBe('Sales');
		});

		it('should call pushHistory when modifications are made', async () => {
			const { pushHistory } = await import('$lib/stores');
			const nodes = [createEntityNode('1', 'Customer')];
			nodesStore.set(nodes);

			bulkAssignDomain(['1'], 'Sales');

			expect(pushHistory).toHaveBeenCalledTimes(1);
		});

		it('should not call pushHistory when no entities match', async () => {
			const { pushHistory } = await import('$lib/stores');
			const nodes = [createEntityNode('1', 'Customer')];
			nodesStore.set(nodes);

			bulkAssignDomain(['999'], 'Sales'); // Non-existent ID

			expect(pushHistory).not.toHaveBeenCalled();
		});

		it('should handle empty entityIds array', () => {
			const nodes = [createEntityNode('1', 'Customer')];
			nodesStore.set(nodes);

			bulkAssignDomain([], 'Sales');

			const updatedNodes = get(nodesStore);
			expect(updatedNodes).toEqual(nodes); // No changes
		});

		it('should overwrite existing domain', () => {
			const nodes = [createEntityNode('1', 'Customer', 'Marketing')];
			nodesStore.set(nodes);

			bulkAssignDomain(['1'], 'Sales');

			const updatedNodes = get(nodesStore);
			expect(updatedNodes[0].data.domain).toBe('Sales');
		});

		it('should handle large batch of entities', () => {
			const nodes = Array.from({ length: 100 }, (_, i) =>
				createEntityNode(String(i), `Entity ${i}`)
			);
			nodesStore.set(nodes);

			const entityIds = Array.from({ length: 100 }, (_, i) => String(i));
			bulkAssignDomain(entityIds, 'Sales');

			const updatedNodes = get(nodesStore);
			updatedNodes.forEach((node) => {
				expect(node.data.domain).toBe('Sales');
			});
		});

		it('should preserve other node data fields', () => {
			const nodes = [
				createEntityNode('1', 'Customer', 'Marketing', ['pii', 'master-data']),
			];
			nodesStore.set(nodes);

			bulkAssignDomain(['1'], 'Sales');

			const updatedNodes = get(nodesStore);
			expect(updatedNodes[0].data.label).toBe('Customer');
			expect(updatedNodes[0].data.tags).toEqual(['pii', 'master-data']);
			expect(updatedNodes[0].data.entity_type).toBe('dimension');
		});
	});

	describe('bulkAddTags', () => {
		it('should add tags to multiple entities', () => {
			const nodes = [
				createEntityNode('1', 'Customer'),
				createEntityNode('2', 'Order'),
				createEntityNode('3', 'Product'),
			];
			nodesStore.set(nodes);

			bulkAddTags(['1', '2'], ['pii', 'sensitive']);

			const updatedNodes = get(nodesStore);
			expect(updatedNodes[0].data.tags).toEqual(['pii', 'sensitive']);
			expect(updatedNodes[1].data.tags).toEqual(['pii', 'sensitive']);
			expect(updatedNodes[2].data.tags).toBeUndefined();
		});

		it('should avoid duplicate tags', () => {
			const nodes = [createEntityNode('1', 'Customer', 'Sales', ['pii'])];
			nodesStore.set(nodes);

			bulkAddTags(['1'], ['pii', 'sensitive']);

			const updatedNodes = get(nodesStore);
			expect(updatedNodes[0].data.tags).toEqual(['pii', 'sensitive']); // No duplicate 'pii'
		});

		it('should merge with existing tags', () => {
			const nodes = [createEntityNode('1', 'Customer', 'Sales', ['master-data'])];
			nodesStore.set(nodes);

			bulkAddTags(['1'], ['pii', 'sensitive']);

			const updatedNodes = get(nodesStore);
			expect(updatedNodes[0].data.tags).toEqual(['master-data', 'pii', 'sensitive']);
		});

		it('should handle entities with undefined tags', () => {
			const nodes = [{ ...createEntityNode('1', 'Customer'), data: { label: 'Customer' } }];
			nodesStore.set(nodes);

			bulkAddTags(['1'], ['pii']);

			const updatedNodes = get(nodesStore);
			expect(updatedNodes[0].data.tags).toEqual(['pii']);
		});

		it('should handle entities with empty tags array', () => {
			const nodes = [createEntityNode('1', 'Customer', 'Sales', [])];
			nodesStore.set(nodes);

			bulkAddTags(['1'], ['pii']);

			const updatedNodes = get(nodesStore);
			expect(updatedNodes[0].data.tags).toEqual(['pii']);
		});

		it('should call pushHistory when modifications are made', async () => {
			const { pushHistory } = await import('$lib/stores');
			const nodes = [createEntityNode('1', 'Customer')];
			nodesStore.set(nodes);

			bulkAddTags(['1'], ['pii']);

			expect(pushHistory).toHaveBeenCalledTimes(1);
		});

		it('should not call pushHistory when no new tags added', async () => {
			const { pushHistory } = await import('$lib/stores');
			const nodes = [createEntityNode('1', 'Customer', 'Sales', ['pii'])];
			nodesStore.set(nodes);

			bulkAddTags(['1'], ['pii']); // Tag already exists

			expect(pushHistory).not.toHaveBeenCalled();
		});

		it('should handle empty entityIds array', () => {
			const nodes = [createEntityNode('1', 'Customer')];
			nodesStore.set(nodes);

			bulkAddTags([], ['pii']);

			const updatedNodes = get(nodesStore);
			expect(updatedNodes).toEqual(nodes); // No changes
		});

		it('should handle empty tagsToAdd array', () => {
			const nodes = [createEntityNode('1', 'Customer')];
			nodesStore.set(nodes);

			bulkAddTags(['1'], []);

			const updatedNodes = get(nodesStore);
			expect(updatedNodes).toEqual(nodes); // No changes
		});

		it('should only update entity nodes', () => {
			const nodes = [
				createEntityNode('1', 'Customer'),
				{ id: '2', type: 'process', position: { x: 0, y: 0 }, data: {} },
			];
			nodesStore.set(nodes);

			bulkAddTags(['1', '2'], ['pii']);

			const updatedNodes = get(nodesStore);
			expect(updatedNodes[0].data.tags).toEqual(['pii']);
			expect(updatedNodes[1].data.tags).toBeUndefined();
		});

		it('should handle large number of tags', () => {
			const nodes = [createEntityNode('1', 'Customer')];
			nodesStore.set(nodes);

			const manyTags = Array.from({ length: 20 }, (_, i) => `tag-${i}`);
			bulkAddTags(['1'], manyTags);

			const updatedNodes = get(nodesStore);
			expect(updatedNodes[0].data.tags).toHaveLength(20);
		});

		it('should handle non-array tags field gracefully', () => {
			const nodes = [
				{
					...createEntityNode('1', 'Customer'),
					data: { label: 'Customer', tags: 'not-an-array' as any },
				},
			];
			nodesStore.set(nodes);

			bulkAddTags(['1'], ['pii']);

			const updatedNodes = get(nodesStore);
			expect(updatedNodes[0].data.tags).toEqual(['pii']); // Replaces invalid value
		});
	});

	describe('bulkRemoveTags', () => {
		it('should remove tags from multiple entities', () => {
			const nodes = [
				createEntityNode('1', 'Customer', 'Sales', ['pii', 'sensitive', 'master-data']),
				createEntityNode('2', 'Order', 'Sales', ['pii', 'transactional']),
			];
			nodesStore.set(nodes);

			bulkRemoveTags(['1', '2'], ['pii']);

			const updatedNodes = get(nodesStore);
			expect(updatedNodes[0].data.tags).toEqual(['sensitive', 'master-data']);
			expect(updatedNodes[1].data.tags).toEqual(['transactional']);
		});

		it('should remove multiple tags at once', () => {
			const nodes = [
				createEntityNode('1', 'Customer', 'Sales', ['pii', 'sensitive', 'master-data']),
			];
			nodesStore.set(nodes);

			bulkRemoveTags(['1'], ['pii', 'sensitive']);

			const updatedNodes = get(nodesStore);
			expect(updatedNodes[0].data.tags).toEqual(['master-data']);
		});

		it('should set tags to undefined when all tags removed', () => {
			const nodes = [createEntityNode('1', 'Customer', 'Sales', ['pii'])];
			nodesStore.set(nodes);

			bulkRemoveTags(['1'], ['pii']);

			const updatedNodes = get(nodesStore);
			expect(updatedNodes[0].data.tags).toBeUndefined();
		});

		it('should handle entities without matching tags', () => {
			const nodes = [createEntityNode('1', 'Customer', 'Sales', ['master-data'])];
			nodesStore.set(nodes);

			bulkRemoveTags(['1'], ['pii']); // Tag doesn't exist

			const updatedNodes = get(nodesStore);
			expect(updatedNodes[0].data.tags).toEqual(['master-data']); // Unchanged
		});

		it('should handle entities with undefined tags', () => {
			const nodes = [createEntityNode('1', 'Customer')];
			nodesStore.set(nodes);

			bulkRemoveTags(['1'], ['pii']);

			const updatedNodes = get(nodesStore);
			expect(updatedNodes[0].data.tags).toBeUndefined(); // Still undefined
		});

		it('should handle entities with empty tags array', () => {
			const nodes = [createEntityNode('1', 'Customer', 'Sales', [])];
			nodesStore.set(nodes);

			bulkRemoveTags(['1'], ['pii']);

			const updatedNodes = get(nodesStore);
			expect(updatedNodes[0].data.tags).toBeUndefined(); // Empty array becomes undefined
		});

		it('should call pushHistory when modifications are made', async () => {
			const { pushHistory } = await import('$lib/stores');
			const nodes = [createEntityNode('1', 'Customer', 'Sales', ['pii'])];
			nodesStore.set(nodes);

			bulkRemoveTags(['1'], ['pii']);

			expect(pushHistory).toHaveBeenCalledTimes(1);
		});

		it('should not call pushHistory when no tags removed', async () => {
			const { pushHistory } = await import('$lib/stores');
			const nodes = [createEntityNode('1', 'Customer', 'Sales', ['master-data'])];
			nodesStore.set(nodes);

			bulkRemoveTags(['1'], ['pii']); // Tag doesn't exist

			expect(pushHistory).not.toHaveBeenCalled();
		});

		it('should handle empty entityIds array', () => {
			const nodes = [createEntityNode('1', 'Customer', 'Sales', ['pii'])];
			nodesStore.set(nodes);

			bulkRemoveTags([], ['pii']);

			const updatedNodes = get(nodesStore);
			expect(updatedNodes).toEqual(nodes); // No changes
		});

		it('should handle empty tagsToRemove array', () => {
			const nodes = [createEntityNode('1', 'Customer', 'Sales', ['pii'])];
			nodesStore.set(nodes);

			bulkRemoveTags(['1'], []);

			const updatedNodes = get(nodesStore);
			expect(updatedNodes).toEqual(nodes); // No changes
		});

		it('should only update entity nodes', () => {
			const nodes = [
				createEntityNode('1', 'Customer', 'Sales', ['pii']),
				{ id: '2', type: 'process', position: { x: 0, y: 0 }, data: { tags: ['pii'] } },
			];
			nodesStore.set(nodes);

			bulkRemoveTags(['1', '2'], ['pii']);

			const updatedNodes = get(nodesStore);
			expect(updatedNodes[0].data.tags).toBeUndefined(); // Entity tag removed
			expect(updatedNodes[1].data.tags).toEqual(['pii']); // Process node unchanged
		});

		it('should handle non-array tags field gracefully', () => {
			const nodes = [
				{
					...createEntityNode('1', 'Customer'),
					data: { label: 'Customer', tags: 'not-an-array' as any },
				},
			];
			nodesStore.set(nodes);

			bulkRemoveTags(['1'], ['pii']);

			const updatedNodes = get(nodesStore);
			// Should not crash, tags remain unchanged (not an array)
			expect(updatedNodes[0].data.tags).toBe('not-an-array');
		});
	});

	describe('bulkDeleteEntities', () => {
		it('should delete multiple entities', () => {
			const nodes = [
				createEntityNode('1', 'Customer'),
				createEntityNode('2', 'Order'),
				createEntityNode('3', 'Product'),
			];
			nodesStore.set(nodes);

			bulkDeleteEntities(['1', '2']);

			const updatedNodes = get(nodesStore);
			expect(updatedNodes).toHaveLength(1);
			expect(updatedNodes[0].id).toBe('3');
		});

		it('should remove edges connected to deleted entities', () => {
			const nodes = [
				createEntityNode('1', 'Customer'),
				createEntityNode('2', 'Order'),
				createEntityNode('3', 'Product'),
			];
			const edges = [
				createEdge('e1', '1', '2'), // Customer -> Order
				createEdge('e2', '2', '3'), // Order -> Product
			];
			nodesStore.set(nodes);
			edgesStore.set(edges);

			bulkDeleteEntities(['2']); // Delete Order

			const updatedNodes = get(nodesStore);
			const updatedEdges = get(edgesStore);
			expect(updatedNodes).toHaveLength(2);
			expect(updatedEdges).toHaveLength(0); // Both edges removed (connected to Order)
		});

		it('should preserve edges not connected to deleted entities', () => {
			const nodes = [
				createEntityNode('1', 'Customer'),
				createEntityNode('2', 'Order'),
				createEntityNode('3', 'Product'),
			];
			const edges = [
				createEdge('e1', '1', '2'), // Customer -> Order
				createEdge('e2', '2', '3'), // Order -> Product
			];
			nodesStore.set(nodes);
			edgesStore.set(edges);

			bulkDeleteEntities(['1']); // Delete Customer

			const updatedEdges = get(edgesStore);
			expect(updatedEdges).toHaveLength(1);
			expect(updatedEdges[0].id).toBe('e2'); // Order -> Product still exists
		});

		it('should clear entitySelection store', () => {
			const nodes = [
				createEntityNode('1', 'Customer'),
				createEntityNode('2', 'Order'),
			];
			nodesStore.set(nodes);
			entitySelection.set(new Set(['1', '2']));

			bulkDeleteEntities(['1']);

			const selection = get(entitySelection);
			expect(selection.size).toBe(0);
		});

		it('should call pushHistory when modifications are made', async () => {
			const { pushHistory } = await import('$lib/stores');
			const nodes = [createEntityNode('1', 'Customer')];
			nodesStore.set(nodes);

			bulkDeleteEntities(['1']);

			expect(pushHistory).toHaveBeenCalledTimes(1);
		});

		it('should not call pushHistory when no entities deleted', async () => {
			const { pushHistory } = await import('$lib/stores');
			const nodes = [createEntityNode('1', 'Customer')];
			nodesStore.set(nodes);

			bulkDeleteEntities(['999']); // Non-existent ID

			expect(pushHistory).not.toHaveBeenCalled();
		});

		it('should handle empty entityIds array', () => {
			const nodes = [createEntityNode('1', 'Customer')];
			nodesStore.set(nodes);

			bulkDeleteEntities([]);

			const updatedNodes = get(nodesStore);
			expect(updatedNodes).toEqual(nodes); // No changes
		});

		it('should handle deleting all entities', () => {
			const nodes = [
				createEntityNode('1', 'Customer'),
				createEntityNode('2', 'Order'),
			];
			nodesStore.set(nodes);

			bulkDeleteEntities(['1', '2']);

			const updatedNodes = get(nodesStore);
			expect(updatedNodes).toHaveLength(0);
		});

		it('should handle non-existent entity IDs gracefully', () => {
			const nodes = [createEntityNode('1', 'Customer')];
			nodesStore.set(nodes);

			bulkDeleteEntities(['999', '1000']);

			const updatedNodes = get(nodesStore);
			expect(updatedNodes).toEqual(nodes); // No changes
		});

		it('should preserve non-entity nodes', () => {
			const nodes = [
				createEntityNode('1', 'Customer'),
				{ id: '2', type: 'process', position: { x: 0, y: 0 }, data: {} },
				createEntityNode('3', 'Product'),
			];
			nodesStore.set(nodes);

			bulkDeleteEntities(['1', '2', '3']);

			const updatedNodes = get(nodesStore);
			expect(updatedNodes).toHaveLength(1);
			expect(updatedNodes[0].id).toBe('2'); // Process node preserved
			expect(updatedNodes[0].type).toBe('process');
		});

		it('should handle large batch deletion', () => {
			const nodes = Array.from({ length: 100 }, (_, i) =>
				createEntityNode(String(i), `Entity ${i}`)
			);
			nodesStore.set(nodes);

			const idsToDelete = Array.from({ length: 50 }, (_, i) => String(i));
			bulkDeleteEntities(idsToDelete);

			const updatedNodes = get(nodesStore);
			expect(updatedNodes).toHaveLength(50);
		});

		it('should handle deletion when only edges change', async () => {
			const { pushHistory } = await import('$lib/stores');
			const nodes = [createEntityNode('1', 'Customer')];
			const edges = [createEdge('e1', '999', '1')]; // Edge from non-existent node
			nodesStore.set(nodes);
			edgesStore.set(edges);

			bulkDeleteEntities(['1']); // Delete Customer

			const updatedNodes = get(nodesStore);
			const updatedEdges = get(edgesStore);
			expect(updatedNodes).toHaveLength(0);
			expect(updatedEdges).toHaveLength(0);
			expect(pushHistory).toHaveBeenCalledTimes(1);
		});
	});
});
