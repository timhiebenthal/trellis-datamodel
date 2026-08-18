import {
    expect,
    test,
    type Browser,
    type Page,
    type Request,
    type Response,
} from '@playwright/test';
import { spawn, type ChildProcess } from 'node:child_process';
import { createHash } from 'node:crypto';
import * as fs from 'node:fs';
import * as os from 'node:os';
import * as path from 'node:path';

import { BOOT_FIXTURE_COUNTS } from './boot-fixture';
import { TEST_CONFIG_PATH } from './ensure-e2e-trellis-config';

const ROUTES = ['/canvas', '/entity-list'] as const;
const COLD_SAMPLES = 3;
const WARM_SAMPLES = 5;
const SAMPLE_TIMEOUT_MS = Number(process.env['TRELLIS_BOOT_SAMPLE_TIMEOUT_MS'] ?? 300_000);
const BENCHMARK_COMMAND =
    'cd frontend && TRELLIS_BOOT_BENCHMARK=1 npx playwright test tests/boot-performance.spec.ts --project=chromium';
const BASELINE_PATH = path.resolve(process.cwd(), 'tests/benchmarks/frontend-boot-baseline.json');
const BENCHMARK_OUTPUT = process.env['TRELLIS_BOOT_BENCHMARK_OUTPUT'];
const BENCHMARK_OUTPUT_PATH = path.resolve(
    process.cwd(),
    BENCHMARK_OUTPUT ?? 'tests/benchmarks/frontend-boot-baseline.json',
);
const SHOULD_COMPARE = BENCHMARK_OUTPUT !== undefined;
const REPOSITORY_ROOT = path.resolve(process.cwd(), '..');

type PhaseTimings = Record<string, number>;

type BootSample = {
    spinnerToFirstUsefulRenderMs: number;
    firstRenderedFrameMs: number;
    requestCount: number;
    responseBytes: number;
    manifestParseCount: number;
    lineageCallCount: number;
    schemaCallCount: number;
    browserLongTaskCount: number;
    browserLongTaskMs: number;
    failedRequestCount: number;
    entityCount: number;
    relationshipCount: number;
    usefulElementCount: number;
    relationshipSetFingerprint: string;
    savedLayoutFingerprint: string;
    frontendPhaseTimings: PhaseTimings;
    backendPhaseTimings: PhaseTimings;
};

type BenchmarkSample = BootSample & {
    route: string;
    mode: 'cold' | 'warm';
    sample: number;
};

type RouteResults = {
    cold: BenchmarkSample[];
    warm: BenchmarkSample[];
};

type BenchmarkResults = Record<(typeof ROUTES)[number], RouteResults>;

type BenchmarkArtifact = {
    schemaVersion: number;
    fixture: {
        fingerprint: string;
        counts: typeof BOOT_FIXTURE_COUNTS;
    };
    raw: Record<string, RouteResults>;
    medians: Record<string, Record<'cold' | 'warm', Record<string, unknown>>>;
    comparison?: Record<string, unknown>;
};

type FixturePaths = {
    manifestPath: string;
    catalogPath: string;
    dataModelPath: string;
    layoutPath: string;
};

type BenchmarkWindow = Window & {
    __trellisBootBenchmark?: {
        firstFrameAt: number | null;
        longTasks: Array<{ duration: number }>;
    };
};

function median(values: number[]): number {
    if (values.length === 0) return 0;
    const sorted = [...values].sort((left, right) => left - right);
    const middle = Math.floor(sorted.length / 2);
    return sorted.length % 2 === 0
        ? (sorted[middle - 1] + sorted[middle]) / 2
        : sorted[middle];
}

function medianSamples(samples: BootSample[]): Record<string, number | Record<string, number>> {
    const scalarKeys: Array<keyof BootSample> = [
        'spinnerToFirstUsefulRenderMs',
        'firstRenderedFrameMs',
        'requestCount',
        'responseBytes',
        'manifestParseCount',
        'lineageCallCount',
        'schemaCallCount',
        'browserLongTaskCount',
        'browserLongTaskMs',
        'failedRequestCount',
        'entityCount',
        'relationshipCount',
        'usefulElementCount',
    ];
    const result: Record<string, number | Record<string, number>> = {};
    for (const key of scalarKeys) {
        result[key] = median(samples.map((sample) => sample[key] as number));
    }

    for (const key of ['frontendPhaseTimings', 'backendPhaseTimings'] as const) {
        const names = new Set(samples.flatMap((sample) => Object.keys(sample[key])));
        result[key] = Object.fromEntries(
            [...names].sort().map((name) => [
                name,
                median(samples.map((sample) => sample[key][name] ?? 0)),
            ]),
        );
    }
    return result;
}

