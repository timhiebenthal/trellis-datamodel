/**
 * Synchronously prepare trellis.yml + dbt artifacts for Playwright E2E.
 *
 * Must run when playwright.config.ts loads — before webServer starts.
 * (Playwright starts webServers before globalSetup, so globalSetup alone races the backend.)
 */
import * as path from 'path';
import * as fs from 'fs';
import { fileURLToPath } from 'url';
import { execSync } from 'child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const TEST_DATA_MODEL_PATH = path.resolve(__dirname, 'test_data_model.yml');
const CONFIG_DIR = path.resolve(__dirname, '.trellis-test');
const TEST_CONFIG_PATH = path.join(CONFIG_DIR, 'trellis.yml');

const dbtCompanyDummyPath = path.resolve(__dirname, '..', '..', 'dbt_company_dummy');
const manifestPath = path.join(dbtCompanyDummyPath, 'target', 'manifest.json');
const catalogPath = path.join(dbtCompanyDummyPath, 'target', 'catalog.json');

export function ensureE2ETrellisConfig(): void {
    if (!fs.existsSync(CONFIG_DIR)) {
        fs.mkdirSync(CONFIG_DIR, { recursive: true });
    }

    const manifestStale =
        !fs.existsSync(manifestPath) ||
        !fs.existsSync(catalogPath) ||
        fs.statSync(manifestPath).size < 32;

    if (manifestStale) {
        console.log('[ensure-e2e-trellis-config] Compiling dbt_company_dummy...');
        try {
            execSync('uvx --from dbt-duckdb==1.8.2 dbt compile --profiles-dir .', {
                cwd: dbtCompanyDummyPath,
                stdio: 'inherit',
            });
            console.log('[ensure-e2e-trellis-config] dbt compile finished');
        } catch (e) {
            console.error('[ensure-e2e-trellis-config] dbt compile failed:', e);
        }
    }

    const TEST_CONFIG = `framework: dbt-core
dbt_project_path: ${dbtCompanyDummyPath}
dbt_manifest_path: ${manifestPath}
dbt_catalog_path: ${catalogPath}
data_model_file: ${TEST_DATA_MODEL_PATH}
modeling_style: dimensional_model
lineage:
  enabled: false
bus_matrix:
  enabled: true
business_events:
  enabled: true

# Optional: enable other features if needed
# exposures:
#   enabled: true
`;

    fs.writeFileSync(TEST_CONFIG_PATH, TEST_CONFIG);
    process.env['TRELLIS_CONFIG_PATH'] = TEST_CONFIG_PATH;
}

export { TEST_CONFIG_PATH, CONFIG_DIR, TEST_DATA_MODEL_PATH };
