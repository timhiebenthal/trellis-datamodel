import { test, expect, type Locator, type Page } from '@playwright/test';
import * as fs from 'fs';
import { parse } from 'yaml';
import { METRIC_LAYOUT_PATH, METRIC_TREE_PATH } from './ensure-e2e-trellis-config';

/**
 * End-to-end path for the metric tree: enable the feature, add two draft
 * metrics, draw one influence, reload, and check that the graph and both
 * artifact files survive.
 *
 * The feature is enabled in the e2e `trellis.yml` written by
 * `ensure-e2e-trellis-config.ts`. The skip below is the guard for a harness that
 * points at another config (CI reuse, a hand-edited file): the spec must not
 * fail just because no backend has `metrics.enabled` on.
 */

/** Remove a previous run's artifacts so the canvas starts empty. */
function resetMetricFiles(): void {
    for (const target of [METRIC_TREE_PATH, METRIC_LAYOUT_PATH]) {
        fs.rmSync(target, { force: true });
    }
}

function readYaml(path: string): any {
    return parse(fs.readFileSync(path, 'utf8')) ?? {};
}

async function fillSelectedDraft(page: Page, label: string, expression: string): Promise<void> {
    await page.getByTestId('metric-field-label').fill(label);
    await page.getByTestId('metric-field-expression').fill(expression);
}

/** Drag from the upper effect node's bottom source handle onto the lower driver node's top target handle. */
async function connectMetrics(page: Page, driverId: string, effectId: string): Promise<void> {
    const source = page.locator(
        `[data-testid="metric-node"][data-metric-id="${effectId}"] .svelte-flow__handle.source`,
    );
    const target = page.locator(
        `[data-testid="metric-node"][data-metric-id="${driverId}"] .svelte-flow__handle.target`,
    );

    const from = await source.boundingBox();
    const to = await target.boundingBox();
    expect(from).not.toBeNull();
    expect(to).not.toBeNull();

    await page.mouse.move(from!.x + from!.width / 2, from!.y + from!.height / 2);
    await page.mouse.down();
    await page.mouse.move(to!.x + to!.width / 2, to!.y + to!.height / 2, { steps: 12 });
    await page.mouse.up();
}

async function dragNode(page: Page, node: Locator): Promise<void> {
    const box = await node.boundingBox();
    expect(box).not.toBeNull();

    await page.mouse.move(box!.x + box!.width / 2, box!.y + box!.height / 2);
    await page.mouse.down();
    await page.mouse.move(box!.x + box!.width / 2 + 60, box!.y + box!.height / 2 + 40, {
        steps: 10,
    });
    await page.mouse.up();
}

test.describe('Metric tree - E2E', () => {
    test('two metrics and an influence survive a reload and land in both files', async ({
        page,
        request,
    }) => {
        const info = await request.get('/api/config-info');
        const configInfo = info.ok() ? ((await info.json()) as { metrics_enabled?: boolean }) : {};
        test.skip(
            configInfo.metrics_enabled !== true,
            'metrics.enabled is false in the e2e trellis.yml',
        );

        resetMetricFiles();

        await page.goto('/metrics-tree');
        await expect(page.getByTestId('metric-canvas-empty')).toBeVisible();

        // 1. Two drafts. Each needs an expression or autosave stays paused.
        await page.getByTestId('metric-canvas-empty-cta').click();
        await fillSelectedDraft(page, 'Revenue', 'sum(amount) from fct__order');

        await page.getByTestId('metric-sidebar-add').click();
        await fillSelectedDraft(page, 'Order count', 'count(*) from fct__order');

        // The inspector overlaps the right edge of the canvas; close it so both
        // nodes are reachable for the connection drag.
        await page.getByTestId('metric-detail-close').click();

        const nodes = page.getByTestId('metric-node');
        await expect(nodes).toHaveCount(2);

        const driverId = await nodes.nth(0).getAttribute('data-metric-id');
        const effectId = await nodes.nth(1).getAttribute('data-metric-id');
        expect(driverId).toBeTruthy();
        expect(effectId).toBeTruthy();

        // 2. One directed influence: the drag source is the driver.
        await connectMetrics(page, driverId!, effectId!);

        const edge = page.locator(`.svelte-flow__edge[data-id="influence:${driverId}:${effectId}"]`);
        await expect(edge).toHaveCount(1);

        // The save is debounced; wait for the document to reach the backend.
        await expect
            .poll(async () => {
                const res = await request.get('/api/metric-tree');
                if (!res.ok()) return null;
                const tree = (await res.json()) as { metrics: unknown[]; influences: unknown[] };
                return { metrics: tree.metrics.length, influences: tree.influences.length };
            })
            .toEqual({ metrics: 2, influences: 1 });

        // 3. Drop a node so a position has to reach metric_layout.yml too.
        await dragNode(page, nodes.nth(1));

        await expect
            .poll(
                () => {
                    if (!fs.existsSync(METRIC_LAYOUT_PATH)) return null;
                    const layout = readYaml(METRIC_LAYOUT_PATH);
                    const position = layout?.[effectId!]?.position;
                    return position ? typeof position.x : null;
                },
                { timeout: 10_000 },
            )
            .toBe('number');

        // 4. Reload: the graph comes back from the files, not from page state.
        await page.reload();
        await expect(page.getByTestId('metric-node')).toHaveCount(2);
        await expect(
            page.locator(`.svelte-flow__edge[data-id="influence:${driverId}:${effectId}"]`),
        ).toHaveCount(1);
        await expect(page.getByTestId('metric-count')).toContainText('2 metrics');
        await expect(page.getByTestId('metric-count')).toContainText('1 influences');

        // 5. Both artifacts exist and hold the documented shape.
        expect(fs.existsSync(METRIC_TREE_PATH)).toBe(true);
        expect(fs.existsSync(METRIC_LAYOUT_PATH)).toBe(true);

        const tree = readYaml(METRIC_TREE_PATH);
        expect(tree.version).toBe(0.1);
        expect(tree.metrics.map((metric: any) => metric.id)).toEqual(
            [driverId!, effectId!].sort(),
        );
        for (const metric of tree.metrics) {
            expect(typeof metric.label).toBe('string');
            expect(metric.label.length).toBeGreaterThan(0);
            expect(typeof metric.expression).toBe('string');
            expect(metric.expression.length).toBeGreaterThan(0);
            // Positions live in metric_layout.yml, never in the definitions file.
            expect(metric.position).toBeUndefined();
        }
        expect(tree.influences).toEqual([{ effect: effectId, drivers: [driverId] }]);

        const layout = readYaml(METRIC_LAYOUT_PATH);
        const draggedPosition = layout?.[effectId!]?.position;
        expect(typeof draggedPosition?.x).toBe('number');
        expect(typeof draggedPosition?.y).toBe('number');
        for (const key of Object.keys(layout)) {
            expect([driverId, effectId]).toContain(key);
        }
    });
});