function parseFixturePaths(): FixturePaths {
    const config = fs.readFileSync(TEST_CONFIG_PATH, 'utf8');
    const read = (configKey: string): string => {
        const line = config
            .split(/\r?\n/)
            .find((candidate) => candidate.startsWith(`${configKey}:`));
        if (!line) throw new Error(`Benchmark fixture config is missing ${configKey}`);
        return line.slice(`${configKey}:`.length).trim();
    };
    return {
        manifestPath: read('dbt_manifest_path'),
        catalogPath: read('dbt_catalog_path'),
        dataModelPath: read('data_model_file'),
        layoutPath: read('canvas_layout_file'),
    };
}

function fixtureFingerprint(paths: FixturePaths): string {
    const hash = createHash('sha256');
    for (const key of Object.keys(paths).sort() as Array<keyof FixturePaths>) {
        hash.update(key);
        hash.update(fs.readFileSync(paths[key]));
    }
    return hash.digest('hex');
}

function responsePath(response: Response): string {
    return new URL(response.url()).pathname;
}

function parseServerTiming(header: string | undefined): Array<{ name: string; duration: number }> {
    if (!header) return [];
    return header.split(/,(?=[a-zA-Z0-9_-]+;)/).flatMap((entry) => {
        const name = entry.split(';', 1)[0]?.trim();
        const durationText = entry.match(/(?:^|;)dur=([0-9.]+)/)?.[1];
        const duration = durationText === undefined ? undefined : Number(durationText);
        return name && duration !== undefined && Number.isFinite(duration)
            ? [{ name, duration }]
            : [];
    });
}

async function measureResponse(
    response: Response,
    state: {
        responseBytes: number;
        requestCount: number;
        failedRequestCount: number;
        manifestParseCount: number;
        lineageCallCount: number;
        schemaCallCount: number;
        entityCount: number;
        relationshipCount: number;
        relationshipSetFingerprint: string;
        savedLayoutFingerprint: string;
        backendPhaseTimings: PhaseTimings;
    },
): Promise<void> {
    state.requestCount += 1;
    const urlPath = responsePath(response);
    if (response.status() >= 400) {
        state.failedRequestCount += 1;
        console.log(
            `[boot-benchmark-response-failure] ${JSON.stringify({
                path: urlPath,
                status: response.status(),
            })}`,
        );
    }
    if (urlPath.includes('/lineage/')) state.lineageCallCount += 1;
    if (urlPath.includes('/models/') && urlPath.endsWith('/schema')) state.schemaCallCount += 1;

    const headerBytes = Number(response.headers()['content-length']);
    const needsCounts = urlPath.endsWith('/data-model');
    const body = needsCounts
        ? await response.body().catch(() => Buffer.alloc(0))
        : Buffer.alloc(0);
    state.responseBytes +=
        Number.isFinite(headerBytes) && headerBytes >= 0
            ? headerBytes
            : needsCounts
              ? body.byteLength
              : 0;

    const serverTiming = parseServerTiming(response.headers()['server-timing']);
    for (const metric of serverTiming) {
        state.backendPhaseTimings[metric.name] =
            (state.backendPhaseTimings[metric.name] ?? 0) + metric.duration;
    }
    if (urlPath.endsWith('/manifest') && response.status() < 400) {
        state.manifestParseCount += 1;
    }

    if (
        urlPath.endsWith('/data-model') &&
        response.request().method() === 'GET' &&
        response.status() < 400
    ) {
        try {
            const dataModel = JSON.parse(body.toString('utf8')) as {
                entities?: Array<{ id?: string; position?: { x?: number; y?: number } }>;
                relationships?: Array<Record<string, unknown>>;
            };
            state.entityCount = dataModel.entities?.length ?? state.entityCount;
            state.relationshipCount = dataModel.relationships?.length ?? state.relationshipCount;
            state.relationshipSetFingerprint = createHash('sha256')
                .update(JSON.stringify(dataModel.relationships ?? []))
                .digest('hex');
            state.savedLayoutFingerprint = createHash('sha256')
                .update(
                    JSON.stringify(
                        (dataModel.entities ?? [])
                            .map((entity) => ({
                            id: entity.id,
                            position: entity.position,
                            }))
                            .sort((left, right) => (left.id ?? '').localeCompare(right.id ?? '')),
                    ),
                )
                .digest('hex');
        } catch {
            // Correctness is asserted from the rendered view if the API body is unavailable.
        }
    }
}

