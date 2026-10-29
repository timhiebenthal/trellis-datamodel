import { describe, expect, it, vi } from 'vitest';
import type { Edge, Node } from '@xyflow/svelte';
import type { LineageNode, LineageResponse } from '$lib/types';
import {
    CONNECTED_NODE_CLASS,
    DEFAULT_EDGE_STYLE,
    HIGHLIGHT_EDGE_STYLE,
    buildLineageGraph,
    buildUpstreamMap,
    computeVisibleNodeIds,
    highlightConnections,
} from './lineage-graph';

function node(id: string, level: number, extra: Partial<LineageNode> = {}): LineageNode {
    return { id, label: id, level, isSource: false, ...extra };
}

function response(
    nodes: LineageNode[],
    edges: Array<[string, string]>,
    lineageLayers?: string[],
): LineageResponse {
    return {
        nodes,
        edges: edges.map(([source, target]) => ({ source, target, level: 1 })),
        metadata: {
            root_model_id: 'root',
            level_counts: {},
            total_nodes: nodes.length,
            total_edges: edges.length,
            lineage_layers: lineageLayers,
        },
    };
}

function build(data: LineageResponse, expanded: string[] = [], onExpand = vi.fn()) {
    return buildLineageGraph({
        data,
        modelId: null,
        expandedNodeIds: new Set(expanded),
        existingPositions: new Map(),
        onExpand,
    });
}

// root <- a <- b <- c, plus a source feeding c
const CHAIN = response(
    [
        node('root', 0),
        node('a', 1),
        node('b', 2),
        node('c', 3),
        node('src', 4, { isSource: true, sourceName: 'crm' }),
    ],
    [
        ['a', 'root'],
        ['b', 'a'],
        ['c', 'b'],
        ['src', 'c'],
    ],
);

describe('computeVisibleNodeIds', () => {
    it('shows root, direct parents and all sources, then one more hop per expanded node', () => {
        const upstreamOf = buildUpstreamMap(CHAIN.edges);

        expect([...computeVisibleNodeIds(CHAIN, 'root', new Set(), upstreamOf)].sort()).toEqual([
            'a',
            'root',
            'src',
        ]);
        expect([...computeVisibleNodeIds(CHAIN, 'root', new Set(['a']), upstreamOf)].sort()).toEqual([
            'a',
            'b',
            'root',
            'src',
        ]);
    });
});

describe('buildLineageGraph', () => {
    it('returns null when there is no root to anchor on', () => {
        const data = response([], []);
        data.metadata.root_model_id = '';

        expect(build(data)).toBeNull();
    });

    it('positions unlayered nodes by level: sources on top, root at the bottom', () => {
        const graph = build(CHAIN)!;
        const byId = new Map(graph.nodes.map((n) => [n.id, n]));

        expect(byId.get('src')!.position.y).toBe(80);
        expect(byId.get('root')!.position.y).toBe(500);
        expect(byId.get('a')!.position.y).toBe(380);
        expect(byId.get('src')!.type).toBe('source');
        expect(byId.get('root')!.type).toBe('default');
        expect(graph.layerBandMeta).toEqual([]);
        expect(graph.layerBoundsByLayer).toEqual({});
    });

    it('routes hidden intermediates through a placeholder instead of a direct edge', () => {
        const graph = build(CHAIN)!;

        // c is hidden; src (visible) reaches root only through hidden c, b, so a `...`
        // placeholder hangs off the downstream visible node (root).
        const placeholder = graph.nodes.find((n) => n.id === 'placeholder-a');
        expect(placeholder).toBeDefined();
        expect(placeholder!.type).toBe('placeholder');

        const edgeIds = graph.edges.map((e) => e.id).sort();
        expect(edgeIds).toEqual(
            ['edge-a-root', 'edge-src-placeholder-a', 'edge-placeholder-a-a'].sort(),
        );
    });

    it('wires placeholder clicks to the expand callback with the target id', () => {
        const onExpand = vi.fn();
        const graph = build(CHAIN, [], onExpand)!;

        const placeholder = graph.nodes.find((n) => n.id === 'placeholder-a')!;
        (placeholder.data as { onClick: () => void }).onClick();

        expect(onExpand).toHaveBeenCalledWith('a');
    });

    it('drops the placeholder once the hidden hop is expanded', () => {
        const graph = build(CHAIN, ['a', 'b', 'c'])!;

        expect(graph.nodes.some((n) => n.type === 'placeholder')).toBe(false);
        expect(graph.edges.map((e) => e.id)).toContain('edge-b-a');
    });

    it('keeps a dragged x on rebuild (y is only kept inside layer bands)', () => {
        const graph = buildLineageGraph({
            data: CHAIN,
            modelId: null,
            expandedNodeIds: new Set(),
            existingPositions: new Map([['a', { x: 42, y: 77 }]]),
            onExpand: vi.fn(),
        })!;

        expect(graph.nodes.find((n) => n.id === 'a')!.position).toEqual({ x: 42, y: 380 });
    });

    describe('with layers configured', () => {
        const layered = response(
            [
                node('root', 0, { layer: '2_core' }),
                node('a', 1, { layer: '1_clean' }),
                node('src', 2, { isSource: true, layer: 'sources' }),
                node('stray', 1, { layer: 'unassigned' }),
            ],
            [
                ['a', 'root'],
                ['src', 'a'],
                ['stray', 'root'],
            ],
            ['1_clean', '2_core'],
        );

        it('stacks bands as sources, configured layers in order, then unassigned', () => {
            const graph = build(layered)!;

            expect(graph.nodes.filter((n) => n.type === 'layerBand').map((n) => n.id)).toEqual([
                'layer-band-sources',
                'layer-band-1_clean',
                'layer-band-2_core',
                'layer-band-unassigned',
            ]);
            expect(graph.layerBandMeta.map((b) => b.id)).toEqual([
                'layer-band-sources',
                'layer-band-1_clean',
                'layer-band-2_core',
                'layer-band-unassigned',
            ]);

            const bounds = graph.layerBoundsByLayer;
            expect(bounds.sources.top).toBe(60);
            expect(bounds['1_clean'].top).toBe(bounds.sources.bottom + 24);
        });

        it('clamps nodes inside their band and gives them a vertical extent', () => {
            const graph = build(layered)!;
            const root = graph.nodes.find((n) => n.id === 'root')!;
            const { top, bottom } = graph.layerBoundsByLayer['2_core'];

            expect(root.position.y).toBeGreaterThanOrEqual(top + 30);
            expect(root.position.y).toBeLessThanOrEqual(bottom - 30);
            expect(root.extent).toEqual([
                [-100000, top + 30],
                [100000, bottom - 30],
            ]);
        });

        it('keeps a dragged y, clamped to the band', () => {
            const graph = buildLineageGraph({
                data: layered,
                modelId: null,
                expandedNodeIds: new Set(),
                existingPositions: new Map([['root', { x: 5, y: 100000 }]]),
                onExpand: vi.fn(),
            })!;
            const root = graph.nodes.find((n) => n.id === 'root')!;

            expect(root.position.x).toBe(5);
            expect(root.position.y).toBe(graph.layerBoundsByLayer['2_core'].bottom - 30);
        });

        it('puts bands behind edges and nodes', () => {
            const graph = build(layered)!;

            for (const n of graph.nodes) {
                if (n.type === 'layerBand') expect(n.zIndex).toBe(-1);
                else expect(n.zIndex).toBeGreaterThanOrEqual(10);
            }
        });
    });
});

