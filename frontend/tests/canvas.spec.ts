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
        const addEntityBtn = page.getByRole('button', { name: 'Add Entity' });
        await expect(addEntityBtn).toBeVisible({ timeout: 10000 });
        await addEntityBtn.click();

        // Check if new entity appears (default name "New Entity")
        const entity = page.getByPlaceholder('Entity Name').first();
        await expect(entity).toBeVisible({ timeout: 10000 });

        // 2. Rename Entity
        await entity.fill('Orders');
        await entity.blur(); // Trigger update

        // Check if ID updated (we can't easily check internal ID, but label should persist)
        await expect(entity).toHaveValue('Orders');

        // 3. Delete Entity
        // Hover to see delete button
        await page.locator('.svelte-flow__node-entity').hover();
        await page.getByRole('button', { name: 'Delete entity Orders', exact: true }).click();

        // Confirm modal
        await expect(page.getByRole('dialog', { name: /delete entity/i })).toBeVisible();
        await page.getByRole('dialog', { name: /delete entity/i }).getByRole('button', { name: 'Delete' }).click();

        // Verify gone
        await expect(entity).not.toBeVisible();
    });

    test('expand/collapse all entities toggle', async ({ page }) => {
        // 1. Create multiple entities
        const addEntityBtn = page.getByRole('button', { name: 'Add Entity' });
        await expect(addEntityBtn).toBeVisible({ timeout: 10000 });
        
        // Create first entity
        await addEntityBtn.click();
        await page.waitForTimeout(500);
        
        // Create second entity
        await addEntityBtn.click();
        await page.waitForTimeout(500);

        // Wait for entities to be visible
        const entities = page.locator('.svelte-flow__node-entity');
        await expect(entities).toHaveCount(2, { timeout: 5000 });

        // 2. Verify entities are expanded by default (we can see the content area)
        // Check that at least one entity has visible content (not collapsed)
        const firstEntity = entities.first();
        // Check for the collapse tooltip or chevron-down icon (expanded state)
        const collapsedIndicator = firstEntity.locator('[title*="collapse"], [title*="Collapse"]');
        await expect(collapsedIndicator.first()).toBeVisible({ timeout: 2000 });

        // 3. Click collapse all button (now in the top bar)
        const collapseAllBtn = page.getByRole('button', { name: 'Collapse All' });
        await expect(collapseAllBtn).toBeVisible({ timeout: 5000 });
        await collapseAllBtn.click();
        await page.waitForTimeout(500);

        // 4. Verify all entities are collapsed
        // Check that entities show "Click to expand" tooltip (collapsed state)
        for (let i = 0; i < 2; i++) {
            const entity = entities.nth(i);
            const expandIndicator = entity.locator('[title*="expand"], [title*="Expand"]');
            const isCollapsed = await expandIndicator.isVisible({ timeout: 1000 }).catch(() => false);
            expect(isCollapsed).toBeTruthy();
        }

        // 5. Verify button text changed to "Expand All"
        const expandAllBtn = page.getByRole('button', { name: 'Expand All' });
        await expect(expandAllBtn).toBeVisible({ timeout: 2000 });

        // 6. Click expand all button
        await expandAllBtn.click();
        await page.waitForTimeout(500);

        // 7. Verify all entities are expanded again
        for (let i = 0; i < 2; i++) {
            const entity = entities.nth(i);
            const collapseIndicator = entity.locator('[title*="collapse"], [title*="Collapse"]');
            const isExpanded = await collapseIndicator.isVisible({ timeout: 1000 }).catch(() => false);
            expect(isExpanded).toBeTruthy();
        }

        // Wait for save to finish before reload to ensure state is persisted on backend
        await expect(page.getByText('Saving...')).not.toBeVisible({ timeout: 5000 });

        // 8. Reload page and verify state persisted (should be expanded)
        await page.reload();
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(1000); // Wait for state to be applied

        const entitiesAfterReload = page.locator('.svelte-flow__node-entity');
        await expect(entitiesAfterReload).toHaveCount(2, { timeout: 5000 });

        // Verify entities are expanded (last state was expanded)
        const firstEntityAfterReload = entitiesAfterReload.first();
        const collapseIndicatorAfterReload = firstEntityAfterReload.locator('[title*="collapse"], [title*="Collapse"]');
        const isExpandedAfterReload = await collapseIndicatorAfterReload.isVisible({ timeout: 2000 }).catch(() => false);
        expect(isExpandedAfterReload).toBeTruthy();

        // Verify button shows "Collapse All" (since state was expanded)
        const collapseAllBtnAfterReload = page.getByRole('button', { name: 'Collapse All' });
        await expect(collapseAllBtnAfterReload).toBeVisible({ timeout: 5000 });
    });
});
