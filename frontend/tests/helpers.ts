import type { Page } from '@playwright/test';

/**
 * Save the current data model state
 */
export async function saveDataModelState(page: Page): Promise<any> {
    return await page.evaluate(async () => {
        const response = await fetch('/api/data-model');
        return await response.json();
    });
}

/**
 * Restore a saved data model state
 */
export async function restoreDataModelState(page: Page, state: any): Promise<void> {
    await page.evaluate(async (dataModel) => {
        await fetch('/api/data-model', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(dataModel)
        });
    }, state);
    
    // Reload page to reflect restored state
    await page.reload();
    await page.waitForLoadState('networkidle');
}

/**
 * Delete all entities with "New Entity" as the default name (test entities)
 */
export async function cleanupTestEntities(page: Page): Promise<void> {
    try {
        // Wait a bit for any pending saves
        await page.waitForTimeout(1500);
        
        const entities = page.locator('.svelte-flow__node-entity');
        const count = await entities.count();
        
        // Delete in reverse order to avoid index shifting
        for (let i = count - 1; i >= 0; i--) {
            const entity = entities.nth(i);
            const input = entity.locator('input[value="New Entity"]');
            
            if (await input.count() > 0) {
                await entity.hover();
                const deleteBtn = page.getByRole('button', { name: 'Delete entity' }).first();
                if (await deleteBtn.isVisible({ timeout: 1000 }).catch(() => false)) {
                    await deleteBtn.click();
                    await page.getByRole('button', { name: 'Delete' }).click();
                    await page.waitForTimeout(800); // Wait for deletion and save
                }
            }
        }
    } catch (e) {
        // Ignore cleanup errors - tests should still pass
        console.log('Cleanup warning (non-fatal):', e);
    }
}

