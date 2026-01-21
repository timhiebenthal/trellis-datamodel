import { test, expect } from '@playwright/test';

test.describe('Config Reload Flow', () => {
    test('reloads backend config after successful save', async ({ page }) => {
        // Navigate to config page
        await page.goto('/config');

        // Wait for config to load
        await page.waitForSelector('form', { timeout: 5000 });

        // Intercept API calls to verify reload is called
        const reloadCalls: any[] = [];
        const updateCalls: any[] = [];

        await page.route('**/api/config', async (route) => {
            const request = route.request();
            if (request.method() === 'PUT') {
                updateCalls.push({ method: request.method(), url: request.url() });
                // Mock successful update
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        config: { framework: 'dbt-core', modeling_style: 'entity_model' },
                        file_info: { path: '/test/trellis.yml', mtime: Date.now(), hash: 'test-hash' }
                    })
                });
            } else {
                await route.continue();
            }
        });

        await page.route('**/api/config/reload', async (route) => {
            const request = route.request();
            if (request.method() === 'POST') {
                reloadCalls.push({ method: request.method(), url: request.url() });
                // Mock successful reload
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        status: 'success',
                        message: 'Configuration reloaded successfully'
                    })
                });
            } else {
                await route.continue();
            }
        });

        // Find and click the save/apply button
        const applyButton = page.locator('button:has-text("Apply"), button:has-text("Save")').first();
        if (await applyButton.isVisible()) {
            await applyButton.click();

            // Wait for save to complete (check for success toast)
            await page.waitForSelector('text=/Configuration saved and reloaded successfully/i', { timeout: 5000 });

            // Verify updateConfig was called
            expect(updateCalls.length).toBeGreaterThan(0);

            // Verify reloadConfig was called after update
            expect(reloadCalls.length).toBeGreaterThan(0);
        }
    });

    test('shows error toast when reload fails after successful save', async ({ page }) => {
        // Navigate to config page
        await page.goto('/config');

        // Wait for config to load
        await page.waitForSelector('form', { timeout: 5000 });

        // Intercept API calls - update succeeds but reload fails
        await page.route('**/api/config', async (route) => {
            const request = route.request();
            if (request.method() === 'PUT') {
                // Mock successful update
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        config: { framework: 'dbt-core', modeling_style: 'entity_model' },
                        file_info: { path: '/test/trellis.yml', mtime: Date.now(), hash: 'test-hash' }
                    })
                });
            } else {
                await route.continue();
            }
        });

        await page.route('**/api/config/reload', async (route) => {
            const request = route.request();
            if (request.method() === 'POST') {
                // Mock failed reload
                await route.fulfill({
                    status: 500,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        detail: { error: 'internal_error', message: 'Failed to reload config' }
                    })
                });
            } else {
                await route.continue();
            }
        });

        // Find and click the save/apply button
        const applyButton = page.locator('button:has-text("Apply"), button:has-text("Save")').first();
        if (await applyButton.isVisible()) {
            await applyButton.click();

            // Wait for error toast to appear
            await page.waitForSelector('text=/Configuration saved but reload failed/i', { timeout: 5000 });

            // Verify error message is shown
            const errorToast = page.locator('text=/Configuration saved but reload failed/i');
            await expect(errorToast).toBeVisible();
        }
    });
});
