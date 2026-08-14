import { describe, it, expect, afterEach } from 'vitest';
import { fireEvent, render, cleanup, screen } from '@testing-library/svelte';
import EntityRow from './EntityRow.svelte';
import type { Entity, ModelInfo } from '$lib/types';
import { frameworkModels, nodes } from '$lib/stores';
import { get } from 'svelte/store';

const baseEntity: Entity = {
	id: 'booking',
	label: 'Booking',
	position: { x: 0, y: 0 },
};

describe('EntityRow — dbt build status badge', () => {
	afterEach(() => {
		cleanup();
		frameworkModels.set([]);
		nodes.set([]);
	});

	it('renders a dbt badge with tooltip showing the resolved model name for a bound entity', () => {
		const entity: Entity = {
			...baseEntity,
			model_ref: 'model.project.dim_customer',
		};

		render(EntityRow, { props: { entity } });

		// The badge is the title-bearing wrapper around the Icon component (mirrors the
		// existing "Materialized in dbt model" convention in EntityDetailModal.svelte, where
		// assertions target the wrapper's title/aria-label rather than the Icon's internal
		// (async-loaded) SVG markup).
		const badge = document.querySelector('[title*="Built with dbt"]');
		expect(badge).toBeTruthy();
		expect(badge?.getAttribute('title')).toContain('Built with dbt: dim_customer');
	});

	it('does not render a dbt badge for an unbound entity (no dbt_model)', () => {
		const entity: Entity = {
			...baseEntity,
			model_ref: undefined,
		};

		render(EntityRow, { props: { entity } });

		const badge = document.querySelector('[title*="Built with dbt"]');
		expect(badge).toBeFalsy();
	});

	it('binds an entity from the row action without opening the detail modal', async () => {
		const model: ModelInfo = {
			unique_id: 'model.project.booking',
			name: 'booking',
			schema: 'analytics',
			table: 'booking',
			columns: [],
		};
		frameworkModels.set([model]);
		nodes.set([{
			id: 'booking',
			type: 'entity',
			position: { x: 0, y: 0 },
			data: { label: 'Booking' },
		} as any]);

		render(EntityRow, { props: { entity: baseEntity } });
		await fireEvent.click(screen.getByRole('button', { name: 'Bind model' }));
		await fireEvent.click(screen.getByRole('button', { name: 'booking' }));

		expect((get(nodes)[0].data as any).model_ref).toBe('model.project.booking');
		expect(screen.queryByText('Entity X Details')).not.toBeInTheDocument();
	});
});
