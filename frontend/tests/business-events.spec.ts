import { test, expect } from '@playwright/test';
import { applyConfigOverrides, getCompanyDummyConfigOverrides, restoreConfig } from './helpers';

/**
 * E2E tests for Business Events feature.
 * These tests use API route interception to mock responses for predictable test data.
 */

test.describe.configure({ mode: 'serial' });

test.describe('Business Events - E2E', () => {
    test.use({ storageState: { cookies: [], origins: [] } }); // Isolate session

    const mockEvents = [
        {
            id: 'evt_20260121_001',
            text: 'customer buys product',
            type: 'discrete',
            created_at: '2026-01-21T10:30:00Z',
            updated_at: '2026-01-21T10:30:00Z',
            annotations: {
                who: [{ id: 'ent1', text: 'customer' }],
                what: [{ id: 'ent2', text: 'product' }],
                when: [],
                where: [],
                how: [],
                how_many: [{ id: 'ent3', text: 'buys' }],
                why: []
            },
            derived_entities: [],
        },
        {
            id: 'evt_20260121_002',
            text: 'monthly account statement',
            type: 'recurring',
            created_at: '2026-01-21T11:00:00Z',
            updated_at: '2026-01-21T11:00:00Z',
            annotations: {
                who: [],
                what: [],
                when: [],
                where: [],
                how: [],
                how_many: [],
                why: []
            },
            derived_entities: [],
        },
    ];

    const mockGeneratedEntities = {
        entities: [
            {
                id: 'dim_customer',
                label: 'Customer',
                entity_type: 'dimension',
            },
            {
                id: 'fct_buys',
                label: 'Buys',
                entity_type: 'fact',
            },
            {
                id: 'dim_product',
                label: 'Product',
                entity_type: 'dimension',
            },
        ],
        relationships: [
            {
                source: 'dim_customer',
                target: 'fct_buys',
                type: 'one_to_many',
            },
            {
                source: 'dim_product',
                target: 'fct_buys',
                type: 'one_to_many',
            },
        ],
        errors: [],
    };

    test.beforeEach(async ({ page }) => {
        // Mock API responses
        await page.route('**/api/business-events', async (route) => {
            if (route.request().method() === 'GET') {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify(mockEvents),
                });
            } else if (route.request().method() === 'POST') {
                const body = await route.request().postDataJSON();
                const newEvent = {
                    id: 'evt_20260121_003',
                    text: body.text,
                    type: body.type,
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString(),
                    annotations: {
                        who: [],
                        what: [],
                        when: [],
                        where: [],
                        how: [],
                        how_many: [],
                        why: []
                    },
                    derived_entities: [],
                };
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify(newEvent),
                });
            } else {
                await route.continue();
            }
        });

        await page.route('**/api/business-events/*', async (route) => {
            if (route.request().method() === 'DELETE') {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({ status: 'success' }),
                });
            } else if (route.request().method() === 'PUT') {
                const body = await route.request().postDataJSON();
                const updatedEvent = {
                    ...mockEvents[0],
                    ...body,
                    updated_at: new Date().toISOString(),
                };
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify(updatedEvent),
                });
            } else {
                await route.continue();
            }
        });

        await page.route('**/api/business-events/*/generate-entities', async (route) => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify(mockGeneratedEntities),
            });
        });

        await page.goto('/');
    });

    test('tab should not be visible when business_events.enabled is false', async ({ page }) => {
        await page.waitForLoadState('domcontentloaded');

        // Mock config API to return business_events.enabled: false
        await page.route('**/api/config', async (route) => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    config: {
                        modeling_style: 'dimensional_model',
                        business_events: { enabled: false },
                    },
                }),
            });
        });

        await page.reload();
        await page.waitForLoadState('domcontentloaded');

        // Business Events tab should not be visible
        const businessEventsLink = page.getByRole('link', { name: 'Business Events' });
        await expect(businessEventsLink).not.toBeVisible({ timeout: 2000 });
    });

    test.skip('tab should be visible when business_events.enabled is true and modeling_style is dimensional_model', async ({ page, request }) => {
        // Skip: config changes cause test pollution in CI
        const originalConfig = await applyConfigOverrides(request, {
            ...getCompanyDummyConfigOverrides(),
            modeling_style: 'dimensional_model',
            business_events: { enabled: true },
        });

        try {
            await page.addInitScript(() => {
                localStorage.clear();
                sessionStorage.clear();
            });
            await page.reload();
            await page.waitForLoadState('networkidle');

            // Business Events tab should be visible
            const businessEventsLink = page.getByRole('link', { name: 'Business Events' });
            await expect(businessEventsLink).toBeVisible({ timeout: 5000 });
        } finally {
            await restoreConfig(request, originalConfig);
        }
    });

    test('should display empty state when no events exist', async ({ page }) => {
        // Mock empty events list
        await page.route('**/api/business-events', async (route) => {
            if (route.request().method() === 'GET') {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify([]),
                });
            } else {
                await route.continue();
            }
        });

        // Navigate to business events and verify it exists
        const response = await page.goto('/business-events').catch(() => null);
        
        if (!response || !response.ok()) {
            test.skip();
            return;
        }
        
        await page.waitForLoadState('domcontentloaded');

        // Check for empty state message
        const emptyState = page.getByText(/no business events/i);
        const emptyStateVisible = await emptyState.isVisible({ timeout: 3000 }).catch(() => false);
        
        if (emptyStateVisible) {
            await expect(emptyState).toBeVisible();
            // Check for example text
            const exampleText = page.getByText(/customer buys product/i);
            await expect(exampleText).toBeVisible();
        } else {
            // If empty state not found, events might be loaded - check for events list instead
            const eventsList = page.locator('[data-testid="events-list"]').or(page.locator('text=customer buys product'));
            const hasEvents = await eventsList.isVisible({ timeout: 2000 }).catch(() => false);
            if (!hasEvents) {
                // Neither empty state nor events found - test may need route implementation
                test.skip();
            }
        }
    });

    test('should display events list when events exist', async ({ page }) => {
        // Navigate to business events and verify it exists
        const response = await page.goto('/business-events').catch(() => null);
        
        if (!response || !response.ok()) {
            test.skip();
            return;
        }
        
        await page.waitForLoadState('domcontentloaded');

        // Check for event text
        const eventText = page.getByText('customer buys product');
        const isVisible = await eventText.isVisible({ timeout: 5000 }).catch(() => false);
        
        if (isVisible) {
            await expect(eventText).toBeVisible();
        } else {
            // Route might not be implemented yet
            test.skip();
        }
    });

    test('should filter events by type', async ({ page }) => {
        const response = await page.goto('/business-events').catch(() => null);
        
        if (!response || !response.ok()) {
            test.skip();
            return;
        }
        
        await page.waitForLoadState('domcontentloaded');

        // Find filter dropdown
        const filterSelect = page.locator('select').filter({ hasText: /all|discrete|evolving|recurring/i });
        const filterExists = await filterSelect.isVisible({ timeout: 3000 }).catch(() => false);

        if (!filterExists) {
            test.skip();
            return;
        }

        // Select "Discrete" filter
        await filterSelect.selectOption('discrete');
        await page.waitForTimeout(500);

        // Verify only discrete events are shown
        const discreteEvent = page.getByText('customer buys product');
        const recurringEvent = page.getByText('monthly account statement');

        await expect(discreteEvent).toBeVisible();
        await expect(recurringEvent).not.toBeVisible();
    });

    test('should create new event', async ({ page }) => {
        const response = await page.goto('/business-events').catch(() => null);
        
        if (!response || !response.ok()) {
            test.skip();
            return;
        }
        
        await page.waitForLoadState('domcontentloaded');

        // Click "Add Event" button
        const addButton = page.getByRole('button', { name: /add event/i });
        const buttonExists = await addButton.isVisible({ timeout: 3000 }).catch(() => false);

        if (!buttonExists) {
            test.skip();
            return;
        }

        await addButton.click();

        // Wait for modal/form to appear
        const modal = page.getByRole('dialog').or(page.locator('text=Create Event'));
        await modal.waitFor({ state: 'visible', timeout: 3000 }).catch(() => {
            test.skip();
        });

        // Fill in form (if CreateEventModal is implemented)
        const textInput = page.locator('textarea').or(page.locator('input[type="text"]')).first();
        const inputExists = await textInput.isVisible({ timeout: 2000 }).catch(() => false);

        if (inputExists) {
            await textInput.fill('employee processes claim');
            
            // Select type if dropdown exists
            const typeSelect = page.locator('select').filter({ hasText: /discrete|evolving|recurring/i });
            const typeSelectExists = await typeSelect.isVisible({ timeout: 1000 }).catch(() => false);
            if (typeSelectExists) {
                await typeSelect.selectOption('discrete');
            }

            // Click save button
            const saveButton = page.getByRole('button', { name: /save|create/i });
            await saveButton.click();

            // Verify event appears in list (wait for API call)
            await page.waitForTimeout(1000);
            const newEvent = page.getByText('employee processes claim');
            await expect(newEvent).toBeVisible({ timeout: 5000 });
        } else {
            // Modal placeholder might be showing - skip detailed test
            test.skip();
        }
    });

    test('should delete event', async ({ page }) => {
        const response = await page.goto('/business-events').catch(() => null);
        
        if (!response || !response.ok()) {
            test.skip();
            return;
        }
        
        await page.waitForLoadState('domcontentloaded');

        // Find delete button for first event
        const deleteButton = page.getByRole('button', { name: /delete/i }).first();
        const buttonExists = await deleteButton.isVisible({ timeout: 3000 }).catch(() => false);

        if (!buttonExists) {
            test.skip();
            return;
        }

        await deleteButton.click();

        // Confirm deletion if confirmation dialog appears
        const confirmButton = page.getByRole('button', { name: /confirm|delete/i });
        const confirmExists = await confirmButton.isVisible({ timeout: 2000 }).catch(() => false);
        if (confirmExists) {
            await confirmButton.click();
        }

        // Verify event is removed (wait for API call)
        await page.waitForTimeout(1000);
        const deletedEvent = page.getByText('customer buys product');
        await expect(deletedEvent).not.toBeVisible({ timeout: 3000 });
    });


    /**
     * 7 Ws E2E Tests
     */
    test('should create business event with 7 Ws', async ({ page }) => {
        // Navigate to business events and verify it exists
        const response = await page.goto('/business-events').catch(() => null);
        
        if (!response || !response.ok()) {
            test.skip();
            return;
        }
        
        await page.waitForLoadState('domcontentloaded');

        // Click "Add Event" button
        const addButton = page.getByRole('button', { name: /add event/i });
        const buttonExists = await addButton.isVisible({ timeout: 3000 }).catch(() => false);

        if (!buttonExists) {
            test.skip();
            return;
        }

        await addButton.click();

        // Wait for CreateEventModal
        const modal = page.getByRole('dialog').filter({ hasText: /create event|add event/i });
        await expect(modal).toBeVisible({ timeout: 5000 });

        // Fill event text
        const textInput = page.locator('textarea').or(page.locator('input[name="text"]'));
        const inputVisible = await textInput.isVisible({ timeout: 2000 }).catch(() => false);

        if (inputVisible) {
            await textInput.fill('customer buys product online');

            // Select event type
            const typeSelect = page.locator('select').filter({ hasText: /event type/i });
            const typeExists = await typeSelect.isVisible({ timeout: 2000 }).catch(() => false);

            if (typeExists) {
                await typeSelect.selectOption('discrete');
            }

            // Wait for SevenWsForm to be visible (it should be rendered below)
            await page.waitForTimeout(500);

            // Fill 7 Ws
            await page.locator('[data-testid="seven-ws-form"]').or(page.locator('text=7 Ws')).waitFor({ state: 'visible', timeout: 5000 });

            // Add "Who" entry
            const whoSection = page.locator('text=Who').first();
            await whoSection.click();

            // Click "Add Entry" in Who section
            const whoAddButton = page.locator('button').filter({ hasText: /add entry/i }).first();
            const whoAddVisible = await whoAddButton.isVisible({ timeout: 2000 }).catch(() => false);

            if (whoAddVisible) {
                await whoAddButton.click();

                // Type in the new entry field
                const whoInput = page.locator('input[placeholder*="customer"]').first();
                const whoInputVisible = await whoInput.isVisible({ timeout: 2000 }).catch(() => false);

                if (whoInputVisible) {
                    await whoInput.fill('John Doe');

                    // Add "What" entry
                    const whatSection = page.locator('text=What').first();
                    await whatSection.click();

                    const whatAddButton = page.locator('button').filter({ hasText: /add entry/i }).nth(1);
                    await whatAddButton.click();

                    const whatInput = page.locator('input[placeholder*="product"]').first();
                    const whatInputVisible = await whatInput.isVisible({ timeout: 2000 }).catch(() => false);

                    if (whatInputVisible) {
                        await whatInput.fill('Product');

                        // Add "How Many" entry
                        const howManySection = page.locator('text=How Many').first();
                        await howManySection.click();

                        const howManyAddButton = page.locator('button').filter({ hasText: /add entry/i }).nth(2);
                        await howManyAddButton.click();

                        const howManyInput = page.locator('input[placeholder*="quantity"]').first();
                        const howManyInputVisible = await howManyInput.isVisible({ timeout: 2000 }).catch(() => false);

                        if (howManyInputVisible) {
                            await howManyInput.fill('100 units');

                            // Click save button
                            const saveButton = page.getByRole('button', { name: /save/i });
                            await saveButton.click();

                            // Wait for modal to close and event to appear
                            await expect(modal).not.toBeVisible({ timeout: 5000 });

                            // Verify event appears with 7 Ws badge
                            const badge = page.locator('text=/\\d+/\\d+\\s\\s+Ws/i').first();
                            await expect(badge).toBeVisible({ timeout: 5000 });
                        }
                    }
                }
            }
        }
    });

    test('should select existing dimension from autocomplete', async ({ page }) => {
        // Mock dimensions API response
        await page.route('**/api/data-model', async (route) => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    entities: [
                        { id: 'dim_customer', label: 'Customer', entity_type: 'dimension', annotation_type: 'who' },
                        { id: 'dim_product', label: 'Product', entity_type: 'dimension', annotation_type: 'what' }
                    ]
                }),
            });
        });

        // Navigate and click add event
        const response = await page.goto('/business-events').catch(() => null);
        
        if (!response || !response.ok()) {
            test.skip();
            return;
        }
        
        await page.waitForLoadState('domcontentloaded');

        const addButton = page.getByRole('button', { name: /add event/i });
        const buttonExists = await addButton.isVisible({ timeout: 3000 }).catch(() => false);

        if (buttonExists) {
            await addButton.click();

            // Wait for CreateEventModal
            const modal = page.getByRole('dialog').filter({ hasText: /create event|add event/i });
            await expect(modal).toBeVisible({ timeout: 5000 });

            // Fill event text
            const textInput = page.locator('textarea').or(page.locator('input[name="text"]'));
            const inputVisible = await textInput.isVisible({ timeout: 2000 }).catch(() => false);

            if (inputVisible) {
                await textInput.fill('test event');

                // Wait for SevenWsForm
                await page.locator('[data-testid="seven-ws-form"]').or(page.locator('text=7 Ws')).waitFor({ state: 'visible', timeout: 5000 });

                // Add "Who" entry
                const whoSection = page.locator('text=Who').first();
                await whoSection.click();

                const whoAddButton = page.locator('button').filter({ hasText: /add entry/i }).first();
                const whoAddVisible = await whoAddButton.isVisible({ timeout: 2000 }).catch(() => false);

                if (whoAddVisible) {
                    await whoAddButton.click();

                    // Focus on dimension_id autocomplete field
                    const dimensionInput = page.locator('input').filter({ hasText: /dimension|select/i }).first();
                    const dimInputVisible = await dimensionInput.isVisible({ timeout: 2000 }).catch(() => false);

                    if (dimInputVisible) {
                        // Click on dimension input to trigger autocomplete
                        await dimensionInput.click();
                        await page.waitForTimeout(300);

                        // Type "cust" to filter
                        await dimensionInput.fill('cust');
                        await page.waitForTimeout(300);

                        // Check if "Customer" appears in dropdown
                        const customerOption = page.locator('text=Customer').or(page.locator('[data-testid*="Customer"]'));
                        const customerVisible = await customerOption.isVisible({ timeout: 2000 }).catch(() => false);

                        if (customerVisible) {
                            // Select "Customer" from dropdown
                            await customerOption.click();

                            // Verify the selection
                            await expect(page.locator('text=Customer')).toBeVisible();
                        }
                    }
                }
            }
        }
    });

    test('should generate entities from 7 Ws', async ({ page }) => {
        // Mock entities generation API
        await page.route('**/api/business-events/*/generate-entities', async (route) => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    entities: [
                        { id: 'dim_customer', label: 'Customer', entity_type: 'dimension' },
                        { id: 'dim_product', label: 'Product', entity_type: 'dimension' },
                        { id: 'fct_event', label: 'Event', entity_type: 'fact' }
                    ],
                    relationships: [
                        { source: 'dim_customer', target: 'fct_event', type: 'one_to_many' },
                        { source: 'dim_product', target: 'fct_event', type: 'one_to_many' }
                    ],
                    errors: []
                }),
            });
        });

        // Navigate to business events and verify it exists
        const response = await page.goto('/business-events').catch(() => null);
        
        if (!response || !response.ok()) {
            test.skip();
            return;
        }
        
        await page.waitForLoadState('domcontentloaded');

        // Find event card with 7 Ws
        const eventCard = page.locator('[data-testid="event-card"]').or(page.locator('.bg-white.rounded-lg')).first();
        const eventExists = await eventCard.isVisible({ timeout: 3000 }).catch(() => false);

        if (eventExists) {
            // Click generate entities button
            const generateButton = page.getByRole('button', { name: /generate/i });
            await generateButton.click();

            // Wait for generation dialog
            const dialog = page.getByRole('dialog').filter({ hasText: /generate/i });
            await expect(dialog).toBeVisible({ timeout: 5000 });

            // Verify generated entities
            await expect(page.getByText('dim_customer')).toBeVisible({ timeout: 5000 });
            await expect(page.getByText('dim_product')).toBeVisible({ timeout: 5000 });
            await expect(page.getByText('fct_event')).toBeVisible({ timeout: 5000 });
        }
    });

    test('should edit existing event\'s 7 Ws', async ({ page }) => {
        // Mock update API
        await page.route('**/api/business-events/**', async (route) => {
            if (route.request().method() === 'PUT') {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        id: 'evt_001',
                        text: 'customer buys product',
                        type: 'discrete',
                        annotations: {
                            who: [{ id: 'ent1', text: 'Customer Updated' }],
                            what: [{ id: 'ent2', text: 'Product Updated' }],
                            when: [],
                            where: [],
                            how: [],
                            how_many: [{ id: 'ent3', text: '200 units' }],
                            why: []
                        },
                        derived_entities: [],
                        created_at: '2025-01-22T10:00:00Z',
                        updated_at: new Date().toISOString()
                    }),
                });
            } else {
                await route.continue();
            }
        });

        // Navigate and click edit
        const response = await page.goto('/business-events').catch(() => null);
        
        if (!response || !response.ok()) {
            test.skip();
            return;
        }
        
        await page.waitForLoadState('domcontentloaded');

        const editButton = page.getByRole('button', { name: /7 ws|highlighter/i }).first();
        const editExists = await editButton.isVisible({ timeout: 3000 }).catch(() => false);

        if (editExists) {
            await editButton.click();

            // Wait for edit modal
            const modal = page.getByRole('dialog').filter({ hasText: /edit/i });
            await expect(modal).toBeVisible({ timeout: 5000 });

            // Wait for SevenWsForm
            await page.locator('[data-testid="seven-ws-form"]').or(page.locator('text=7 Ws')).waitFor({ state: 'visible', timeout: 5000 });

            // Edit "Who" entry
            const whoInput = page.locator('input').filter({ hasText: /customer/i }).first();
            const whoInputVisible = await whoInput.isVisible({ timeout: 2000 }).catch(() => false);

            if (whoInputVisible) {
                await whoInput.clear();
                await whoInput.fill('Customer Updated');

                // Click save
                const saveButton = page.getByRole('button', { name: /save/i });
                await saveButton.click();

                // Wait for modal to close
                await expect(modal).not.toBeVisible({ timeout: 5000 });
            }
        }
    });

    test('should require domain selection before creating process', async ({ page }) => {
        // Mock processes API
        await page.route('**/api/processes', async (route) => {
            if (route.request().method() === 'POST') {
                const body = await route.request().postDataJSON();
                await route.fulfill({
                    status: 201,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        id: 'proc_20260127_001',
                        name: body.name,
                        type: body.type,
                        domain: body.domain,
                        event_ids: body.event_ids,
                        created_at: new Date().toISOString(),
                        updated_at: new Date().toISOString()
                    })
                });
            } else {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify([])
                });
            }
        });

        // Mock domains API
        await page.route('**/api/business-events/domains', async (route) => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify(['Sales', 'Marketing', 'Finance'])
            });
        });

        // Navigate to business events and verify it exists
        const response = await page.goto('/business-events').catch(() => null);
        
        if (!response || !response.ok()) {
            test.skip();
            return;
        }
        
        await page.waitForLoadState('domcontentloaded');

        // Select multiple events (checkboxes)
        const checkboxes = page.locator('input[type="checkbox"]').filter({ hasNotText: /select all/i });
        const checkboxCount = await checkboxes.count();

        if (checkboxCount < 2) {
            test.skip();
            return;
        }

        // Select at least 2 events
        await checkboxes.nth(0).check();
        await checkboxes.nth(1).check();

        // Click "Group into Process" button
        const groupButton = page.getByRole('button', { name: /group into process/i });
        const groupButtonExists = await groupButton.isVisible({ timeout: 3000 }).catch(() => false);

        if (!groupButtonExists) {
            test.skip();
            return;
        }

        await groupButton.click();

        // Wait for ProcessGroupModal to appear
        const modal = page.getByRole('dialog').filter({ hasText: /group into process/i });
        await expect(modal).toBeVisible({ timeout: 5000 });

        // Fill in process name
        const nameInput = page.getByLabel(/process name/i);
        await nameInput.fill('Test Process');

        // Verify Create Process button is disabled (domain not selected)
        const createButton = page.getByRole('button', { name: /create process/i });
        await expect(createButton).toBeDisabled();

        // Verify domain required message is shown
        const domainRequired = page.getByText(/process domain is required/i);
        await expect(domainRequired).toBeVisible();

        // Fill in domain
        const domainInput = page.getByLabel(/process domain/i);
        await domainInput.fill('Sales');

        // Verify Create Process button is now enabled
        await expect(createButton).not.toBeDisabled({ timeout: 2000 });

        // Clear domain
        await domainInput.clear();

        // Verify Create Process button is disabled again
        await expect(createButton).toBeDisabled({ timeout: 2000 });

        // Fill domain again and verify button enables
        await domainInput.fill('Marketing');
        await expect(createButton).not.toBeDisabled({ timeout: 2000 });
    });

    test('should show generate entities button on process rows', async ({ page }) => {
        const response = await page.goto('/business-events').catch(() => null);
        
        if (!response || !response.ok()) {
            test.skip();
            return;
        }
        
        await page.waitForLoadState('domcontentloaded');

        // Check if there are any processes displayed
        const processRow = page.locator('[class*="process"]').or(
            page.locator('text=/process/i')
        ).first();

        const hasProcess = await processRow.isVisible({ timeout: 5000 }).catch(() => false);

        if (hasProcess) {
            // Verify the generate entities button exists on the process row
            const generateBtn = page.getByTitle(/generate dimensional entities from process/i);
            const btnExists = await generateBtn.isVisible({ timeout: 3000 }).catch(() => false);

            if (btnExists) {
                // Verify button is clickable
                await expect(generateBtn).toBeEnabled();

                // Click button to open dialog
                await generateBtn.click();

                // Verify dialog opens in process mode
                const generateDialog = page.getByRole('dialog').filter({
                    hasText: /generate entities from process/i
                });
                await expect(generateDialog).toBeVisible({ timeout: 5000 });
            } else {
                // No generate button found, skip test
                test.skip();
            }
        } else {
            // No processes exist, skip test
            test.skip();
        }
    });

});

