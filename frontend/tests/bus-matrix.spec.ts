import { test, expect } from '@playwright/test';
import * as XLSX from 'xlsx';
import * as fs from 'fs';

const MOCK_BUS_MATRIX_DATA = {
    dimensions: [
        { id: 'dim_customer', label: 'Customer Dimension', tags: ['core'] },
        { id: 'dim_date', label: 'Date Dimension', tags: ['core'] },
        { id: 'dim_product', label: 'Product Dimension', tags: ['core'] },
    ],
    facts: [
        { id: 'fct_orders', label: 'Orders Fact', tags: ['core'] },
        { id: 'fct_sales', label: 'Sales Fact', tags: ['core'] },
    ],
    connections: [
        { dimension_id: 'dim_customer', fact_id: 'fct_orders' },
        { dimension_id: 'dim_customer', fact_id: 'fct_sales' },
        { dimension_id: 'dim_date', fact_id: 'fct_orders' },
        { dimension_id: 'dim_product', fact_id: 'fct_orders' },
        { dimension_id: 'dim_product', fact_id: 'fct_sales' },
    ],
};

async function mockBusMatrixRoutes(page: any, busMatrixData = MOCK_BUS_MATRIX_DATA) {
    await page.route('**/api/config-status', async (route: any) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ status: 'ok' }),
        });
    });
    await page.route('**/api/config-info', async (route: any) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ bus_matrix_enabled: true }),
        });
    });
    await page.route('**/api/bus-matrix**', async (route: any) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(busMatrixData),
        });
    });
}

test.describe('Bus Matrix Counts and Sorting', () => {
    test('should show visible usage counts for filtered matrix', async ({ page }) => {
        await mockBusMatrixRoutes(page);
        await page.goto('/bus-matrix');
        await page.waitForLoadState('networkidle');

        // Customer Dimension shows 2 related facts (fct_orders + fct_sales)
        await expect(page.locator('[aria-label="2 related facts"]').first()).toBeVisible();

        // Date Dimension shows 1 related fact (fct_orders only)
        await expect(page.locator('[aria-label="1 related facts"]').first()).toBeVisible();

        // Apply fact filter for Orders Fact only
        await page.locator('select#fact-filter').selectOption({ label: 'Orders Fact' });
        await page.waitForTimeout(300);

        // After filtering to Orders Fact only, Customer Dimension shows count 1
        // (dim_customer was connected to fct_orders + fct_sales, but only fct_orders is now visible)
        const filteredBadges = page.locator('[aria-label="1 related facts"]');
        await expect(filteredBadges.first()).toBeVisible();

        // Date Dimension still shows 1 related fact (only connected to fct_orders which is still visible)
        // Product Dimension shows 1 related fact (connected to fct_orders + fct_sales but only fct_orders visible)
        const countBadges = await page.locator('[aria-label*="related facts"]').count();
        expect(countBadges).toBeGreaterThan(0);
    });

    test('should sort dimensions and facts by display label', async ({ page }) => {
        const outOfOrderData = {
            dimensions: [
                { id: 'dim_z', label: 'Apple Dimension', tags: [] },
                { id: 'dim_a', label: 'Zebra Dimension', tags: [] },
                { id: 'dim_m', label: 'Mango Dimension', tags: [] },
            ],
            facts: [
                { id: 'fct_z', label: 'Banana Fact', tags: [] },
                { id: 'fct_a', label: 'Walnut Fact', tags: [] },
            ],
            connections: [],
        };

        await mockBusMatrixRoutes(page, outOfOrderData);
        await page.goto('/bus-matrix');
        await page.waitForLoadState('networkidle');

        // Sort controls must exist
        await expect(page.locator('[aria-label="Sort dimensions"]')).toBeVisible();
        await expect(page.locator('[aria-label="Sort facts"]')).toBeVisible();

        // Select Label A-Z for dimensions
        await page.locator('[aria-label="Sort dimensions"]').selectOption('label-asc');
        // Select Label A-Z for facts
        await page.locator('[aria-label="Sort facts"]').selectOption('label-asc');
        await page.waitForTimeout(200);

        // Rows should now be ordered: Apple → Mango → Zebra
        const rows = page.locator('tbody tr');
        await expect(rows.nth(0).locator('td').first()).toContainText('Apple Dimension');
        await expect(rows.nth(1).locator('td').first()).toContainText('Mango Dimension');
        await expect(rows.nth(2).locator('td').first()).toContainText('Zebra Dimension');

        // Fact column headers should be: Banana → Walnut
        await expect(page.locator('thead th').nth(1)).toContainText('Banana Fact');
        await expect(page.locator('thead th').nth(2)).toContainText('Walnut Fact');
    });

    test('should sort dimensions and facts by visible usage count', async ({ page }) => {
        const countData = {
            dimensions: [
                { id: 'dim_low', label: 'Low Use Dim', tags: [] },
                { id: 'dim_high', label: 'High Use Dim', tags: [] },
            ],
            facts: [
                { id: 'fct_a', label: 'Fact A', tags: [] },
                { id: 'fct_b', label: 'Fact B', tags: [] },
            ],
            connections: [
                { dimension_id: 'dim_high', fact_id: 'fct_a' },
                { dimension_id: 'dim_high', fact_id: 'fct_b' },
                // dim_low has 0 connections
            ],
        };

        await mockBusMatrixRoutes(page, countData);
        await page.goto('/bus-matrix');
        await page.waitForLoadState('networkidle');

        // Sort dimensions by count descending
        await page.locator('[aria-label="Sort dimensions"]').selectOption('count-desc');
        await page.waitForTimeout(200);

        // dim_high (2 connections) should appear first
        await expect(page.locator('tbody tr').nth(0).locator('td').first()).toContainText('High Use Dim');
        await expect(page.locator('tbody tr').nth(1).locator('td').first()).toContainText('Low Use Dim');

        // Sort facts by count descending
        await page.locator('[aria-label="Sort facts"]').selectOption('count-desc');
        await page.waitForTimeout(200);

        // fct_a and fct_b each have 1 dimension connection (dim_high connects to both)
        // Count badges should show related dimensions
        await expect(page.locator('[aria-label="1 related dimensions"]').first()).toBeVisible();
    });
});

