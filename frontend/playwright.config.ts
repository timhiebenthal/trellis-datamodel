import { defineConfig, devices } from '@playwright/test';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Path to test data file (isolated from production data)
const TEST_DATA_MODEL_PATH = path.resolve(__dirname, 'tests/test_data_model.yml');

/**
 * See https://playwright.dev/docs/test-configuration.
 */
export default defineConfig({
    testDir: './tests',
    globalSetup: './tests/global-setup.ts',
    globalTeardown: './tests/global-teardown.ts',
    /* Run tests in files in parallel - disabled locally to prevent WSL2 memory issues */
    fullyParallel: !!process.env.CI,
    /* Fail the build on CI if you accidentally left test.only in the source code. */
    forbidOnly: !!process.env.CI,
    /* Retry on CI only */
    retries: process.env.CI ? 2 : 0,
    /* Limit workers locally to prevent WSL2 crashes */
    workers: process.env.CI ? 4 : 1,
    /* Reporter to use. See https://playwright.dev/docs/test-reporters */
    reporter: 'html',
    /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
    use: {
        /* Base URL to use in actions like `await page.goto('')`. */
        baseURL: 'http://localhost:5173',

        /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
        trace: 'on-first-retry',
    },

    /* Configure projects for major browsers */
    /* Note: Only chromium runs locally to save resources. CI runs all browsers. */
    projects: process.env.CI
        ? [
              {
                  name: 'chromium',
                  use: { ...devices['Desktop Chrome'] },
              },
              {
                  name: 'firefox',
                  use: { ...devices['Desktop Firefox'] },
              },
              {
                  name: 'webkit',
                  use: { ...devices['Desktop Safari'] },
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
            command: `cd ${path.resolve(__dirname, '..')} && DATAMODEL_TEST_DIR=${path.dirname(TEST_DATA_MODEL_PATH)} DATAMODEL_DATA_MODEL_PATH=${TEST_DATA_MODEL_PATH} uv run trellis run --port 8000 --no-browser`,
            url: 'http://localhost:8000/health',
            reuseExistingServer: !process.env.CI,
            timeout: 30000,
        },
        {
            // Frontend dev server
            command: 'npm run dev',
            env: {
                // Point frontend to backend API during tests
                PUBLIC_API_URL: 'http://localhost:8000/api',
            },
            url: 'http://localhost:5173',
            reuseExistingServer: !process.env.CI,
        },
    ],
});
