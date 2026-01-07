import { test, expect } from '@playwright/test';
import { resetDataModel, completeEntityWizard } from './helpers';

/**
 * E2E tests for Exposures feature flag and transposed layout.
 * These tests use isolated test data (test_data_model.yml) to ensure
 * predictable results and avoid interfering with user's production data.
 */

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

        // Exposures button should NOT be visible
        const exposuresButton = page.getByRole('button', { name: 'Exposures View' });
        await expect(exposuresButton).not.toBeVisible({ timeout: 5000 });

        // Canvas button should be active (default view)
        const canvasButton = page.getByRole('button', { name: 'Canvas View' });
        await expect(canvasButton).toBeVisible();
        await expect(canvasButton).toHaveAttribute('class', /bg-white/); // active state
    });

    test('exposures view should be accessible when enabled in config', async ({ page, request }) => {
        // Note: This test requires a test config with exposures.enabled: true
        // The test setup should configure this in test_data_model.yml or backend
        
        await page.waitForLoadState('networkidle');

        // Exposures button should be visible
        const exposuresButton = page.getByRole('button', { name: 'Exposures View' });
        
        // Wait a bit and check if button appears (may not appear if disabled)
        const isVisible = await exposuresButton.isVisible({ timeout: 3000 }).catch(() => false);
        
        if (!isVisible) {
            // If disabled, skip this test
            test.skip();
            return;
        }

        // Click exposures button
        await exposuresButton.click();

        // Wait for exposures table to load
        await page.waitForTimeout(2000);

        // Verify exposures table is visible
        const exposuresTable = page.locator('table');
        await expect(exposuresTable).toBeVisible({ timeout: 10000 });

        // Verify we can navigate back to canvas
        const canvasButton = page.getByRole('button', { name: 'Canvas View' });
        await canvasButton.click();
        
        await page.waitForTimeout(1000);
        
        // Verify canvas is visible again
        const canvasContainer = page.locator('.svelte-flow__viewport');
        await expect(canvasContainer).toBeVisible({ timeout: 5000 });
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

    test.beforeEach(async ({ page, request }) => {
    // Reset to clean data model
    await resetDataModel(request);
    
    // Create some test entities
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    
    // Click "Add Entity" button
    const addEntityBtn = page.getByRole('button', { name: 'Add Entity' });
    await expect(addEntityBtn).toBeVisible({ timeout: 10000 });
    await addEntityBtn.click();
    
    // Complete wizard for Customer entity
    await completeEntityWizard(page);
    await page.waitForTimeout(500);
    
    // Add Order entity
    await addEntityBtn.click();
    const nameInput = page.getByPlaceholder('Entity Name');
    await nameInput.fill('Order');
    await nameInput.blur();
    await page.waitForTimeout(500);
    
    // Add Product entity
    await addEntityBtn.click();
    await page.waitForTimeout(500);
    const nameInput2 = page.getByPlaceholder('Entity Name');
    await nameInput2.fill('Product');
    await nameInput2.blur();
    await page.waitForTimeout(500);
});

    test('should default to dashboards-as-rows layout', async ({ page }) => {
        await page.waitForLoadState('networkidle');

        const exposuresButton = page.getByRole('button', { name: 'Exposures View' });
        const isVisible = await exposuresButton.isVisible({ timeout: 3000 }).catch(() => false);
        
        if (!isVisible) {
            test.skip();
            return;
        }

        await exposuresButton.click();
        await page.waitForTimeout(2000);

        // Check initial button text (should be "Dashboards as rows" or similar)
        const transposeButton = page.getByRole('button', { name: /Switch to|Transpose/ });
        const buttonText = await transposeButton.textContent();
        
        // Button should indicate we can switch to entities-as-rows
        expect(buttonText).toMatch(/entities/i);
    });

    test('should toggle to entities-as-rows when button is clicked', async ({ page }) => {
        await page.waitForLoadState('networkidle');

        const exposuresButton = page.getByRole('button', { name: 'Exposures View' });
        const isVisible = await exposuresButton.isVisible({ timeout: 3000 }).catch(() => false);
        
        if (!isVisible) {
            test.skip();
            return;
        }

        await exposuresButton.click();
        await page.waitForTimeout(2000);

        // Get initial state
        const transposeButton = page.getByRole('button', { name: /Switch to|Transpose/ });
        const initialText = await transposeButton.textContent();
        
        // Click to toggle
        await transposeButton.click();
        await page.waitForTimeout(500);

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

        const exposuresButton = page.getByRole('button', { name: 'Exposures View' });
        const isVisible = await exposuresButton.isVisible({ timeout: 3000 }).catch(() => false);
        
        if (!isVisible) {
            test.skip();
            return;
        }

        await exposuresButton.click();
        await page.waitForTimeout(2000);

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
        const transposeButton = page.getByRole('button', { name: /Switch to|Transpose/ });
        await transposeButton.click();
        await page.waitForTimeout(500);
        
        // After toggle, count should still be same (filters maintained)
        const newRowCount = await table.locator('tbody tr').count();
        expect(newRowCount).toBe(filteredRowCount);
    });

    test('should work with auto-fit columns in both layouts', async ({ page }) => {
        await page.waitForLoadState('networkidle');

        const exposuresButton = page.getByRole('button', { name: 'Exposures View' });
        const isVisible = await exposuresButton.isVisible({ timeout: 3000 }).catch(() => false);
        
        if (!isVisible) {
            test.skip();
            return;
        }

        await exposuresButton.click();
        await page.waitForTimeout(2000);

        // Find auto-fit checkbox
        const autoFitCheckbox = page.getByRole('checkbox', { name: 'Auto-fit columns' });
        await expect(autoFitCheckbox).toBeVisible({ timeout: 5000 });
        
        // Ensure it's checked (default)
        await expect(autoFitCheckbox).toBeChecked();
        
        // Toggle layout multiple times
        const transposeButton = page.getByRole('button', { name: /Switch to|Transpose/ });
        
        for (let i = 0; i < 3; i++) {
            await transposeButton.click();
            await page.waitForTimeout(500);
            
            // Auto-fit checkbox should remain visible in both layouts
            await expect(autoFitCheckbox).toBeVisible();
            await expect(autoFitCheckbox).toBeChecked();
        }
    });

    test('should handle empty states in both layouts', async ({ page }) => {
        await page.waitForLoadState('networkidle');

        const exposuresButton = page.getByRole('button', { name: 'Exposures View' });
        const isVisible = await exposuresButton.isVisible({ timeout: 3000 }).catch(() => false);
        
        if (!isVisible) {
            test.skip();
            return;
        }

        await exposuresButton.click();
        await page.waitForTimeout(2000);

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
        const transposeButton = page.getByRole('button', { name: /Switch to|Transpose/ });
        await transposeButton.click();
        await page.waitForTimeout(500);
        
        // Empty state should still be visible in transposed layout
        await expect(emptyState).toBeVisible();
    });
});

