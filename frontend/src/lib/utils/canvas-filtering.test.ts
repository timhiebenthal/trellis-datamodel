import { describe, expect, it } from 'vitest';
import { matchesCanvasFilters } from './canvas-filtering';

describe('canvas-filtering', () => {
	it('matches when any selected domain is in the singular or list domain fields', () => {
		expect(
			matchesCanvasFilters(
				{ domain: 'Sales', domains: ['Operations'] },
				{ selectedDomains: ['Operations'], selectedTags: [] },
			),
		).toBe(true);
		expect(
			matchesCanvasFilters(
				{ domain: 'Sales', domains: ['Operations'] },
				{ selectedDomains: ['Sales'], selectedTags: [] },
			),
		).toBe(true);
	});

	it('excludes an entity without a domain when domain filters are active', () => {
		expect(
			matchesCanvasFilters(
				{ tags: [] },
				{ selectedDomains: ['Sales'], selectedTags: [] },
			),
		).toBe(false);
	});

	it('uses OR semantics for selected tags, including bound model and UI tags', () => {
		expect(
			matchesCanvasFilters(
				{
					model_ref: 'model.project.customer',
					ui_tags: ['sensitive'],
				},
				{ selectedDomains: [], selectedTags: ['analytics'] },
				[{ unique_id: 'model.project.customer', tags: ['analytics'] }],
			),
		).toBe(true);
	});

	it('combines domain and tag filters with AND semantics', () => {
		const entity = { domain: 'Sales', tags: ['transactional'] };

		expect(
			matchesCanvasFilters(entity, {
				selectedDomains: ['Sales'],
				selectedTags: ['transactional', 'analytics'],
			}),
		).toBe(true);
		expect(
			matchesCanvasFilters(entity, {
				selectedDomains: ['Marketing'],
				selectedTags: ['transactional'],
			}),
		).toBe(false);
		expect(
			matchesCanvasFilters(entity, {
				selectedDomains: ['Sales'],
				selectedTags: ['analytics'],
			}),
		).toBe(false);
	});

	it('matches all entities when filters are empty', () => {
		expect(
			matchesCanvasFilters(
				{ id: 'outside-url-subset', tags: ['analytics'] },
				{ selectedDomains: [], selectedTags: [] },
			),
		).toBe(true);
	});

	it('does not apply an explicit URL entity subset', () => {
		expect(
			matchesCanvasFilters(
				{ id: 'url-selected-entity', domain: 'Sales' },
				{ selectedDomains: ['Sales'], selectedTags: [] },
			),
		).toBe(true);
	});
});
