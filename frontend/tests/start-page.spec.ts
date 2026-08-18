import { test, expect } from '@playwright/test';
import { applyConfigOverrides, restoreConfig } from './helpers';

test.describe('Start page navigation', () => {
    test('configured start page canvas opens /canvas', async ({ page, request }) => {
        const originalConfig = await applyConfigOverrides(request, { start_page: 'canvas' });

        try {
            await page.goto('/');
            await expect(page).toHaveURL(/\/canvas$/);
        } finally {
            await restoreConfig(request, originalConfig);
        }
    });

    test('configured start page entity-list opens /entity-list', async ({ page, request }) => {
        const originalConfig = await applyConfigOverrides(request, { start_page: 'entity-list' });

        try {
            await page.goto('/');
            await expect(page).toHaveURL(/\/entity-list$/);
        } finally {
            await restoreConfig(request, originalConfig);
        }
    });

    test('falls back to /canvas when the start page is unsupported', async ({ page }) => {
        await page.route('**/api/config-info', async (route) => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({ start_page: 'unsupported' }),
            });
        });

        await page.goto('/');
        await expect(page).toHaveURL(/\/canvas$/);
    });

    test('falls back to /canvas when config is unavailable', async ({ page }) => {
        await page.route('**/api/config-info', async (route) => {
            await route.abort();
        });

        await page.goto('/');
        await expect(page).toHaveURL(/\/canvas$/);
    });

    test('direct route remains /canvas regardless of configured start page', async ({ page, request }) => {
        const originalConfig = await applyConfigOverrides(request, { start_page: 'entity-list' });

        try {
            await page.goto('/canvas');
            await expect(page).toHaveURL(/\/canvas$/);
        } finally {
            await restoreConfig(request, originalConfig);
        }
    });

    test('direct entity detail route remains unchanged', async ({ page, request }) => {
        const originalConfig = await applyConfigOverrides(request, { start_page: 'entity-list' });

        try {
            await page.goto('/entity-list/dim__region');
            await expect(page).toHaveURL(/\/entity-list\/dim__region$/);
        } finally {
            await restoreConfig(request, originalConfig);
        }
    });
});
