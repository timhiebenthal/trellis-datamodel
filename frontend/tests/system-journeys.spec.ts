import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';
import { parse as parseYaml, stringify as stringifyYaml } from 'yaml';
import { resetDataModel, type DataModelPayload } from './helpers';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, '..', '..');
const DATA_MODEL_YML = path.join(__dirname, 'test_data_model.yml');
const CLEAN_CUSTOMER_SCHEMA_YML = path.join(
	REPO_ROOT,
	'dbt_company_dummy',
	'models',
	'1_clean',
	'clean_customer.yml',
);
const API_URL = 'http://127.0.0.1:8000/api';

function readDataModelFile(): { entities?: Array<Record<string, any>> } {
	return parseYaml(fs.readFileSync(DATA_MODEL_YML, 'utf8')) ?? {};
}

function findEntity(entities: Array<Record<string, any>> | undefined, id: string) {
	return (entities ?? []).find((e) => e.id === id);
}

test.describe.configure({ mode: 'serial' });

test.describe('System journeys (UI -> proxy -> backend -> disk)', () => {
	test.afterEach(async ({ request }) => {
		if (fs.existsSync(CLEAN_CUSTOMER_SCHEMA_YML)) {
			fs.unlinkSync(CLEAN_CUSTOMER_SCHEMA_YML);
		}
		await resetDataModel(request);
	});

	test('J1: add tag on canvas -> autosave to ui_tags -> push merges into schema.yml', async ({
		page,
		request,
	}) => {
		// Hand-written dbt-native tag that Trellis must preserve on push.
		fs.writeFileSync(
			CLEAN_CUSTOMER_SCHEMA_YML,
			`version: 2
models:
  - name: clean_customer
    config:
      tags:
        - nightly
`,
			'utf8',
		);

		// Description is set, so only the "Attributes Without Descriptions" push warning opens
		// (the bound model's 7 dbt columns have no descriptions) - handled deterministically below.
		const payload: DataModelPayload = {
			version: 0.1,
			entities: [
				{
					id: 'clean_customer_journey',
					label: 'Clean Customer Journey',
					description: 'Customer master used by the tag journey test',
					entity_type: 'dimension',
					model_ref: 'model.company_dummy.clean_customer',
					drafted_fields: [],
				},
			],
			relationships: [],
		};
		await resetDataModel(request, payload);

		await page.addInitScript(() => {
			localStorage.setItem('trellis_all_expanded', 'true');
		});
		await page.goto('/');
		await page.waitForSelector('[data-testid="canvas-ready"]', { timeout: 25000 });
		await page.waitForSelector('[data-testid="app-ready"]', { timeout: 30000 });

		const nameInput = page.getByPlaceholder('Entity Name').first();
		await expect(nameInput).toHaveValue('Clean Customer Journey', { timeout: 20000 });
		const node = page.locator('.svelte-flow__node-entity').filter({ has: nameInput });
		await expect(node).toBeVisible();

		await node.getByRole('button', { name: 'Add new tag' }).click();
		const tagInput = node.getByRole('textbox', { name: 'Add new tag' });
		await tagInput.fill('finance');
		await tagInput.press('Enter');
		await expect(node.getByRole('button', { name: 'Remove finance tag' })).toBeVisible();

		// (1) Autosave (debounced) lands in the data model file as ui_tags only.
		await expect
			.poll(() => findEntity(readDataModelFile().entities, 'clean_customer_journey')?.ui_tags, {
				timeout: 15000,
			})
			.toEqual(['finance']);
		const saved = findEntity(readDataModelFile().entities, 'clean_customer_journey')!;
		expect(saved).not.toHaveProperty('tags');

		const apiEntity = (
			await (await request.get(`${API_URL}/data-model`)).json()
		).entities.find((e: Record<string, any>) => e.id === 'clean_customer_journey');
		expect(apiEntity.ui_tags).toEqual(['finance']);

		// (2) Push to dbt.
		await page.getByRole('button', { name: 'Push to dbt' }).click();
		const warning = page.getByRole('dialog', { name: /Attributes Without Descriptions/ });
		await expect(warning).toBeVisible();
		await warning.getByRole('button', { name: 'Continue Anyway' }).click();
		await expect(page.getByText(/Updated \d+ file\(s\)/)).toBeVisible({ timeout: 20000 });

		// (3) schema.yml keeps the dbt-native tag and gains the Trellis tag.
		const schema = parseYaml(fs.readFileSync(CLEAN_CUSTOMER_SCHEMA_YML, 'utf8'));
		const model = schema.models.find((m: Record<string, any>) => m.name === 'clean_customer');
		const tags: string[] = model.config?.tags ?? model.tags ?? [];
		expect(tags).toContain('nightly');
		expect(tags).toContain('finance');
	});

	test('J1b: remove a pushed tag on the canvas -> autosave clears ui_tags -> push removes it from schema.yml', async ({
		page,
		request,
	}) => {
		fs.writeFileSync(
			CLEAN_CUSTOMER_SCHEMA_YML,
			`version: 2
models:
  - name: clean_customer
    config:
      tags:
        - nightly
`,
			'utf8',
		);

		const payload: DataModelPayload = {
			version: 0.1,
			entities: [
				{
					id: 'clean_customer_journey',
					label: 'Clean Customer Journey',
					description: 'Customer master used by the tag journey test',
					entity_type: 'dimension',
					model_ref: 'model.company_dummy.clean_customer',
					drafted_fields: [],
				},
			],
			relationships: [],
		};
		await resetDataModel(request, payload);

		await page.addInitScript(() => {
			localStorage.setItem('trellis_all_expanded', 'true');
		});
		await page.goto('/');
		await page.waitForSelector('[data-testid="canvas-ready"]', { timeout: 25000 });
		await page.waitForSelector('[data-testid="app-ready"]', { timeout: 30000 });

		const nameInput = page.getByPlaceholder('Entity Name').first();
		await expect(nameInput).toHaveValue('Clean Customer Journey', { timeout: 20000 });
		const node = page.locator('.svelte-flow__node-entity').filter({ has: nameInput });
		await expect(node).toBeVisible();

		const readEntity = () => findEntity(readDataModelFile().entities, 'clean_customer_journey');
		const readModelTags = (): string[] => {
			const schema = parseYaml(fs.readFileSync(CLEAN_CUSTOMER_SCHEMA_YML, 'utf8'));
			const model = schema.models.find((m: Record<string, any>) => m.name === 'clean_customer');
			return model.config?.tags ?? model.tags ?? [];
		};
		const pushToDbt = async () => {
			await page.getByRole('button', { name: 'Push to dbt' }).click();
			const warning = page.getByRole('dialog', { name: /Attributes Without Descriptions/ });
			await expect(warning).toBeVisible();
			await warning.getByRole('button', { name: 'Continue Anyway' }).click();
		};

		// Add finance and push it.
		await node.getByRole('button', { name: 'Add new tag' }).click();
		const tagInput = node.getByRole('textbox', { name: 'Add new tag' });
		await tagInput.fill('finance');
		await tagInput.press('Enter');
		await expect(node.getByRole('button', { name: 'Remove finance tag' })).toBeVisible();
		await expect.poll(() => readEntity()?.ui_tags, { timeout: 15000 }).toEqual(['finance']);

		await pushToDbt();
		await expect(page.getByText(/Updated \d+ file\(s\)/)).toBeVisible({ timeout: 20000 });

		// (1) schema.yml carries both; (2) backend recorded what it pushed.
		expect(readModelTags()).toContain('nightly');
		expect(readModelTags()).toContain('finance');
		expect(readEntity()!.pushed_tags).toEqual(['finance']);

		// A dbt developer hand-adds a tag; Trellis must never touch it.
		const schemaDoc = parseYaml(fs.readFileSync(CLEAN_CUSTOMER_SCHEMA_YML, 'utf8'));
		const schemaModel = schemaDoc.models.find(
			(m: Record<string, any>) => m.name === 'clean_customer',
		);
		if (schemaModel.config?.tags) {
			schemaModel.config.tags.push('hourly');
		} else {
			schemaModel.tags.push('hourly');
		}
		fs.writeFileSync(CLEAN_CUSTOMER_SCHEMA_YML, stringifyYaml(schemaDoc), 'utf8');
		expect(readModelTags()).toContain('hourly');

		// Remove the pushed tag on the canvas: autosave omits ui_tags, backend stores [].
		await node.getByRole('button', { name: 'Remove finance tag' }).click();
		await expect(node.getByRole('button', { name: 'Remove finance tag' })).toBeHidden();
		await expect.poll(() => readEntity()?.ui_tags, { timeout: 15000 }).toEqual([]);
		expect(readEntity()!.pushed_tags).toEqual(['finance']);

		// Second push removes finance only.
		await pushToDbt();
		await expect
			.poll(() => [...readModelTags()].sort(), { timeout: 20000 })
			.toEqual(['hourly', 'nightly']);
		await expect.poll(() => readEntity()?.pushed_tags, { timeout: 15000 }).toEqual([]);
	});

	test('J2-lite: structured roles survive a description edit made in the modal', async ({
		page,
		request,
	}) => {
		// Unbound entity: no dbt model/schema.yml involved, so Save Changes only touches
		// the data model and the roles round trip is the single thing under test.
		const payload: DataModelPayload = {
			version: 0.1,
			entities: [
				{
					id: 'roles_journey',
					label: 'Roles Journey',
					description: 'before edit',
					entity_type: 'dimension',
					roles: [
						{ label: 'Buyer', role: 'buyer', source: 'user' },
						{ label: 'Approver', role: 'approver', source: 'dbt' },
					],
					drafted_fields: [],
				},
			],
			relationships: [],
		};
		await resetDataModel(request, payload);

		await page.goto('/entity-list');
		await page.waitForSelector('[data-testid="app-ready"]', { timeout: 30000 });

		await page.getByRole('row', { name: /Roles Journey/i }).click();
		const dialog = page.getByRole('dialog').filter({
			has: page.getByRole('heading', { name: /Roles Journey/i }),
		});
		await expect(dialog).toBeVisible({ timeout: 15000 });

		await dialog.getByLabel('Description').fill('after edit');
		await dialog.getByRole('button', { name: /Save Changes/i }).click();
		await expect(dialog).toBeHidden({ timeout: 10000 });

		await page.reload();
		await page.waitForSelector('[data-testid="app-ready"]', { timeout: 30000 });

		const expectedRoles = [
			{ label: 'Buyer', role: 'buyer', source: 'user' },
			{ label: 'Approver', role: 'approver', source: 'dbt' },
		];

		await expect
			.poll(() => findEntity(readDataModelFile().entities, 'roles_journey')?.description, {
				timeout: 15000,
			})
			.toBe('after edit');
		expect(findEntity(readDataModelFile().entities, 'roles_journey')!.roles).toEqual(
			expectedRoles,
		);

		const apiEntity = (
			await (await request.get(`${API_URL}/data-model`)).json()
		).entities.find((e: Record<string, any>) => e.id === 'roles_journey');
		expect(apiEntity.description).toBe('after edit');
		expect(apiEntity.roles).toEqual(expectedRoles);
	});
});
