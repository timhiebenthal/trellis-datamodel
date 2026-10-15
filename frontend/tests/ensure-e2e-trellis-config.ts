/**
 * Synchronously prepare trellis.yml + dbt artifacts + test servers for Playwright E2E.
 *
 * Must run when playwright.config.ts loads — before webServer starts.
 * (Playwright starts webServers before globalSetup, so globalSetup alone races the backend.)
 *
 * Cost tiers (measured in GitHub issue #142):
 *  1. Artifacts fresh + servers already running → a few fs checks, no subprocesses.
 *  2. Artifacts fresh, servers down             → spawn both detached, wait for health.
 *  3. Artifacts stale/missing                   → run the full dbt pipeline ONCE,
 *                                                 guarded by a lock so concurrent
 *                                                 module loads don't duplicate it.
 *
 * Notes:
 *  - The dbt pipeline mirrors CI (.github/workflows/ci.yml): generate CSVs → dbt run →
 *    dbt docs generate. `dbt compile` alone can never produce catalog.json, and
 *    artifactsFresh() treats a missing catalog as stale.
 *  - Server spawning is skipped on CI (process.env.CI): Playwright owns the server
 *    lifecycle there.
 *  - Servers we spawn are deliberately left running after teardown; the next Playwright
 *    invocation reuses them (webServer url health checks) instead of re-paying boot and
 *    the Playwright port probe. Kill them with:
 *      pkill -f 'trellis_datamodel.cli run --port 8000'
 *      pkill -f 'vite dev --port 5174'
 */
import * as path from 'path';
import * as fs from 'fs';
import * as http from 'http';
import { execSync, spawn as nodeSpawn } from 'child_process';
import { fileURLToPath } from 'url';
import { buildBootFixture } from './boot-fixture';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const TEST_DATA_MODEL_PATH = path.resolve(__dirname, 'test_data_model.yml');
const CONFIG_DIR = path.resolve(__dirname, '.trellis-test');
const TEST_CONFIG_PATH = path.join(CONFIG_DIR, 'trellis.yml');

const REPO_ROOT = path.resolve(__dirname, '..', '..');
const dbtCompanyDummyPath = path.join(REPO_ROOT, 'dbt_company_dummy');
const manifestPath = path.join(dbtCompanyDummyPath, 'target', 'manifest.json');
const catalogPath = path.join(dbtCompanyDummyPath, 'target', 'catalog.json');

const BACKEND_PORT = 8000;
const FRONTEND_PORT = 5174;
const BACKEND_HEALTH_URL = `http://127.0.0.1:${BACKEND_PORT}/health`;
const FRONTEND_HEALTH_URL = `http://127.0.0.1:${FRONTEND_PORT}/`;
const DBT_TOOL = 'uvx --from dbt-duckdb==1.8.2';
const SERVER_BUDGET_MS = 25_000;
const WAIT_POLL_MS = 250;
const LOCK_TIMEOUT_MS = 12 * 60 * 1000;

// Staleness sources for the artifacts: if any of these is newer than manifest.json,
// the artifacts were built against an older project and must be regenerated.
const DBT_SOURCES = [
    path.join(dbtCompanyDummyPath, 'dbt_project.yml'),
    path.join(dbtCompanyDummyPath, 'profiles.yml'),
    path.join(dbtCompanyDummyPath, 'models'),
    path.join(dbtCompanyDummyPath, 'macros'),
    path.join(dbtCompanyDummyPath, 'data'),
];

/** Latest mtime under a file/dir tree (0 if missing). */
function maxMtime(target: string): number {
    let st: fs.Stats;
    try {
        st = fs.statSync(target);
    } catch {
        return 0;
    }
    if (st.isFile()) return st.mtimeMs;
    let max = st.mtimeMs;
    try {
        for (const entry of fs.readdirSync(target)) {
            max = Math.max(max, maxMtime(path.join(target, entry)));
        }
    } catch {
        /* unreadable dir — the dir's own mtime is the signal */
    }
    return max;
}

/**
 * True when manifest + catalog exist and are newer than every dbt source.
 * This is the fast path: it makes the repeated module loads (config eval,
 * globalSetup, worker re-eval) cheap after the first one.
 */
function artifactsFresh(): boolean {
    let manifestMtime = 0;
    try {
        if (fs.statSync(manifestPath).size < 32) return false;
        manifestMtime = fs.statSync(manifestPath).mtimeMs;
        fs.statSync(catalogPath); // throws if missing
    } catch {
        return false;
    }
    for (const source of DBT_SOURCES) {
        if (maxMtime(source) > manifestMtime) return false;
    }
    return true;
}

