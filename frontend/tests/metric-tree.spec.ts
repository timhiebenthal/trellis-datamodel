import { test, expect, type Page } from '@playwright/test';
import * as fs from 'fs';
import { parse } from 'yaml';
import { METRIC_TREE_PATH } from './ensure-e2e-trellis-config';

/**
 * End-to-end path for the metric tree: enable the feature, add two draft
 * metrics, link one influence, reload, and check that the graph and
 * `metric_tree.yml` survive.
 *
 * The feature is enabled in the e2e `trellis.yml` written by
 * `ensure-e2e-trellis-config.ts`. The skip below is the guard for a harness that
 * points at another config (CI reuse, a hand-edited file): the spec must not
 * fail just because no backend has `metrics.enabled` on.
 */

/** Remove a previous run's artifact so the canvas starts empty. */
function resetMetricFiles(): void {
    fs.rmSync(METRIC_TREE_PATH, { force: true });
}

function readYaml(path: string): any {
    return parse(fs.readFileSync(path, 'utf8')) ?? {};
}

/** Fill the New metric form and create it; the metric joins the tree only on Create. */
async function createDraft(page: Page, label: string, expression: string): Promise<void> {
    await page.getByTestId('metric-field-label').fill(label);
    await page.getByTestId('metric-field-expression').fill(expression);
    await page.getByTestId('metric-create').click();
}

/**
 * Link two metrics through the effect node's "+ Add driver" picker. The mouse
 * cannot start a drag on the connection handle: the add button is drawn over it.
 */
async function linkDriver(
    page: Page,
    effectId: string,
    driverLabel: string,
): Promise<void> {
    const effect = page.locator(`[data-testid="metric-node"][data-metric-id="${effectId}"]`);
    await effect.getByTestId('metric-node-add-driver').click();
    await page
        .getByTestId('metric-node-picker-tree-item')
        .filter({ hasText: driverLabel })
        .click();
}

test.describe('Metric tree - E2E', () => {
    test('two metrics and an influence survive a reload and land in metric_tree.yml', async ({
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

        // A cancelled new metric leaves the canvas empty.
        await page.getByTestId('metric-canvas-empty-cta').click();
        await page.getByTestId('metric-field-label').fill('Discarded');
        await page.getByTestId('metric-cancel').click();
        await expect(page.getByTestId('metric-canvas-empty')).toBeVisible();

        // 1. Two drafts. Each joins the tree only once it has a label and an expression.
        await page.getByTestId('metric-canvas-empty-cta').click();
        await createDraft(page, 'Revenue', 'sum(amount) from fct__order');

        await page.getByTestId('metric-sidebar-add').click();
        await createDraft(page, 'Order count', 'count(*) from fct__order');

        // The inspector overlaps the right edge of the canvas; close it so both
        // nodes are reachable for the connection drag.
        await page.getByTestId('metric-detail-close').click();

        const nodes = page.getByTestId('metric-node');
        await expect(nodes).toHaveCount(2);

        const driverId = await nodes.nth(0).getAttribute('data-metric-id');
        const effectId = await nodes.nth(1).getAttribute('data-metric-id');
        expect(driverId).toBeTruthy();
        expect(effectId).toBeTruthy();

        // 2. One directed influence: Revenue drives Order count.
        await linkDriver(page, effectId!, 'Revenue');

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

        // 3. Reload: the graph comes back from metric_tree.yml, not from page state.
        await page.reload();
        await expect(page.getByTestId('metric-node')).toHaveCount(2);
        await expect(
            page.locator(`.svelte-flow__edge[data-id="influence:${driverId}:${effectId}"]`),
        ).toHaveCount(1);
        await expect(page.getByTestId('metric-count')).toContainText('2 metrics');
        await expect(page.getByTestId('metric-count')).toContainText('1 influences');

        // 4. The artifact exists and holds the documented shape.
        expect(fs.existsSync(METRIC_TREE_PATH)).toBe(true);

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
            expect(metric.position).toBeUndefined();
        }
        expect(tree.influences).toEqual([{ effect: effectId, drivers: [driverId] }]);
    });
});
