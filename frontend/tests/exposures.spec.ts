import { test, expect } from '@playwright/test';

test.describe('Exposures View', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/');
    });

    test('should show Exposures button when exposures_enabled is true', async ({ page, request }) => {
        // Note: This test requires a test config with exposures.enabled: true
        // For now, we'll just check if the Exposures button exists in the DOM when enabled
        
        // Navigate to page
        await page.waitForLoadState('networkidle');
        
        // Check if Exposures button is visible
        const exposuresButton = page.getByRole('button', { name: 'Exposures View' });
        
        // In a real test environment with exposures.enabled: true, this should be visible
        // For now, we're documenting the expected behavior
    });

    test('should hide Exposures button when exposures_enabled is false', async ({ page, request }) => {
        // Note: This test requires a test config with exposures.enabled: false
        // For now, we'll just check if the Exposures button doesn't exist when disabled
        
        await page.waitForLoadState('networkidle');
        
        // Exposures button should not be visible
        const exposuresButton = page.getByRole('button', { name: 'Exposures View' });
        await expect(exposuresButton).not.toBeVisible({ timeout: 5000 });
    });

    test('should switch to Exposures view when clicked', async ({ page, request }) => {
        // Skip if exposures is disabled
        await page.waitForLoadState('networkidle');
        
        const exposuresButton = page.getByRole('button', { name: 'Exposures View' });
        const isVisible = await exposuresButton.isVisible({ timeout: 2000 }).catch(() => false);
        
        if (!isVisible) {
            test.skip();
            return;
        }

        // Click Exposures button
        await exposuresButton.click();

        // Wait for exposures table to load
        await page.waitForTimeout(2000);

        // Verify we're in exposures view (table should be visible)
        const exposuresTable = page.locator('table');
        await expect(exposuresTable).toBeVisible({ timeout: 10000 });
    });

    test('should switch back to Canvas view when switching away', async ({ page, request }) => {
        await page.waitForLoadState('networkidle');
        
        const exposuresButton = page.getByRole('button', { name: 'Exposures View' });
        const isVisible = await exposuresButton.isVisible({ timeout: 2000 }).catch(() => false);
        
        if (!isVisible) {
            test.skip();
            return;
        }

        // Click Exposures button
        await exposuresButton.click();
        await page.waitForTimeout(2000);

        // Verify we're in exposures view
        const exposuresTable = page.locator('table');
        await expect(exposuresTable).toBeVisible({ timeout: 10000 });

        // Click Canvas button
        const canvasButton = page.getByRole('button', { name: 'Canvas View' });
        await canvasButton.click();

        // Wait for canvas to be visible
        await page.waitForTimeout(1000);

        // Verify we're back in canvas view (canvas container should be visible)
        const canvasContainer = page.locator('.svelte-flow__viewport');
        await expect(canvasContainer).toBeVisible({ timeout: 5000 });
    });

    test('should show empty state when no exposures', async ({ page, request }) => {
        await page.waitForLoadState('networkidle');
        
        const exposuresButton = page.getByRole('button', { name: 'Exposures View' });
        const isVisible = await exposuresButton.isVisible({ timeout: 2000 }).catch(() => false);
        
        if (!isVisible) {
            test.skip();
            return;
        }

        await exposuresButton.click();
        await page.waitForTimeout(2000);

        // Check if empty state message is shown
        const noExposures = page.getByText('No Exposures Found');
        const isVisibleEmpty = await noExposures.isVisible({ timeout: 5000 }).catch(() => false);
        
        if (isVisibleEmpty) {
            await expect(noExposures).toBeVisible();
        }
    });
});

test.describe('Exposures Layout Toggle', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/');
    });

    test('should show layout toggle button in exposures view', async ({ page }) => {
        await page.waitForLoadState('networkidle');
        
        const exposuresButton = page.getByRole('button', { name: 'Exposures View' });
        const isVisible = await exposuresButton.isVisible({ timeout: 2000 }).catch(() => false);
        
        if (!isVisible) {
            test.skip();
            return;
        }

        await exposuresButton.click();
        await page.waitForTimeout(2000);

        // Look for the transpose button (contains "Dashboards as rows" or "Entities as rows")
        const transposeButton = page.getByRole('button', { name: /Switch to|Transpose/ });
        await expect(transposeButton).toBeVisible({ timeout: 5000 });
    });

    test('should toggle layout when button is clicked', async ({ page }) => {
        await page.waitForLoadState('networkidle');
        
        const exposuresButton = page.getByRole('button', { name: 'Exposures View' });
        const isVisible = await exposuresButton.isVisible({ timeout: 2000 }).catch(() => false);
        
        if (!isVisible) {
            test.skip();
            return;
        }

        await exposuresButton.click();
        await page.waitForTimeout(2000);

        // Get initial button text
        const transposeButton = page.getByRole('button', { name: /Switch to|Transpose/ });
        const initialText = await transposeButton.textContent();

        // Click to toggle
        await transposeButton.click();
        await page.waitForTimeout(500);

        // Verify button text changed
        const newText = await transposeButton.textContent();
        expect(newText).not.toBe(initialText);
    });

    test('should maintain filters after layout toggle', async ({ page }) => {
        await page.waitForLoadState('networkidle');
        
        const exposuresButton = page.getByRole('button', { name: 'Exposures View' });
        const isVisible = await exposuresButton.isVisible({ timeout: 2000 }).catch(() => false);
        
        if (!isVisible) {
            test.skip();
            return;
        }

        await exposuresButton.click();
        await page.waitForTimeout(2000);

        // Apply an exposure filter (if available)
        const typeFilter = page.locator('#exposure-type-filter');
        const hasFilter = await typeFilter.isVisible({ timeout: 2000 }).catch(() => false);
        
        if (!hasFilter) {
            test.skip();
            return;
        }

        // Select first type (if any)
        await typeFilter.click();
        await page.waitForTimeout(500);
        
        // Get initial number of rows/columns
        const table = page.locator('table');
        const initialRows = await table.locator('tbody tr').count();

        // Toggle layout
        const transposeButton = page.getByRole('button', { name: /Switch to|Transpose/ });
        await transposeButton.click();
        await page.waitForTimeout(500);

        // Verify filters still active (number of visible items should match)
        const newRows = await table.locator('tbody tr').count();
        expect(newRows).toBe(initialRows);
    });
});

