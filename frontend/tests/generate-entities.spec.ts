import { test, expect, type APIRequestContext } from '@playwright/test';
import { resetDataModel } from './helpers';

const API_URL = 'http://127.0.0.1:8000/api';

// Real backend, real generator: the event below is created through the API and the entities
// are produced by the server, so this covers generate -> preview -> save -> reload end to end.
const EVENT_TEXT = 'E2E customer places order';

test.describe.configure({ mode: 'serial' });

async function createEvent(request: APIRequestContext): Promise<string> {
	const res = await request.post(`${API_URL}/business-events`, {
		data: {
			text: EVENT_TEXT,
			type: 'discrete',
			annotations: {
				who: [{ id: 'w1', text: 'e2e_shopper' }],
				what: [{ id: 'w2', text: 'e2e_basket' }],
				how_many: [{ id: 'w3', text: 'e2e_order_value' }],
			},
		},
	});
	expect(res.status()).toBe(201);
	return (await res.json()).id as string;
}

async function persistedEntities(request: APIRequestContext) {
	const res = await request.get(`${API_URL}/data-model`);
	return (await res.json()).entities as Array<Record<string, any>>;
}

test.describe('Generate entities from a business event', () => {
	let eventId: string;

	test.beforeEach(async ({ request }) => {
		await resetDataModel(request);
		eventId = await createEvent(request);
	});

	test.afterEach(async ({ request }) => {
		await request.delete(`${API_URL}/business-events/${eventId}`);
		await resetDataModel(request);
	});

	test('generates a preview, creates the entities, and they persist after reload', async ({
		page,
		request,
	}) => {
		await page.goto('/business-events');
		await page.waitForSelector('[data-testid="app-ready"]', { timeout: 30000 });

		await expect(page.getByText(EVENT_TEXT)).toBeVisible();
		const generateBtn = page.getByTitle('Generate dimensional entities from annotations');
		await expect(generateBtn).toBeEnabled();
		await generateBtn.click();

		const dialog = page.getByRole('dialog', { name: 'Generate Entities from Event' });
		await expect(dialog).toBeVisible();

		// Preview: two dimensions (who, what) and one fact (how many), all editable by label.
		const labelInputs = dialog.locator('tbody input[type="text"]');
		await expect(dialog.locator('tbody tr')).toHaveCount(3, { timeout: 10000 });
		await expect(dialog.getByText('Dimension', { exact: true })).toHaveCount(2);
		await expect(dialog.getByText('Fact', { exact: true })).toHaveCount(1);
		const previewLabels = await labelInputs.evaluateAll((els) =>
			els.map((el) => (el as HTMLInputElement).value),
		);
		expect(previewLabels.join(' ').toLowerCase()).toContain('e2e_shopper');
		expect(previewLabels.join(' ').toLowerCase()).toContain('fct_e2e_customer_places_order');

		// Nothing is persisted before confirming.
		expect(
			(await persistedEntities(request)).filter((e) => /e2e_/.test(e.id)),
		).toHaveLength(0);

		await dialog.getByRole('button', { name: 'Create All' }).click();
		await expect(dialog.getByText('Entities created successfully!')).toBeVisible({ timeout: 15000 });

		// Persisted to the data model on the backend, with the fact joined to both dimensions.
		const saved = (await persistedEntities(request)).filter((e) => /e2e_/.test(e.id));
		expect(saved).toHaveLength(3);
		expect(saved.filter((e) => e.entity_type === 'dimension')).toHaveLength(2);
		expect(saved.filter((e) => e.entity_type === 'fact')).toHaveLength(1);

		const modelRes = await request.get(`${API_URL}/data-model`);
		const relationships = (await modelRes.json()).relationships as Array<Record<string, any>>;
		const factId = saved.find((e) => e.entity_type === 'fact')!.id;
		const dimIds = saved.filter((e) => e.entity_type === 'dimension').map((e) => e.id);
		for (const dimId of dimIds) {
			expect(
				relationships.some(
					(r) =>
						[r.source, r.target].includes(dimId) && [r.source, r.target].includes(factId),
				),
			).toBe(true);
		}

		// The event now records which entities it produced.
		const events = await (await request.get(`${API_URL}/business-events`)).json();
		const updated = events.find((e: any) => e.id === eventId);
		expect(updated.derived_entities.map((d: any) => d.entity_id).sort()).toEqual(
			saved.map((e) => e.id).sort(),
		);

		// Reload: the entities are still there on the canvas / entity list.
		await page.goto('/entity-list');
		await page.waitForSelector('[data-testid="app-ready"]', { timeout: 30000 });
		for (const entity of saved) {
			await expect(page.getByRole('row').filter({ hasText: entity.label })).toBeVisible();
		}
		await page.reload();
		await page.waitForSelector('[data-testid="app-ready"]', { timeout: 30000 });
		for (const entity of saved) {
			await expect(page.getByRole('row').filter({ hasText: entity.label })).toBeVisible();
		}
	});

	test('cancelling the preview creates no entities', async ({ page, request }) => {
		await page.goto('/business-events');
		await page.waitForSelector('[data-testid="app-ready"]', { timeout: 30000 });

		await page.getByTitle('Generate dimensional entities from annotations').click();
		const dialog = page.getByRole('dialog', { name: 'Generate Entities from Event' });
		await expect(dialog.locator('tbody tr')).toHaveCount(3, { timeout: 10000 });

		await dialog.getByRole('button', { name: 'Cancel' }).click();
		await expect(dialog).toBeHidden();

		expect((await persistedEntities(request)).filter((e) => /e2e_/.test(e.id))).toHaveLength(0);
	});
});
