import { describe, it, expect, afterEach, beforeEach } from 'vitest';
import { render, cleanup, fireEvent } from '@testing-library/svelte';
import { get } from 'svelte/store';
import { entityListFilters } from '$lib/stores';
import EntityListFilters from './EntityListFilters.svelte';

describe('EntityListFilters — Built (build status) filter', () => {
	beforeEach(() => {
		entityListFilters.set({
			searchTerm: '',
			selectedDomains: [],
			selectedTags: [],
			selectedEntityTypes: [],
			selectedBuildStatus: [],
			sortDirection: 'asc',
			groupByEntityType: false,
		});
	});

	afterEach(() => {
		cleanup();
	});

	it('adds "bound" to selectedBuildStatus when selecting "Bound" from the Built dropdown', async () => {
		render(EntityListFilters, { props: { filteredCount: 0, totalCount: 0 } });

		const select = document.querySelector('select[data-testid="build-status-select"]') as HTMLSelectElement;
		expect(select).toBeTruthy();

		await fireEvent.change(select, { target: { value: 'bound' } });

		expect(get(entityListFilters).selectedBuildStatus).toEqual(['bound']);
	});

	it('removes "bound" from selectedBuildStatus when the chip remove button is clicked', async () => {
		entityListFilters.update((filters) => ({ ...filters, selectedBuildStatus: ['bound'] }));

		render(EntityListFilters, { props: { filteredCount: 0, totalCount: 0 } });

		const removeButton = document.querySelector('[title="Remove Bound"]') as HTMLButtonElement;
		expect(removeButton).toBeTruthy();

		await fireEvent.click(removeButton);

		expect(get(entityListFilters).selectedBuildStatus).toEqual([]);
	});

	it('resets selectedBuildStatus to [] along with other filters when Clear is clicked', async () => {
		entityListFilters.update((filters) => ({
			...filters,
			searchTerm: 'foo',
			selectedBuildStatus: ['bound', 'unbound'],
			selectedEntityTypes: ['fact'],
		}));

		render(EntityListFilters, { props: { filteredCount: 0, totalCount: 0 } });

		const clearButton = document.querySelector('button[title="Clear all filters"]') as HTMLButtonElement;
		expect(clearButton).toBeTruthy();

		await fireEvent.click(clearButton);

		const filters = get(entityListFilters);
		expect(filters.selectedBuildStatus).toEqual([]);
		expect(filters.selectedEntityTypes).toEqual([]);
		expect(filters.searchTerm).toEqual('');
	});
});
