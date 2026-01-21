import { test, expect } from '@playwright/test';
import { applyConfigOverrides, getCompanyDummyConfigOverrides, resetDataModel, restoreConfig, type DataModelPayload } from './helpers';

const API_URL = process.env.VITE_PUBLIC_API_URL || 'http://localhost:8000/api';

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
    test('opens lineage modal for bound entity when enabled', async ({ page, request }) => {
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
            const entityInput = page.locator('input[value="Customer"]');
            await expect(entityInput).toBeVisible({ timeout: 15000 });

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
});
