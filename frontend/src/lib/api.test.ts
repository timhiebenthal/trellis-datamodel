import { describe, it, expect, vi, afterEach } from 'vitest';
import { inferRelationships } from './api';

describe('inferRelationships', () => {
    afterEach(() => {
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
    });

    it('returns relationships when API responds with array', async () => {
        const rel = {
            source: 'lead',
            target: 'customer',
            source_field: 'lead_id',
            target_field: 'lead_id',
        };

        vi.stubGlobal(
            'fetch',
            vi.fn().mockResolvedValue({
                ok: true,
                json: vi.fn().mockResolvedValue([rel]),
            }),
        );

        const result = await inferRelationships();
        expect(result).toHaveLength(1);
        expect(result[0]).toMatchObject(rel);
    });

    it('returns relationships when API responds with object wrapper', async () => {
        const rel = {
            source: 'lead',
            target: 'customer',
            source_field: 'lead_id',
            target_field: 'lead_id',
        };

        vi.stubGlobal(
            'fetch',
            vi.fn().mockResolvedValue({
                ok: true,
                json: vi.fn().mockResolvedValue({ relationships: [rel] }),
            }),
        );

        const result = await inferRelationships();
        expect(result).toHaveLength(1);
        expect(result[0]).toMatchObject(rel);
    });

    it('returns empty array on 400 response', async () => {
        vi.stubGlobal(
            'fetch',
            vi.fn().mockResolvedValue({
                ok: false,
                status: 400,
                statusText: 'Bad Request',
                text: vi.fn().mockResolvedValue(''),
            }),
        );

        await expect(inferRelationships()).resolves.toEqual([]);
    });
});