async function readBrowserTimings(page: Page): Promise<{
    firstRenderedFrameMs: number;
    browserLongTaskCount: number;
    browserLongTaskMs: number;
    frontendPhaseTimings: PhaseTimings;
}> {
    return page.evaluate(() => {
        const benchmarkWindow = window as BenchmarkWindow;
        const state = benchmarkWindow.__trellisBootBenchmark;
        const measures = performance.getEntriesByType('measure');
        const frontendPhaseTimings: PhaseTimings = {};
        for (const entry of measures) {
            if (!entry.name.startsWith('trellis-boot:')) continue;
            frontendPhaseTimings[entry.name] =
                (frontendPhaseTimings[entry.name] ?? 0) + entry.duration;
        }
        const longTasks = state?.longTasks ?? performance.getEntriesByType('longtask');
        const longTaskDurations = longTasks.map((entry) => entry.duration);
        return {
            firstRenderedFrameMs: state?.firstFrameAt ?? performance.now(),
            browserLongTaskCount: longTasks.length,
            browserLongTaskMs: longTaskDurations.reduce((total, duration) => total + duration, 0),
            frontendPhaseTimings,
        };
    });
}

async function measureSample(
    page: Page,
    route: (typeof ROUTES)[number],
    mode: 'cold' | 'warm',
): Promise<BootSample> {
    const state = {
        responseBytes: 0,
        requestCount: 0,
        failedRequestCount: 0,
        manifestParseCount: 0,
        lineageCallCount: 0,
        schemaCallCount: 0,
        entityCount: 0,
        relationshipCount: 0,
        relationshipSetFingerprint: '',
        savedLayoutFingerprint: '',
        backendPhaseTimings: {} as PhaseTimings,
    };
    const responseTasks: Promise<void>[] = [];
    const onResponse = (response: Response) => {
        responseTasks.push(measureResponse(response, state));
    };
    const onRequestFailed = (request: Request) => {
        // A reload intentionally aborts optional schema work from the prior document.
        // Treat browser navigation cancellation as teardown, not an application failure.
        const failure = request.failure()?.errorText;
        if (failure !== 'net::ERR_ABORTED') {
            state.failedRequestCount += 1;
            console.log(
                `[boot-benchmark-request-failure] ${JSON.stringify({
                    path: new URL(request.url()).pathname,
                    error: failure,
                })}`,
            );
        }
    };
    page.on('response', onResponse);
    page.on('requestfailed', onRequestFailed);

    try {
        if (mode === 'cold') {
            await page.goto(route, { waitUntil: 'domcontentloaded', timeout: SAMPLE_TIMEOUT_MS });
        } else {
            await page.reload({ waitUntil: 'domcontentloaded', timeout: SAMPLE_TIMEOUT_MS });
        }

        const usefulView =
            route === '/canvas'
                ? page.locator('[data-testid="canvas-ready"] .svelte-flow__node-entity').first()
                : page.locator('[role="row"]').first();
        try {
            await expect(usefulView).toBeVisible({ timeout: SAMPLE_TIMEOUT_MS });
        } catch (error) {
            await page.screenshot({
                path: `test-results/boot-performance-${route.slice(1)}-${mode}-correctness.png`,
                fullPage: false,
            });
            console.log(
                `[boot-benchmark] ${JSON.stringify({
                    failure: true,
                    route,
                    mode,
                    requestCount: state.requestCount,
                    responseBytes: state.responseBytes,
                    failedRequestCount: state.failedRequestCount,
                    manifestParseCount: state.manifestParseCount,
                    lineageCallCount: state.lineageCallCount,
                    schemaCallCount: state.schemaCallCount,
                    entityCount: state.entityCount,
                    relationshipCount: state.relationshipCount,
                    backendPhaseTimings: state.backendPhaseTimings,
                })}`,
            );
            throw error;
        }
        const firstUsefulRenderAt = await page.evaluate(() => performance.now());
        const bootPhases = await page.evaluate(() =>
            performance
                .getEntriesByType('measure')
                .filter((entry) => entry.name.startsWith('trellis-boot:'))
                .map((entry) => ({
                    name: entry.name,
                    startTime: entry.startTime,
                    endTime: entry.startTime + entry.duration,
                })),
        );
        const phaseEnd = (phaseName: string): number | undefined => {
            const matching = bootPhases.filter((phase) =>
                phase.name.startsWith(`trellis-boot:${phaseName}:`),
            );
            return matching.length > 0
                ? Math.max(...matching.map((phase) => phase.endTime))
                : undefined;
        };
        const corePublishEnd = phaseEnd('core-publish');
        expect(corePublishEnd, `${route} must publish core content`).toBeDefined();
        expect(corePublishEnd).toBeLessThanOrEqual(firstUsefulRenderAt);
        for (const optionalPhase of ['relationship-inference', 'elk-layout']) {
            const optionalEnd = phaseEnd(optionalPhase);
            if (optionalEnd !== undefined) {
                expect(firstUsefulRenderAt, `${route} useful content precedes ${optionalPhase}`).toBeLessThan(
                    optionalEnd,
                );
            }
        }
        // Let optional schema requests finish before the sample context is reused or closed.
        // Otherwise a warm reload (or cold-context teardown) reports its own canceled requests
        // as benchmark failures.
        await page.waitForLoadState('networkidle', { timeout: SAMPLE_TIMEOUT_MS });
        const usefulElementCount =
            route === '/canvas'
                ? await page.locator('[data-testid="canvas-ready"] .svelte-flow__node-entity').count()
                : await page.locator('[role="row"]').count();
        const browserTimings = await readBrowserTimings(page);
        await Promise.all(responseTasks);

        return {
            spinnerToFirstUsefulRenderMs: firstUsefulRenderAt,
            firstRenderedFrameMs: browserTimings.firstRenderedFrameMs,
            requestCount: state.requestCount,
            responseBytes: state.responseBytes,
            manifestParseCount: state.manifestParseCount,
            lineageCallCount: state.lineageCallCount,
            schemaCallCount: state.schemaCallCount,
            browserLongTaskCount: browserTimings.browserLongTaskCount,
            browserLongTaskMs: browserTimings.browserLongTaskMs,
            failedRequestCount: state.failedRequestCount,
            entityCount: state.entityCount || usefulElementCount,
            relationshipCount: state.relationshipCount,
            usefulElementCount,
            relationshipSetFingerprint: state.relationshipSetFingerprint,
            savedLayoutFingerprint: state.savedLayoutFingerprint,
            frontendPhaseTimings: browserTimings.frontendPhaseTimings,
            backendPhaseTimings: state.backendPhaseTimings,
        };
    } finally {
        page.off('response', onResponse);
        page.off('requestfailed', onRequestFailed);
    }
}

