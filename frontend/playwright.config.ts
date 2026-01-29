import { defineConfig, devices } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Path to test data file (isolated from production data)
const TEST_DATA_MODEL_PATH = path.resolve(__dirname, 'tests/test_data_model.yml');

// Path to test config file (created by global-setup.ts)
const TEST_CONFIG_DIR = path.resolve(__dirname, 'tests/.trellis-test');
const TEST_CONFIG_PATH = path.join(TEST_CONFIG_DIR, 'trellis.yml');

// Ensure the Playwright backend always has a test config before servers start.
// This mirrors the logic in tests/global-setup.ts so webServer startup never races
// with config creation (seen as 500s when DATA_MODEL_PATH is empty).
if (!fs.existsSync(TEST_CONFIG_DIR)) {
    fs.mkdirSync(TEST_CONFIG_DIR, { recursive: true });
}
const TEST_CONFIG_CONTENT = `framework: dbt-core
dbt_project_path: ${path.resolve(__dirname, '..', 'dbt_concept')}
data_model_file: ${TEST_DATA_MODEL_PATH}
modeling_style: dimensional_model
lineage:
  enabled: false
bus_matrix:
  enabled: true

# Optional: enable other features if needed
# business_events:
#   enabled: true
# exposures:
#   enabled: true
`;
fs.writeFileSync(TEST_CONFIG_PATH, TEST_CONFIG_CONTENT);

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
        /* Base URL to use in actions like `await page.goto('')`. */
        baseURL: 'http://localhost:5173',

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
            // Frontend dev server
            command: 'npm run dev',
            env: {
                // Point frontend Vite proxy to test backend API
                VITE_DEV_API_TARGET: 'http://localhost:8000',
            },
            url: 'http://localhost:5173',
            reuseExistingServer: !process.env.CI,
        },
    ],
});
