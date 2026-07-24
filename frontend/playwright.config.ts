import { defineConfig, devices } from '@playwright/test';
import * as path from 'path';
import { fileURLToPath } from 'url';
import { ensureE2ETrellisConfig, TEST_CONFIG_PATH } from './tests/ensure-e2e-trellis-config';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Run before webServer: Playwright starts webServers before globalSetup, so the backend
// must see a valid trellis.yml on first boot (see ensure-e2e-trellis-config.ts).
ensureE2ETrellisConfig();

/**
 * See https://playwright.dev/docs/test-configuration.
 */
export default defineConfig({
    testDir: './tests',
    globalSetup: './tests/global-setup.ts',
    globalTeardown: './tests/global-teardown.ts',
    /* Run tests in files in parallel - disabled to prevent collisions on shared backend data model */
    fullyParallel: false,
    /* Fail the build on CI if you accidentally left test.only in the source code. */
    forbidOnly: !!process.env.CI,
    /* Retry on CI only */
    retries: process.env.CI ? 2 : 0,
    /* Limit workers to 1 to prevent collisions on shared backend data model */
    workers: 1,
    /* Reporter to use. See https://playwright.dev/docs/test-reporters */
    reporter: 'html',
    /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
    use: {
        /* Dedicated dev port so E2E does not collide with a running `make frontend` on 5173. */
        baseURL: 'http://localhost:5174',

        /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
        trace: 'on-first-retry',
    },

    /* Configure projects for major browsers */
    /* Note: Only chromium runs (locally and in CI) to keep CI time reasonable. */
    projects: process.env.CI
        ? [
              {
                  name: 'chromium',
                  use: { ...devices['Desktop Chrome'] },
              },
          ]
        : [
              {
                  name: 'chromium',
                  use: { ...devices['Desktop Chrome'] },
              },
          ],

    /* Start both frontend and backend servers for tests */
    webServer: [
        {
            // Backend with test data file
            command: `cd ${path.resolve(__dirname, '..')} && PYTHONPATH=. uv run python -m trellis_datamodel.cli run --port 8000 --no-browser --config "${TEST_CONFIG_PATH}"`,
            url: 'http://localhost:8000/health',
            reuseExistingServer: !process.env.CI,
            timeout: 30000,
        },
        {
            // Frontend dev server on 5174 — avoids colliding with `make frontend` on 5173.
            command: 'npm run dev -- --port 5174',
            env: {
                VITE_DEV_API_TARGET: 'http://localhost:8000',
            },
            url: 'http://localhost:5174',
            reuseExistingServer: false,
        },
    ],
});