function run(command: string, cwd: string): void {
    execSync(command, { cwd, stdio: 'inherit' });
}

/**
 * One-shot artifact pipeline, CI parity:
 *   generate mock CSVs (only when absent) → dbt run → dbt docs generate.
 * `dbt docs generate` is what writes catalog.json; `dbt compile` alone cannot.
 */
function generateDbtArtifacts(): boolean {
    if (!fs.existsSync(path.join(dbtCompanyDummyPath, 'data', 'customer.csv'))) {
        console.log('[ensure-e2e-trellis-config] Generating mock data csvs...');
        run('uv run --extra dbt-example python dbt_company_dummy/generate_data.py', REPO_ROOT);
    }
    const vars = `--vars "data_path: ${dbtCompanyDummyPath}/data"`;
    console.log('[ensure-e2e-trellis-config] Regenerating dbt artifacts (dbt run + docs generate)...');
    run(`${DBT_TOOL} dbt run --project-dir . --profiles-dir . ${vars}`, dbtCompanyDummyPath);
    run(`${DBT_TOOL} dbt docs generate --project-dir . --profiles-dir . ${vars}`, dbtCompanyDummyPath);
    if (!artifactsFresh()) {
        console.error('[ensure-e2e-trellis-config] dbt pipeline finished but artifacts are still stale');
        return false;
    }
    return true;
}

// ————— single-flight lock so concurrent config loads compile at most once —————

const LOCK_DIR = path.join(CONFIG_DIR, '.dbt-pipeline.lock');
const LOCK_OWNER_FILE = path.join(LOCK_DIR, 'owner');

function pidAlive(pid: number): boolean {
    try {
        process.kill(pid, 0);
        return true;
    } catch {
        return false;
    }
}

function lockHolderPid(): number | null {
    if (!fs.existsSync(LOCK_DIR)) return null;
    try {
        const owner = fs.readFileSync(LOCK_OWNER_FILE, 'utf8').split('-')[0];
        const pid = Number.parseInt(owner, 10);
        return Number.isFinite(pid) ? pid : null;
    } catch {
        return null;
    }
}

function acquireLock(): boolean {
    try {
        fs.mkdirSync(LOCK_DIR, { recursive: false });
    } catch {
        return false; // already exists
    }
    const holder = lockHolderPid();
    if (holder !== null && holder !== process.pid && pidAlive(holder)) {
        // A live process re-created the lock between our mkdir and read — give it back.
        fs.rmdirSync(LOCK_DIR);
        return false;
    }
    fs.writeFileSync(LOCK_OWNER_FILE, `${process.pid}-at-${Date.now()}`, 'utf8');
    return true;
}

function releaseLock(): void {
    try {
        fs.rmSync(LOCK_DIR, { recursive: true, force: true });
    } catch {
        /* nothing to clean */
    }
}

const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

/** Block (bounded) until the lock holder finishes its pipeline, or take over if it died. */
async function waitBehindLock(): Promise<void> {
    const deadline = Date.now() + LOCK_TIMEOUT_MS;
    while (Date.now() < deadline && !artifactsFresh()) {
        const holder = lockHolderPid();
        if (holder === null || !pidAlive(holder)) {
            if (acquireLock()) {
                console.log('[ensure-e2e-trellis-config] took over stale dbt pipeline lock');
                break;
            }
        }
        await sleep(WAIT_POLL_MS);
    }
    if (!artifactsFresh()) {
        console.error('[ensure-e2e-trellis-config] timed out waiting for another process to prepare dbt artifacts');
    }
}

// ————— detached test servers (skipped on CI; Playwright owns servers there) —————

function probe200(url: string, timeoutMs: number): Promise<boolean> {
    return new Promise((resolve) => {
        const req = http.get(url, { timeout: timeoutMs }, (res) => resolve(res.statusCode === 200));
        req.on('timeout', () => {
            req.destroy();
            resolve(false);
        });
        req.on('error', () => resolve(false));
    });
}

async function serverUp(url: string): Promise<boolean> {
    return probe200(url, 3_000);
}

async function waitServerUp(url: string, budgetMs: number): Promise<boolean> {
    const deadline = Date.now() + budgetMs;
    while (Date.now() < deadline) {
        if (await probe200(url, 1_000)) return true;
        await sleep(WAIT_POLL_MS);
    }
    return false;
}

