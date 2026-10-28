import { test, expect } from '@playwright/test';
import { resetDataModel, type DataModelPayload } from './helpers';
import { assertGrabbable, box, dragHandle, openFreshCanvas, prepareCanvas } from './resize-helpers';

/**
 * Regression coverage for #140: a group node's resize handles must resize the
 * group live during the pointer drag and keep the new size after release.
 */

// Three real dbt_company_dummy models so each entity resolves to a folder.
// All three live in `models/3_core/all/`, which renders exactly one group node
// with id `group-3_core-all`.
const GROUP_TEST_DATA_MODEL: DataModelPayload = {
    version: 0.1,
    entities: [
        {
            id: 'entity1',
            label: 'Entity 1',
            domain: 'Sales',
            entity_type: 'fact',
            model_ref: 'model.company_dummy.dim_sale',
            position: { x: 0, y: 0 },
        },
        {
            id: 'entity2',
            label: 'Entity 2',
            domain: 'Sales',
            entity_type: 'dimension',
            model_ref: 'model.company_dummy.dim_customer',
            position: { x: 200, y: 0 },
        },
        {
            id: 'entity3',
            label: 'Entity 3',
            domain: 'Sales',
            entity_type: 'dimension',
            model_ref: 'model.company_dummy.dim_product',
            position: { x: 400, y: 0 },
        },
    ],
    relationships: [],
};

const GROUP = '.svelte-flow__node-group[data-id="group-3_core-all"]';
const GROUP_BODY = `${GROUP} .group-node`;
const WIDTH_HANDLE = `${GROUP_BODY} .width-resize-handle`;
const HEIGHT_HANDLE = `${GROUP_BODY} .height-resize-handle`;

test.describe('Group Node Resize', () => {
    test.beforeEach(async ({ page, request }) => {
        // Wide viewport plus the zoom-out in prepareCanvas keeps the right-edge
        // handle grabbable after the group grows.
        await page.setViewportSize({ width: 1600, height: 900 });
        await resetDataModel(request, GROUP_TEST_DATA_MODEL);
    });

    test('dragging the width handle resizes the group live and keeps the size', async ({ page }) => {
        await openFreshCanvas(page);
        // The group node sits above its children (negative y), so fit the view to
        // bring it into the pane, then zoom out for drag headroom.
        await prepareCanvas(page, GROUP);

        // The hover affordance the reporter saw: handle is hit-testable and shows the cursor.
        await page.locator(WIDTH_HANDLE).hover();
        await expect(page.locator(WIDTH_HANDLE)).toHaveCSS('cursor', 'ew-resize');
        const grab = await assertGrabbable(page, WIDTH_HANDLE, 'width-resize-handle');

        const nodeBefore = await box(page, GROUP);
        const { before, during, after } = await dragHandle(
            page,
            grab,
            () => box(page, GROUP_BODY),
            140,
            0,
        );
        const nodeAfter = await box(page, GROUP);

        // Resize must be live: visible while still dragging.
        expect(
            during.width,
            `group width must grow during the drag (before=${before.width}, during=${during.width})`,
        ).toBeGreaterThan(before.width + 50);

        // And it must survive release plus the auto-fit-children pass.
        expect(
            after.width,
            `group width must persist after release (before=${before.width}, after=${after.width})`,
        ).toBeGreaterThan(before.width + 50);

        // Resizing must not drag the node around.
        expect(Math.abs(nodeAfter.x - nodeBefore.x)).toBeLessThan(5);
        expect(Math.abs(nodeAfter.y - nodeBefore.y)).toBeLessThan(5);
    });

    test('dragging the width handle inward shrinks the group', async ({ page }) => {
        await openFreshCanvas(page);
        await prepareCanvas(page, GROUP);

        // Grow first so there is room to shrink back.
        const growGrab = await assertGrabbable(page, WIDTH_HANDLE, 'width-resize-handle');
        const grown = await dragHandle(page, growGrab, () => box(page, GROUP_BODY), 160, 0);
        expect(grown.after.width).toBeGreaterThan(grown.before.width + 100);

        // The right edge moved outward, so re-resolve the grab point.
        const shrinkGrab = await assertGrabbable(page, WIDTH_HANDLE, 'width-resize-handle');
        const shrunk = await dragHandle(page, shrinkGrab, () => box(page, GROUP_BODY), -160, 0);
        expect(
            shrunk.after.width,
            `group width must shrink (grown=${grown.after.width}, shrunk=${shrunk.after.width})`,
        ).toBeLessThan(grown.after.width - 50);
    });

    test('dragging the height handle resizes the group vertically', async ({ page }) => {
        await openFreshCanvas(page);
        await prepareCanvas(page, GROUP);

        const grab = await assertGrabbable(page, HEIGHT_HANDLE, 'height-resize-handle');
        const { before, during, after } = await dragHandle(
            page,
            grab,
            () => box(page, GROUP_BODY),
            0,
            120,
        );

        expect(
            during.height,
            `group height must grow during the drag (before=${before.height}, during=${during.height})`,
        ).toBeGreaterThan(before.height + 50);
        expect(
            after.height,
            `group height must persist after release (before=${before.height}, after=${after.height})`,
        ).toBeGreaterThan(before.height + 50);
    });

    test('the dragged edge follows the cursor at the current zoom', async ({ page }) => {
        await openFreshCanvas(page);
        await prepareCanvas(page, GROUP);

        // Pointer deltas are screen pixels, sizes are flow units: without the zoom
        // correction the edge drifts away from the cursor (#170).
        const grab = await assertGrabbable(page, HEIGHT_HANDLE, 'height-resize-handle');
        const { before, after } = await dragHandle(page, grab, () => box(page, GROUP_BODY), 0, 120);

        const bottomMovedBy = after.y + after.height - (before.y + before.height);
        expect(bottomMovedBy).toBeGreaterThan(120 - 3);
        expect(bottomMovedBy).toBeLessThan(120 + 3);
    });
});
