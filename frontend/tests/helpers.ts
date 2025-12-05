import type { APIRequestContext, Page } from '@playwright/test';

// Playwright pages use the frontend baseURL (localhost:5173). Point API calls to the backend.
const API_URL = process.env.VITE_PUBLIC_API_URL || 'http://localhost:8000/api';

const EMPTY_DATA_MODEL = {
    version: 0.1,
    entities: [],
    relationships: [],
};

/**
 * Reset the backend data model to an empty state via the API.
 * This is faster and more reliable than driving the UI for cleanup.
 */
export async function resetDataModel(request: APIRequestContext): Promise<void> {
    await request.post(`${API_URL}/data-model`, {
        data: EMPTY_DATA_MODEL,
    });
}

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
        // Prefer API reset to avoid UI flakiness and keep tests isolated.
        await resetDataModel(page.request);
    } catch (e) {
        // Ignore cleanup errors - tests should still pass
        console.log('Cleanup warning (non-fatal):', e);
    }
}

