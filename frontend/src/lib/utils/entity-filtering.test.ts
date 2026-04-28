import { describe, it, expect } from 'vitest';
import { filterEntities } from './entity-filtering';
import type { Entity } from '$lib/types';

describe('entity-filtering', () => {
	// Helper function to create test entities
	const createEntity = (
		id: string,
		label: string,
		domain?: string,
		tags?: string[],
		domains?: string[],
		entity_type?: 'dimension' | 'fact' | 'unclassified'
	): Entity => ({
		id,
		label,
		domain,
		domains,
		tags,
		description: '',
		entity_type: entity_type ?? 'dimension',
		attributes: [],
	});

	describe('filterEntities', () => {
		describe('Search term filtering', () => {
			it('should return all entities when search term is empty', () => {
				const entities = [
					createEntity('1', 'Customer'),
					createEntity('2', 'Order'),
					createEntity('3', 'Product'),
				];

				const result = filterEntities(entities, {
					searchTerm: '',
					selectedDomains: [],
					selectedTags: [],
				});

				expect(result).toHaveLength(3);
				expect(result).toEqual(entities);
			});

			it('should filter entities by case-insensitive substring match', () => {
				const entities = [
					createEntity('1', 'Customer'),
					createEntity('2', 'Order'),
					createEntity('3', 'Product'),
				];

				const result = filterEntities(entities, {
					searchTerm: 'cust',
					selectedDomains: [],
					selectedTags: [],
				});

				expect(result).toHaveLength(1);
				expect(result[0].label).toBe('Customer');
			});

			it('should filter entities with case-insensitive search', () => {
				const entities = [
					createEntity('1', 'Customer'),
					createEntity('2', 'Order'),
					createEntity('3', 'Product'),
				];

				const result = filterEntities(entities, {
					searchTerm: 'CUSTOMER',
					selectedDomains: [],
					selectedTags: [],
				});

				expect(result).toHaveLength(1);
				expect(result[0].label).toBe('Customer');
			});

			it('should return empty array when no entities match search term', () => {
				const entities = [
					createEntity('1', 'Customer'),
					createEntity('2', 'Order'),
					createEntity('3', 'Product'),
				];

				const result = filterEntities(entities, {
					searchTerm: 'xyz',
					selectedDomains: [],
					selectedTags: [],
				});

				expect(result).toHaveLength(0);
			});

			it('should handle partial matches anywhere in the label', () => {
				const entities = [
					createEntity('1', 'Customer Order'),
					createEntity('2', 'Order Details'),
					createEntity('3', 'Product'),
				];

				const result = filterEntities(entities, {
					searchTerm: 'order',
					selectedDomains: [],
					selectedTags: [],
				});

				expect(result).toHaveLength(2);
				expect(result.map((e) => e.label)).toEqual(['Customer Order', 'Order Details']);
			});
		});

		describe('Domain filtering', () => {
			it('should return all entities when no domains selected', () => {
				const entities = [
					createEntity('1', 'Customer', 'Sales'),
					createEntity('2', 'Order', 'Sales'),
					createEntity('3', 'Product', 'Inventory'),
				];

				const result = filterEntities(entities, {
					searchTerm: '',
					selectedDomains: [],
					selectedTags: [],
				});

				expect(result).toHaveLength(3);
			});

			it('should filter entities by single domain', () => {
				const entities = [
					createEntity('1', 'Customer', 'Sales'),
					createEntity('2', 'Order', 'Sales'),
					createEntity('3', 'Product', 'Inventory'),
				];

				const result = filterEntities(entities, {
					searchTerm: '',
					selectedDomains: ['Sales'],
					selectedTags: [],
				});

				expect(result).toHaveLength(2);
				expect(result.map((e) => e.label)).toEqual(['Customer', 'Order']);
			});

			it('should filter entities by multiple domains (OR logic)', () => {
				const entities = [
					createEntity('1', 'Customer', 'Sales'),
					createEntity('2', 'Order', 'Sales'),
					createEntity('3', 'Product', 'Inventory'),
					createEntity('4', 'Warehouse', 'Logistics'),
				];

				const result = filterEntities(entities, {
					searchTerm: '',
					selectedDomains: ['Sales', 'Logistics'],
					selectedTags: [],
				});

				expect(result).toHaveLength(3);
				expect(result.map((e) => e.label)).toEqual(['Customer', 'Order', 'Warehouse']);
			});

		it('should match entities with multiple domains', () => {
			const entities = [
				createEntity('1', 'Customer', undefined, undefined, ['Sales', 'Marketing']),
				createEntity('2', 'Order', 'Sales'),
			];

			const result = filterEntities(entities, {
				searchTerm: '',
				selectedDomains: ['Marketing'],
				selectedTags: [],
			});

			expect(result).toHaveLength(1);
			expect(result[0].label).toBe('Customer');
		});

			it('should handle entities without domain field', () => {
				const entities = [
					createEntity('1', 'Customer', 'Sales'),
					createEntity('2', 'Order'), // No domain
					createEntity('3', 'Product', 'Inventory'),
				];

				const result = filterEntities(entities, {
					searchTerm: '',
					selectedDomains: ['Sales'],
					selectedTags: [],
				});

				expect(result).toHaveLength(1);
				expect(result[0].label).toBe('Customer');
			});

			it('should treat empty domain as empty string', () => {
				const entities = [
					createEntity('1', 'Customer', ''),
					createEntity('2', 'Order', 'Sales'),
				];

				const result = filterEntities(entities, {
					searchTerm: '',
					selectedDomains: [''],
					selectedTags: [],
				});

				expect(result).toHaveLength(1);
				expect(result[0].label).toBe('Customer');
			});
		});

		describe('Tag filtering', () => {
			it('should return all entities when no tags selected', () => {
				const entities = [
					createEntity('1', 'Customer', 'Sales', ['pii', 'master-data']),
					createEntity('2', 'Order', 'Sales', ['transactional']),
					createEntity('3', 'Product', 'Inventory', ['master-data']),
				];

				const result = filterEntities(entities, {
					searchTerm: '',
					selectedDomains: [],
					selectedTags: [],
				});

				expect(result).toHaveLength(3);
			});

			it('should filter entities by single tag', () => {
				const entities = [
					createEntity('1', 'Customer', 'Sales', ['pii', 'master-data']),
					createEntity('2', 'Order', 'Sales', ['transactional']),
					createEntity('3', 'Product', 'Inventory', ['master-data']),
				];

				const result = filterEntities(entities, {
					searchTerm: '',
					selectedDomains: [],
					selectedTags: ['master-data'],
				});

				expect(result).toHaveLength(2);
				expect(result.map((e) => e.label)).toEqual(['Customer', 'Product']);
			});

			it('should filter entities by multiple tags (OR logic)', () => {
				const entities = [
					createEntity('1', 'Customer', 'Sales', ['pii', 'master-data']),
					createEntity('2', 'Order', 'Sales', ['transactional']),
					createEntity('3', 'Product', 'Inventory', ['master-data']),
					createEntity('4', 'Invoice', 'Finance', ['transactional', 'legal']),
				];

				const result = filterEntities(entities, {
					searchTerm: '',
					selectedDomains: [],
					selectedTags: ['pii', 'legal'],
				});

				expect(result).toHaveLength(2);
				expect(result.map((e) => e.label)).toEqual(['Customer', 'Invoice']);
			});

			it('should handle entities without tags', () => {
				const entities = [
					createEntity('1', 'Customer', 'Sales', ['pii']),
					createEntity('2', 'Order', 'Sales'), // No tags
					createEntity('3', 'Product', 'Inventory', ['master-data']),
				];

				const result = filterEntities(entities, {
					searchTerm: '',
					selectedDomains: [],
					selectedTags: ['pii'],
				});

				expect(result).toHaveLength(1);
				expect(result[0].label).toBe('Customer');
			});

			it('should handle entities with empty tags array', () => {
				const entities = [
					createEntity('1', 'Customer', 'Sales', []),
					createEntity('2', 'Order', 'Sales', ['transactional']),
				];

				const result = filterEntities(entities, {
					searchTerm: '',
					selectedDomains: [],
					selectedTags: ['transactional'],
				});

				expect(result).toHaveLength(1);
				expect(result[0].label).toBe('Order');
			});
		});

		describe('Combined filtering (AND logic)', () => {
			it('should combine search term + domain filter', () => {
				const entities = [
					createEntity('1', 'Customer Master', 'Sales'),
					createEntity('2', 'Customer Order', 'Sales'),
					createEntity('3', 'Product Master', 'Inventory'),
				];

				const result = filterEntities(entities, {
					searchTerm: 'customer',
					selectedDomains: ['Sales'],
					selectedTags: [],
				});

				expect(result).toHaveLength(2);
				expect(result.map((e) => e.label)).toEqual(['Customer Master', 'Customer Order']);
			});

			it('should combine search term + tag filter', () => {
				const entities = [
					createEntity('1', 'Customer Master', 'Sales', ['pii', 'master-data']),
					createEntity('2', 'Customer Order', 'Sales', ['transactional']),
					createEntity('3', 'Product Master', 'Inventory', ['master-data']),
				];

				const result = filterEntities(entities, {
					searchTerm: 'master',
					selectedDomains: [],
					selectedTags: ['master-data'],
				});

				expect(result).toHaveLength(2);
				expect(result.map((e) => e.label)).toEqual(['Customer Master', 'Product Master']);
			});

			it('should combine domain + tag filter', () => {
				const entities = [
					createEntity('1', 'Customer', 'Sales', ['pii', 'master-data']),
					createEntity('2', 'Order', 'Sales', ['transactional']),
					createEntity('3', 'Product', 'Inventory', ['master-data']),
				];

				const result = filterEntities(entities, {
					searchTerm: '',
					selectedDomains: ['Sales'],
					selectedTags: ['master-data'],
				});

				expect(result).toHaveLength(1);
				expect(result[0].label).toBe('Customer');
			});

			it('should combine all three filters (search + domain + tag)', () => {
				const entities = [
					createEntity('1', 'Customer Master', 'Sales', ['pii', 'master-data']),
					createEntity('2', 'Customer Order', 'Sales', ['transactional']),
					createEntity('3', 'Product Master', 'Inventory', ['master-data']),
					createEntity('4', 'Order Master', 'Sales', ['master-data']),
				];

				const result = filterEntities(entities, {
					searchTerm: 'customer',
					selectedDomains: ['Sales'],
					selectedTags: ['master-data'],
				});

				expect(result).toHaveLength(1);
				expect(result[0].label).toBe('Customer Master');
			});

			it('should return empty array when combined filters match nothing', () => {
				const entities = [
					createEntity('1', 'Customer', 'Sales', ['pii']),
					createEntity('2', 'Order', 'Sales', ['transactional']),
					createEntity('3', 'Product', 'Inventory', ['master-data']),
				];

				const result = filterEntities(entities, {
					searchTerm: 'invoice',
					selectedDomains: ['Finance'],
					selectedTags: ['legal'],
				});

				expect(result).toHaveLength(0);
			});
		});

		describe('Edge cases', () => {
			it('should handle empty entities array', () => {
				const result = filterEntities([], {
					searchTerm: 'customer',
					selectedDomains: ['Sales'],
					selectedTags: ['pii'],
				});

				expect(result).toHaveLength(0);
			});

			it('should handle undefined domain field', () => {
				const entities = [
					{ ...createEntity('1', 'Customer'), domain: undefined },
					createEntity('2', 'Order', 'Sales'),
				];

				const result = filterEntities(entities, {
					searchTerm: '',
					selectedDomains: ['Sales'],
					selectedTags: [],
				});

				expect(result).toHaveLength(1);
				expect(result[0].label).toBe('Order');
			});

			it('should handle undefined tags field', () => {
				const entities = [
					{ ...createEntity('1', 'Customer'), tags: undefined },
					createEntity('2', 'Order', 'Sales', ['transactional']),
				];

				const result = filterEntities(entities, {
					searchTerm: '',
					selectedDomains: [],
					selectedTags: ['transactional'],
				});

				expect(result).toHaveLength(1);
				expect(result[0].label).toBe('Order');
			});

			it('should handle entities with special characters in labels', () => {
				const entities = [
					createEntity('1', 'Customer (Master)', 'Sales'),
					createEntity('2', 'Order/Invoice', 'Sales'),
					createEntity('3', 'Product & Service', 'Inventory'),
				];

				const result = filterEntities(entities, {
					searchTerm: 'master)',
					selectedDomains: [],
					selectedTags: [],
				});

				expect(result).toHaveLength(1);
				expect(result[0].label).toBe('Customer (Master)');
			});

			it('should handle whitespace in search term', () => {
				const entities = [
					createEntity('1', 'Customer Master'),
					createEntity('2', 'Order'),
				];

				const result = filterEntities(entities, {
					searchTerm: '  customer  ',
					selectedDomains: [],
					selectedTags: [],
				});

				expect(result).toHaveLength(1);
				expect(result[0].label).toBe('Customer Master');
			});

			it('should handle large number of entities', () => {
				const entities = Array.from({ length: 1000 }, (_, i) =>
					createEntity(
						String(i),
						`Entity ${i}`,
						i % 3 === 0 ? 'Sales' : 'Inventory',
						i % 2 === 0 ? ['master-data'] : ['transactional']
					)
				);

				const result = filterEntities(entities, {
					searchTerm: '123',
					selectedDomains: ['Sales'],
					selectedTags: [],
				});

				// Should find Entity 123 if it's in Sales domain (123 % 3 === 0)
				expect(result.length).toBe(1);
				expect(result[0].label).toBe('Entity 123');
			});

			it('should handle entities with 10+ tags', () => {
				const manyTags = Array.from({ length: 15 }, (_, i) => `tag-${i}`);
				const entities = [
					createEntity('1', 'Customer', 'Sales', manyTags),
					createEntity('2', 'Order', 'Sales', ['transactional']),
				];

				const result = filterEntities(entities, {
					searchTerm: '',
					selectedDomains: [],
					selectedTags: ['tag-7'],
				});

				expect(result).toHaveLength(1);
				expect(result[0].label).toBe('Customer');
			});

			it('should handle case where entity matches multiple selected tags', () => {
				const entities = [
					createEntity('1', 'Customer', 'Sales', ['pii', 'master-data', 'sensitive']),
					createEntity('2', 'Order', 'Sales', ['transactional']),
				];

				const result = filterEntities(entities, {
					searchTerm: '',
					selectedDomains: [],
					selectedTags: ['pii', 'sensitive'],
				});

				// Entity should appear once even though it matches multiple selected tags
				expect(result).toHaveLength(1);
				expect(result[0].label).toBe('Customer');
			});
		});
	});

	describe('Entity type filtering', () => {
		it('should return all entities when selectedEntityTypes is empty', () => {
			const entities = [
				createEntity('1', 'Customer', 'Sales', [], [], 'dimension'),
				createEntity('2', 'Order', 'Sales', [], [], 'fact'),
				createEntity('3', 'Event', 'Sales', [], [], 'unclassified'),
			];

			const result = filterEntities(entities, {
				searchTerm: '',
				selectedDomains: [],
				selectedTags: [],
				selectedEntityTypes: [],
			});

			expect(result).toHaveLength(3);
		});

		it('should filter entities to dimensions only', () => {
			const entities = [
				createEntity('1', 'Customer', 'Sales', [], [], 'dimension'),
				createEntity('2', 'Order', 'Sales', [], [], 'fact'),
				createEntity('3', 'Event', 'Sales', [], [], 'unclassified'),
			];

			const result = filterEntities(entities, {
				searchTerm: '',
				selectedDomains: [],
				selectedTags: [],
				selectedEntityTypes: ['dimension'],
			});

			expect(result).toHaveLength(1);
			expect(result[0].label).toBe('Customer');
		});

		it('should filter entities to facts only', () => {
			const entities = [
				createEntity('1', 'Customer', 'Sales', [], [], 'dimension'),
				createEntity('2', 'Sales Order', 'Sales', [], [], 'fact'),
				createEntity('3', 'Revenue', 'Finance', [], [], 'fact'),
			];

			const result = filterEntities(entities, {
				searchTerm: '',
				selectedDomains: [],
				selectedTags: [],
				selectedEntityTypes: ['fact'],
			});

			expect(result).toHaveLength(2);
			expect(result.map((e) => e.label)).toEqual(['Sales Order', 'Revenue']);
		});

		it('should filter entities to unclassified only', () => {
			const entities = [
				createEntity('1', 'Customer', 'Sales', [], [], 'dimension'),
				createEntity('2', 'Order', 'Sales', [], [], 'fact'),
				createEntity('3', 'Event', 'Sales', [], [], 'unclassified'),
			];

			const result = filterEntities(entities, {
				searchTerm: '',
				selectedDomains: [],
				selectedTags: [],
				selectedEntityTypes: ['unclassified'],
			});

			expect(result).toHaveLength(1);
			expect(result[0].label).toBe('Event');
		});

		it('should treat missing entity_type as unclassified', () => {
			const entities = [
				createEntity('1', 'Customer', 'Sales', [], [], 'dimension'),
				{ ...createEntity('2', 'Mystery', 'Sales'), entity_type: undefined },
			];

			const result = filterEntities(entities, {
				searchTerm: '',
				selectedDomains: [],
				selectedTags: [],
				selectedEntityTypes: ['unclassified'],
			});

			expect(result).toHaveLength(1);
			expect(result[0].label).toBe('Mystery');
		});

		it('should use OR logic within selected entity types', () => {
			const entities = [
				createEntity('1', 'Customer', 'Sales', [], [], 'dimension'),
				createEntity('2', 'Sales Order', 'Sales', [], [], 'fact'),
				createEntity('3', 'Event', 'Sales', [], [], 'unclassified'),
			];

			const result = filterEntities(entities, {
				searchTerm: '',
				selectedDomains: [],
				selectedTags: [],
				selectedEntityTypes: ['dimension', 'fact'],
			});

			expect(result).toHaveLength(2);
			expect(result.map((e) => e.label)).toEqual(['Customer', 'Sales Order']);
		});

		it('should combine entity type filter with search, domain, and tag filters', () => {
			const entities = [
				createEntity('1', 'Customer Master', 'Sales', ['pii'], [], 'dimension'),
				createEntity('2', 'Customer Order', 'Sales', ['transactional'], [], 'fact'),
				createEntity('3', 'Product', 'Inventory', ['pii'], [], 'dimension'),
				createEntity('4', 'Revenue Event', 'Finance', ['pii'], [], 'unclassified'),
			];

			const result = filterEntities(entities, {
				searchTerm: 'customer',
				selectedDomains: ['Sales'],
				selectedTags: ['pii'],
				selectedEntityTypes: ['dimension'],
			});

			expect(result).toHaveLength(1);
			expect(result[0].label).toBe('Customer Master');
		});
	});
});
