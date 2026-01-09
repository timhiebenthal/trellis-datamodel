import * as path from 'path';
import * as fs from 'fs';
import { fileURLToPath } from 'url';

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
    
    const TEST_CONFIG_PATH = path.join(CONFIG_DIR, 'trellis.yml');
    const TEST_CONFIG = `framework: dbt-core
dbt_project_path: .
modeling_style: dimensional_model

# Optional: enable other features if needed
# exposures:
#   enabled: true
# lineage:
#   enabled: true
# bus_matrix:
#   enabled: true
`;
    
    // Write test config file
    fs.writeFileSync(TEST_CONFIG_PATH, TEST_CONFIG);
    
    // Set environment variable for backend to use test config
    process.env['TRELLIS_CONFIG_PATH'] = TEST_CONFIG_PATH;
}

export default globalSetup;

