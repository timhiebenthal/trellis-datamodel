import * as path from 'path';
import * as fs from 'fs';
import { fileURLToPath } from 'url';
import { execSync } from 'child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const TEST_DATA_MODEL_PATH = path.resolve(__dirname, 'test_data_model.yml');

async function globalSetup() {
    // Create a temporary trellis.yml config file for tests
    // This enables dimensional_model features like Auto Layout
    const CONFIG_DIR = path.resolve(__dirname, '.trellis-test');

    if (!fs.existsSync(CONFIG_DIR)) {
        fs.mkdirSync(CONFIG_DIR, { recursive: true });
    }

    // Compile dbt projects to generate manifests before tests run
    console.log('Compiling dbt projects for tests...');

    // Note: dbt_concept is not a dbt project, just a data model directory - skip compilation

    // Compile dbt_company_dummy (used by lineage tests)
    const dbtCompanyDummyPath = path.resolve(__dirname, '..', '..', 'dbt_company_dummy');
    try {
        execSync('uv run dbt compile --profiles-dir .', {
            cwd: dbtCompanyDummyPath,
            stdio: 'inherit'
        });
        console.log('✓ dbt_company_dummy manifest generated');
    } catch (e) {
        console.error('Warning: dbt_company_dummy compilation failed:', e);
    }

    const TEST_CONFIG_PATH = path.join(CONFIG_DIR, 'trellis.yml');

    // Write test config file
    // Use dbt_company_dummy as the dbt project since dbt_concept is not a real dbt project
    const TEST_CONFIG = `framework: dbt-core
dbt_project_path: ${dbtCompanyDummyPath}
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

    // Set environment variable for backend to use test config
    process.env['TRELLIS_CONFIG_PATH'] = TEST_CONFIG_PATH;
}

export default globalSetup;