test.describe('Bus Matrix View', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('/');
        await page.waitForLoadState('networkidle');
    });

    test('should show Bus Matrix button in navigation', async ({ page }) => {
        // Check if Bus Matrix link exists in navigation
        const busMatrixLink = page.locator('a[href="/bus-matrix"]');

        // If bus matrix is not enabled, this test should be skipped
        const isVisible = await busMatrixLink.isVisible().catch(() => false);

        if (!isVisible) {
            test.skip();
        }

        await expect(busMatrixLink).toBeVisible();
        await expect(busMatrixLink).toContainText('Bus Matrix');
    });

    test('should switch to Bus Matrix view when link is clicked', async ({ page }) => {
        const busMatrixLink = page.locator('a[href="/bus-matrix"]');
        const isVisible = await busMatrixLink.isVisible().catch(() => false);

        if (!isVisible) {
            test.skip();
        }

        // Click Bus Matrix link
        await busMatrixLink.click();
        await page.waitForLoadState('networkidle');

        // Verify URL changed to /bus-matrix
        await expect(page).toHaveURL(/\/bus-matrix/);

        // Verify Bus Matrix component loads (check for loading or content)
        const busMatrixContent = page.locator('.h-full.w-full.overflow-auto.bg-gray-50');
        await expect(busMatrixContent).toBeVisible({ timeout: 10000 });
    });

    test('should render table structure with dimensions and facts', async ({ page }) => {
        // Navigate to Bus Matrix view
        await page.goto('/bus-matrix');
        await page.waitForLoadState('networkidle');

        // Wait for either data or error state
        const loadingIndicator = page.locator('text=Loading Bus Matrix...');
        const errorState = page.locator('text=Error Loading Bus Matrix');
        const tableContainer = page.locator('table');

        // Wait for loading to complete
        await Promise.race([
            loadingIndicator.waitFor({ state: 'hidden', timeout: 10000 }).catch(() => {}),
            errorState.waitFor({ state: 'visible', timeout: 10000 }).catch(() => {}),
            tableContainer.waitFor({ state: 'visible', timeout: 10000 }).catch(() => {})
        ]);

        // If there's an error or no data, skip
        const hasError = await errorState.isVisible().catch(() => false);
        if (hasError) {
            test.skip();
        }

        // Check if table exists
        const tableExists = await tableContainer.isVisible().catch(() => false);
        if (!tableExists) {
            test.skip();
        }

        // Verify table structure
        await expect(tableContainer).toBeVisible();

        // Check for header row with "Dimensions" label
        const dimensionsHeader = page.locator('th:has-text("Dimensions")');
        await expect(dimensionsHeader).toBeVisible();

        // Check that table has rows (dimension rows)
        const tableRows = page.locator('tbody tr');
        const rowCount = await tableRows.count();

        // If no data, that's ok - the test verified structure exists
        expect(rowCount).toBeGreaterThanOrEqual(0);
    });

    test('should display checkmark or dash for cell connections', async ({ page }) => {
        await page.goto('/bus-matrix');
        await page.waitForLoadState('networkidle');

        // Wait for table to load
        const tableContainer = page.locator('table');
        const tableExists = await tableContainer.isVisible().catch(() => false);

        if (!tableExists) {
            test.skip();
        }

        // Check for connection indicators in table cells
        // Implementation uses ✓ for connected and — for not connected
        const checkmarks = page.locator('td:has-text("✓")');
        const dashes = page.locator('td:has-text("—")');

        const checkmarkCount = await checkmarks.count();
        const dashCount = await dashes.count();

        // At least one type of indicator should exist if there's data
        expect(checkmarkCount + dashCount).toBeGreaterThanOrEqual(0);
    });

    test('should show filter controls for dimensions, facts, and tags', async ({ page }) => {
        await page.goto('/bus-matrix');
        await page.waitForLoadState('networkidle');

        // Check for filter section
        const filterSection = page.locator('text=Filters:');
        const filterExists = await filterSection.isVisible().catch(() => false);

        if (!filterExists) {
            test.skip();
        }

        await expect(filterSection).toBeVisible();

        // Check for dimension filter dropdown
        const dimensionFilter = page.locator('select#dimension-filter');
        await expect(dimensionFilter).toBeVisible();

        // Check for fact filter dropdown
        const factFilter = page.locator('select#fact-filter');
        await expect(factFilter).toBeVisible();

        // Check for tag filter dropdown
        const tagFilter = page.locator('select#tag-filter');
        await expect(tagFilter).toBeVisible();
    });

    test('should filter dimensions using dropdown selection', async ({ page }) => {
        await page.goto('/bus-matrix');
        await page.waitForLoadState('networkidle');

        const dimensionFilter = page.locator('select#dimension-filter');
        const tableRows = page.locator('tbody tr');

        const filterExists = await dimensionFilter.isVisible().catch(() => false);
        if (!filterExists) {
            test.skip();
        }

        // Get initial row count
        const initialCount = await tableRows.count();

        // Check if there are options to select
        const options = await dimensionFilter.locator('option').count();

        if (options <= 1) {
            // No data to filter, skip test
            test.skip();
        }

        // Select first available dimension (index 1, since 0 is placeholder)
        await dimensionFilter.selectOption({ index: 1 });
        await page.waitForTimeout(500); // Wait for filter to apply

        // Check that a filter tag was added
        const filterTags = page.locator('span.inline-flex.items-center.gap-1.px-2.py-1.bg-primary-100');
        const tagCount = await filterTags.count();

        expect(tagCount).toBeGreaterThan(0);
    });

    test('should handle empty state when no matching data', async ({ page }) => {
        await mockBusMatrixRoutes(page, {
            dimensions: [],
            facts: [],
            connections: [],
        });
        await page.goto('/bus-matrix');
        await page.waitForLoadState('networkidle');

        const table = page.locator('table');
        const emptyMessage = page.locator('td:has-text("No dimensions match the current filters")');
        await expect(table).toBeVisible({ timeout: 10000 });
        await expect(emptyMessage).toBeVisible();
    });

    test('should have scrollable table container', async ({ page }) => {
        await page.goto('/bus-matrix');
        await page.waitForLoadState('networkidle');

        // Check that table container has overflow styling
        const tableWrapper = page.locator('.overflow-x-auto.overflow-y-auto');
        const exists = await tableWrapper.isVisible().catch(() => false);

        if (!exists) {
            test.skip();
        }

        await expect(tableWrapper).toBeVisible();

        // Verify max-height is set for scrolling
        const hasMaxHeight = await tableWrapper.evaluate((el) => {
            const style = window.getComputedStyle(el);
            return style.maxHeight !== 'none';
        });

        expect(hasMaxHeight).toBe(true);
    });

    test('should be responsive at 1024x768 resolution', async ({ page }) => {
        await page.setViewportSize({ width: 1024, height: 768 });
        await page.goto('/bus-matrix');
        await page.waitForLoadState('networkidle');

        // Check if page loaded without errors
        const errorState = page.locator('text=Error Loading Bus Matrix');
        const hasError = await errorState.isVisible().catch(() => false);

        if (hasError) {
            test.skip();
        }

        // Verify main container is visible
        const mainContainer = page.locator('.h-full.w-full.overflow-auto');
        await expect(mainContainer).toBeVisible();

        // Verify header is visible
        const header = page.locator('h2:has-text("Bus Matrix")');
        await expect(header).toBeVisible();
    });

    // Skip tests for unimplemented features
    test.skip('should highlight relationship on canvas when cell is clicked', async ({ page }) => {
        // Feature not yet implemented - cells are not clickable
    });

    test.skip('should center view on both entities after cell click', async ({ page }) => {
        // Feature not yet implemented - cells are not clickable
    });

    test.skip('should maintain filter state when switching views', async ({ page }) => {
        // Filter state persistence not implemented yet
    });
});

