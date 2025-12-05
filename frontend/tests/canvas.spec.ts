import { test, expect } from '@playwright/test';
import { cleanupTestEntities, resetDataModel } from './helpers';

test.describe('Canvas Interactions', () => {
    test.beforeEach(async ({ page, request }) => {
        // Ensure a clean data model before each test run
        await resetDataModel(request);
        await page.goto('/');
    });

    test.afterEach(async ({ page }) => {
        // Cleanup: Delete test entities
        await cleanupTestEntities(page);
        
        // Also delete "Orders" entity if it exists (from this test)
        try {
            const ordersEntity = page.locator('input[value="Orders"]');
            if (await ordersEntity.count() > 0) {
                await page.locator('.svelte-flow__node-entity').filter({ hasText: 'Orders' }).hover();
                const deleteBtn = page.getByRole('button', { name: 'Delete entity' }).first();
                if (await deleteBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
                    await deleteBtn.click();
                    await page.getByRole('button', { name: 'Delete' }).click();
                    await page.waitForTimeout(800);
                }
            }
        } catch (e) {
            // Ignore cleanup errors
        }
    });

    test('create and delete entity', async ({ page }) => {
        // 1. Add Entity
        await page.getByRole('button', { name: 'Add Entity' }).click();

        // Check if new entity appears (default name "New Entity")
        const entity = page.locator('input[value="New Entity"]');
        await expect(entity).toBeVisible();

        // 2. Rename Entity
        await entity.fill('Orders');
        await entity.blur(); // Trigger update

        // Check if ID updated (we can't easily check internal ID, but label should persist)
        await expect(page.locator('input[value="Orders"]')).toBeVisible();

        // 3. Delete Entity
        // Hover to see delete button
        await page.locator('.svelte-flow__node-entity').hover();
        await page.getByRole('button', { name: 'Delete entity' }).click();

        // Confirm modal
        await expect(page.getByText('Are you sure you want to delete this entity?')).toBeVisible();
        await page.getByRole('button', { name: 'Delete' }).click();

        // Verify gone
        await expect(page.locator('input[value="Orders"]')).not.toBeVisible();
    });
});