async function measureColdSample(
    browser: Browser,
    route: (typeof ROUTES)[number],
    sampleIndex: number,
): Promise<BootSample> {
    const port = 18000 + (process.pid % 1000) + sampleIndex;
    const backend = spawn(
        'uv',
        [
            'run',
            'python',
            '-m',
            'trellis_datamodel.cli',
            'run',
            '--port',
            String(port),
            '--no-browser',
            '--config',
            TEST_CONFIG_PATH,
        ],
        {
            cwd: REPOSITORY_ROOT,
            env: { ...process.env, PYTHONPATH: REPOSITORY_ROOT },
            stdio: 'ignore',
            detached: true,
        },
    );
    try {
        await waitForBackend(port, backend);
        const context = await browser.newContext();
        try {
            const page = await context.newPage();
            await page.route('http://localhost:8000/api/**', async (routeRequest) => {
                const backendUrl = new URL(routeRequest.request().url());
                backendUrl.port = String(port);
                await routeRequest.continue({ url: backendUrl.toString() });
            });
            return await measureSample(page, route, 'cold');
        } finally {
            await context.close();
        }
    } finally {
        await stopBackend(backend);
    }
}

async function waitForBackend(port: number, backend: ChildProcess): Promise<void> {
    const healthUrl = `http://127.0.0.1:${port}/health`;
    for (let attempt = 0; attempt < 60; attempt += 1) {
        if (backend.exitCode !== null) {
            throw new Error(`Cold benchmark backend exited before health check: ${backend.exitCode}`);
        }
        try {
            const response = await fetch(healthUrl);
            if (response.ok) return;
        } catch {
            // The process may still be starting.
        }
        await new Promise((resolve) => setTimeout(resolve, 500));
    }
    throw new Error(`Cold benchmark backend did not become healthy on port ${port}`);
}