function startDetached(name: string, command: string, cwd: string, envExtra: Record<string, string>): void {
    const logFd = fs.openSync(path.join(CONFIG_DIR, `${name}.log`), 'a');
    const child = nodeSpawn('bash', ['-c', command], {
        cwd,
        detached: true,
        stdio: ['ignore', logFd, logFd],
        env: { ...process.env, ...envExtra },
    });
    child.on('error', (err) => console.error(`[ensure-e2e-trellis-config] ${name} spawn failed:`, err));
    child.unref();
    console.log(`[ensure-e2e-trellis-config] started ${name} (pid ${child.pid}, log: tests/.trellis-test/${name}.log)`);
}

const BACKEND_COMMAND =
    `uv run python -m trellis_datamodel.cli run --port ${BACKEND_PORT} --no-browser --config "${TEST_CONFIG_PATH}"`;
const FRONTEND_COMMAND = `npm run dev -- --port ${FRONTEND_PORT}`;

function killBackend(): void {
    try {
        execSync(`pkill -f 'trellis_datamodel.cli run --port ${BACKEND_PORT}' 2>/dev/null || true`, {
            stdio: 'ignore',
        });
    } catch {
        /* pkill is best-effort */
    }
}

/**
 * Spawn both servers detached when they are not already up, and give them time to bind.
 * After a fresh artifact generation the backend must be restarted so it boots against
 * the new manifest/catalog instead of the copy it cached at startup.
 */
async function ensureServersUp(regeneratedArtifacts: boolean): Promise<void> {
    const backendUp = await serverUp(BACKEND_HEALTH_URL);
    if (backendUp && regeneratedArtifacts) {
        console.log('[ensure-e2e-trellis-config] restarting backend to pick up regenerated artifacts');
        killBackend();
        await sleep(1_000);
        startDetached('backend', BACKEND_COMMAND, REPO_ROOT, {});
        await waitServerUp(BACKEND_HEALTH_URL, SERVER_BUDGET_MS);
    } else if (!backendUp) {
        startDetached('backend', BACKEND_COMMAND, REPO_ROOT, {});
        const up = await waitServerUp(BACKEND_HEALTH_URL, SERVER_BUDGET_MS);
        if (!up) console.error('[ensure-e2e-trellis-config] backend did not come up in time; Playwright will retry its own boot');
    }

    if (!(await serverUp(FRONTEND_HEALTH_URL))) {
        startDetached(
            'frontend',
            FRONTEND_COMMAND,
            path.join(REPO_ROOT, 'frontend'),
            { VITE_DEV_API_TARGET: `http://localhost:${BACKEND_PORT}` },
        );
        const up = await waitServerUp(FRONTEND_HEALTH_URL, SERVER_BUDGET_MS);
        if (!up) console.error('[ensure-e2e-trellis-config] frontend did not come up in time; Playwright will retry its own boot');
    }
}

export async function ensureE2ETrellisConfig(): Promise<void> {
    fs.mkdirSync(CONFIG_DIR, { recursive: true });

    if (process.env['TRELLIS_BOOT_BENCHMARK'] === '1') {
        const fixture = buildBootFixture();
        const benchmarkConfig = `framework: dbt-core
dbt_project_path: ${fixture.projectDir}
dbt_manifest_path: ${fixture.manifestPath}
dbt_catalog_path: ${fixture.catalogPath}
data_model_file: ${fixture.dataModelPath}
canvas_layout_file: ${fixture.layoutPath}
dbt_model_paths:
  - models/boot_fixture
modeling_style: dimensional_model
lineage:
  enabled: false
bus_matrix:
  enabled: true
business_events:
  enabled: true
`;
        fs.writeFileSync(TEST_CONFIG_PATH, benchmarkConfig);
        process.env['TRELLIS_CONFIG_PATH'] = TEST_CONFIG_PATH;
        return;
    }

    let regeneratedArtifacts = false;
    if (!artifactsFresh()) {
        if (acquireLock()) {
            try {
                if (!artifactsFresh()) { // re-check after winning the lock
                    regeneratedArtifacts = generateDbtArtifacts();
                }
            } finally {
                releaseLock();
            }
        } else {
            await waitBehindLock();
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

    if (!process.env.CI) {
        await ensureServersUp(regeneratedArtifacts);
    }
}

export { TEST_CONFIG_PATH, CONFIG_DIR, TEST_DATA_MODEL_PATH };
