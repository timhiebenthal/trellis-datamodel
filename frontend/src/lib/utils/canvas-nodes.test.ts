import { describe, it, expect } from 'vitest';
import type { Node } from '@xyflow/svelte';
import type { Entity, EntityFlowNode, ModelInfo } from '$lib/types';
import { buildEntityNodes, groupEntityNodesByFolder, smartPositionNodes } from './canvas-nodes';

function model(name: string, file_path?: string): ModelInfo {
    return { unique_id: `model.proj.${name}`, name, schema: 's', table: name, columns: [], file_path };
}

function flowNode(id: string, x: number, y: number, data: Partial<EntityFlowNode['data']> = {}): EntityFlowNode {
    return { id, type: 'entity', position: { x, y }, data: { label: id, ...data } } as EntityFlowNode;
}

describe('buildEntityNodes', () => {
    it('applies defaults and resolves folder and label from the bound model', () => {
        const orders = model('dim_customer', 'models/marts/core/dim_customer.sql');
        const [node] = buildEntityNodes(
            [{ id: 'customer', label: '', model_ref: orders.unique_id } as unknown as Entity],
            [orders],
            ['dim_'],
        );

        expect(node).toMatchObject({
            id: 'customer',
            type: 'entity',
            position: { x: 0, y: 0 },
            zIndex: 10,
            parentId: undefined,
            data: {
                label: 'Customer',
                model_ref: orders.unique_id,
                width: 280,
                panelHeight: 200,
                collapsed: false,
                folder: 'marts/core',
            },
        });
    });

    it('keeps explicit values and accepts the legacy panelHeight key', () => {
        const [explicit, legacy] = buildEntityNodes(
            [
                { id: 'a', label: '  Alpha ', position: { x: 5, y: 6 }, width: 300, panel_height: 120, collapsed: true } as unknown as Entity,
                { id: 'b_thing', panelHeight: 90 } as unknown as Entity,
            ],
            [],
            [],
        );

        expect(explicit.position).toEqual({ x: 5, y: 6 });
        expect(explicit.data).toMatchObject({ label: 'Alpha', width: 300, panelHeight: 120, collapsed: true, folder: null });
        // Unbound entities fall back to a label formatted from the id.
        expect(legacy.data).toMatchObject({ label: 'B Thing', panelHeight: 90, folder: null });
        expect(legacy.data.model_ref).toBeUndefined();
    });
});

describe('groupEntityNodesByFolder', () => {
    it('wraps each folder in a padded group and reparents its children', () => {
        const a = flowNode('a', 100, 200, { folder: 'marts/core', width: 280, panelHeight: 200 });
        const b = flowNode('b', 400, 300, { folder: 'marts/core', width: 280, panelHeight: 200 });
        const loose = flowNode('loose', 0, 0, { folder: null });

        const groups = groupEntityNodesByFolder([a, b, loose]);

        expect(groups).toHaveLength(1);
        const [group] = groups;
        // x: 100 - 40, y: 200 - 40 - 60, width: (680 - 100) + 80, height: (500 - 200) + 80 + 60
        expect(group).toMatchObject({
            id: 'group-marts-core',
            type: 'group',
            position: { x: 60, y: 100 },
            style: 'width: 660px; height: 440px;',
            zIndex: 1,
            data: { label: 'core', description: 'Folder: marts/core', width: 660, height: 440, collapsed: false },
        });
        expect(a).toMatchObject({ parentId: 'group-marts-core', position: { x: 40, y: 100 }, extent: 'parent' });
        expect(b.position).toEqual({ x: 340, y: 200 });
        expect(loose.parentId).toBeUndefined();
    });

    it('moves an overlapping group to the right of and below the previous one', () => {
        const first = flowNode('a', 0, 0, { folder: 'one' });
        const second = flowNode('b', 10, 10, { folder: 'two' });

        const [g1, g2] = groupEntityNodesByFolder([first, second]);

        expect(g1.position).toEqual({ x: -40, y: -100 });
        // g1 is 360 x 340; g2 starts after it plus 50px spacing on both axes.
        expect(g2.position).toEqual({ x: -40 + 360 + 50, y: -100 + 340 + 50 });
    });

    it('returns no groups when no entity has a folder', () => {
        expect(groupEntityNodesByFolder([flowNode('a', 0, 0)])).toEqual([]);
    });
});

describe('smartPositionNodes', () => {
    it('places facts in a central grid, dimensions on a ring and the rest around the center', () => {
        const fact = flowNode('fact', 0, 0, { entity_type: 'fact' });
        const dim1 = flowNode('dim1', 1000, 0, { entity_type: 'dimension' });
        const dim2 = flowNode('dim2', 0, 800, { entity_type: 'dimension' });
        const other = flowNode('other', 1000, 800);
        const group: Node = { id: 'g', type: 'group', position: { x: 9, y: 9 }, data: {} };
        const nodes: Node[] = [group, fact, dim1, dim2, other];

        const result = smartPositionNodes(nodes, [fact, dim1, dim2, other], () => 0.75);

        // Center is the midpoint of the entity bounding box: (500, 400).
        expect(result[0]).toBe(group);
        expect(result[1].position).toEqual({ x: 400, y: 300 });
        expect(result[2].position).toEqual({ x: 1000, y: 400 });
        expect(result[3].position.x).toBeCloseTo(0);
        expect(result[3].position.y).toBeCloseTo(400);
        expect(result[4].position).toEqual({ x: 650, y: 550 });
    });

    it('leaves nodes outside the given entity list untouched', () => {
        const a = flowNode('a', 1, 2, { entity_type: 'fact' });
        const b = flowNode('b', 3, 4, { entity_type: 'fact' });

        const result = smartPositionNodes([a, b], [a]);

        expect(result[1]).toBe(b);
    });
});
