import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';
import { resetDataModel, type DataModelPayload } from './helpers';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, '..', '..');
const MANIFEST_PATH = path.join(REPO_ROOT, 'dbt_company_dummy', 'target', 'manifest.json');
const MODEL_ID = 'model.company_dummy.clean_customer';

test.describe('Origin display in EntityDetailModal', () => {
	let manifestBackup: string;

	test.beforeAll(() => {
		manifestBackup = fs.readFileSync(MANIFEST_PATH, 'utf8');
	});

	test.afterAll(() => {
		fs.writeFileSync(MANIFEST_PATH, manifestBackup, 'utf8');
	});

	test('shows read-only structured origin for draft and dbt fields', async ({ page, request }) => {
		const manifest = JSON.parse(manifestBackup);
		manifest.nodes[MODEL_ID].columns = {
			...(manifest.nodes[MODEL_ID].columns ?? {}),
			id: {
				name: 'id',
				data_type: 'bigint',
				description: 'Customer id',
				meta: { origin: [{ DH1: 'CORE.CUSTOMER.ID' }] },
			},
		};
		fs.writeFileSync(MANIFEST_PATH, JSON.stringify(manifest), 'utf8');

		const payload: DataModelPayload = {
			version: 0.1,
			entities: [
				{
					id: 'origin_draft_e2e',
					label: 'Origin Draft E2E',
					entity_type: 'dimension',
					drafted_fields: [
						{
							name: 'campaign_amount',
							datatype: 'float',
							description: 'Allocated amount',
							origin: [
								{ DH1: 'CORE.T_SALES.AMOUNT' },
								{ DH2: 'CBUS.AMOUNT' },
							],
						},
					],
				},
				{
					id: 'clean_customer_e2e',
					label: 'Clean Customer E2E',
					entity_type: 'dimension',
					dbt_model: MODEL_ID,
					drafted_fields: [],
				},
			],
			relationships: [],
		};
		await resetDataModel(request, payload);

		await page.goto('/entity-list');
		await page.waitForLoadState('networkidle');

		await page.getByRole('row', { name: /Origin Draft E2E/i }).click();
		let dialog = page.getByRole('dialog');
		await expect(dialog.getByTestId('origin-entry').filter({ hasText: 'DH1: CORE.T_SALES.AMOUNT' })).toBeVisible();
		await expect(dialog.getByTestId('origin-entry').filter({ hasText: 'DH2: CBUS.AMOUNT' })).toBeVisible();
		await expect(dialog.locator('input[placeholder="Origin"]')).toHaveCount(0);

		await dialog.getByRole('button', { name: 'Close' }).click();
		await expect(dialog).toBeHidden({ timeout: 10000 });

		await page.reload();
		await page.waitForLoadState('networkidle');

		await page.getByRole('row', { name: /Clean Customer E2E/i }).click();
		dialog = page.getByRole('dialog');
		const idRow = dialog.getByTestId('merged-field-row-id');
		await expect(idRow.getByTestId('origin-entry').filter({ hasText: 'DH1: CORE.CUSTOMER.ID' })).toBeVisible({
			timeout: 15000,
		});
		await expect(dialog.locator('input[placeholder="Origin"]')).toHaveCount(0);
	});
});
