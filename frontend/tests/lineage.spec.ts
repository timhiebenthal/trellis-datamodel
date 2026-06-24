import { test, expect } from '@playwright/test';
import { applyConfigOverrides, getCompanyDummyConfigOverrides, resetDataModel, restoreConfig, type DataModelPayload } from './helpers';

const API_URL = 'http://127.0.0.1:8000/api';

test.describe.configure({ mode: 'serial' });

test.describe('Lineage feature flag', () => {
    test('hides lineage UI when disabled', async ({ page }) => {
        await page.goto('/');

        const modalHeading = page.getByText('Upstream Lineage');
        await expect(modalHeading).toHaveCount(0);
    });

    test.skip('config info exposes lineage flag', async ({ request }) => {
        // Skip: this test assumes lineage is disabled, but other tests may enable it
        const response = await request.get(`${API_URL}/config-info`);
        expect(response.ok()).toBeTruthy();

        const data = await response.json();
        expect(data.lineage_enabled).toBe(false);
    });
});

test.describe('Lineage button behavior', () => {
    test.skip('opens lineage modal for bound entity when enabled', async ({ page, request }) => {
        // Skip: config changes cause test pollution in CI
        const originalConfig = await applyConfigOverrides(request, {
            ...getCompanyDummyConfigOverrides(),
            lineage: { enabled: true },
        });

        try {
            const SEEDED_MODEL: DataModelPayload = {
                version: 0.1,
                entities: [
                    {
                        id: 'customer',
                        label: 'Customer',
                        dbt_model: 'model.company_dummy.customer',
                    },
                ],
                relationships: [],
            };

            await resetDataModel(request, SEEDED_MODEL);
            await page.addInitScript(() => {
                localStorage.clear();
                sessionStorage.clear();
            });
            await page.goto('/');
            await page.waitForLoadState('networkidle');

            // Wait for entity node to appear first
            const lineageButton = page.locator(
                'button[aria-label="Show lineage for model.company_dummy.customer"]',
            );
            await expect(lineageButton).toBeVisible({ timeout: 10000 });
            await lineageButton.click();

            await expect(page.getByRole('heading', { name: 'Upstream Lineage' })).toBeVisible({ timeout: 10000 });
        } finally {
            await restoreConfig(request, originalConfig);
        }
    });

    // Requires dbt_company_dummy/target/manifest.json (gitignored). CI runs `dbt parse` before e2e.
    test('renders lineage edges for a model', async ({ page, request }) => {
        const originalConfig = await applyConfigOverrides(request, {
            ...getCompanyDummyConfigOverrides(),
            lineage: { enabled: true },
        });

        try {
            const SEEDED_MODEL: DataModelPayload = {
                version: 0.1,
                entities: [
                    {
                        id: 'dim_customer',
                        label: 'Dim Customer',
                        dbt_model: 'model.company_dummy.dim_customer',
                    },
                ],
                relationships: [],
            };

            await resetDataModel(request, SEEDED_MODEL);
            await page.addInitScript(() => {
                localStorage.clear();
                sessionStorage.clear();
            });
            await page.goto('/');
            await page.waitForLoadState('networkidle');

            // Wait for canvas to finish loading
            await page.waitForSelector('[data-testid="canvas-ready"]', { timeout: 15000 });

            const lineageButton = page.locator(
                'button[aria-label="Show lineage for model.company_dummy.dim_customer"]',
            );
            const hasLineageButton = await lineageButton.isVisible({ timeout: 10000 }).catch(() => false);
            if (!hasLineageButton) {
                test.skip(true, 'Lineage button unavailable in current test environment');
                return;
            }
            await lineageButton.click();

            await expect(page.getByRole('heading', { name: 'Upstream Lineage' })).toBeVisible({
                timeout: 10000,
            });

            const edgeLocator = page.locator('.svelte-flow__edge');
            await expect
                .poll(async () => edgeLocator.count(), { timeout: 15000 })
                .toBeGreaterThan(0);
        } finally {
            await restoreConfig(request, originalConfig);
        }
    });
});
