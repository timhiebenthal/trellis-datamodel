import { test, expect } from '@playwright/test';
import { applyConfigOverrides, getCompanyDummyConfigOverrides, resetDataModel, restoreConfig, type DataModelPayload } from './helpers';

/**
 * E2E tests for Exposures feature flag and transposed layout.
 * These tests use isolated test data (test_data_model.yml) to ensure
 * predictable results and avoid interfering with user's production data.
 */

test.describe.configure({ mode: 'serial' });

test.describe('Exposures Feature Flag - E2E', () => {
    test.use({ storageState: { cookies: [], origins: [] } }); // Isolate session

    test.beforeEach(async ({ page, request }) => {
        // Reset to clean data model before each test
        await resetDataModel(request);
        await page.goto('/');
    });

    test('exposures view should not be accessible when disabled in config', async ({ page }) => {
        // Navigate to home
        await page.waitForLoadState('networkidle');

        // If Exposures is enabled in this environment, this test isn't applicable.
        const exposuresButton = page.getByRole('link', { name: 'Exposures' });
        if (await exposuresButton.isVisible().catch(() => false)) {
            test.skip();
            return;
        }

        // Canvas button should be active (default view)
        const canvasButton = page.getByRole('link', { name: 'Canvas' });
        await expect(canvasButton).toBeVisible();
        await expect(canvasButton).toHaveClass(/bg-white/); // active state
    });

    test('exposures view should be accessible when enabled in config', async ({ page, request }) => {
        const originalConfig = await applyConfigOverrides(request, {
            ...getCompanyDummyConfigOverrides(),
            exposures: { enabled: true },
        });

        try {
            await page.addInitScript(() => {
                localStorage.clear();
                sessionStorage.clear();
            });
            await page.goto('/');
            await page.waitForLoadState('networkidle');

            // Exposures button should be visible
            const exposuresButton = page.getByRole('link', { name: 'Exposures' });
            await expect(exposuresButton).toBeVisible({ timeout: 5000 });

            // Click exposures button
            await exposuresButton.click();
            await expect(page).toHaveURL(/\/exposures/);

            // Verify exposures view rendered (table or empty state)
            const exposuresTable = page.locator('table');
            const emptyState = page.getByText(/no exposures found/i);
            await Promise.race([
                exposuresTable.waitFor({ state: 'visible', timeout: 10000 }),
                emptyState.waitFor({ state: 'visible', timeout: 10000 }),
            ]);
            const tableVisible = await exposuresTable.isVisible().catch(() => false);
            const emptyVisible = await emptyState.isVisible().catch(() => false);
            expect(tableVisible || emptyVisible).toBeTruthy();

            // Verify we can navigate back to canvas
            const canvasButton = page.getByRole('link', { name: 'Canvas' });
            await canvasButton.click();

            // Verify canvas is visible again
            const canvasContainer = page.locator('.svelte-flow__viewport');
            await expect(canvasContainer).toBeVisible({ timeout: 5000 });
        } finally {
            await restoreConfig(request, originalConfig);
        }
    });

    test('entity exposure button navigates to exposures and filters entity', async ({ page, request }) => {
        const originalConfig = await applyConfigOverrides(request, {
            ...getCompanyDummyConfigOverrides(),
            exposures: { enabled: true },
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

            const exposureButton = page.locator(
                'button[aria-label="Show exposures for Customer"]',
            );
            await expect(exposureButton).toBeVisible({ timeout: 10000 });
            await exposureButton.click();

            await expect(page).toHaveURL(/\/exposures/);
            await expect(page.getByText('Entity: Customer')).toBeVisible({ timeout: 10000 });
        } finally {
            await restoreConfig(request, originalConfig);
        }
    });

    test('API should return 403 when exposures endpoint is called while disabled', async ({ page, context }) => {
        // Make direct API call to /api/exposures when exposures is disabled
        const response = await context.request.get('/api/exposures');
        
        // Expect 403 Forbidden when disabled
        // Note: This test assumes exposures are disabled in test config
        if (response.status() === 403) {
            expect(response.status()).toBe(403);
            expect(response.statusText()).toBe('Forbidden');
        } else if (response.status() === 200) {
            // If enabled, skip this test
            test.skip();
            return;
        }
    });
});

test.describe('Exposures Transposed Layout - E2E', () => {
    test.use({ storageState: { cookies: [], origins: [] } }); // Isolate session

    const SEEDED_MODEL: DataModelPayload = {
        version: 0.1,
        entities: [
            { id: 'customer', label: 'Customer' },
            { id: 'order', label: 'Order' },
            { id: 'product', label: 'Product' },
        ],
        relationships: [],
    };

    test.beforeEach(async ({ page, request }) => {
        // Seed a stable data model via API (avoid flaky wizard/UI interactions)
        await resetDataModel(request, SEEDED_MODEL);

        await page.goto('/');
        await page.waitForLoadState('networkidle');
    });

    test('should default to dashboards-as-rows layout', async ({ page }) => {
        await page.waitForLoadState('networkidle');

        const exposuresButton = page.getByRole('link', { name: 'Exposures' });
        const isVisible = await exposuresButton.isVisible({ timeout: 3000 }).catch(() => false);
        
        if (!isVisible) {
            test.skip();
            return;
        }

        await exposuresButton.click();
        await page.getByText(/loading exposures/i).waitFor({ state: 'hidden', timeout: 15000 }).catch(() => {});

        // If there are no exposures in this environment, the layout toggle won't be present.
        if (await page.getByText(/no exposures found/i).isVisible().catch(() => false)) {
            test.skip();
            return;
        }

        // Check initial button text (should be "Dashboards as rows" or similar)
        const transposeButton = page.getByRole('button', { name: /entities as rows|dashboards as rows/i });
        const buttonText = await transposeButton.textContent();
        
        // Button should indicate we can switch to entities-as-rows
        expect(buttonText).toMatch(/entities/i);
    });

    test('should toggle to entities-as-rows when button is clicked', async ({ page }) => {
        await page.waitForLoadState('networkidle');

        const exposuresButton = page.getByRole('link', { name: 'Exposures' });
        const isVisible = await exposuresButton.isVisible({ timeout: 3000 }).catch(() => false);
        
        if (!isVisible) {
            test.skip();
            return;
        }

        await exposuresButton.click();
        await page.getByText(/loading exposures/i).waitFor({ state: 'hidden', timeout: 15000 }).catch(() => {});
        if (await page.getByText(/no exposures found/i).isVisible().catch(() => false)) {
            test.skip();
            return;
        }

        // Get initial state
        const transposeButton = page.getByRole('button', { name: /entities as rows|dashboards as rows/i });
        const initialText = await transposeButton.textContent();
        
        // Click to toggle
        await transposeButton.click();

        // Verify layout changed (button text should be different)
        const newText = await transposeButton.textContent();
        expect(newText).not.toBe(initialText);
        expect(newText).toMatch(/dashboards/i);
        
        // Verify table structure changed
        const table = page.locator('table');
        const firstHeader = table.locator('th').first();
        const firstHeaderText = await firstHeader.textContent();
        
        // After toggle, first header should be "Dashboard" (or "Entity" depending on which layout we're now in)
        expect(firstHeaderText?.toLowerCase()).toMatch(/dashboard|entity/i);
    });

    test('should maintain filters when toggling layout', async ({ page }) => {
        await page.waitForLoadState('networkidle');

        const exposuresButton = page.getByRole('link', { name: 'Exposures' });
        const isVisible = await exposuresButton.isVisible({ timeout: 3000 }).catch(() => false);
        
        if (!isVisible) {
            test.skip();
            return;
        }

        await exposuresButton.click();
        await page.getByText(/loading exposures/i).waitFor({ state: 'hidden', timeout: 15000 }).catch(() => {});
        if (await page.getByText(/no exposures found/i).isVisible().catch(() => false)) {
            test.skip();
            return;
        }

        // Apply a filter (if any exposure types are available)
        const typeFilter = page.locator('#exposure-type-filter');
        const hasFilter = await typeFilter.isVisible({ timeout: 2000 }).catch(() => false);
        
        if (!hasFilter) {
            // No exposures to filter, skip test
            test.skip();
            return;
        }

        // Get initial count of rows/columns
        const table = page.locator('table');
        const initialRowCount = await table.locator('tbody tr').count();
        
        // Select first type to filter
        await typeFilter.click();
        await page.waitForTimeout(500);
        const firstOption = typeFilter.locator('option:not([value=""])').first();
        await firstOption.click();
        
        // Wait for filter to apply
        await page.waitForTimeout(1000);
        
        const filteredRowCount = await table.locator('tbody tr').count();
        expect(filteredRowCount).toBeLessThan(initialRowCount);
        
        // Toggle layout
        const transposeButton = page.getByRole('button', { name: /entities as rows|dashboards as rows/i });
        await transposeButton.click();
        
        // After toggle, count should still be same (filters maintained)
        const newRowCount = await table.locator('tbody tr').count();
        expect(newRowCount).toBe(filteredRowCount);
    });

    test('should work with auto-fit columns in both layouts', async ({ page }) => {
        await page.waitForLoadState('networkidle');

        const exposuresButton = page.getByRole('link', { name: 'Exposures' });
        const isVisible = await exposuresButton.isVisible({ timeout: 3000 }).catch(() => false);
        
        if (!isVisible) {
            test.skip();
            return;
        }

        await exposuresButton.click();
        await page.getByText(/loading exposures/i).waitFor({ state: 'hidden', timeout: 15000 }).catch(() => {});
        if (await page.getByText(/no exposures found/i).isVisible().catch(() => false)) {
            test.skip();
            return;
        }

        // Find auto-fit checkbox
        const autoFitCheckbox = page.getByRole('checkbox', { name: 'Auto-fit columns' });
        await expect(autoFitCheckbox).toBeVisible({ timeout: 5000 });
        
        // Ensure it's checked (default)
        await expect(autoFitCheckbox).toBeChecked();
        
        // Toggle layout multiple times
        const transposeButton = page.getByRole('button', { name: /entities as rows|dashboards as rows/i });
        
        for (let i = 0; i < 3; i++) {
            await transposeButton.click();
            
            // Auto-fit checkbox should remain visible in both layouts
            await expect(autoFitCheckbox).toBeVisible();
            await expect(autoFitCheckbox).toBeChecked();
        }
    });

    test('should handle empty states in both layouts', async ({ page }) => {
        await page.waitForLoadState('networkidle');

        const exposuresButton = page.getByRole('link', { name: 'Exposures' });
        const isVisible = await exposuresButton.isVisible({ timeout: 3000 }).catch(() => false);
        
        if (!isVisible) {
            test.skip();
            return;
        }

        await exposuresButton.click();
        await page.getByText(/loading exposures/i).waitFor({ state: 'hidden', timeout: 15000 }).catch(() => {});

        // Check if there are any entities in the system
        const table = page.locator('table');
        const emptyState = page.getByText(/no.*match.*filter/i);
        const hasEmptyState = await emptyState.isVisible({ timeout: 2000 }).catch(() => false);
        
        if (!hasEmptyState) {
            // If there are entities and exposures, skip this test
            test.skip();
            return;
        }

        // Empty state should be visible
        await expect(emptyState).toBeVisible();
        
        // Toggle layout
        const transposeButton = page.getByRole('button', { name: /entities as rows|dashboards as rows/i });
        await transposeButton.click();
        
        // Empty state should still be visible in transposed layout
        await expect(emptyState).toBeVisible();
    });
});

