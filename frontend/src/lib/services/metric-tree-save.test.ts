import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { MetricTreeFile } from '$lib/types';

vi.mock('$lib/api', () => ({
    saveMetricTree: vi.fn(),
}));

import { saveMetricTree } from '$lib/api';
import { MetricTreeSaveService, type MetricTreeSaveState } from './metric-tree-save';

const saveMock = vi.mocked(saveMetricTree);

function tree(overrides: Partial<MetricTreeFile> = {}): MetricTreeFile {
    return {
        version: 0.1,
        metrics: [
            { id: 'revenue', label: 'Revenue', expression: 'sum(amount)' },
            { id: 'orders', label: 'Orders', expression: 'count(*)' },
        ],
        influences: [{ effect: 'revenue', drivers: ['orders'] }],
        ...overrides,
    };
}

function renamed(label: string): MetricTreeFile {
    const payload = tree();
    payload.metrics[0] = { ...payload.metrics[0], label };
    return payload;
}

describe('MetricTreeSaveService', () => {
    let states: MetricTreeSaveState[];

    beforeEach(() => {
        vi.useFakeTimers();
        saveMock.mockReset();
        saveMock.mockResolvedValue({ status: 'success', warnings: [] });
        states = [];
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    function service(options: { canSave?: (payload: MetricTreeFile) => boolean } = {}) {
        return new MetricTreeSaveService({
            debounceMs: 400,
            canSave: options.canSave,
            onStateChange: (state) => states.push(state),
        });
    }

    it('waits 400 ms before saving', async () => {
        const saver = service();

        saver.save(tree());
        await vi.advanceTimersByTimeAsync(399);
        expect(saveMock).not.toHaveBeenCalled();

        await vi.advanceTimersByTimeAsync(1);
        expect(saveMock).toHaveBeenCalledOnce();
        expect(saveMock).toHaveBeenCalledWith(tree());
    });

    it('coalesces rapid edits into a single save of the latest payload', async () => {
        const saver = service();

        saver.save(renamed('Revenue a'));
        await vi.advanceTimersByTimeAsync(200);
        saver.save(renamed('Revenue ab'));
        await vi.advanceTimersByTimeAsync(200);
        saver.save(renamed('Revenue abc'));

        await vi.advanceTimersByTimeAsync(400);

        expect(saveMock).toHaveBeenCalledOnce();
        expect((saveMock.mock.calls[0][0] as MetricTreeFile).metrics[0].label).toBe('Revenue abc');
    });

    it('coalesces an edit made while a save is in flight and sends it once the first settles', async () => {
        const saver = service();
        let releaseFirst: (value: { status: string; warnings: string[] }) => void = () => {};
        saveMock.mockImplementationOnce(
            () =>
                new Promise((resolve) => {
                    releaseFirst = resolve;
                }),
        );

        saver.save(renamed('first'));
        await vi.advanceTimersByTimeAsync(400);
        expect(saveMock).toHaveBeenCalledOnce();

        saver.save(renamed('second'));
        releaseFirst({ status: 'success', warnings: [] });
        await vi.advanceTimersByTimeAsync(0);

        expect(saveMock).toHaveBeenCalledTimes(2);
        expect((saveMock.mock.calls[1][0] as MetricTreeFile).metrics[0].label).toBe('second');
    });

    it('does not save the same payload twice', async () => {
        const saver = service();

        saver.save(tree());
        await vi.advanceTimersByTimeAsync(400);
        saver.save(tree());
        await vi.advanceTimersByTimeAsync(400);

        expect(saveMock).toHaveBeenCalledOnce();
    });

    it('reports isSaving and hasUnsavedChanges around a save', async () => {
        const saver = service();
        const payload = tree();
        saver.initializeBaseline(payload);

        expect(saver.hasUnsavedChanges(payload)).toBe(false);

        const edited = renamed('Changed');
        saver.save(edited);
        expect(saver.isSavingActive()).toBe(true);
        expect(saver.hasUnsavedChanges(edited)).toBe(true);

        await vi.advanceTimersByTimeAsync(400);

        expect(saver.isSavingActive()).toBe(false);
        expect(saver.hasUnsavedChanges(edited)).toBe(false);
        expect(states.at(-1)?.isSaving).toBe(false);
    });

    it('keeps the edit and the error when the save is rejected', async () => {
        const saver = service();
        saver.initializeBaseline(tree());
        saveMock.mockRejectedValueOnce(new Error('Failed to save metric tree: 422 - bad expression'));

        const edited = renamed('Broken');
        saver.save(edited);
        await vi.advanceTimersByTimeAsync(400);

        expect(saver.getError()).toContain('422');
        expect(saver.hasUnsavedChanges(edited)).toBe(true);
        expect(saver.isSavingActive()).toBe(false);
        expect(states.at(-1)?.error).toContain('422');
    });

    it('clears the error on the next successful save', async () => {
        const saver = service();
        saveMock.mockRejectedValueOnce(new Error('boom'));

        saver.save(renamed('First'));
        await vi.advanceTimersByTimeAsync(400);
        expect(saver.getError()).toBe('boom');

        const fixed = renamed('Fixed');
        saver.save(fixed);
        await vi.advanceTimersByTimeAsync(400);

        expect(saver.getError()).toBeNull();
        expect(saver.hasUnsavedChanges(fixed)).toBe(false);
    });

    it('surfaces server warnings and clears them on the next successful save', async () => {
        const saver = service();
        saveMock.mockResolvedValueOnce({ status: 'success', warnings: ['revenue: dataset_ref gone'] });

        saver.save(renamed('First'));
        await vi.advanceTimersByTimeAsync(400);
        expect(saver.getWarnings()).toEqual(['revenue: dataset_ref gone']);

        saver.save(renamed('Second'));
        await vi.advanceTimersByTimeAsync(400);
        expect(saver.getWarnings()).toEqual([]);
    });

    it('refuses to save while the payload is incomplete', async () => {
        const saver = service({ canSave: (payload) => payload.metrics.every((m) => m.binding || m.expression) });
        saver.initializeBaseline(tree());

        const incomplete = tree();
        incomplete.metrics[1] = { id: 'orders', label: 'Orders', description: '', expression: '' };

        saver.save(incomplete);
        await vi.advanceTimersByTimeAsync(1000);

        expect(saveMock).not.toHaveBeenCalled();
        expect(saver.isSavingActive()).toBe(false);
        expect(saver.hasUnsavedChanges(incomplete)).toBe(true);
    });

    it('saves again once the payload becomes valid', async () => {
        const saver = service({ canSave: (payload) => payload.metrics.every((m) => m.binding || m.expression) });
        const incomplete = tree();
        incomplete.metrics[1] = { id: 'orders', label: 'Orders', description: '', expression: '' };

        saver.save(incomplete);
        await vi.advanceTimersByTimeAsync(500);
        expect(saveMock).not.toHaveBeenCalled();

        saver.save(tree());
        await vi.advanceTimersByTimeAsync(400);

        expect(saveMock).toHaveBeenCalledOnce();
    });

    it('saveNow bypasses the debounce', async () => {
        const saver = service();

        await saver.saveNow(tree());

        expect(saveMock).toHaveBeenCalledOnce();
        expect(saver.isSavingActive()).toBe(false);
    });

    it('flushSync sends a pending change immediately and cancels the timer', async () => {
        const saver = service();
        const edited = renamed('Pending');

        saver.save(edited);
        await saver.flushSync(edited);

        expect(saveMock).toHaveBeenCalledOnce();
        expect(saveMock).toHaveBeenCalledWith(edited);

        await vi.advanceTimersByTimeAsync(1000);
        expect(saveMock).toHaveBeenCalledOnce();
    });

    it('flushSync does nothing when there is nothing pending', async () => {
        const saver = service();
        const payload = tree();
        saver.initializeBaseline(payload);

        await saver.flushSync(payload);

        expect(saveMock).not.toHaveBeenCalled();
    });

    it('flushSync waits for a save already in flight for the same payload', async () => {
        const saver = service();
        let release: (value: { status: string; warnings: string[] }) => void = () => {};
        saveMock.mockImplementationOnce(
            () =>
                new Promise((resolve) => {
                    release = resolve;
                }),
        );

        const edited = renamed('In flight');
        saver.save(edited);
        await vi.advanceTimersByTimeAsync(400);

        const flushed = saver.flushSync(edited);
        release({ status: 'success', warnings: [] });
        await flushed;

        expect(saveMock).toHaveBeenCalledOnce();
        expect(saver.hasUnsavedChanges(edited)).toBe(false);
    });
});
