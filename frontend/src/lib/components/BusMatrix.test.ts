import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, cleanup, fireEvent, waitFor } from '@testing-library/svelte';
import BusMatrix from './BusMatrix.svelte';

const mockBusMatrixData = vi.hoisted(() => ({
	dimensions: [
		{ id: 'dim_bound', label: 'Bound Dimension', tags: [], model_ref: 'model.project.dim_bound' },
		{ id: 'dim_unbound', label: 'Unbound Dimension', tags: [] },
	],
	facts: [
		{ id: 'fct_bound', label: 'Bound Fact', tags: [], model_ref: 'model.project.fct_bound' },
		{ id: 'fct_unbound', label: 'Unbound Fact', tags: [] },
	],
	connections: [{ dimension_id: 'dim_bound', fact_id: 'fct_bound' }],
}));

vi.mock('$lib/api', () => ({
	getBusMatrix: vi.fn().mockResolvedValue(mockBusMatrixData),
}));

describe('BusMatrix — dbt build status badges', () => {
	afterEach(() => {
		cleanup();
	});

	it('renders a filled build-status dot for bound dimension/fact and a hollow one for unbound', async () => {
		render(BusMatrix);

		await waitFor(() => {
			expect(document.querySelector('table')).toBeTruthy();
		});

		const filledDots = Array.from(document.querySelectorAll('.bg-primary-600'));
		expect(filledDots.length).toBe(2);

		const boundDimRow = Array.from(document.querySelectorAll('td')).find((td) =>
			td.textContent?.includes('Bound Dimension')
		) as HTMLElement;
		expect(boundDimRow?.querySelector('.bg-primary-600')).toBeTruthy();

		const unboundDimRow = Array.from(document.querySelectorAll('td')).find((td) =>
			td.textContent?.includes('Unbound Dimension')
		) as HTMLElement;
		expect(unboundDimRow?.querySelector('.bg-primary-600')).toBeFalsy();
		expect(unboundDimRow?.querySelector('[title="Not yet built with dbt"]')).toBeTruthy();

		const boundFactHeader = Array.from(document.querySelectorAll('th')).find((th) =>
			th.textContent?.includes('Bound Fact')
		) as HTMLElement;
		expect(boundFactHeader?.querySelector('.bg-primary-600')).toBeTruthy();

		const unboundFactHeader = Array.from(document.querySelectorAll('th')).find((th) =>
			th.textContent?.includes('Unbound Fact')
		) as HTMLElement;
		expect(unboundFactHeader?.querySelector('.bg-primary-600')).toBeFalsy();
		expect(unboundFactHeader?.querySelector('[title="Not yet built with dbt"]')).toBeTruthy();
	});

	it('explains what dimension and fact usage counts represent', async () => {
		render(BusMatrix);

		await waitFor(() => {
			expect(document.querySelector('table')).toBeTruthy();
		});

		const dimensionBadge = document.querySelector('[aria-label="1 related facts"]') as HTMLElement;
		const factBadge = document.querySelector('[aria-label="1 related dimensions"]') as HTMLElement;

		await fireEvent.mouseEnter(dimensionBadge.parentElement as HTMLElement);
		expect(document.querySelector('[role="tooltip"]')?.textContent).toContain(
			'1 related facts'
		);

		await fireEvent.mouseEnter(factBadge.parentElement as HTMLElement);
		expect(
			Array.from(document.querySelectorAll('[role="tooltip"]')).some(tooltip =>
				tooltip.textContent?.includes('1 related dimensions')
			)
		).toBe(true);
	});

	it('filtering to "Bound" only shows the bound dimension row and bound fact column', async () => {
		render(BusMatrix);

		await waitFor(() => {
			expect(document.querySelector('table')).toBeTruthy();
		});

		const select = document.querySelector('#build-status-filter') as HTMLSelectElement;
		expect(select).toBeTruthy();

		await fireEvent.change(select, { target: { value: 'bound' } });

		await waitFor(() => {
			const table = document.querySelector('table') as HTMLElement;
			expect(table.textContent).not.toContain('Unbound Dimension');
		});

		const table = document.querySelector('table') as HTMLElement;
		expect(table.textContent).toContain('Bound Dimension');
		expect(table.textContent).not.toContain('Unbound Fact');
		expect(table.textContent).toContain('Bound Fact');

		// only one connected fact/dimension remains visible, so counts should be 1
		const countBadges = Array.from(table.querySelectorAll('[aria-label*="connected"]'));
		expect(countBadges.some((el) => el.getAttribute('aria-label')?.startsWith('1 connected'))).toBe(true);
	});
});
