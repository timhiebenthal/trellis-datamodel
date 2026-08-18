import { test, expect } from '@playwright/test';
import { resetDataModel, type DataModelPayload } from './helpers';

const ENTITY_LIST_DATA: DataModelPayload = {
	version: 0.1,
	entities: [
		{
			id: 'customer_profile',
			label: 'Customer Profile',
			entity_type: 'dimension',
			domain: 'sales',
			tags: ['customer', 'profile'],
		},
		{
			id: 'customer_event',
			label: 'Customer Event',
			entity_type: 'dimension',
			domain: 'sales',
			tags: ['customer', 'event'],
		},
		{
			id: 'order_fact',
			label: 'Order Fact',
			entity_type: 'fact',
			domain: 'sales',
			tags: ['order'],
		},
		{
			id: 'inventory_dimension',
			label: 'Inventory Dimension',
			entity_type: 'dimension',
			domain: 'operations',
			tags: ['inventory'],
		},
	],
	relationships: [],
};

test('Open filtered on Canvas navigates with the complete filtered entity set', async ({ page, request }) => {
	await resetDataModel(request, ENTITY_LIST_DATA);
	await page.goto('/entity-list');
	await page.waitForSelector('[data-testid="app-ready"]', { timeout: 30000 });

	// Apply domain, tag, type, and search filters. Both customer entities remain visible.
	const filterSelects = page.locator('select:not(#folder-select):not(#tag-select)');
	await filterSelects.nth(0).selectOption('sales');
	await filterSelects.nth(1).selectOption('customer');
	await filterSelects.nth(2).selectOption('dimension');
	await page.getByPlaceholder('Search by entity name...').fill('Customer');

	await expect(page.getByText('2', { exact: true }).first()).toBeVisible();
	const openOnCanvas = page.getByRole('link', { name: 'Open filtered on Canvas (2 entities)' });
	await expect(openOnCanvas).toBeVisible();
	await expect(openOnCanvas).toHaveAttribute(
		'href',
		'/canvas?entities=customer_profile%2Ccustomer_event',
	);

	await openOnCanvas.click();
	await expect(page).toHaveURL(
		/canvas\?entities=customer_profile%2Ccustomer_event$/,
	);
	await page.waitForSelector('[data-testid="canvas-ready"]', { timeout: 30000 });
	const canvasEntities = page.locator('.svelte-flow__node-entity');
	await expect(canvasEntities).toHaveCount(2, { timeout: 30000 });
	await expect(canvasEntities.filter({ hasText: 'Customer Profile' })).toBeVisible();
	await expect(canvasEntities.filter({ hasText: 'Customer Event' })).toBeVisible();
	await expect(canvasEntities.filter({ hasText: 'Order Fact' })).toHaveCount(0);
});