describe('highlightConnections', () => {
    const nodes: Node[] = [
        { id: 'root', position: { x: 0, y: 0 }, data: {} },
        { id: 'a', position: { x: 0, y: 0 }, data: {} },
        { id: 'other', position: { x: 0, y: 0 }, data: {} },
        { id: 'layer-band-x', position: { x: 0, y: 0 }, data: {} },
    ];
    const edges: Edge[] = [
        { id: 'e1', source: 'a', target: 'root' },
        { id: 'e2', source: 'other', target: 'a2' },
    ];
    const lineageEdges = [{ source: 'a', target: 'root', level: 1 }];

    it('highlights the selected node and its upstream closure, dims the rest', () => {
        const result = highlightConnections(nodes, edges, 'root', lineageEdges);

        expect(result.edges.find((e) => e.id === 'e1')!.style).toBe(HIGHLIGHT_EDGE_STYLE);
        expect(result.edges.find((e) => e.id === 'e2')!.style).toBe(DEFAULT_EDGE_STYLE);
        expect(result.nodes.find((n) => n.id === 'root')!.class).toBe(CONNECTED_NODE_CLASS);
        expect(result.nodes.find((n) => n.id === 'a')!.class).toBe(CONNECTED_NODE_CLASS);
        expect(result.nodes.find((n) => n.id === 'other')!.class).toBeUndefined();
    });

    it('leaves background layer bands untouched', () => {
        const result = highlightConnections(nodes, edges, 'root', lineageEdges);

        expect(result.nodes.find((n) => n.id === 'layer-band-x')).toBe(nodes[3]);
    });

    it('resets to the default look when nothing is selected', () => {
        const result = highlightConnections(nodes, edges, null, lineageEdges);

        expect(result.edges.every((e) => e.style === DEFAULT_EDGE_STYLE)).toBe(true);
        expect(result.nodes.find((n) => n.id === 'root')!.style).toBe('opacity: 1;');
        expect(result.nodes.find((n) => n.id === 'root')!.class).toBeUndefined();
    });

    it('extends highlighting through a placeholder next to a connected node', () => {
        const withPlaceholder: Edge[] = [
            { id: 'p1', source: 'far', target: 'placeholder-root' },
            { id: 'p2', source: 'placeholder-root', target: 'root' },
        ];

        const result = highlightConnections(
            [{ id: 'placeholder-root', position: { x: 0, y: 0 }, data: {} }, ...nodes],
            withPlaceholder,
            'root',
            [],
        );

        expect(result.edges.find((e) => e.id === 'p2')!.style).toBe(HIGHLIGHT_EDGE_STYLE);
    });
});
