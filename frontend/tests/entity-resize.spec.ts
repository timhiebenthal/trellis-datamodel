import { test, expect, type Page } from '@playwright/test';
import { resetDataModel, type DataModelPayload } from './helpers';
import {
    assertGrabbable,
    dragHandle,
    openFreshCanvas,
    prepareCanvas,
    type Box,
} from './resize-helpers';

/**
 * #140: an entity node must resize when you drag its resize handle.
 *
 * The issue confirmed group nodes were broken and listed entity nodes as "not yet
 * confirmed". This spec is the honest signal for the entity path: it presses the
 * entity's `.width-resize-handle`, drags outward, samples the width mid-drag
 * (button still held), then samples again after release, and asserts the width
 * grew and stayed grown.
 */

// One entity bound to a real dbt_company_dummy model; the e2e backend resolves
// entities against `dbt_company_dummy`.
const ENTITY_DATA_MODEL: DataModelPayload = {
    version: 0.1,
    entities: [
        {
            id: 'e1',
            label: 'Sale',
            domain: 'Sales',
            entity_type: 'fact',
            model_ref: 'model.company_dummy.dim_sale',
            position: { x: 0, y: 0 },
        },
    ],
    relationships: [],
};

const ENTITY = '.svelte-flow__node-entity[data-id="e1"]';
const WIDTH_HANDLE = `${ENTITY} .width-resize-handle`;
const VIEWPORT = '.svelte-flow__viewport';

/** Rendered box of the entity body (the element carrying `width:${nodeWidth}px`). */
async function bodyRect(page: Page, handleSelector: string): Promise<Box> {
    const rect = await page.evaluate((sel) => {
        const handle = document.querySelector(sel) as HTMLElement | null;
        const body = handle?.parentElement as HTMLElement | null;
        if (!body) return null;
        const b = body.getBoundingClientRect();
        return { x: b.x, y: b.y, width: b.width, height: b.height };
    }, handleSelector);
    if (!rect) throw new Error(`no entity body for ${handleSelector}`);
    return rect;
}

/** Inline `width` applied to the entity root (`width:${nodeWidth}px`), zoom independent. */
async function appliedWidth(page: Page, handleSelector: string): Promise<number> {
    return await page.evaluate((sel) => {
        const handle = document.querySelector(sel) as HTMLElement | null;
        const body = handle?.parentElement as HTMLElement | null;
        return body ? parseFloat(body.style.width) : NaN;
    }, handleSelector);
}

/** Current viewport zoom, parsed from the viewport transform matrix. */
async function viewportZoom(page: Page): Promise<number> {
    return await page.evaluate((sel) => {
        const el = document.querySelector(sel) as HTMLElement | null;
        if (!el) return 1;
        const t = getComputedStyle(el).transform;
        const m = t?.match(/matrix\(([^)]+)\)/);
        if (!m) return 1;
        return parseFloat(m[1].split(',')[0].trim()) || 1;
    }, VIEWPORT);
}

/** Rendered bounding box of the node wrapper itself. */
async function nodeBox(page: Page): Promise<Box> {
    const bb = await page.locator(ENTITY).boundingBox();
    if (!bb) throw new Error('no bounding box for entity wrapper');
    return bb;
}

/**
 * The e2e config boots entities collapsed. Expansion is not required for the
 * width signal (the root carries `width:${nodeWidth}px` either way), but a
 * collapsed root is only header-height and its right-edge centre can collide with
 * the header's hover affordances, so expand via the toolbar when it is offered.
 * Best-effort: never hard-fail here, the resize assertion is the real signal.
 */
async function expandAllEntities(page: Page): Promise<void> {
    const expandAll = page.getByRole('button', { name: 'Expand all entities' });
    if ((await expandAll.count()) > 0) {
        await expandAll.first().click();
        await page.waitForTimeout(300);
    }
}

type Sample = { rendered: Box; zoom: number; contentWidth: number; appliedWidth: number };

test.describe('Entity Node Resize (#140)', () => {
    test.beforeEach(async ({ page, request }) => {
        await page.setViewportSize({ width: 1600, height: 900 });
        await resetDataModel(request, ENTITY_DATA_MODEL);
    });

    test('dragging the width handle resizes the entity live and keeps the size', async ({ page }) => {
        await openFreshCanvas(page);
        await prepareCanvas(page, ENTITY);
        await expandAllEntities(page);
        await prepareCanvas(page, ENTITY); // re-fit after the expand pass

        const grab = await assertGrabbable(page, WIDTH_HANDLE, 'width-resize-handle');

        const sample = async (): Promise<Sample> => {
            const rendered = await bodyRect(page, WIDTH_HANDLE);
            const zoom = await viewportZoom(page);
            return {
                rendered,
                zoom,
                contentWidth: rendered.width / zoom,
                appliedWidth: await appliedWidth(page, WIDTH_HANDLE),
            };
        };

        const nodeBefore = await nodeBox(page);
        // The entity root has `transition-all duration-200`: the applied width jumps
        // immediately while the rendered box animates, so hold the drag long enough
        // for the transition to settle before sampling "during".
        const { before, during, after } = await dragHandle(page, grab, sample, 140, 0, 350);
        const nodeAfter = await nodeBox(page);

        // 1) Resize must be live: rendered width grows while the button is still down.
        expect(
            during.rendered.width,
            `entity width must grow during the drag ` +
                `(before=${before.rendered.width}px, during=${during.rendered.width}px)`,
        ).toBeGreaterThan(before.rendered.width + 50);

        // 2) And it must survive release (~600ms later).
        expect(
            after.rendered.width,
            `entity width must persist after release ` +
                `(before=${before.rendered.width}px, after=${after.rendered.width}px)`,
        ).toBeGreaterThan(before.rendered.width + 50);

        // 3) The applied size tracks the drag exactly (zoom independent).
        expect(after.contentWidth - before.contentWidth).toBeGreaterThan(100);

        // 4) Resizing must not drag the node around.
        expect(
            Math.abs(nodeAfter.x - nodeBefore.x),
            `node x must not shift (before=${nodeBefore.x}, after=${nodeAfter.x})`,
        ).toBeLessThan(5);
        expect(
            Math.abs(nodeAfter.y - nodeBefore.y),
            `node y must not shift (before=${nodeBefore.y}, after=${nodeAfter.y})`,
        ).toBeLessThan(5);
    });
});