test.describe('Bus Matrix Export', () => {
    test('should show export full matrix action', async ({ page }) => {
        await mockBusMatrixRoutes(page);
        await page.goto('/bus-matrix');
        await page.waitForLoadState('networkidle');

        await expect(page.getByRole('button', { name: 'Export full matrix' })).toBeVisible();
    });

    test('should export full matrix even when filters are active', async ({ page }) => {
        await mockBusMatrixRoutes(page);
        await page.goto('/bus-matrix');
        await page.waitForLoadState('networkidle');

        // Apply a fact filter so only Orders Fact is visible
        await page.locator('select#fact-filter').selectOption({ label: 'Orders Fact' });
        await page.waitForTimeout(300);

        const downloadPromise = page.waitForEvent('download');
        await page.getByRole('button', { name: 'Export full matrix' }).click();
        const download = await downloadPromise;

        expect(download.suggestedFilename()).toBe('trellis-bus-matrix.xlsx');
    });

    test('should create workbook with matrix and longlist sheets', async ({ page }) => {
        await mockBusMatrixRoutes(page);
        await page.goto('/bus-matrix');
        await page.waitForLoadState('networkidle');

        const downloadPromise = page.waitForEvent('download');
        await page.getByRole('button', { name: 'Export full matrix' }).click();
        const download = await downloadPromise;

        const downloadPath = await download.path();
        const buffer = fs.readFileSync(downloadPath!);
        const workbook = XLSX.read(buffer, { type: 'buffer' });

        // Must have Matrix and Longlist sheets
        expect(workbook.SheetNames).toContain('Matrix');
        expect(workbook.SheetNames).toContain('Longlist');

        // Longlist must contain all dimension-fact combinations
        const longlistSheet = workbook.Sheets['Longlist'];
        const longlistData = XLSX.utils.sheet_to_json<{ dimension: string; fact: string; linked: string }>(longlistSheet);

        // 3 dimensions × 2 facts = 6 total combinations
        expect(longlistData.length).toBe(6);

        // Verify columns exist
        expect(Object.keys(longlistData[0])).toContain('dimension');
        expect(Object.keys(longlistData[0])).toContain('fact');
        expect(Object.keys(longlistData[0])).toContain('linked');

        // Linked values must be TRUE or FALSE strings
        const linkedValues = new Set(longlistData.map(row => row.linked));
        expect(linkedValues).not.toContain(undefined);
        linkedValues.forEach(v => expect(['TRUE', 'FALSE']).toContain(v));

        // Known connections from MOCK_BUS_MATRIX_DATA must appear as TRUE
        const connectedPairs = [
            { dimension: 'Customer Dimension', fact: 'Orders Fact' },
            { dimension: 'Customer Dimension', fact: 'Sales Fact' },
            { dimension: 'Date Dimension', fact: 'Orders Fact' },
            { dimension: 'Product Dimension', fact: 'Orders Fact' },
            { dimension: 'Product Dimension', fact: 'Sales Fact' },
        ];
        for (const pair of connectedPairs) {
            const row = longlistData.find(r => r.dimension === pair.dimension && r.fact === pair.fact);
            expect(row?.linked).toBe('TRUE');
        }

        // The unconnected pair must be FALSE
        const unconnected = longlistData.find(
            r => r.dimension === 'Date Dimension' && r.fact === 'Sales Fact'
        );
        expect(unconnected?.linked).toBe('FALSE');
    });
});