async function stopBackend(backend: ChildProcess): Promise<void> {
    if (backend.exitCode !== null) return;
    const signalProcessGroup = (signal: NodeJS.Signals): void => {
        if (!backend.pid) return;
        try {
            process.kill(-backend.pid, signal);
        } catch {
            backend.kill(signal);
        }
    };
    signalProcessGroup('SIGTERM');
    await new Promise<void>((resolve) => {
        const timer = setTimeout(() => {
            signalProcessGroup('SIGKILL');
            resolve();
        }, 5000);
        backend.once('exit', () => {
            clearTimeout(timer);
            resolve();
        });
    });
}

async function collectRouteSamples(
    browser: Browser,
    route: (typeof ROUTES)[number],
): Promise<RouteResults> {
    const cold: BenchmarkSample[] = [];
    for (let index = 0; index < COLD_SAMPLES; index += 1) {
        const sample = await measureColdSample(browser, route, index);
        cold.push({ ...sample, route, mode: 'cold', sample: index + 1 });
        console.log(`[boot-benchmark] ${JSON.stringify(cold[cold.length - 1])}`);
    }

    const context = await browser.newContext();
    const page = await context.newPage();
    const warm: BenchmarkSample[] = [];
    try {
        await page.goto(route, { waitUntil: 'domcontentloaded', timeout: SAMPLE_TIMEOUT_MS });
        const initialUsefulView =
            route === '/canvas'
                ? page.locator('[data-testid="canvas-ready"] .svelte-flow__node-entity').first()
                : page.locator('[role="row"]').first();
        await expect(initialUsefulView).toBeVisible({ timeout: SAMPLE_TIMEOUT_MS });
        for (let index = 0; index < WARM_SAMPLES; index += 1) {
            const sample = await measureSample(page, route, 'warm');
            warm.push({ ...sample, route, mode: 'warm', sample: index + 1 });
            console.log(`[boot-benchmark] ${JSON.stringify(warm[warm.length - 1])}`);
        }
    } finally {
        await context.close();
    }
    return { cold, warm };
}

function buildBenchmarkArtifact(results: BenchmarkResults, fixture: FixturePaths): BenchmarkArtifact {
    return {
        schemaVersion: 1,
        fixture: {
            fingerprint: fixtureFingerprint(fixture),
            counts: BOOT_FIXTURE_COUNTS,
        },
        machine: {
            platform: os.platform(),
            release: os.release(),
            arch: os.arch(),
            cpuCount: os.cpus().length,
            totalMemoryBytes: os.totalmem(),
            nodeVersion: process.version,
            browserProject: 'chromium',
            coldProcessRestarted: true,
        },
        command: BENCHMARK_COMMAND,
        sampleCounts: {
            cold: COLD_SAMPLES,
            warm: WARM_SAMPLES,
            perRoute: {
                '/canvas': COLD_SAMPLES + WARM_SAMPLES,
                '/entity-list': COLD_SAMPLES + WARM_SAMPLES,
            },
        },
        raw: Object.fromEntries(
            ROUTES.map((route) => [
                route,
                {
                    cold: results[route].cold,
                    warm: results[route].warm,
                },
            ]),
        ),
        medians: Object.fromEntries(
            ROUTES.map((route) => [
                route,
                {
                    cold: medianSamples(results[route].cold),
                    warm: medianSamples(results[route].warm),
                },
            ]),
        ),
    } as BenchmarkArtifact;
}

function writeBenchmarkArtifact(benchmark: BenchmarkArtifact): void {
    fs.mkdirSync(path.dirname(BENCHMARK_OUTPUT_PATH), { recursive: true });
    fs.writeFileSync(BENCHMARK_OUTPUT_PATH, `${JSON.stringify(benchmark, null, 2)}\n`, 'utf8');
}

