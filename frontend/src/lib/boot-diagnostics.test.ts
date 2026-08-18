import { afterEach, describe, expect, it, vi } from 'vitest';
import {
    emitBootSummary,
    failBootPhase,
    finishBootPhase,
    parseServerTiming,
    recordBootRequest,
    startBootPhase,
} from './boot-diagnostics';

describe('boot diagnostics', () => {
    afterEach(() => {
        vi.restoreAllMocks();
        window.history.replaceState({}, '', '/');
    });

    it('pairs_start_and_finish_marks_into_one_measure', () => {
        const mark = vi.spyOn(performance, 'mark');
        const measure = vi.spyOn(performance, 'measure');

        const phase = startBootPhase('manifest');
        finishBootPhase(phase);

        expect(mark).toHaveBeenCalledWith(expect.stringContaining(':start'));
        expect(mark).toHaveBeenCalledWith(expect.stringContaining(':end'));
        expect(measure).toHaveBeenCalledWith(
            expect.stringContaining('manifest'),
            expect.objectContaining({ start: expect.stringContaining(':start'), end: expect.stringContaining(':end') }),
        );
    });

    it('failed_phase_records_duration_and_failure_without_payload_data', () => {
        const phase = startBootPhase('data-model');
        failBootPhase(phase, new Error('secret payload should not be stored'));

        const summary = emitBootSummary({ search: '?trellisDebug=boot' });
        const failedPhase = summary.phases.find((entry) => entry.name === 'data-model');

        expect(failedPhase).toMatchObject({ name: 'data-model', status: 'failed' });
        expect(failedPhase?.duration).toEqual(expect.any(Number));
        expect(JSON.stringify(summary)).not.toContain('secret payload');
    });

    it('parses_server_timing_metrics_with_duration_and_description', () => {
        expect(parseServerTiming('db;dur=12.5;desc="database", app;dur=3')).toEqual([
            { name: 'db', duration: 12.5, description: 'database' },
            { name: 'app', duration: 3 },
        ]);
    });

    it('debug_summary_is_emitted_only_for_trellis_debug_boot', () => {
        const group = vi.spyOn(console, 'groupCollapsed').mockImplementation(() => {});
        const log = vi.spyOn(console, 'log').mockImplementation(() => {});

        emitBootSummary({ search: '' });
        expect(group).not.toHaveBeenCalled();

        emitBootSummary({ search: '?trellisDebug=boot' });
        expect(group).toHaveBeenCalledTimes(1);
        expect(log).toHaveBeenCalledTimes(1);
    });

    it('summary_contains_phase_names_counts_status_sizes_and_durations_only', () => {
        recordBootRequest({
            url: '/api/manifest?model=customer',
            method: 'GET',
            status: 200,
            bytes: 128,
            duration: 4.5,
            payload: { model: 'customer', secret: 'do-not-store' },
        });

        const summary = emitBootSummary();
        const request = summary.requests.find((entry) => entry.path === '/api/manifest');

        expect(request).toMatchObject({
            path: '/api/manifest',
            method: 'GET',
            status: 200,
            bytes: 128,
            duration: 4.5,
        });
        expect(Object.keys(request ?? {}).sort()).toEqual(['bytes', 'duration', 'method', 'path', 'status']);
        expect(JSON.stringify(summary)).not.toContain('customer');
        expect(JSON.stringify(summary)).not.toContain('do-not-store');
    });
});