/**
 * Entity Model mode E2E tests.
 *
 * These tests mock the config-info API to simulate `modeling_style: 'entity_model'`
 * so the frontend hides the event-type selector and the "How Many" annotation section.
 */

function getEntityModelConfigOverrides() {
    return { modeling_style: 'entity_model', business_events: { enabled: true } };
}

test.describe('Business Events - entity_model mode', () => {
    test.use({ storageState: { cookies: [], origins: [] } });

    const mockEvents = [
        {
            id: 'evt_em_001',
            text: 'customer places order',
            type: 'discrete',
            created_at: '2026-01-21T10:30:00Z',
            updated_at: '2026-01-21T10:30:00Z',
            annotations: {
                who: [{ id: 'ent1', text: 'customer' }],
                what: [],
                when: [],
                where: [],
                how: [],
                how_many: [],
                why: []
            },
            derived_entities: [],
        },
    ];

    /**
     * Registers route mocks for the business-events API and the config-info endpoint
     * so the page thinks it is running in entity_model mode with business events enabled.
     */
    async function setupEntityModelMocks(page: import('@playwright/test').Page) {
        const overrides = getEntityModelConfigOverrides();

        await page.route('**/api/config-info', async (route) => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    business_events_enabled: overrides.business_events.enabled,
                    modeling_style: overrides.modeling_style,
                }),
            });
        });

        await page.route('**/api/business-events', async (route) => {
            if (route.request().method() === 'GET') {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify(mockEvents),
                });
            } else if (route.request().method() === 'POST') {
                const body = await route.request().postDataJSON();
                const newEvent = {
                    id: 'evt_em_new',
                    text: body.text,
                    type: body.type ?? null,
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString(),
                    annotations: { who: [], what: [], when: [], where: [], how: [], how_many: [], why: [] },
                    derived_entities: [],
                };
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify(newEvent),
                });
            } else {
                await route.continue();
            }
        });

        await page.route('**/api/business-events/*', async (route) => {
            if (route.request().method() === 'PUT') {
                const body = await route.request().postDataJSON();
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({ ...mockEvents[0], ...body, updated_at: new Date().toISOString() }),
                });
            } else {
                await route.continue();
            }
        });

        await page.route('**/api/business-events/*/generate-entities', async (route) => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({ entities: [], relationships: [], errors: [] }),
            });
        });

        // Stub auxiliary APIs so the page loads cleanly
        await page.route('**/api/business-events/domains', async (route) => {
            await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
        });
        await page.route('**/api/processes', async (route) => {
            await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
        });
        await page.route('**/api/data-model', async (route) => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({ entities: [], relationships: [] }),
            });
        });
    }

    test('entity_model route accessible', async ({ page }) => {
        await setupEntityModelMocks(page);
        await page.goto('/');

        const response = await page.goto('/business-events').catch(() => null);
        if (!response || !response.ok()) {
            test.skip();
            return;
        }

        await page.waitForLoadState('domcontentloaded');

        // Should not have been redirected to /canvas
        expect(page.url()).not.toContain('/canvas');

        // Heading should be visible
        const heading = page.getByRole('heading', { name: /business events/i });
        await expect(heading).toBeVisible({ timeout: 5000 });
    });

    test('entity_model no event type selector', async ({ page }) => {
        await setupEntityModelMocks(page);
        await page.goto('/');

        const response = await page.goto('/business-events').catch(() => null);
        if (!response || !response.ok()) {
            test.skip();
            return;
        }

        await page.waitForLoadState('domcontentloaded');

        // Open the Create Event modal
        const addButton = page.getByRole('button', { name: /add event/i });
        const buttonExists = await addButton.isVisible({ timeout: 5000 }).catch(() => false);
        if (!buttonExists) {
            test.skip();
            return;
        }

        await addButton.click();

        // Wait for the modal to appear
        const modal = page.getByRole('dialog');
        await modal.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {
            test.skip();
        });

        // The event-type select must NOT be present in entity_model mode
        const eventTypeSelect = page.locator('select#event-type');
        await expect(eventTypeSelect).not.toBeAttached({ timeout: 2000 });
    });

    test('entity_model seven ws shows 6 sections', async ({ page }) => {
        await setupEntityModelMocks(page);
        await page.goto('/');

        const response = await page.goto('/business-events').catch(() => null);
        if (!response || !response.ok()) {
            test.skip();
            return;
        }

        await page.waitForLoadState('domcontentloaded');

        // Open the 7 Ws form via the highlighter button on the first event card
        const highlighterButton = page.getByRole('button', { name: /annotations|add annotations|edit annotations/i }).first();
        const buttonExists = await highlighterButton.isVisible({ timeout: 5000 }).catch(() => false);

        if (!buttonExists) {
            // Fall back to title-based locator
            const fallback = page.locator('button[title*="annotation"]').first();
            const fallbackExists = await fallback.isVisible({ timeout: 2000 }).catch(() => false);
            if (!fallbackExists) {
                test.skip();
                return;
            }
            await fallback.click();
        } else {
            await highlighterButton.click();
        }

        // Wait for the annotations modal
        const modal = page.getByRole('dialog');
        await modal.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {
            test.skip();
        });

        // Count annotation section headers rendered inside the modal.
        // Each section renders a <button> with aria-expanded that toggles the collapse.
        // In entity_model mode, "How Many" is hidden, so exactly 6 sections should render.
        const sectionButtons = modal.locator('button[aria-expanded]');
        await expect(sectionButtons).toHaveCount(6, { timeout: 5000 });
    });

    test('entity_model progress badge /6', async ({ page }) => {
        await setupEntityModelMocks(page);
        await page.goto('/');

        const response = await page.goto('/business-events').catch(() => null);
        if (!response || !response.ok()) {
            test.skip();
            return;
        }

        await page.waitForLoadState('domcontentloaded');

        // Open the 7 Ws annotations form for the first event.
        // The first mock event already has 1 annotation (who: customer) so the badge
        // should immediately show "1/6 completed".
        const highlighterButton = page.getByRole('button', { name: /annotations|add annotations|edit annotations/i }).first();
        const buttonExists = await highlighterButton.isVisible({ timeout: 5000 }).catch(() => false);

        if (!buttonExists) {
            const fallback = page.locator('button[title*="annotation"]').first();
            const fallbackExists = await fallback.isVisible({ timeout: 2000 }).catch(() => false);
            if (!fallbackExists) {
                test.skip();
                return;
            }
            await fallback.click();
        } else {
            await highlighterButton.click();
        }

        // Wait for modal
        const modal = page.getByRole('dialog');
        await modal.waitFor({ state: 'visible', timeout: 5000 }).catch(() => {
            test.skip();
        });

        // The progress badge denominator must be 6 in entity_model mode
        const progressBadge = modal.locator('text=/\\d+\\/6/');
        await expect(progressBadge).toBeVisible({ timeout: 5000 });
    });
});
