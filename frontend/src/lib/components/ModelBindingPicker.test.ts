import { afterEach, describe, expect, it } from 'vitest';
import { fireEvent, render, screen, cleanup } from '@testing-library/svelte';
import { frameworkModels } from '$lib/stores';
import type { ModelInfo } from '$lib/types';
import ModelBindingPicker from './ModelBindingPicker.svelte';

const models: ModelInfo[] = [
	{
		unique_id: 'model.project.customers',
		name: 'customers',
		schema: 'analytics',
		table: 'customers',
		columns: [],
		file_path: 'models/3/core/customers.sql',
	},
	{
		unique_id: 'model.project.orders',
		name: 'orders',
		schema: 'analytics',
		table: 'orders',
		columns: [],
		file_path: 'models/3/core/orders.sql',
	},
];

describe('ModelBindingPicker', () => {
	afterEach(() => {
		cleanup();
		frameworkModels.set([]);
	});

	it('filters models and emits the selected model', async () => {
		frameworkModels.set(models);
		const onSelect = (model: ModelInfo) => selected.push(model);
		const selected: ModelInfo[] = [];

		render(ModelBindingPicker, { props: { onSelect } });
		await fireEvent.click(screen.getByRole('button', { name: 'Bind model' }));

		const search = screen.getByRole('searchbox', { name: 'Search models' });
		await fireEvent.input(search, { target: { value: 'orders' } });

		expect(screen.queryByRole('button', { name: /customers/ })).not.toBeInTheDocument();
		await fireEvent.click(screen.getByRole('button', { name: /orders/ }));

		expect(selected).toEqual([models[1]]);
	});

	it('marks already-bound models and does not emit them again', async () => {
		frameworkModels.set(models);
		const onSelect = (model: ModelInfo) => selected.push(model);
		const selected: ModelInfo[] = [];

		render(ModelBindingPicker, {
			props: { onSelect, selectedModelIds: ['model.project.customers'] },
		});
		await fireEvent.click(screen.getByRole('button', { name: 'Bind model' }));

		const selectedModel = screen.getByRole('button', { name: /customers.*Already bound/i });
		expect(selectedModel).toBeDisabled();
		expect(screen.getByText('3/core')).toBeInTheDocument();
		expect(selected).toEqual([]);
	});

	it('shows top-level folders and reserves Uncategorized for missing paths', async () => {
		frameworkModels.set([
			models[0],
			{
				...models[1],
				unique_id: 'model.project.standalone',
				name: 'standalone',
				file_path: undefined,
			},
		]);

		render(ModelBindingPicker, { props: { onSelect: () => {} } });
		await fireEvent.click(screen.getByRole('button', { name: 'Bind model' }));

		expect(screen.getByText('3/core')).toBeInTheDocument();
		expect(screen.getByText('Uncategorized')).toBeInTheDocument();
	});
});
