import type { APIRequestContext, Page } from '@playwright/test';
import * as path from 'path';
import { fileURLToPath } from 'url';

// Playwright pages use the frontend baseURL (localhost:5173). Point API calls to the backend.
const API_URL = process.env.VITE_PUBLIC_API_URL || 'http://localhost:8000/api';
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const REPO_ROOT = path.resolve(__dirname, '..', '..');
const DBT_COMPANY_DUMMY_PATH = path.join(REPO_ROOT, 'dbt_company_dummy');

type ConfigFileInfo = {
    mtime: number;
    hash: string;
};

type ConfigResponse = {
    config: Record<string, any>;
    file_info?: ConfigFileInfo | null;
};

export type DataModelPayload = {
    version: number;
    entities: Array<Record<string, any>>;
    relationships: Array<Record<string, any>>;
};

const EMPTY_DATA_MODEL: DataModelPayload = {
    version: 0.1,
    entities: [],
    relationships: [],
};

/**
 * Reset the backend data model to an empty state via the API.
 * This is faster and more reliable than driving the UI for cleanup.
 */
export async function resetDataModel(
    request: APIRequestContext,
    dataModel: DataModelPayload = EMPTY_DATA_MODEL,
): Promise<void> {
    const res = await request.post(`${API_URL}/data-model`, { data: dataModel });
    if (!res.ok()) {
        throw new Error(`Failed to reset data model: ${res.status()} ${res.statusText()}`);
    }
}

export async function getConfig(
    request: APIRequestContext,
): Promise<ConfigResponse> {
    const res = await request.get(`${API_URL}/config`);
    if (!res.ok()) {
        throw new Error(`Failed to fetch config: ${res.status()} ${res.statusText()}`);
    }
    return (await res.json()) as ConfigResponse;
}

export async function saveConfig(
    request: APIRequestContext,
    config: Record<string, any>,
    fileInfo?: ConfigFileInfo | null,
): Promise<void> {
    const res = await request.put(`${API_URL}/config`, {
        data: {
            config,
            expected_mtime: fileInfo?.mtime ?? null,
            expected_hash: fileInfo?.hash ?? null,
        },
    });
    if (!res.ok()) {
        throw new Error(`Failed to update config: ${res.status()} ${res.statusText()}`);
    }
}

export async function reloadConfig(request: APIRequestContext): Promise<void> {
    const res = await request.post(`${API_URL}/config/reload`);
    if (!res.ok()) {
        throw new Error(`Failed to reload config: ${res.status()} ${res.statusText()}`);
    }
}

export async function applyConfigOverrides(
    request: APIRequestContext,
    overrides: Record<string, any>,
): Promise<Record<string, any>> {
    const current = await getConfig(request);
    const nextConfig = {
        ...current.config,
        ...overrides,
    };
    await saveConfig(request, nextConfig, current.file_info ?? null);
    await reloadConfig(request);
    return current.config;
}

export async function restoreConfig(
    request: APIRequestContext,
    config: Record<string, any>,
): Promise<void> {
    const current = await getConfig(request);
    await saveConfig(request, config, current.file_info ?? null);
    await reloadConfig(request);
}

export function getCompanyDummyConfigOverrides(): Record<string, any> {
    return {
        dbt_project_path: DBT_COMPANY_DUMMY_PATH,
        dbt_manifest_path: path.join(DBT_COMPANY_DUMMY_PATH, 'target', 'manifest.json'),
        dbt_catalog_path: path.join(DBT_COMPANY_DUMMY_PATH, 'target', 'catalog.json'),
    };
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

/**
 * Complete the entity creation wizard by skipping through all steps
 * This handles the wizard modal that appears when `guidance.entity_wizard.enabled` is true
 */
export async function completeEntityWizard(page: Page): Promise<void> {
    // Check if wizard modal is visible
    const wizardModal = page.getByRole('dialog', { name: /create new entity/i });
    const isWizardVisible = await wizardModal.isVisible({ timeout: 2000 }).catch(() => false);
    
    if (!isWizardVisible) {
        // Wizard might be disabled, entity should appear directly
        return;
    }

    // Skip through all steps - the wizard has up to 3 steps
    // We'll click "Skip" or "Done" until the modal closes
    let attempts = 0;
    const maxAttempts = 5; // Safety limit
    
    while (await wizardModal.isVisible({ timeout: 500 }).catch(() => false) && attempts < maxAttempts) {
        // Try "Done" button first (final step)
        const doneBtn = page.getByRole('button', { name: 'Done' });
        if (await doneBtn.isVisible({ timeout: 500 }).catch(() => false)) {
            await doneBtn.click();
            await page.waitForTimeout(300);
            break;
        }
        
        // Otherwise try "Skip" button
        const skipBtn = page.getByRole('button', { name: 'Skip' });
        if (await skipBtn.isVisible({ timeout: 500 }).catch(() => false)) {
            await skipBtn.click();
            await page.waitForTimeout(300);
        } else {
            // No buttons found, break to avoid infinite loop
            break;
        }
        
        attempts++;
    }

    // Wait for wizard to close
    await wizardModal.waitFor({ state: 'hidden', timeout: 3000 }).catch(() => {});
}
