import { ensureE2ETrellisConfig } from './ensure-e2e-trellis-config';

async function globalSetup() {
    // Idempotent: playwright.config.ts already ran this before webServer; repeat here so
    // standalone `playwright test --global-setup-only` or future runners stay consistent.
    ensureE2ETrellisConfig();
}

export default globalSetup;
