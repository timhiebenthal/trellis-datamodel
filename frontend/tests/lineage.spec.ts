import { test, expect } from '@playwright/test';

test.describe('Lineage feature flag', () => {
    test('hides lineage UI when disabled', async ({ page }) => {
        await page.goto('/');

        const modalHeading = page.getByText('Upstream Lineage');
        await expect(modalHeading).toHaveCount(0);
    });

    test('config info exposes lineage flag', async ({ request }) => {
        const response = await request.get('/api/config-info');
        expect(response.ok()).toBeTruthy();

        const data = await response.json();
        expect(data.lineage_enabled).toBe(false);
    });
});
