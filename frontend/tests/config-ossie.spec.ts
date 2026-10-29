import { test, expect } from '@playwright/test';
import { applyConfigOverrides, restoreConfig } from './helpers';

test.describe.configure({ mode: 'serial' });

const DANGER_ZONE_ACK = 'I understand these features are experimental and may change';

test.describe('Apache Ossie config section', () => {
    test('toggles ossie.enabled, clears an override, saves and round-trips on reload', async ({ page, request }) => {
        const originalConfig = await applyConfigOverrides(request, {
            ossie: { enabled: false, source: { database: 'analytics' } },
        });

        try {
            await page.goto('/config');
            await page.getByLabel(DANGER_ZONE_ACK).check();

            await expect(page.getByLabel('Ossie Export Enabled')).not.toBeChecked();
            await expect(page.getByLabel('Database Override')).toHaveValue('analytics');

            await page.locator('label:has(#ossie-enabled-toggle)').click();
            await page.getByLabel('Database Override').fill('');
            await page.getByLabel('Schema Override').fill('marts');

            await page.getByRole('button', { name: 'Apply Configuration' }).click();
            await expect(page.getByText('Configuration saved and reloaded successfully')).toBeVisible();

            await page.reload();
            await page.getByLabel(DANGER_ZONE_ACK).check();
            await expect(page.getByLabel('Ossie Export Enabled')).toBeChecked();
            await expect(page.getByLabel('Database Override')).toHaveValue('');
            await expect(page.getByLabel('Schema Override')).toHaveValue('marts');
        } finally {
            await restoreConfig(request, originalConfig);
        }
    });
});
