import { test, expect } from '@playwright/test';

test('smoke test - app loads without errors', async ({ page }) => {
    await page.addInitScript(() => {
        // Flag to let frontend short-circuit noisy calls during smoke
        (window as any).__SMOKE_TEST__ = true;
    });

    // Collect console errors
    const consoleErrors: string[] = [];
    page.on('console', (msg) => {
        if (msg.type() === 'error') {
            consoleErrors.push(msg.text());
        }
    });

    // Navigate to app
    const response = await page.goto('/');
    
    // Check HTTP response is OK (not 500, 404, etc)
    expect(response?.status(), 'Page should return 200 OK').toBeLessThan(400);

    // Check page doesn't show error message
    const bodyText = await page.textContent('body');
    expect(bodyText).not.toContain('500');
    expect(bodyText).not.toContain('Internal Error');
    expect(bodyText).not.toContain('Internal Server Error');

    // Wait a moment for any runtime errors to appear
    await page.waitForTimeout(1000);

    // Check no critical console errors (filter out expected warnings)
    const criticalErrors = consoleErrors.filter((err) => 
        !err.includes('favicon') && 
        !err.includes('404') &&
        !err.includes('inferring relationships') &&
        !err.includes('infer-relationships') &&
        // Filter out generic browser 400 errors (WebKit logs these for relationship inference when no schema files exist)
        !(err.includes('400') && err.includes('Bad Request'))
    );
    expect(criticalErrors, 'No critical console errors').toHaveLength(0);

    // If we got here without 500 errors and no critical console errors,
    // the app at least bootstrapped. UI elements may need backend.
    // Check title if available (proves app bootstrapped)
    const title = await page.title();
    if (title) {
        expect(title).toMatch(/Data Model UI/);
    }

    // These checks may fail if backend is not running - that's ok for smoke test
    // The main goal is to catch 500 errors and runtime crashes
});
