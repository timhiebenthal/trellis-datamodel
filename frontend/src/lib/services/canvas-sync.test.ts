import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import type { Edge, Node } from '@xyflow/svelte';
import type { ModelInfo, Relationship } from '$lib/types';

vi.mock('$lib/api', () => ({
    inferRelationships: vi.fn(),
    syncDbtTests: vi.fn(),
}));

import { inferRelationships, syncDbtTests } from '$lib/api';
import {
    mergeInferredRelationships,
    pullFromFramework,
    pushToFramework,
    type CanvasGraph,
} from './canvas-sync';

const mockInfer = vi.mocked(inferRelationships);
const mockSync = vi.mocked(syncDbtTests);

function entity(id: string, data: Record<string, unknown> = {}): Node {
    return { id, type: 'entity', position: { x: 0, y: 0 }, data: { label: id, description: 'Described', ...data } };
}

function rel(source: string, target: string): Relationship {
    return { source, target, type: 'one_to_many' };
}

function model(name: string, extra: Partial<ModelInfo> = {}): ModelInfo {
    return { unique_id: `model.proj.${name}`, name, schema: 's', table: name, columns: [], ...extra };
}

function graph(overrides: Partial<CanvasGraph> = {}): CanvasGraph {
    return { nodes: [], edges: [], models: [], labelPrefixes: [], ...overrides };
}

describe('mergeInferredRelationships', () => {
    it('adds edges between existing entities without adding nodes', () => {
        const nodes = [entity('a'), entity('b')];
        const result = mergeInferredRelationships([rel('a', 'b')], graph({ nodes }));

        expect(result.addedRelationships).toBe(1);
        expect(result.addedNodes).toBe(0);
        expect(result.nodes).toBe(nodes);
        expect(result.edges).toHaveLength(1);
    });

    it('aggregates relationships for the same entity pair into one edge', () => {
        const nodes = [entity('a'), entity('b')];
        const result = mergeInferredRelationships([rel('a', 'b'), rel('b', 'a')], graph({ nodes }));

        expect(result.addedRelationships).toBe(1);
        expect(result.edges).toHaveLength(1);
    });

    it('does not mutate the input edges', () => {
        const edges: Edge[] = [];
        mergeInferredRelationships([rel('a', 'b')], graph({ nodes: [entity('a'), entity('b')], edges }));
        expect(edges).toHaveLength(0);
    });

    it('adds missing endpoints as entity nodes, staggered and labelled from the model', () => {
        const orders = model('fct_orders', {
            description: 'Orders',
            file_path: 'models/marts/fct_orders.sql',
            tags: ['core'],
        });
        const result = mergeInferredRelationships(
            [rel(orders.unique_id, 'raw_customer')],
            graph({ models: [orders], labelPrefixes: ['fct_'] }),
        );

        expect(result.addedNodes).toBe(2);
        const [first, second] = result.nodes;
        expect(first).toMatchObject({
            id: orders.unique_id,
            type: 'entity',
            position: { x: 200, y: 200 },
            zIndex: 10,
            data: {
                label: 'Orders',
                description: 'Orders',
                model_ref: orders.unique_id,
                folder: 'marts',
                tags: ['core'],
                width: 280,
                panelHeight: 200,
                collapsed: false,
            },
        });
        // Unknown models fall back to the id for the label and stay unbound.
        expect(second).toMatchObject({
            id: 'raw_customer',
            position: { x: 260, y: 200 },
            data: { label: 'Raw Customer', description: '', model_ref: null, folder: null, tags: [] },
        });
    });

    it('matches models by name as well as unique_id and adds each endpoint once', () => {
        const orders = model('orders');
        const result = mergeInferredRelationships(
            [rel('orders', 'customers'), rel('orders', 'customers')],
            graph({ models: [orders] }),
        );

        expect(result.addedNodes).toBe(2);
        expect(result.nodes[0].data.model_ref).toBe(orders.unique_id);
    });

    it('ignores empty endpoints', () => {
        const result = mergeInferredRelationships(
            [{ source: '', target: 'b', type: 'one_to_one' }],
            graph({ nodes: [entity('b')] }),
        );
        expect(result.addedNodes).toBe(0);
    });
});

