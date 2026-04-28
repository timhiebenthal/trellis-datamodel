import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';
import { resetDataModel, type DataModelPayload } from './helpers';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, '..', '..');
const CLEAN_CUSTOMER_SCHEMA_YML = path.join(
	REPO_ROOT,
	'dbt_company_dummy',
	'models',
	'1_clean',
	'clean_customer.yml',
);

test.describe.configure({ mode: 'serial' });

test.describe('Merged dbt + drafted fields', () => {
	test.afterEach(() => {
		try {
			if (fs.existsSync(CLEAN_CUSTOMER_SCHEMA_YML)) {
				fs.unlinkSync(CLEAN_CUSTOMER_SCHEMA_YML);
			}
		} catch {
			// ignore
		}
	});

	test('canvas logical view shows materialized indicators for a bound entity', async ({ page, request }) => {
		const payload: DataModelPayload = {
			version: 0.1,
			entities: [
				{
					id: 'clean_customer_e2e',
					label: 'Clean Customer E2E',
					entity_type: 'dimension',
					dbt_model: 'model.company_dummy.clean_customer',
					drafted_fields: [],
				},
			],
			relationships: [],
		};
		await resetDataModel(request, payload);

		await page.goto('/');
		await page.waitForSelector('[data-testid="canvas-ready"]', { timeout: 25000 });
		// Wait for manifest + data model to finish loading before switching views
		await page.waitForSelector('[data-testid="app-ready"]', { timeout: 30000 });

		const nameInput = page.getByPlaceholder('Entity Name').first();
		await expect(nameInput).toHaveValue('Clean Customer E2E', { timeout: 20000 });

		await page.getByRole('button', { name: 'Logical' }).click();

		const node = page.locator('.svelte-flow__node-entity').filter({ has: nameInput });
		await expect(node).toBeVisible({ timeout: 5000 });

		const materialized = node.locator('[aria-label*="Materialized in dbt model"]');
		await expect(materialized.first()).toBeVisible({ timeout: 15000 });
		// clean_customer catalog columns (manifest + catalog merge)
		await expect(materialized).toHaveCount(7);

		await expect(node.getByRole('button', { name: /Add Field/i })).toBeVisible();
	});

	test('modal: add draft, save, materialize writes schema.yml and shows SQL-gap warning', async ({ page, request }) => {
		const payload: DataModelPayload = {
			version: 0.1,
			entities: [
				{
					id: 'clean_customer_e2e',
					label: 'Clean Customer E2E',
					entity_type: 'dimension',
					dbt_model: 'model.company_dummy.clean_customer',
					drafted_fields: [],
				},
			],
			relationships: [],
		};
		await resetDataModel(request, payload);

		await page.goto('/entity-list');
		await page.waitForLoadState('networkidle');

		await page.getByRole('row', { name: /Clean Customer E2E/i }).click();
		await expect(page.getByRole('heading', { name: /Clean Customer E2E Details/i })).toBeVisible({
			timeout: 15000,
		});

		const dialog = page.getByRole('dialog').filter({
			has: page.getByRole('heading', { name: /Clean Customer E2E Details/i }),
		});

		const matBefore = dialog.locator('[aria-label*="Materialized in dbt model"]');
		await expect(matBefore.first()).toBeVisible({ timeout: 15000 });
		await expect(matBefore).toHaveCount(7);

		await dialog.getByRole('button', { name: /Add Attribute/i }).click();

		const nameInputs = dialog.getByPlaceholder('attribute_name');
		await expect(nameInputs).toHaveCount(8);
		await nameInputs.nth(7).fill('pending_col');

		const draftRowSelect = dialog.locator('select').last();
		await draftRowSelect.selectOption('text');

		await dialog.getByRole('button', { name: /Save Changes/i }).click();
		await expect(dialog).toBeHidden({ timeout: 10000 });

		await page.getByRole('row', { name: /Clean Customer E2E/i }).click();
		await expect(page.getByRole('heading', { name: /Clean Customer E2E Details/i })).toBeVisible({
			timeout: 15000,
		});

		const dialog2 = page.getByRole('dialog').filter({
			has: page.getByRole('heading', { name: /Clean Customer E2E Details/i }),
		});
		await expect(dialog2.locator('[aria-label*="Drafted in Trellis"]')).toHaveCount(1);

		await dialog2.getByTitle(/Write to clean_customer's schema\.yml/i).click();

		await expect(dialog2.getByText(/added to schema\.yml/i)).toBeVisible({ timeout: 20000 });
		await expect(dialog2.getByText(/\.sql/i)).toBeVisible();

		expect(fs.existsSync(CLEAN_CUSTOMER_SCHEMA_YML)).toBeTruthy();
		const yml = fs.readFileSync(CLEAN_CUSTOMER_SCHEMA_YML, 'utf8');
		expect(yml).toContain('pending_col');

		await expect(dialog2.locator('[aria-label*="Drafted in Trellis"]')).toHaveCount(0);
	});

	test('modal: editing a materialized column description persists to schema.yml', async ({ page, request }) => {
		fs.writeFileSync(
			CLEAN_CUSTOMER_SCHEMA_YML,
			`version: 2
models:
  - name: clean_customer
    columns:
      - name: id
        data_type: bigint
        description: before e2e
      - name: name
        data_type: varchar
      - name: email
        data_type: varchar
`,
			'utf8',
		);

		const payload: DataModelPayload = {
			version: 0.1,
			entities: [
				{
					id: 'clean_customer_e2e',
					label: 'Clean Customer E2E',
					entity_type: 'dimension',
					dbt_model: 'model.company_dummy.clean_customer',
					drafted_fields: [],
				},
			],
			relationships: [],
		};
		await resetDataModel(request, payload);

		await page.goto('/entity-list');
		await page.waitForLoadState('networkidle');

		await page.getByRole('row', { name: /Clean Customer E2E/i }).click();
		await expect(page.getByRole('heading', { name: /Clean Customer E2E Details/i })).toBeVisible({
			timeout: 15000,
		});

		const dialog = page.getByRole('dialog').filter({
			has: page.getByRole('heading', { name: /Clean Customer E2E Details/i }),
		});

		const idRow = dialog.getByTestId('merged-field-row-id');
		await idRow.getByPlaceholder('Description (optional)').fill('after e2e description');

		await dialog.getByRole('button', { name: /Save Changes/i }).click();
		await expect(dialog).toBeHidden({ timeout: 10000 });

		const yml = fs.readFileSync(CLEAN_CUSTOMER_SCHEMA_YML, 'utf8');
		expect(yml).toContain('after e2e description');
		expect(yml).not.toContain('before e2e');
	});
});
