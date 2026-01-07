import { test, expect } from '@playwright/test';

const API_URL = process.env.VITE_PUBLIC_API_URL || 'http://localhost:8000/api';

test.describe('Lineage feature flag', () => {
    test('hides lineage UI when disabled', async ({ page }) => {
        await page.goto('/');

        const modalHeading = page.getByText('Upstream Lineage');
        await expect(modalHeading).toHaveCount(0);
    });

    test('config info exposes lineage flag', async ({ request }) => {
        const response = await request.get(`${API_URL}/config-info`);
        expect(response.ok()).toBeTruthy();

        const data = await response.json();
        expect(data.lineage_enabled).toBe(false);
    });
});
