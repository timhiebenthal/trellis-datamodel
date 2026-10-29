import { describe, it, expect } from 'vitest';
import type { Node, Edge } from '@xyflow/svelte';
import type { BusinessEvent, BusinessEventProcess } from '$lib/types';
import {
    addEntityModelStubs,
    buildDerivedEntities,
    collectEventLevelEntityIds,
    groupDraftedFieldsByEntity,
    mergeGeneratedRelationships,
    removeProcessDerivedEntities,
} from './entity-generation-canvas';

const entityNode = (id: string, data: Record<string, unknown> = {}): Node => ({
    id,
    type: 'entity',
    position: { x: 0, y: 0 },
    data: { label: id, ...data },
});

describe('collectEventLevelEntityIds', () => {
    it('reads string and object derived entities', () => {
        const events = [
            { derived_entities: ['a', { entity_id: 'b' }] },
            { derived_entities: undefined },
        ] as unknown as BusinessEvent[];
        expect([...collectEventLevelEntityIds(events)]).toEqual(['a', 'b']);
    });
});

describe('removeProcessDerivedEntities', () => {
    it('removes derived entities and edges, capturing drafted fields', () => {
        const fields = [{ name: 'qty', datatype: 'integer' }];
        const nodes = [
            entityNode('old', { drafted_fields: fields }),
            entityNode('keep'),
            { id: 'g', type: 'group', position: { x: 0, y: 0 }, data: {} } as Node,
        ];
        const edges = [
            { id: 'e1', source: 'old', target: 'keep' },
            { id: 'e2', source: 'keep', target: 'keep' },
        ] as Edge[];
        const result = removeProcessDerivedEntities({
            nodes,
            edges,
            process: { derived_entities: [{ entity_id: 'old' }] } as unknown as BusinessEventProcess,
            eventLevelEntityIds: new Set(),
            editedEntities: [],
        });
        expect(result.nodes.map((n) => n.id)).toEqual(['keep', 'g']);
        expect(result.edges.map((e) => e.id)).toEqual(['e2']);
        expect(result.previousDraftedFieldsMap.get('old')).toBe(fields);
    });
});

describe('groupDraftedFieldsByEntity', () => {
    it('maps target entity ids through slugged edited ids', () => {
        const map = groupDraftedFieldsByEntity(
            [{ id: 'orig' }],
            [{ id: 'New Name' }],
            [
                { name: 'a', datatype: 'text' as any, targetEntityId: 'orig' },
                { name: 'b', datatype: 'text' as any, targetEntityId: 'other' },
            ]
        );
        expect(map.get('new_name')).toEqual([{ name: 'a', datatype: 'text' }]);
        expect(map.get('other')).toEqual([{ name: 'b', datatype: 'text' }]);
    });
});

describe('addEntityModelStubs', () => {
    it('creates stub nodes for unknown relationship endpoints only', () => {
        const rels = [{ source: 'main', target: 'employee', label: 'Employee' }, { source: 'main', target: 'exists' }];
        const result = addEntityModelStubs({
            nodes: [entityNode('exists')],
            previewEntities: [{ id: 'main' }],
            previewRelationships: rels,
            relationships: rels,
            fieldsByEntity: new Map(),
            entityIdByIndex: ['main'],
            createdEntityIds: ['main'],
            inheritedDomain: 'sales',
            maxZIndex: 10,
        });
        expect(result.stubEntityIds).toEqual(['employee']);
        const stub = result.nodes.find((n) => n.id === 'employee')!;
        expect(stub.data).toMatchObject({ label: 'Employee', domain: 'sales', domains: ['sales'] });
        expect(stub.zIndex).toBe(15);
    });

    it('merges drafted fields onto existing canvas entities without duplicates', () => {
        const result = addEntityModelStubs({
            nodes: [entityNode('target', { drafted_fields: [{ name: 'a', datatype: 'text' }] })],
            previewEntities: [],
            previewRelationships: [],
            relationships: [],
            fieldsByEntity: new Map([
                ['target', [{ name: 'a', datatype: 'text' }, { name: 'b', datatype: 'text' }] as any],
            ]),
            entityIdByIndex: [],
            createdEntityIds: [],
            inheritedDomain: undefined,
            maxZIndex: 10,
        });
        expect((result.nodes[0].data as any).drafted_fields.map((f: any) => f.name)).toEqual(['a', 'b']);
    });

    it('skips fields for entities created in this run', () => {
        const result = addEntityModelStubs({
            nodes: [],
            previewEntities: [],
            previewRelationships: [],
            relationships: [],
            fieldsByEntity: new Map([['made', [{ name: 'a', datatype: 'text' }] as any]]),
            entityIdByIndex: ['made'],
            createdEntityIds: [],
            inheritedDomain: undefined,
            maxZIndex: 10,
        });
        expect(result.nodes).toEqual([]);
    });
});

describe('mergeGeneratedRelationships', () => {
    const base = {
        previewEntities: [{ id: 'orig_a' }, { id: 'orig_b' }],
        entityIdByIndex: ['a', 'b'],
        createdEntityIds: ['a', 'b'],
        nodes: [entityNode('a'), entityNode('b', { label: 'Bee' })],
        edges: [] as Edge[],
    };

    it('maps ids and creates an edge', () => {
        const edges = mergeGeneratedRelationships({
            ...base,
            relationships: [{ source: 'orig_a', target: 'orig_b', label: 'has', type: 'many_to_one' }],
        });
        expect(edges).toHaveLength(1);
        expect([edges[0].source, edges[0].target]).toEqual(['a', 'b']);
    });

    it('blanks filler labels and skips missing endpoints', () => {
        const edges = mergeGeneratedRelationships({
            ...base,
            relationships: [
                { source: 'orig_a', target: 'orig_b', label: 'Bee' },
                { source: 'orig_a', target: 'ghost', label: 'x' },
            ],
        });
        expect(edges).toHaveLength(1);
        expect(edges[0].data?.label).toBe('');
    });
});

describe('buildDerivedEntities', () => {
    it('dedupes ids and stamps created_at', () => {
        const now = new Date('2026-01-01T00:00:00Z');
        expect(buildDerivedEntities(['a', ''], ['a', 'b'], now)).toEqual([
            { entity_id: 'a', created_at: now.toISOString() },
            { entity_id: 'b', created_at: now.toISOString() },
        ]);
    });
});
