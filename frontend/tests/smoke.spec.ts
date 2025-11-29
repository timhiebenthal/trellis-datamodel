import { test, expect } from '@playwright/test';

test('smoke test', async ({ page }) => {
    await page.goto('/');

    // Check title
    await expect(page).toHaveTitle(/Data Model UI/);

    // Check sidebar exists
    await expect(page.locator('aside')).toBeVisible();

    // Check canvas exists
    await expect(page.locator('.svelte-flow')).toBeVisible();
});