function compareWithBaseline(
    results: BenchmarkResults,
    benchmark: BenchmarkArtifact,
    fixture: FixturePaths,
): Record<string, unknown> {
    const baseline = JSON.parse(fs.readFileSync(BASELINE_PATH, 'utf8')) as BenchmarkArtifact;
    expect(benchmark.fixture.fingerprint, 'benchmark fixture must match baseline').toBe(
        baseline.fixture.fingerprint,
    );

    const routes: Record<string, unknown> = {};
    let passed = true;
    for (const route of ROUTES) {
        const routeComparison: Record<string, unknown> = {};
        for (const mode of ['cold', 'warm'] as const) {
            const afterMedian = benchmark.medians[route][mode];
            const baselineMedian = baseline.medians[route][mode];
            const afterMs = Number(afterMedian.spinnerToFirstUsefulRenderMs);
            const baselineMs = Number(baselineMedian.spinnerToFirstUsefulRenderMs);
            const reduction = baselineMs > 0 ? 1 - afterMs / baselineMs : 0;
            const thresholdMs = mode === 'cold' ? 5_000 : 2_000;
            const modePassed = afterMs <= thresholdMs || reduction >= 0.7;
            passed = passed && modePassed;
            routeComparison[mode] = {
                gatePassed: modePassed,
                baselineMs,
                remainingMs: afterMs,
                reductionPercent: reduction * 100,
                thresholdMs,
                requestCount: afterMedian.requestCount,
                responseBytes: afterMedian.responseBytes,
                browserLongTaskCount: afterMedian.browserLongTaskCount,
                browserLongTaskMs: afterMedian.browserLongTaskMs,
                manifestParseCount: afterMedian.manifestParseCount,
                lineageCallCount: afterMedian.lineageCallCount,
                schemaCallCount: afterMedian.schemaCallCount,
                frontendPhaseTimings: afterMedian.frontendPhaseTimings,
                backendPhaseTimings: afterMedian.backendPhaseTimings,
            };
            for (const sample of results[route][mode]) {
                // The cold first sample captures the deterministic fixture's original
                // relationship/layout state before the pre-optimization startup save.
                const baselineSample = baseline.raw[route].cold[0];
                expect(sample.relationshipSetFingerprint, `${mode} ${route} relationships`).toBe(
                    baselineSample.relationshipSetFingerprint,
                );
                expect(sample.savedLayoutFingerprint, `${mode} ${route} saved layout`).toBe(
                    baselineSample.savedLayoutFingerprint,
                );
            }
        }
        routes[route] = routeComparison;
    }
    const comparison = {
        baselinePath: path.relative(REPOSITORY_ROOT, BASELINE_PATH),
        fixtureFingerprint: fixtureFingerprint(fixture),
        passed,
        routes,
    };
    console.log(`[boot-benchmark-comparison] ${JSON.stringify(comparison)}`);
    return comparison;
}

test.describe.configure({ mode: 'serial', timeout: 60 * 60 * 1000 });

test('captures cold and warm frontend boot baseline', async ({ browser }) => {
    test.skip(
        !process.env['TRELLIS_BOOT_BENCHMARK'],
        'Run the benchmark explicitly with TRELLIS_BOOT_BENCHMARK=1',
    );
    const results = {} as BenchmarkResults;
    const fixture = parseFixturePaths();
    for (const route of ROUTES) {
        results[route] = await collectRouteSamples(browser, route);
        const firstSample = [...results[route].cold, ...results[route].warm][0];
        for (const sample of [...results[route].cold, ...results[route].warm]) {
            expect(sample.failedRequestCount, `${sample.mode} ${route} has failed requests`).toBe(0);
            expect(sample.entityCount, `${sample.mode} ${route} entity count`).toBe(
                BOOT_FIXTURE_COUNTS.entities,
            );
            expect(sample.relationshipCount, `${sample.mode} ${route} relationship count`).toBe(
                BOOT_FIXTURE_COUNTS.relationships,
            );
            expect(sample.usefulElementCount, `${sample.mode} ${route} useful view`).toBeGreaterThan(0);
            expect(sample.relationshipSetFingerprint, `${sample.mode} ${route} relationships`).toBe(
                firstSample.relationshipSetFingerprint,
            );
            expect(sample.savedLayoutFingerprint, `${sample.mode} ${route} saved layout`).toBe(
                firstSample.savedLayoutFingerprint,
            );
        }
    }
    const benchmark = buildBenchmarkArtifact(results, fixture);
    if (SHOULD_COMPARE) {
        benchmark.comparison = compareWithBaseline(results, benchmark, fixture);
    }
    writeBenchmarkArtifact(benchmark);
    if (SHOULD_COMPARE) {
        expect((benchmark.comparison as { passed: boolean }).passed).toBe(true);
    }
});
