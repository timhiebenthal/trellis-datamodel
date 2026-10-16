/**
 * Boot regression loop for the canvas entry state.
 *
 * Reported symptom: with entities already in the store, the canvas route rendered a
 * lone "placeholder" entity box in the top-left instead of the shared loading
 * spinner, and deferred the Canvas import by 2000 ms.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, cleanup } from '@testing-library/svelte';
import { flushSync } from 'svelte';
import { writable } from 'svelte/store';
import { nodes, edges } from '$lib/stores';

const { canvasMounted } = vi.hoisted(() => ({ canvasMounted: vi.fn() }));

vi.mock('$app/stores', () => ({
    page: writable({ url: new URL('http://localhost/canvas') }),
}));

vi.mock('$lib/components/Canvas.svelte', () => ({
    default: () => {
        canvasMounted();
    },
}));

import CanvasPage from './+page.svelte';

beforeEach(async () => {
    canvasMounted.mockClear();
    // Resolve the mocked canvas module up front so its cached dynamic-import
    // promise is settled and each test observes a real import resolution.
    await import('$lib/components/Canvas.svelte');
    nodes.set([
        {
            id: 'orders',
            type: 'entity',
            position: { x: 0, y: 0 },
            data: { label: 'Orders' },
        } as any,
    ]);
    edges.set([]);
});

afterEach(() => {
    cleanup();
    vi.useRealTimers();
});

describe('canvas boot state', () => {
    it('shows the loading spinner instead of a placeholder entity box', () => {
        // No layout context is provided, so `loading` falls back to false — i.e. the
        // state the user sees immediately after core data publishes.
        const { container } = render(CanvasPage);

        expect(
            container.querySelector('.svelte-flow__node-entity'),
            'placeholder entity box must not be used as the boot state',
        ).toBeNull();
        expect(
            container.querySelector('[data-testid="canvas-loading"]'),
            'loading spinner must be visible while the canvas module loads',
        ).not.toBeNull();
    });

    it('mounts the canvas without the old 2s deferral', async () => {
        render(CanvasPage);

        expect(canvasMounted, 'canvas must not be mounted synchronously').not.toHaveBeenCalled();

        // The removed deferral only started the import at 2000 ms, so a 1.5s bound
        // fails red against it while passing for an immediate import.
        await new Promise((resolve) => setTimeout(resolve, 1500));
        flushSync();

        expect(
            canvasMounted,
            'canvas must mount without an artificial delay',
        ).toHaveBeenCalled();
    });
});
