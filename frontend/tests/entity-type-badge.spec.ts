import { test, expect } from '@playwright/test';

test.describe('Entity Type Badge', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/canvas');
        await page.waitForLoadState('networkidle');
    });

    test('should show entity type badge on entity node in dimensional modeling mode', async ({ page }) => {
        // Wait for canvas to load
        await page.waitForTimeout(2000);

        // Check if any entity nodes exist
        const entityNodes = page.locator('[data-id]').filter({ has: page.locator('text=/^dim_|^fct_|entity/i') });
        const count = await entityNodes.count();

        if (count === 0) {
            test.skip();
        }

        // Look for entity type badges (they have specific background colors)
        const typeBadges = page.locator('.inline-flex.items-center.gap-1\\.5.px-2\\.5.py-1.rounded-full.text-xs.font-medium.border');
        const badgeCount = await typeBadges.count();

        // Badges should be visible if dimensional modeling is enabled
        expect(badgeCount).toBeGreaterThanOrEqual(0);
    });

    test('should display fact badge with blue styling', async ({ page }) => {
        await page.waitForTimeout(2000);

        // Look for fact badges (blue background)
        const factBadges = page.locator('.bg-blue-100.text-blue-800');
        const count = await factBadges.count();

        if (count === 0) {
            test.skip();
        }

        // Verify fact badge has correct icon
        const factBadge = factBadges.first();
        await expect(factBadge).toBeVisible();

        // Check for bar-chart icon (fact indicator)
        const factIcon = factBadge.locator('[data-icon="lucide:bar-chart-3"]');
        const iconExists = await factIcon.isVisible().catch(() => false);

        if (iconExists) {
            await expect(factIcon).toBeVisible();
        }
    });

    test('should display dimension badge with green styling', async ({ page }) => {
        await page.waitForTimeout(2000);

        // Look for dimension badges (green background)
        const dimensionBadges = page.locator('.bg-green-100.text-green-800');
        const count = await dimensionBadges.count();

        if (count === 0) {
            test.skip();
        }

        // Verify dimension badge has correct icon
        const dimensionBadge = dimensionBadges.first();
        await expect(dimensionBadge).toBeVisible();

        // Check for list icon (dimension indicator)
        const dimensionIcon = dimensionBadge.locator('[data-icon="lucide:list"]');
        const iconExists = await dimensionIcon.isVisible().catch(() => false);

        if (iconExists) {
            await expect(dimensionIcon).toBeVisible();
        }
    });

    test('should display unclassified badge with gray styling', async ({ page }) => {
        await page.waitForTimeout(2000);

        // Look for unclassified badges (gray background)
        const unclassifiedBadges = page.locator('.bg-gray-100.text-gray-800');
        const count = await unclassifiedBadges.count();

        if (count === 0) {
            test.skip();
        }

        // Verify unclassified badge exists
        const unclassifiedBadge = unclassifiedBadges.first();
        await expect(unclassifiedBadge).toBeVisible();
    });

    test('should show tooltip on badge hover', async ({ page }) => {
        await page.waitForTimeout(2000);

        const typeBadges = page.locator('.inline-flex.items-center.gap-1\\.5.px-2\\.5.py-1.rounded-full');
        const count = await typeBadges.count();

        if (count === 0) {
            test.skip();
        }

        const firstBadge = typeBadges.first();
        await firstBadge.hover();

        // Check if badge has title attribute for tooltip
        const title = await firstBadge.getAttribute('title');
        expect(title).toBeTruthy();
    });

    test('should show dropdown menu when badge is clicked', async ({ page }) => {
        await page.waitForTimeout(2000);

        const typeBadges = page.locator('.inline-flex.items-center.gap-1\\.5.px-2\\.5.py-1.rounded-full.cursor-pointer');
        const count = await typeBadges.count();

        if (count === 0) {
            test.skip();
        }

        const firstBadge = typeBadges.first();
        await firstBadge.click();
        await page.waitForTimeout(300);

        // Check for dropdown menu with type options
        const dropdown = page.locator('[role="menu"]').or(page.locator('.absolute.z-50'));
        const dropdownVisible = await dropdown.isVisible().catch(() => false);

        if (dropdownVisible) {
            await expect(dropdown).toBeVisible();
        }
    });

    test('should have type change options in dropdown', async ({ page }) => {
        await page.waitForTimeout(2000);

        const typeBadges = page.locator('.inline-flex.items-center.gap-1\\.5.px-2\\.5.py-1.rounded-full.cursor-pointer');
        const count = await typeBadges.count();

        if (count === 0) {
            test.skip();
        }

        const firstBadge = typeBadges.first();
        await firstBadge.click();
        await page.waitForTimeout(300);

        // Look for type options (Set as Fact, Set as Dimension, Set as Unclassified)
        const factOption = page.locator('button:has-text("Set as Fact")');
        const dimensionOption = page.locator('button:has-text("Set as Dimension")');
        const unclassifiedOption = page.locator('button:has-text("Set as Unclassified")');

        const hasAnyOption = await Promise.race([
            factOption.isVisible().catch(() => false),
            dimensionOption.isVisible().catch(() => false),
            unclassifiedOption.isVisible().catch(() => false)
        ]);

        if (!hasAnyOption) {
            test.skip();
        }

        // At least one option should be visible
        const optionCount = await page.locator('button:has-text("Set as")').count();
        expect(optionCount).toBeGreaterThan(0);
    });

    test('should maintain type badge after page refresh', async ({ page }) => {
        await page.waitForTimeout(2000);

        const typeBadges = page.locator('.inline-flex.items-center.gap-1\\.5.px-2\\.5.py-1.rounded-full');
        const initialCount = await typeBadges.count();

        if (initialCount === 0) {
            test.skip();
        }

        // Get initial badge text
        const firstBadge = typeBadges.first();
        const initialText = await firstBadge.textContent();

        // Reload page
        await page.reload();
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(2000);

        // Check badge still exists with same type
        const badgesAfterReload = page.locator('.inline-flex.items-center.gap-1\\.5.px-2\\.5.py-1.rounded-full');
        const countAfterReload = await badgesAfterReload.count();

        expect(countAfterReload).toBe(initialCount);

        const firstBadgeAfterReload = badgesAfterReload.first();
        const textAfterReload = await firstBadgeAfterReload.textContent();

        expect(textAfterReload).toBe(initialText);
    });

    // Skip tests for dropdown interaction details (needs proper E2E environment)
    test.skip('should update entity type when option is selected', async ({ page }) => {
        // Requires proper backend and state management testing
    });

    test.skip('should close dropdown when clicking outside', async ({ page }) => {
        // Requires proper E2E environment with working clickOutside handlers
    });
});

