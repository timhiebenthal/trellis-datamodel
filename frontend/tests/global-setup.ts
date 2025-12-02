import * as path from 'path';
import * as fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const TEST_DATA_MODEL_PATH = path.resolve(__dirname, 'test_data_model.yml');

async function globalSetup() {
    // Ensure test data file exists and is clean
    if (!fs.existsSync(TEST_DATA_MODEL_PATH)) {
        fs.writeFileSync(TEST_DATA_MODEL_PATH, 'version: 0.1\nentities: []\nrelationships: []\n');
    } else {
        // Reset to empty state
        fs.writeFileSync(TEST_DATA_MODEL_PATH, 'version: 0.1\nentities: []\nrelationships: []\n');
    }
}

export default globalSetup;

