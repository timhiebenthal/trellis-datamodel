import { test, expect } from '@playwright/test';
import { applyConfigOverrides, restoreConfig } from './helpers';

test.describe.configure({ mode: 'serial' });

test.describe('Canvas configuration controls', () => {
    test('renders configured values and supports adding and removing defaults', async ({ page, request }) => {
        const originalConfig = await applyConfigOverrides(request, {
            start_page: 'entity-list',
            canvas: {
                default_filters: {
                    domains: ['sales'],
                    tags: ['important'],
                },
            },
        });

        try {
            await page.goto('/config');

            await expect(page.getByLabel('Start Page')).toHaveValue('entity-list');
            await expect(page.getByLabel('Canvas Default Domain 1')).toHaveValue('sales');
            await expect(page.getByLabel('Canvas Default Tag 1')).toHaveValue('important');

            await page.getByRole('button', { name: 'Add Domain' }).click();
            await expect(page.getByLabel('Canvas Default Domain 2')).toBeVisible();
            await page.getByLabel('Canvas Default Domain 2').fill('finance');

            await page.getByRole('button', { name: 'Remove Domain 1' }).click();
            await expect(page.getByLabel('Canvas Default Domain 1')).toHaveValue('finance');

            await page.getByRole('button', { name: 'Add Tag' }).click();
            await expect(page.getByLabel('Canvas Default Tag 2')).toBeVisible();
            await page.getByLabel('Canvas Default Tag 2').fill('trusted');

            await page.getByRole('button', { name: 'Remove Tag 1' }).click();
            await expect(page.getByLabel('Canvas Default Tag 1')).toHaveValue('trusted');
        } finally {
            await restoreConfig(request, originalConfig);
        }
    });

    test('applies nested Canvas defaults and reloads configuration', async ({ page, request }) => {
        const originalConfig = await applyConfigOverrides(request, {
            start_page: 'canvas',
            canvas: {
                default_filters: {
                    domains: [],
                    tags: [],
                },
            },
        });

        try {
            await page.goto('/config');
            await page.getByLabel('Start Page').selectOption('entity-list');
            await page.getByRole('button', { name: 'Add Domain' }).click();
            await page.getByLabel('Canvas Default Domain 1').fill('operations');
            await page.getByRole('button', { name: 'Add Tag' }).click();
            await page.getByLabel('Canvas Default Tag 1').fill('certified');

            let submittedConfig: Record<string, any> | undefined;
            let reloadCalls = 0;

            await page.route('**/api/config', async (route) => {
                if (route.request().method() !== 'PUT') {
                    await route.continue();
                    return;
                }

                const body = route.request().postDataJSON();
                submittedConfig = body.config;
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        config: submittedConfig,
                        file_info: {
                            path: '/test/trellis.yml',
                            mtime: Date.now(),
                            hash: 'test-hash',
                        },
                    }),
                });
            });

            await page.route('**/api/config/reload', async (route) => {
                reloadCalls += 1;
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({ status: 'success' }),
                });
            });

            await page.getByRole('button', { name: 'Apply Configuration' }).click();
            await expect(page.getByText('Configuration saved and reloaded successfully')).toBeVisible();

            expect(submittedConfig).toMatchObject({
                start_page: 'entity-list',
                canvas: {
                    default_filters: {
                        domains: ['operations'],
                        tags: ['certified'],
                    },
                },
            });
            expect(reloadCalls).toBe(1);
        } finally {
            await restoreConfig(request, originalConfig);
        }
    });
});