describe('pullFromFramework', () => {
    beforeEach(() => {
        vi.spyOn(console, 'error').mockImplementation(() => {});
    });

    afterEach(() => {
        vi.restoreAllMocks();
        vi.clearAllMocks();
    });

    it('returns the framework copy message when nothing is inferred', async () => {
        mockInfer.mockResolvedValue([]);
        const getGraph = vi.fn(() => graph());

        const outcome = await pullFromFramework({ getGraph, noRelationshipsMessage: 'Nothing here' });

        expect(outcome).toEqual({ message: 'Nothing here', clearAfterMs: 3000 });
        expect(getGraph).not.toHaveBeenCalled();
    });

    it('reports when every inferred relationship already exists', async () => {
        const nodes = [entity('a'), entity('b')];
        const { edges } = mergeInferredRelationships([rel('a', 'b')], graph({ nodes }));
        mockInfer.mockResolvedValue([rel('a', 'b')]);

        const outcome = await pullFromFramework({
            getGraph: () => graph({ nodes, edges }),
            noRelationshipsMessage: 'x',
        });

        expect(outcome).toEqual({ message: '✓ No new relationships found', clearAfterMs: 3000 });
    });

    it('returns edges only when no nodes were added', async () => {
        mockInfer.mockResolvedValue([rel('a', 'b')]);

        const outcome = await pullFromFramework({
            getGraph: () => graph({ nodes: [entity('a'), entity('b')] }),
            noRelationshipsMessage: 'x',
        });

        expect(outcome.message).toBe('✓ Added 1 relationship');
        expect(outcome.clearAfterMs).toBe(3000);
        expect(outcome.nodes).toBeUndefined();
        expect(outcome.edges).toHaveLength(1);
    });

    it('returns new nodes and pluralises the summary', async () => {
        mockInfer.mockResolvedValue([rel('a', 'b'), rel('a', 'c')]);

        const outcome = await pullFromFramework({
            getGraph: () => graph({ nodes: [entity('a')] }),
            noRelationshipsMessage: 'x',
        });

        expect(outcome.message).toBe('✓ Added 2 relationships, 2 nodes');
        expect(outcome.nodes?.map((n) => n.id)).toEqual(['a', 'b', 'c']);
        expect(outcome.edges).toHaveLength(2);
    });

    it('reads the graph after inference resolves', async () => {
        const order: string[] = [];
        mockInfer.mockImplementation(async () => {
            order.push('infer');
            return [rel('a', 'b')];
        });

        await pullFromFramework({
            getGraph: () => {
                order.push('getGraph');
                return graph();
            },
            noRelationshipsMessage: 'x',
        });

        expect(order).toEqual(['infer', 'getGraph']);
    });

    it('returns a failure status when inference throws', async () => {
        mockInfer.mockRejectedValue(new Error('boom'));

        const outcome = await pullFromFramework({ getGraph: () => graph(), noRelationshipsMessage: 'x' });

        expect(outcome).toEqual({ message: '✗ Failed to infer', clearAfterMs: 5000 });
        expect(console.error).toHaveBeenCalled();
    });
});

describe('pushToFramework', () => {
    const incomplete = entity('draft', { description: '' });
    const undescribed = entity('orders', { drafted_fields: [{ name: 'amount', description: '' }] });

    beforeEach(() => {
        mockSync.mockResolvedValue({ message: 'Synced 3 tests' });
        vi.spyOn(console, 'warn').mockImplementation(() => {});
    });

    afterEach(() => {
        vi.restoreAllMocks();
        vi.clearAllMocks();
    });

    function deps(nodes: Node[], overrides: Partial<Parameters<typeof pushToFramework>[0]> = {}) {
        return {
            nodes,
            pushWarningEnabled: true,
            confirmIncomplete: vi.fn().mockResolvedValue(true),
            confirmUndescribed: vi.fn().mockResolvedValue(true),
            ...overrides,
        };
    }

    it('syncs without asking when the model is complete', async () => {
        const d = deps([entity('a')]);

        const outcome = await pushToFramework(d);

        expect(outcome).toEqual({ ok: true, message: '✓ Synced 3 tests', clearAfterMs: 3000 });
        expect(d.confirmIncomplete).not.toHaveBeenCalled();
        expect(d.confirmUndescribed).not.toHaveBeenCalled();
    });

    it('asks about incomplete entities, then undescribed attributes, before syncing', async () => {
        const d = deps([incomplete, undescribed]);

        await pushToFramework(d);

        expect(d.confirmIncomplete).toHaveBeenCalledWith([incomplete]);
        expect(d.confirmUndescribed).toHaveBeenCalledWith([
            { entityLabel: 'orders', entityId: 'orders', attributeNames: ['amount'] },
        ]);
        expect(mockSync).toHaveBeenCalledOnce();
    });

    it('returns null without syncing when the incomplete warning is cancelled', async () => {
        const d = deps([incomplete, undescribed], { confirmIncomplete: vi.fn().mockResolvedValue(false) });

        expect(await pushToFramework(d)).toBeNull();
        expect(d.confirmUndescribed).not.toHaveBeenCalled();
        expect(mockSync).not.toHaveBeenCalled();
    });

    it('returns null without syncing when the undescribed warning is cancelled', async () => {
        const d = deps([undescribed], { confirmUndescribed: vi.fn().mockResolvedValue(false) });

        expect(await pushToFramework(d)).toBeNull();
        expect(d.confirmIncomplete).not.toHaveBeenCalled();
        expect(mockSync).not.toHaveBeenCalled();
    });

    it('skips the warnings when push guidance is disabled', async () => {
        const d = deps([incomplete], { pushWarningEnabled: false });

        const outcome = await pushToFramework(d);

        expect(outcome?.ok).toBe(true);
        expect(d.confirmIncomplete).not.toHaveBeenCalled();
    });

    it('logs sync warnings', async () => {
        mockSync.mockResolvedValue({ message: 'ok', warnings: ['w1'] });

        await pushToFramework(deps([entity('a')]));

        expect(console.warn).toHaveBeenCalledWith('[trellis] sync warning:', 'w1');
    });

    it('returns a failure status with the error message when sync throws', async () => {
        mockSync.mockRejectedValue(new Error('Backend down'));

        expect(await pushToFramework(deps([entity('a')]))).toEqual({
            ok: false,
            message: '✗ Backend down',
            clearAfterMs: 5000,
        });
    });

    it('falls back to a generic message for non-Error rejections', async () => {
        mockSync.mockRejectedValue('nope');

        expect((await pushToFramework(deps([entity('a')])))?.message).toBe('✗ Sync failed');
    });
});
