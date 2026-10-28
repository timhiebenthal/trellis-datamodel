import { describe, it, expect } from 'vitest';
import { buildEntityNodes, findLegacyAliasNodeIds } from '$lib/utils/entity-generation';
import type { Node } from '@xyflow/svelte';

type TestEntity = { id: string; label: string; entity_type: string };

const positioner = {
    calculateSmartPosition: () => ({ x: 100, y: 100 }),
};

function runEntityCreationLoop(editedEntities: TestEntity[], initialNodes: Node[] = []): Node[] {
    return buildEntityNodes({
        editedEntities,
        previewEntities: editedEntities.map((e) => ({
            id: e.id,
            label: e.label,
            entity_type: e.entity_type as 'fact' | 'dimension' | 'unclassified',
        })),
        initialNodes,
        previousDraftedFieldsMap: new Map(),
        fieldsByEntity: new Map(),
        modelingStyle: 'dimensional_model',
        inheritedDomain: undefined,
        maxZIndex: 10,
        positioner,
    }).nodes;
}

function removeLegacyAliasNodes(editedEntities: TestEntity[], initialNodes: Node[]): Node[] {
    const aliasIds = new Set(findLegacyAliasNodeIds(editedEntities, initialNodes));
    return initialNodes.filter((node) => !aliasIds.has(node.id));
}

describe('GenerateEntitiesDialog – entity creation loop deduplication', () => {
    it('adds only one node when two edited entities share the same ID', () => {
        const editedEntities = [
            { id: 'customer', label: 'Customer', entity_type: 'dimension' },
            { id: 'customer', label: 'Customer', entity_type: 'dimension' },
        ];

        const resultNodes = runEntityCreationLoop(editedEntities);

        const entityNodes = resultNodes.filter((n) => n.type === 'entity');
        expect(entityNodes).toHaveLength(1);
        expect(entityNodes[0].id).toBe('customer');
    });

    it('adds distinct nodes when entity IDs are different', () => {
        const editedEntities = [
            { id: 'customer', label: 'Customer', entity_type: 'dimension' },
            { id: 'order',    label: 'Order',    entity_type: 'fact' },
        ];

        const resultNodes = runEntityCreationLoop(editedEntities);

        const entityNodes = resultNodes.filter((n) => n.type === 'entity');
        expect(entityNodes).toHaveLength(2);
        expect(entityNodes.map((n) => n.id)).toEqual(
            expect.arrayContaining(['customer', 'order'])
        );
    });

    it('does not add a node whose ID already exists in the initial canvas nodes', () => {
        const existingNode: Node = {
            id: 'customer',
            type: 'entity',
            position: { x: 0, y: 0 },
            data: { label: 'Existing Customer' },
        };

        const editedEntities = [
            { id: 'customer', label: 'Customer', entity_type: 'dimension' },
        ];

        const resultNodes = runEntityCreationLoop(editedEntities, [existingNode]);

        const entityNodes = resultNodes.filter((n) => n.type === 'entity');
        expect(entityNodes).toHaveLength(1);
        expect(entityNodes[0].data.label).toBe('Existing Customer');
    });

    it('handles three iterations where the first two share an ID and the third is unique', () => {
        const editedEntities = [
            { id: 'product', label: 'Product', entity_type: 'dimension' },
            { id: 'product', label: 'Product', entity_type: 'dimension' },
            { id: 'sales_fact', label: 'Sales Fact', entity_type: 'fact' },
        ];

        const resultNodes = runEntityCreationLoop(editedEntities);

        const entityNodes = resultNodes.filter((n) => n.type === 'entity');
        expect(entityNodes).toHaveLength(2);
        expect(entityNodes.map((n) => n.id)).toEqual(
            expect.arrayContaining(['product', 'sales_fact'])
        );
    });

    it('preserves configured double-underscore prefixes for generated entity IDs', () => {
        const editedEntities = [
            { id: 'dim__employee', label: 'Employee', entity_type: 'dimension' },
            { id: 'fact__lead_gen_funnel', label: 'Lead Gen Funnel', entity_type: 'fact' },
        ];

        const resultNodes = runEntityCreationLoop(editedEntities);

        const entityNodes = resultNodes.filter((n) => n.type === 'entity');
        expect(entityNodes.map((n) => n.id)).toEqual(
            expect.arrayContaining(['dim__employee', 'fact__lead_gen_funnel'])
        );
    });

    it('removes stale legacy aliases before creating canonical IDs', () => {
        const editedEntities = [
            { id: 'dim__employee', label: 'Employee', entity_type: 'dimension' },
            { id: 'fact__lead_gen_funnel', label: 'Lead Gen Funnel', entity_type: 'fact' },
        ];
        const existingNodes: Node[] = [
            {
                id: 'dim_employee',
                type: 'entity',
                position: { x: 0, y: 0 },
                data: { label: 'Employee' },
            },
            {
                id: 'dim_employee_1',
                type: 'entity',
                position: { x: 0, y: 0 },
                data: { label: 'Employee copy' },
            },
            {
                id: 'fact_lead_gen_funnel',
                type: 'entity',
                position: { x: 0, y: 0 },
                data: { label: 'Lead Funnel' },
            },
            {
                id: 'fact_lead_gen_funnel_1',
                type: 'entity',
                position: { x: 0, y: 0 },
                data: { label: 'Lead Funnel copy' },
            },
            {
                id: 'dim__employee',
                type: 'entity',
                position: { x: 0, y: 0 },
                data: { label: 'Canonical employee' },
            },
        ];

        const filteredNodes = removeLegacyAliasNodes(editedEntities, existingNodes);

        expect(filteredNodes.map((node) => node.id)).toEqual(['dim__employee']);
        expect(filteredNodes.map((node) => node.id)).not.toEqual(
            expect.arrayContaining([
                'dim_employee',
                'dim_employee_1',
                'fact_lead_gen_funnel',
                'fact_lead_gen_funnel_1',
            ])
        );
    });

});
