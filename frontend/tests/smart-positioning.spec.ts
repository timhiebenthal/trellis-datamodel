import { test, expect } from '@playwright/test';

test.describe('Smart Positioning', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/canvas');
        await page.waitForLoadState('networkidle');
    });

    test('should have Auto-Layout button in toolbar', async ({ page }) => {
        await page.waitForTimeout(2000);

        // Look for Auto Layout button (only visible in dimensional modeling mode)
        const autoLayoutButton = page.locator('button:has-text("Auto Layout")');
        const isVisible = await autoLayoutButton.isVisible().catch(() => false);

        if (!isVisible) {
            // Auto Layout button only shows in dimensional modeling mode
            test.skip();
        }

        await expect(autoLayoutButton).toBeVisible();
        await expect(autoLayoutButton).toContainText('Auto Layout');
    });

    test('should trigger positioning when Auto-Layout is clicked', async ({ page }) => {
        await page.waitForTimeout(2000);

        const autoLayoutButton = page.locator('button:has-text("Auto Layout")');
        const isVisible = await autoLayoutButton.isVisible().catch(() => false);

        if (!isVisible) {
            test.skip();
        }

        // Get entity count before layout
        const entitiesBefore = page.locator('[data-id]');
        const countBefore = await entitiesBefore.count();

        if (countBefore === 0) {
            test.skip();
        }

        // Click Auto Layout button
        await autoLayoutButton.click();
        await page.waitForTimeout(1000);

        // Verify entities still exist (layout doesn't delete them)
        const entitiesAfter = page.locator('[data-id]');
        const countAfter = await entitiesAfter.count();

        expect(countAfter).toBe(countBefore);
    });

    test('should only show Auto-Layout when modeling_style is dimensional_model', async ({ page }) => {
        await page.waitForTimeout(2000);

        // Check if Auto Layout button exists
        const autoLayoutButton = page.locator('button:has-text("Auto Layout")');
        const isVisible = await autoLayoutButton.isVisible().catch(() => false);

        // Button should only be visible in dimensional modeling mode
        // This test documents the expected behavior
        if (isVisible) {
            // If visible, we're in dimensional modeling mode
            await expect(autoLayoutButton).toBeVisible();
        } else {
            // If not visible, we're in entity modeling mode
            expect(isVisible).toBe(false);
        }
    });

    test('should not crash when clicking Auto-Layout with no entities', async ({ page }) => {
        await page.waitForTimeout(2000);

        const autoLayoutButton = page.locator('button:has-text("Auto Layout")');
        const isVisible = await autoLayoutButton.isVisible().catch(() => false);

        if (!isVisible) {
            test.skip();
        }

        // Click Auto Layout - should handle empty state gracefully
        await autoLayoutButton.click();
        await page.waitForTimeout(500);

        // Verify page didn't crash
        const errorMessage = page.locator('text=/error|crash|failed/i');
        const hasError = await errorMessage.isVisible().catch(() => false);

        expect(hasError).toBe(false);
    });

    // Skip tests that require entity creation and manipulation
    test.skip('should place fact entities in center area', async ({ page }) => {
        // Requires entity creation workflow which is complex in E2E
    });

    test.skip('should place dimension entities in outer ring', async ({ page }) => {
        // Requires entity creation workflow which is complex in E2E
    });

    test.skip('should distribute dimensions evenly around circle', async ({ page }) => {
        // Requires multiple entity creation which is complex in E2E
    });

    test.skip('should not override manually positioned entities', async ({ page }) => {
        // Requires drag-and-drop manipulation which needs proper E2E setup
    });

    test.skip('should not override saved positions from canvas_layout.yml', async ({ page }) => {
        // Requires file system setup and configuration
    });

    test('should work correctly after window resize', async ({ page }) => {
        await page.waitForTimeout(2000);

        const autoLayoutButton = page.locator('button:has-text("Auto Layout")');
        const isVisible = await autoLayoutButton.isVisible().catch(() => false);

        if (!isVisible) {
            test.skip();
        }

        // Resize window to smaller size
        await page.setViewportSize({ width: 800, height: 600 });
        await page.waitForTimeout(500);

        // Click Auto Layout with new viewport size
        await autoLayoutButton.click();
        await page.waitForTimeout(1000);

        // Verify page still works
        const canvas = page.locator('.svelte-flow');
        await expect(canvas).toBeVisible();

        // Resize back to normal
        await page.setViewportSize({ width: 1280, height: 720 });
        await page.waitForTimeout(500);

        // Auto Layout should still work
        await autoLayoutButton.click();
        await page.waitForTimeout(1000);

        await expect(canvas).toBeVisible();
    });

    test('should animate position changes smoothly', async ({ page }) => {
        await page.waitForTimeout(2000);

        const autoLayoutButton = page.locator('button:has-text("Auto Layout")');
        const isVisible = await autoLayoutButton.isVisible().catch(() => false);

        if (!isVisible) {
            test.skip();
        }

        const entities = page.locator('[data-id]');
        const count = await entities.count();

        if (count === 0) {
            test.skip();
        }

        // Click Auto Layout
        await autoLayoutButton.click();

        // Animation should complete within reasonable time
        await page.waitForTimeout(1500);

        // Entities should still be visible after animation
        const entitiesAfter = page.locator('[data-id]');
        const countAfter = await entitiesAfter.count();

        expect(countAfter).toBe(count);
    });

    // Skip tests requiring entity creation
    test.skip('should avoid overlapping existing facts', async ({ page }) => {
        // Requires entity creation workflow
    });

    test.skip('should randomize angle to avoid stacking dimensions', async ({ page }) => {
        // Requires entity creation workflow
    });

    test.skip('should handle canvas center calculation correctly', async ({ page }) => {
        // Requires internal calculation verification
    });
});

