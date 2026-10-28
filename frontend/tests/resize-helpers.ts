import { expect, type Page } from '@playwright/test';

/**
 * Shared plumbing for the pointer-driven resize specs (#140).
 *
 * A pointer drag that leaves the viewport silently hits nothing, which reads as
 * "resize is broken" and would let a test pass or fail for the wrong reason.
 * `prepareCanvas` gives the node's edge handles drag headroom and
 * `assertGrabbable` proves the press actually lands on the handle.
 */

export type Box = { x: number; y: number; width: number; height: number };

export async function box(page: Page, selector: string): Promise<Box> {
    const boundingBox = await page.locator(selector).boundingBox();
    if (!boundingBox) throw new Error(`no bounding box for ${selector}`);
    return boundingBox;
}

export async function openFreshCanvas(page: Page): Promise<void> {
    await page.addInitScript(() => {
        localStorage.clear();
        sessionStorage.clear();
    });
    await page.goto('/canvas');
    await expect(page.getByTestId('canvas-ready')).toBeVisible({ timeout: 15000 });
}

/**
 * Fit the graph, then zoom out so `nodeSelector`'s edge handles have room to move
 * in both directions without leaving the viewport.
 */
export async function prepareCanvas(
    page: Page,
    nodeSelector: string,
    zoomOutClicks = 3,
): Promise<void> {
    // The canvas runs a one-off animated fit shortly after boot. Zooming before it
    // lands gets overridden mid-flight, sliding the handle out from under the
    // pointer so the press hits nothing (#170).
    await expect(page.getByTestId('canvas-fitted')).toBeAttached({ timeout: 10000 });
    await page.locator('.svelte-flow__controls-fitview').click();
    for (let i = 0; i < zoomOutClicks; i++) {
        await page.locator('.svelte-flow__controls-zoomout').click();
    }
    await expect(page.locator(nodeSelector)).toBeVisible({ timeout: 10000 });
    // Wait out the zoom/fit animations: the node must hold still before a handle
    // is measured.
    await expectStable(() => box(page, nodeSelector));
}

/** Poll until `sample` returns the same value on consecutive reads. */
export async function expectStable<T>(sample: () => Promise<T>, intervalMs = 150): Promise<T> {
    let previous = JSON.stringify(await sample());
    await expect
        .poll(
            async () => {
                const current = JSON.stringify(await sample());
                const stable = current === previous;
                previous = current;
                return stable;
            },
            { intervals: [intervalMs], timeout: 10000 },
        )
        .toBe(true);
    return JSON.parse(previous) as T;
}

/**
 * Guard against a vacuous drag: the handle must be the top element at its own
 * centre and that centre must sit inside the viewport. Returns the grab point.
 */
export async function assertGrabbable(
    page: Page,
    handleSelector: string,
    handleClass: string,
): Promise<{ cx: number; cy: number }> {
    const viewport = page.viewportSize();
    if (!viewport) throw new Error('no viewport size');

    const info = (await page.evaluate(
        ([selector, expectedClass]) => {
            const handle = document.querySelector(selector as string) as HTMLElement | null;
            if (!handle) return { grab: null, onTop: false, topClass: 'none', handleClass: 'none' };
            const rect = handle.getBoundingClientRect();
            const cx = rect.x + rect.width / 2;
            const cy = rect.y + rect.height / 2;
            const top = document.elementFromPoint(cx, cy) as HTMLElement | null;
            return {
                grab: { cx, cy },
                onTop: Boolean(top?.classList.contains(expectedClass as string)),
                topClass: top?.className ?? 'none',
                handleClass: handle.className,
            };
        },
        [handleSelector, handleClass],
    )) as {
        grab: { cx: number; cy: number } | null;
        onTop: boolean;
        topClass: string;
        handleClass: string;
    };

    if (!info.grab) throw new Error(`${handleSelector} not rendered`);
    expect(
        info.onTop,
        `handle must be the top element at its centre, got "${info.topClass}" ` +
            `(handle own className: "${info.handleClass}")`,
    ).toBe(true);
    expect(info.grab.cx).toBeGreaterThan(0);
    expect(info.grab.cx).toBeLessThan(viewport.width);
    expect(info.grab.cy).toBeGreaterThan(0);
    expect(info.grab.cy).toBeLessThan(viewport.height);
    return { cx: info.grab.cx, cy: info.grab.cy };
}

/**
 * Press on the returned grab point, drag by (dx, dy), sample mid-drag with the
 * button still held, release, then sample again once the size stops changing (after the
 * auto-fit pass and its 50ms/300ms timers have run).
 *
 * `sample` is caller-supplied so each spec can measure what actually matters for
 * its node type, and `settleMs` lets a caller wait out a CSS transition.
 */
export async function dragHandle<T>(
    page: Page,
    grab: { cx: number; cy: number },
    sample: () => Promise<T>,
    dx: number,
    dy: number,
    settleMs = 0,
): Promise<{ before: T; during: T; after: T }> {
    const before = await sample();
    await page.mouse.move(grab.cx, grab.cy);
    await page.mouse.down();
    await page.mouse.move(grab.cx + dx, grab.cy + dy, { steps: 12 });
    if (settleMs > 0) {
        await page.waitForTimeout(settleMs);
    }
    const during = await sample();
    await page.mouse.up();
    // Auto-fit runs on 50ms/300ms timers after release; wait for the size to hold
    // still rather than guessing a delay.
    await page.waitForTimeout(350);
    const after = await expectStable(sample);
    return { before, during, after };
}
