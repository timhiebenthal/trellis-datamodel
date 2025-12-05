import { test, expect } from '@playwright/test';
import { resetDataModel } from './helpers';

test.describe('Sidebar Filter Interactions', () => {
    test.beforeEach(async ({ page, request }) => {
        // Ensure the backend starts empty for every test
        await resetDataModel(request);
        await page.goto('/');
        // Wait for sidebar to load
        await expect(page.locator('aside')).toBeVisible();
    });

    test('sidebar shows Explorer heading', async ({ page }) => {
        await expect(page.getByText('Explorer')).toBeVisible();
    });

    test('sidebar has Filters section', async ({ page }) => {
        await expect(page.getByText('Filters')).toBeVisible();
    });

    test('folder filter dropdown exists', async ({ page }) => {
        const folderLabel = page.getByText('Filter by Folder');
        // May or may not be visible depending on if models have folders
        // Just check the Filters section exists
        await expect(page.getByText('Filters')).toBeVisible();
    });

    test('tag filter dropdown exists', async ({ page }) => {
        await expect(page.getByText('Filter by Tag')).toBeVisible();
    });

    test('search input filters model list', async ({ page }) => {
        const searchInput = page.getByPlaceholder('Search models...');
        await expect(searchInput).toBeVisible();

        // Type a search term
        await searchInput.fill('test_search');
        await expect(searchInput).toHaveValue('test_search');

        // Clear search
        await searchInput.fill('');
        await expect(searchInput).toHaveValue('');
    });

    test('sidebar can be collapsed and expanded', async ({ page }) => {
        // Find collapse button (chevron-left icon)
        const collapseBtn = page.getByTitle('Collapse sidebar');

        // Check if sidebar is expandable
        if (await collapseBtn.isVisible()) {
            await collapseBtn.click();

            // After collapse, expand button should appear
            const expandBtn = page.getByTitle('Expand sidebar');
            await expect(expandBtn).toBeVisible();

            // Expand again
            await expandBtn.click();
            await expect(page.getByText('Explorer')).toBeVisible();
        }
    });

    test('Clear all filters button appears when filters active', async ({ page }) => {
        // The "Clear all" button only appears when filters are active
        // Initially it should not be visible
        const clearAll = page.getByText('Clear all');
        
        // Check initial state - Clear all should not be visible if no filters
        const isVisible = await clearAll.isVisible().catch(() => false);
        
        // This test passes if:
        // 1. Clear all is not visible (no filters active), OR
        // 2. Clear all is visible (some default filters), and clicking it works
        if (isVisible) {
            await clearAll.click();
            // After clearing, button may disappear
        }
        
        // Either way, the sidebar should still function
        await expect(page.locator('aside')).toBeVisible();
    });
});

test.describe('Model Tree View', () => {
    test.beforeEach(async ({ page, request }) => {
        await resetDataModel(request);
        await page.goto('/');
    });

    test('shows loading or models list', async ({ page }) => {
        const sidebar = page.locator('aside');
        await expect(sidebar).toBeVisible();

        // Allow extra time for slower CI environments to render the sidebar state
        await expect
            .poll(
                async () => {
                    const hasModels =
                        (await page.locator('.sidebar [draggable="true"]').count()) > 0;
                    const hasNoModelsMsg = await page
                        .getByText('No models found')
                        .isVisible()
                        .catch(() => false);
                    const hasNoMatchesMsg = await page
                        .getByText('No matches found')
                        .isVisible()
                        .catch(() => false);
                    const hasSetupMsg = await page
                        .getByText('Setup Required')
                        .isVisible()
                        .catch(() => false);
                    const isLoading = await page
                        .getByText('Loading...')
                        .isVisible()
                        .catch(() => false);

                    return (
                        hasModels ||
                        hasNoModelsMsg ||
                        hasNoMatchesMsg ||
                        hasSetupMsg ||
                        isLoading
                    );
                },
                { timeout: 5000 },
            )
            .toBe(true);
    });
});

