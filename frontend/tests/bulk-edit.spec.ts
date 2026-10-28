import { test, expect, type Page } from '@playwright/test';
import { resetDataModel, type DataModelPayload } from './helpers';

const API_URL = 'http://127.0.0.1:8000/api';

const SEEDED_MODEL: DataModelPayload = {
	version: 0.1,
	entities: [
		{
			id: 'customer_profile',
			label: 'Customer Profile',
			entity_type: 'dimension',
			domain: 'sales',
			tags: ['customer', 'shared'],
		},
		{
			id: 'order_fact',
			label: 'Order Fact',
			entity_type: 'fact',
			domain: 'sales',
			tags: ['order', 'shared'],
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

test.describe.configure({ mode: 'serial' });

function entityRow(page: Page, label: string) {
	return page.getByRole('row').filter({ hasText: label });
}

async function persistedEntity(page: Page, id: string): Promise<Record<string, any> | undefined> {
	const res = await page.request.get(`${API_URL}/data-model`);
	const model = await res.json();
	return (model.entities as Array<Record<string, any>>).find((e) => e.id === id);
}

async function openEntityList(page: Page) {
	await page.goto('/entity-list');
	await page.waitForSelector('[data-testid="app-ready"]', { timeout: 30000 });
	await expect(entityRow(page, 'Customer Profile')).toBeVisible();
}

test.describe('Bulk edit entities', () => {
	test.beforeEach(async ({ request }) => {
		await resetDataModel(request, SEEDED_MODEL);
	});

	test.afterEach(async ({ request }) => {
		await resetDataModel(request);
	});

	test('adds a domain and a tag to the selected entities only, and keeps them after reload', async ({
		page,
	}) => {
		await openEntityList(page);

		await entityRow(page, 'Customer Profile').getByRole('checkbox', { name: 'Select entity' }).check();
		await entityRow(page, 'Order Fact').getByRole('checkbox', { name: 'Select entity' }).check();
		await expect(page.getByText('2 entities selected').first()).toBeVisible();

		await page.getByRole('button', { name: 'Add Tags' }).click();

		const dialog = page.getByRole('dialog', { name: 'Bulk Edit Entities' });
		await expect(dialog).toBeVisible();
		await expect(dialog.getByText('2 entities selected')).toBeVisible();
		await expect(dialog.getByText('Customer Profile')).toBeVisible();
		await expect(dialog.getByText('Order Fact')).toBeVisible();
		await expect(dialog.getByText('Inventory Dimension')).toHaveCount(0);

		await dialog.getByLabel('Add Domain').selectOption('operations');
		await dialog.getByPlaceholder('Type new tag...').fill('reviewed');
		await dialog.getByRole('button', { name: 'Add', exact: true }).click();
		await dialog.getByRole('button', { name: 'Apply Changes' }).click();

		await expect(dialog).toBeHidden();

		// Applied in the UI
		await expect(entityRow(page, 'Customer Profile')).toContainText('reviewed');
		await expect(entityRow(page, 'Order Fact')).toContainText('reviewed');
		await expect(entityRow(page, 'Inventory Dimension')).not.toContainText('reviewed');

		// Autosave writes it to the backend
		await expect
			.poll(async () => (await persistedEntity(page, 'order_fact'))?.tags ?? [], { timeout: 15000 })
			.toContain('reviewed');
		for (const id of ['customer_profile', 'order_fact']) {
			const saved = await persistedEntity(page, id);
			expect(saved?.tags).toContain('reviewed');
			expect(saved?.tags).toContain('shared');
			expect(saved?.domain).toBe('operations');
		}
		const untouched = await persistedEntity(page, 'inventory_dimension');
		expect(untouched?.tags).toEqual(['inventory']);
		expect(untouched?.domain).toBe('operations');

		// ... and survives a full page reload
		await page.reload();
		await page.waitForSelector('[data-testid="app-ready"]', { timeout: 30000 });
		await expect(entityRow(page, 'Customer Profile')).toContainText('reviewed');
		await expect(entityRow(page, 'Order Fact')).toContainText('reviewed');
		await expect(entityRow(page, 'Inventory Dimension')).not.toContainText('reviewed');
	});

	test('removes a tag shared by the selection from every selected entity', async ({ page }) => {
		await openEntityList(page);

		await entityRow(page, 'Customer Profile').getByRole('checkbox', { name: 'Select entity' }).check();
		await entityRow(page, 'Order Fact').getByRole('checkbox', { name: 'Select entity' }).check();
		await page.getByRole('button', { name: 'Remove Tags' }).click();

		const dialog = page.getByRole('dialog', { name: 'Bulk Edit Entities' });
		// Only "shared" is on both entities; "customer"/"order" are not offered for removal.
		const commonTags = dialog.getByText('Common tags:').locator('..');
		await expect(commonTags.getByRole('button', { name: 'shared' })).toBeVisible();
		await expect(commonTags.getByRole('button', { name: 'customer' })).toHaveCount(0);

		await commonTags.getByRole('button', { name: 'shared' }).click();
		await dialog.getByRole('button', { name: 'Apply Changes' }).click();
		await expect(dialog).toBeHidden();

		await expect
			.poll(async () => (await persistedEntity(page, 'order_fact'))?.tags, { timeout: 15000 })
			.toEqual(['order']);
		expect((await persistedEntity(page, 'customer_profile'))?.tags).toEqual(['customer']);

		await page.reload();
		await page.waitForSelector('[data-testid="app-ready"]', { timeout: 30000 });
		await expect(entityRow(page, 'Customer Profile')).not.toContainText('shared');
		await expect(entityRow(page, 'Order Fact')).not.toContainText('shared');
	});

	test('cancel leaves the entities unchanged', async ({ page }) => {
		await openEntityList(page);

		await entityRow(page, 'Customer Profile').getByRole('checkbox', { name: 'Select entity' }).check();
		await page.getByRole('button', { name: 'Add Domain' }).click();

		const dialog = page.getByRole('dialog', { name: 'Bulk Edit Entities' });
		await dialog.getByLabel('Add Domain').selectOption('operations');
		await dialog.getByRole('button', { name: 'Cancel' }).click();
		await expect(dialog).toBeHidden();

		const saved = await persistedEntity(page, 'customer_profile');
		expect(saved?.domain).toBe('sales');
	});
});
