import { test, expect } from '@playwright/test';
import { cleanupTestEntities, resetDataModel, completeEntityWizard } from './helpers';

test.describe('Auto Layout', () => {
    test.beforeEach(async ({ page, request }) => {
        // Collect console errors
        const consoleErrors: string[] = [];
        page.on('console', (msg) => {
            if (msg.type() === 'error') {
                consoleErrors.push(msg.text());
            }
        });

        // Start every test with a clean data model
        await resetDataModel(request);
        await page.goto('/');
        
        // Wait for app to load
        await expect(page.locator('aside')).toBeVisible({ timeout: 10000 });
        
        // Clear any initial errors
        consoleErrors.length = 0;
    });

    test.afterEach(async ({ page }) => {
        // Cleanup: Delete test entities created during tests
        await cleanupTestEntities(page);
    });

    test('Auto Layout button applies layout without errors', async ({ page }) => {
        const consoleErrors: string[] = [];
        page.on('console', (msg) => {
            if (msg.type() === 'error') {
                consoleErrors.push(msg.text());
            }
        });

        // Get initial entity count
        const initialCount = await page.locator('.svelte-flow__node-entity').count();

        // Create at least one entity if none exist
        if (initialCount === 0) {
            const addEntityBtn = page.getByRole('button', { name: 'Add Entity' });
            await expect(addEntityBtn).toBeVisible({ timeout: 10000 });
            await addEntityBtn.click();
            await completeEntityWizard(page);
            await expect(page.getByPlaceholder('Entity Name').first()).toBeVisible({ timeout: 10000 });
        }

        // Click Auto Layout button
        const autoLayoutButton = page.getByRole('button', { name: 'Auto Layout' });
        await expect(autoLayoutButton).toBeVisible();
        
        // Clear errors before clicking
        consoleErrors.length = 0;
        
        await autoLayoutButton.click();

        // Wait a moment for layout to apply
        await page.waitForTimeout(1500);

        // Check for dagre-related errors
        const dagreErrors = consoleErrors.filter(
            (err) => 
                err.includes('dagre') || 
                err.includes('graphlib') ||
                err.includes('Dynamic require') ||
                err.includes('Failed to load dagre') ||
                err.includes('Failed to resolve module')
        );

        expect(dagreErrors, 'No dagre-related errors when clicking Auto Layout').toHaveLength(0);

        // Verify entities still exist (layout didn't crash)
        const finalCount = await page.locator('.svelte-flow__node-entity').count();
        expect(finalCount).toBeGreaterThan(0);
    });

    test('Auto Layout works with multiple entities', async ({ page }) => {
        const consoleErrors: string[] = [];
        page.on('console', (msg) => {
            if (msg.type() === 'error') {
                consoleErrors.push(msg.text());
            }
        });

        // Get initial count
        const initialCount = await page.locator('.svelte-flow__node-entity').count();
        
        // Create entities to reach at least 3 total
        const addEntityBtn = page.getByRole('button', { name: 'Add Entity' });
        await expect(addEntityBtn).toBeVisible({ timeout: 10000 });
        const entitiesToAdd = Math.max(0, 3 - initialCount);
        for (let i = 0; i < entitiesToAdd; i++) {
            await addEntityBtn.click();
            await completeEntityWizard(page);
            await page.waitForTimeout(200); // Small delay between clicks
        }

        const totalCount = await page.locator('.svelte-flow__node-entity').count();
        expect(totalCount).toBeGreaterThanOrEqual(3);

        // Click Auto Layout
        consoleErrors.length = 0;
        await page.getByRole('button', { name: 'Auto Layout' }).click();
        await page.waitForTimeout(1500);

        // Check for errors
        const criticalErrors = consoleErrors.filter(
            (err) => 
                err.includes('dagre') || 
                err.includes('graphlib') ||
                err.includes('Dynamic require') ||
                err.includes('Failed to load') ||
                err.includes('Failed to resolve')
        );

        expect(criticalErrors, 'No layout errors with multiple entities').toHaveLength(0);

        // Verify entities still exist
        const finalCount = await page.locator('.svelte-flow__node-entity').count();
        expect(finalCount).toBeGreaterThanOrEqual(3);
    });
});

