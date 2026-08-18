import { test, expect, type Page } from '@playwright/test';
import {
    applyConfigOverrides,
    cleanupTestEntities,
    completeEntityWizard,
    getConfig,
    getCompanyDummyConfigOverrides,
    reloadConfig,
    resetDataModel,
    restoreConfig,
    saveConfig,
    type DataModelPayload,
} from './helpers';

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

        // Complete wizard if it appears
        await completeEntityWizard(page);

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
        const editedEntityNode = page.locator('.svelte-flow__node-entity').filter({ has: entity }).first();
        await editedEntityNode.hover();
        await editedEntityNode.getByRole('button', { name: 'Delete entity Orders', exact: true }).click();

        // Confirm modal
        await expect(page.getByRole('dialog', { name: /delete entity/i })).toBeVisible();
        await page.getByRole('dialog', { name: /delete entity/i }).getByRole('button', { name: 'Delete' }).click();

        // Verify gone
        await expect(entity).not.toBeVisible();
    });

    test('creates entity directly when wizard guidance is disabled', async ({ page, request }) => {
        const originalConfig = await applyConfigOverrides(request, {
            ...getCompanyDummyConfigOverrides(),
            entity_creation_guidance: { enabled: false },
        });

        try {
            await resetDataModel(request);
            await page.reload();
            await page.waitForLoadState('networkidle');

            const addEntityBtn = page.getByRole('button', { name: 'Add Entity' });
            await expect(addEntityBtn).toBeVisible({ timeout: 10000 });
            await addEntityBtn.click();

            const wizardModal = page.getByRole('dialog', { name: /create new entity/i });
            await expect(wizardModal).not.toBeVisible({ timeout: 2000 });

            const entityNameInput = page.getByPlaceholder('Entity Name').first();
            await expect(entityNameInput).toBeVisible({ timeout: 10000 });
        } finally {
            await restoreConfig(request, originalConfig);
        }
    });

    test('expand/collapse all entities toggle', async ({ page }) => {
        // 1. Create multiple entities
        const addEntityBtn = page.getByRole('button', { name: 'Add Entity' });
        await expect(addEntityBtn).toBeVisible({ timeout: 10000 });
        
        // Create first entity
        await addEntityBtn.click();
        await completeEntityWizard(page);
        await page.waitForTimeout(500);
        
        // Create second entity
        await addEntityBtn.click();
        await completeEntityWizard(page);
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

const CANVAS_FILTER_DATA_MODEL: DataModelPayload = {
    version: 0.1,
    entities: [
        {
            id: 'sales_orders',
            label: 'Sales Orders',
            domain: 'Sales',
            tags: ['revenue'],
            entity_type: 'fact',
            position: { x: 0, y: 0 },
        },
        {
            id: 'marketing_campaigns',
            label: 'Marketing Campaigns',
            domain: 'Marketing',
            tags: ['campaigns'],
            entity_type: 'fact',
            position: { x: 400, y: 0 },
        },
        {
            id: 'sales_customers',
            label: 'Sales Customers',
            domain: 'Sales',
            tags: ['customers'],
            entity_type: 'dimension',
            position: { x: 200, y: 300 },
        },
    ],
    relationships: [],
};

function entityNode(page: Page, label: string) {
    const escapedLabel = label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return page
        .locator('.svelte-flow__node-entity')
        .filter({ has: page.getByRole('button', { name: new RegExp(`^${escapedLabel}\\b`) }) });
}

async function expectEntityHidden(page: Page, label: string): Promise<void> {
    const node = entityNode(page, label);
    await expect
        .poll(
            async () => {
                const count = await node.count();
                return count === 0 || !(await node.first().isVisible());
            },
            { message: `${label} should be hidden by the Canvas filters` },
        )
        .toBe(true);
}

async function openFreshCanvas(page: Page, path = '/canvas'): Promise<void> {
    await page.addInitScript(() => {
        localStorage.clear();
        sessionStorage.clear();
    });
    await page.goto(path);
    await expect(page.getByTestId('canvas-ready')).toBeVisible({ timeout: 15000 });
}

test.describe('Canvas Navigation And Default Filters', () => {
    test.use({ storageState: { cookies: [], origins: [] } });

    test('Canvas default filters hide non-matching entities, expose active filters, and clear cleanly', async ({
        page,
        request,
    }) => {
        const originalConfig = await applyConfigOverrides(request, {
            ...getCompanyDummyConfigOverrides(),
            canvas: {
                default_filters: {
                    domains: ['Sales'],
                    tags: ['revenue'],
                },
            },
        });

        try {
            await resetDataModel(request, CANVAS_FILTER_DATA_MODEL);
            await openFreshCanvas(page);

            await expect(entityNode(page, 'Sales Orders')).toBeVisible();
            await expectEntityHidden(page, 'Marketing Campaigns');
            await expectEntityHidden(page, 'Sales Customers');

            await expect(page.getByRole('status')).toContainText('Filtered');
            await expect(page.getByTestId('canvas-filter-domain-chip')).toContainText('Sales');
            await expect(page.getByTestId('canvas-filter-tag-chip')).toContainText('revenue');
            await expect(page.getByRole('status')).toContainText('Showing 1 of 3 entities');

            await page.getByRole('button', { name: 'Clear Canvas filters' }).click();

            await expect(entityNode(page, 'Marketing Campaigns')).toBeVisible();
            await expect(entityNode(page, 'Sales Customers')).toBeVisible();
            await expect(page.getByRole('button', { name: 'Clear Canvas filters' })).toBeHidden();
        } finally {
            await restoreConfig(request, originalConfig);
        }
    });

    test('explicit Canvas entity filter shows requested entities despite project defaults', async ({
        page,
        request,
    }) => {
        const originalConfig = await applyConfigOverrides(request, {
            ...getCompanyDummyConfigOverrides(),
            canvas: {
                default_filters: {
                    domains: ['Sales'],
                    tags: ['revenue'],
                },
            },
        });

        try {
            await resetDataModel(request, CANVAS_FILTER_DATA_MODEL);
            await openFreshCanvas(page, '/canvas?entities=marketing_campaigns');

            await expect(entityNode(page, 'Marketing Campaigns')).toBeVisible();
            await expectEntityHidden(page, 'Sales Orders');
            await expectEntityHidden(page, 'Sales Customers');
        } finally {
            await restoreConfig(request, originalConfig);
        }
    });

    test('fresh unconfigured Canvas starts conceptual with entities collapsed', async ({ page, request }) => {
        const currentConfig = await getConfig(request);
        const originalConfig = currentConfig.config;
        const unconfiguredConfig = JSON.parse(JSON.stringify(originalConfig)) as Record<string, any>;
        delete unconfiguredConfig.start_page;
        delete unconfiguredConfig.canvas;

        try {
            await saveConfig(request, unconfiguredConfig, currentConfig.file_info ?? null);
            await reloadConfig(request);
            await resetDataModel(request, CANVAS_FILTER_DATA_MODEL);
            await openFreshCanvas(page);

            await expect(page.getByTitle('Conceptual View')).toHaveClass(/text-primary-600/);
            await expect(page.getByRole('button', { name: /Expand all entities/i })).toBeVisible();

            for (const label of ['Sales Orders', 'Marketing Campaigns', 'Sales Customers']) {
                const node = entityNode(page, label);
                await expect(node).toBeVisible();
                await expect(node.locator('[title="Click to expand"]')).toBeVisible();
            }
        } finally {
            await restoreConfig(request, originalConfig);
        }
    });
});
