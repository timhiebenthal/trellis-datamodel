import { describe, it, expect } from 'vitest';
import { groupEntitiesByDomain, groupEntitiesByTag } from './entity-grouping';
import type { Entity } from '$lib/types';

describe('entity-grouping', () => {
	// Helper function to create test entities
	const createEntity = (
		id: string,
		label: string,
		domain?: string,
		tags?: string[],
		domains?: string[]
	): Entity => ({
		id,
		label,
		domain,
		domains,
		tags,
		description: '',
		entity_type: 'dimension',
		attributes: [],
	});

	describe('groupEntitiesByDomain', () => {
		it('should group entities by domain', () => {
			const entities = [
				createEntity('1', 'Customer', 'Sales'),
				createEntity('2', 'Order', 'Sales'),
				createEntity('3', 'Product', 'Inventory'),
			];

			const result = groupEntitiesByDomain(entities);

			expect(result.size).toBe(2);
			expect(result.get('Sales')).toHaveLength(2);
			expect(result.get('Inventory')).toHaveLength(1);
			expect(result.get('Sales')?.map((e) => e.label)).toEqual(['Customer', 'Order']);
			expect(result.get('Inventory')?.map((e) => e.label)).toEqual(['Product']);
		});

		it('should put entities without domain in "Unassigned" group', () => {
			const entities = [
				createEntity('1', 'Customer', 'Sales'),
				createEntity('2', 'Order'), // No domain
				createEntity('3', 'Product'), // No domain
			];

			const result = groupEntitiesByDomain(entities);

			expect(result.size).toBe(2);
			expect(result.get('Unassigned')).toHaveLength(2);
			expect(result.get('Unassigned')?.map((e) => e.label)).toEqual(['Order', 'Product']);
		});

		it('should sort "Unassigned" group alphabetically by label', () => {
			const entities = [
				createEntity('1', 'Zebra'),
				createEntity('2', 'Apple'),
				createEntity('3', 'Mango'),
			];

			const result = groupEntitiesByDomain(entities);

			expect(result.get('Unassigned')?.map((e) => e.label)).toEqual([
				'Apple',
				'Mango',
				'Zebra',
			]);
		});

		it('should handle empty entities array', () => {
			const result = groupEntitiesByDomain([]);

			expect(result.size).toBe(0);
		});

		it('should handle entities with empty string domain', () => {
			const entities = [
				createEntity('1', 'Customer', ''),
				createEntity('2', 'Order', 'Sales'),
			];

			const result = groupEntitiesByDomain(entities);

			expect(result.size).toBe(2);
			expect(result.get('Unassigned')).toHaveLength(1);
			expect(result.get('Unassigned')?.map((e) => e.label)).toEqual(['Customer']);
		});

		it('should handle single domain with multiple entities', () => {
			const entities = [
				createEntity('1', 'Customer', 'Sales'),
				createEntity('2', 'Order', 'Sales'),
				createEntity('3', 'Invoice', 'Sales'),
				createEntity('4', 'Payment', 'Sales'),
			];

			const result = groupEntitiesByDomain(entities);

			expect(result.size).toBe(1);
			expect(result.get('Sales')).toHaveLength(4);
		});

		it('should handle multiple domains', () => {
			const entities = [
				createEntity('1', 'Customer', 'Sales'),
				createEntity('2', 'Product', 'Inventory'),
				createEntity('3', 'Invoice', 'Finance'),
				createEntity('4', 'Warehouse', 'Logistics'),
			];

			const result = groupEntitiesByDomain(entities);

			expect(result.size).toBe(4);
			expect(Array.from(result.keys())).toEqual(['Sales', 'Inventory', 'Finance', 'Logistics']);
		});

		it('should allow entities in multiple domains', () => {
			const entities = [
				createEntity('1', 'Customer', undefined, undefined, ['Sales', 'Marketing']),
				createEntity('2', 'Product', 'Inventory'),
			];

			const result = groupEntitiesByDomain(entities);

			expect(result.get('Sales')?.map((e) => e.label)).toEqual(['Customer']);
			expect(result.get('Marketing')?.map((e) => e.label)).toEqual(['Customer']);
			expect(result.get('Inventory')?.map((e) => e.label)).toEqual(['Product']);
		});

		it('should preserve original order within domain groups (except Unassigned)', () => {
			const entities = [
				createEntity('1', 'Zebra', 'Sales'),
				createEntity('2', 'Apple', 'Sales'),
				createEntity('3', 'Mango', 'Sales'),
			];

			const result = groupEntitiesByDomain(entities);

			// Default sort is A-Z
			expect(result.get('Sales')?.map((e) => e.label)).toEqual(['Apple', 'Mango', 'Zebra']);
		});

		describe('Name sorting', () => {
			it('should sort entities A-Z within a named domain group when sortDirection is asc', () => {
				const entities = [
					createEntity('1', 'Zebra', 'Sales'),
					createEntity('2', 'Apple', 'Sales'),
					createEntity('3', 'Mango', 'Sales'),
				];

				const result = groupEntitiesByDomain(entities, 'asc');

				expect(result.get('Sales')?.map((e) => e.label)).toEqual(['Apple', 'Mango', 'Zebra']);
			});

			it('should sort entities Z-A within a named domain group when sortDirection is desc', () => {
				const entities = [
					createEntity('1', 'Apple', 'Sales'),
					createEntity('2', 'Zebra', 'Sales'),
					createEntity('3', 'Mango', 'Sales'),
				];

				const result = groupEntitiesByDomain(entities, 'desc');

				expect(result.get('Sales')?.map((e) => e.label)).toEqual(['Zebra', 'Mango', 'Apple']);
			});

			it('should sort Unassigned group A-Z when sortDirection is asc', () => {
				const entities = [
					createEntity('1', 'Zebra'),
					createEntity('2', 'Apple'),
					createEntity('3', 'Mango'),
				];

				const result = groupEntitiesByDomain(entities, 'asc');

				expect(result.get('Unassigned')?.map((e) => e.label)).toEqual(['Apple', 'Mango', 'Zebra']);
			});

			it('should sort Unassigned group Z-A when sortDirection is desc', () => {
				const entities = [
					createEntity('1', 'Apple'),
					createEntity('2', 'Zebra'),
					createEntity('3', 'Mango'),
				];

				const result = groupEntitiesByDomain(entities, 'desc');

				expect(result.get('Unassigned')?.map((e) => e.label)).toEqual(['Zebra', 'Mango', 'Apple']);
			});

			it('should sort multi-domain entities consistently in each group', () => {
				const entities = [
					createEntity('1', 'Zebra', undefined, undefined, ['Sales', 'Marketing']),
					createEntity('2', 'Apple', undefined, undefined, ['Sales', 'Marketing']),
					createEntity('3', 'Mango', 'Sales'),
				];

				const result = groupEntitiesByDomain(entities, 'asc');

				expect(result.get('Sales')?.map((e) => e.label)).toEqual(['Apple', 'Mango', 'Zebra']);
				expect(result.get('Marketing')?.map((e) => e.label)).toEqual(['Apple', 'Zebra']);
			});

			it('should sort multiple domain groups consistently', () => {
				const entities = [
					createEntity('1', 'Zebra', 'Sales'),
					createEntity('2', 'Apple', 'Inventory'),
					createEntity('3', 'Mango', 'Sales'),
					createEntity('4', 'Banana', 'Inventory'),
				];

				const result = groupEntitiesByDomain(entities, 'asc');

				expect(result.get('Sales')?.map((e) => e.label)).toEqual(['Mango', 'Zebra']);
				expect(result.get('Inventory')?.map((e) => e.label)).toEqual(['Apple', 'Banana']);
			});
		});

		it('should handle case-sensitive domain names', () => {
			const entities = [
				createEntity('1', 'Customer', 'sales'),
				createEntity('2', 'Order', 'Sales'),
				createEntity('3', 'Product', 'SALES'),
			];

			const result = groupEntitiesByDomain(entities);

			// Domains are case-sensitive, so these are different groups
			expect(result.size).toBe(3);
			expect(result.get('sales')).toHaveLength(1);
			expect(result.get('Sales')).toHaveLength(1);
			expect(result.get('SALES')).toHaveLength(1);
		});

		it('should handle large number of entities', () => {
			const entities = Array.from({ length: 1000 }, (_, i) =>
				createEntity(String(i), `Entity ${i}`, i % 5 === 0 ? undefined : `Domain ${i % 5}`)
			);

			const result = groupEntitiesByDomain(entities);

			// 4 named domains + 1 Unassigned
			expect(result.size).toBe(5);
			expect(result.get('Unassigned')?.length).toBe(200); // Every 5th entity (i % 5 === 0)
		});

		it('should handle entities with special characters in domain names', () => {
			const entities = [
				createEntity('1', 'Customer', 'Sales & Marketing'),
				createEntity('2', 'Order', 'Sales & Marketing'),
				createEntity('3', 'Product', 'Inventory (Warehouse)'),
			];

			const result = groupEntitiesByDomain(entities);

			expect(result.size).toBe(2);
			expect(result.get('Sales & Marketing')).toHaveLength(2);
			expect(result.get('Inventory (Warehouse)')).toHaveLength(1);
		});

		it('should handle undefined domain field', () => {
			const entities = [
				{ ...createEntity('1', 'Customer'), domain: undefined },
				createEntity('2', 'Order', 'Sales'),
			];

			const result = groupEntitiesByDomain(entities);

			expect(result.size).toBe(2);
			expect(result.get('Unassigned')).toHaveLength(1);
		});
	});

	describe('groupEntitiesByTag', () => {
		it('should group entities by tags', () => {
			const entities = [
				createEntity('1', 'Customer', 'Sales', ['pii', 'master-data']),
				createEntity('2', 'Order', 'Sales', ['transactional']),
				createEntity('3', 'Product', 'Inventory', ['master-data']),
			];

			const result = groupEntitiesByTag(entities);

			expect(result.size).toBe(3);
			expect(result.get('pii')).toHaveLength(1);
			expect(result.get('master-data')).toHaveLength(2);
			expect(result.get('transactional')).toHaveLength(1);
		});

		it('should put entities without tags in "Unassigned" group', () => {
			const entities = [
				createEntity('1', 'Customer', 'Sales', ['pii']),
				createEntity('2', 'Order', 'Sales'), // No tags
				createEntity('3', 'Product', 'Inventory'), // No tags
			];

			const result = groupEntitiesByTag(entities);

			expect(result.size).toBe(2);
			expect(result.get('Unassigned')).toHaveLength(2);
			expect(result.get('Unassigned')?.map((e) => e.label)).toEqual(['Order', 'Product']);
		});

		it('should handle entities with multiple tags appearing in multiple groups', () => {
			const entities = [
				createEntity('1', 'Customer', 'Sales', ['pii', 'master-data', 'sensitive']),
			];

			const result = groupEntitiesByTag(entities);

			expect(result.size).toBe(3);
			expect(result.get('pii')).toHaveLength(1);
			expect(result.get('master-data')).toHaveLength(1);
			expect(result.get('sensitive')).toHaveLength(1);
			expect(result.get('pii')?.[0].id).toBe('1');
			expect(result.get('master-data')?.[0].id).toBe('1');
			expect(result.get('sensitive')?.[0].id).toBe('1');
		});

		it('should sort entities alphabetically within each group', () => {
			const entities = [
				createEntity('1', 'Zebra', 'Sales', ['master-data']),
				createEntity('2', 'Apple', 'Sales', ['master-data']),
				createEntity('3', 'Mango', 'Inventory', ['master-data']),
			];

			const result = groupEntitiesByTag(entities);

			expect(result.get('master-data')?.map((e) => e.label)).toEqual([
				'Apple',
				'Mango',
				'Zebra',
			]);
		});

		it('should handle empty entities array', () => {
			const result = groupEntitiesByTag([]);

			expect(result.size).toBe(0);
		});

		it('should handle entities with empty tags array', () => {
			const entities = [
				createEntity('1', 'Customer', 'Sales', []),
				createEntity('2', 'Order', 'Sales', ['transactional']),
			];

			const result = groupEntitiesByTag(entities);

			expect(result.size).toBe(2);
			expect(result.get('Unassigned')).toHaveLength(1);
			expect(result.get('Unassigned')?.map((e) => e.label)).toEqual(['Customer']);
		});

		it('should remove duplicate entities within groups', () => {
			// This tests the deduplication logic in case an entity somehow appears twice
			const entity = createEntity('1', 'Customer', 'Sales', ['pii', 'master-data']);
			const entities = [entity, entity]; // Duplicate

			const result = groupEntitiesByTag(entities);

			expect(result.get('pii')).toHaveLength(1);
			expect(result.get('master-data')).toHaveLength(1);
		});

		it('should handle case-sensitive tag names', () => {
			const entities = [
				createEntity('1', 'Customer', 'Sales', ['PII']),
				createEntity('2', 'Order', 'Sales', ['pii']),
				createEntity('3', 'Product', 'Inventory', ['Pii']),
			];

			const result = groupEntitiesByTag(entities);

			// Tags are case-sensitive
			expect(result.size).toBe(3);
			expect(result.get('PII')).toHaveLength(1);
			expect(result.get('pii')).toHaveLength(1);
			expect(result.get('Pii')).toHaveLength(1);
		});

		it('should handle large number of tags per entity', () => {
			const manyTags = Array.from({ length: 20 }, (_, i) => `tag-${i}`);
			const entities = [createEntity('1', 'Customer', 'Sales', manyTags)];

			const result = groupEntitiesByTag(entities);

			expect(result.size).toBe(20);
			for (let i = 0; i < 20; i++) {
				expect(result.get(`tag-${i}`)).toHaveLength(1);
				expect(result.get(`tag-${i}`)?.[0].label).toBe('Customer');
			}
		});

		it('should handle entities with special characters in tags', () => {
			const entities = [
				createEntity('1', 'Customer', 'Sales', ['pii/sensitive', 'master-data']),
				createEntity('2', 'Order', 'Sales', ['transactional (daily)']),
			];

			const result = groupEntitiesByTag(entities);

			expect(result.size).toBe(3);
			expect(result.get('pii/sensitive')).toHaveLength(1);
			expect(result.get('transactional (daily)')).toHaveLength(1);
		});

		it('should handle undefined tags field', () => {
			const entities = [
				{ ...createEntity('1', 'Customer'), tags: undefined },
				createEntity('2', 'Order', 'Sales', ['transactional']),
			];

			const result = groupEntitiesByTag(entities);

			expect(result.size).toBe(2);
			expect(result.get('Unassigned')).toHaveLength(1);
			expect(result.get('Unassigned')?.map((e) => e.label)).toEqual(['Customer']);
		});

		it('should handle mixed entities with and without tags', () => {
			const entities = [
				createEntity('1', 'Banana', 'Sales', ['fruit']),
				createEntity('2', 'Apple', 'Sales'),
				createEntity('3', 'Cherry', 'Sales', ['fruit']),
				createEntity('4', 'Date'),
			];

			const result = groupEntitiesByTag(entities);

			expect(result.size).toBe(2);
			expect(result.get('fruit')?.map((e) => e.label)).toEqual(['Banana', 'Cherry']);
			expect(result.get('Unassigned')?.map((e) => e.label)).toEqual(['Apple', 'Date']);
		});

		it('should handle large number of entities', () => {
			const entities = Array.from({ length: 1000 }, (_, i) =>
				createEntity(
					String(i),
					`Entity ${i}`,
					'Sales',
					i % 2 === 0 ? ['even'] : ['odd']
				)
			);

			const result = groupEntitiesByTag(entities);

			expect(result.size).toBe(2);
			expect(result.get('even')).toHaveLength(500);
			expect(result.get('odd')).toHaveLength(500);
		});

		it('should sort "Unassigned" group alphabetically', () => {
			const entities = [
				createEntity('1', 'Zebra'),
				createEntity('2', 'Apple'),
				createEntity('3', 'Mango'),
			];

			const result = groupEntitiesByTag(entities);

			expect(result.get('Unassigned')?.map((e) => e.label)).toEqual([
				'Apple',
				'Mango',
				'Zebra',
			]);
		});

		it('should handle single tag shared by all entities', () => {
			const entities = [
				createEntity('1', 'Customer', 'Sales', ['shared']),
				createEntity('2', 'Order', 'Sales', ['shared']),
				createEntity('3', 'Product', 'Inventory', ['shared']),
			];

			const result = groupEntitiesByTag(entities);

			expect(result.size).toBe(1);
			expect(result.get('shared')).toHaveLength(3);
		});

		it('should handle entity appearing in multiple tag groups with correct sorting', () => {
			const entities = [
				createEntity('1', 'Zebra', 'Sales', ['tag-a', 'tag-b']),
				createEntity('2', 'Apple', 'Sales', ['tag-a']),
				createEntity('3', 'Mango', 'Sales', ['tag-b']),
			];

			const result = groupEntitiesByTag(entities);

			expect(result.size).toBe(2);
			// tag-a should have Apple and Zebra (alphabetical)
			expect(result.get('tag-a')?.map((e) => e.label)).toEqual(['Apple', 'Zebra']);
			// tag-b should have Mango and Zebra (alphabetical)
			expect(result.get('tag-b')?.map((e) => e.label)).toEqual(['Mango', 'Zebra']);
		});
	});
});
