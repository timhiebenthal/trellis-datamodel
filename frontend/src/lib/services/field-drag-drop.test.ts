import { describe, it, expect, vi, beforeEach } from 'vitest';
import { get } from 'svelte/store';
import type { ModelSchema } from '$lib/types';

vi.mock('$lib/api', () => ({ getModelSchema: vi.fn() }));

import { getModelSchema } from '$lib/api';
import { draggingField, edges, frameworkModels, nodes } from '$lib/stores';
import { createFieldDragDrop } from './field-drag-drop';

const mockSchema = vi.mocked(getModelSchema);

function entityNode(id: string, modelName: string) {
    return {
        id,
        type: 'entity',
        position: { x: 0, y: 0 },
        data: { label: id, _activeModelName: modelName },
    };
}

function schema(name: string, columns: ModelSchema['columns']): ModelSchema {
    return { model_name: name, columns } as ModelSchema;
}

const dropEvent = { preventDefault: vi.fn(), stopPropagation: vi.fn() } as unknown as DragEvent;

describe('createFieldDragDrop onFieldDrop', () => {
    beforeEach(() => {
        nodes.set([entityNode('orders', 'orders'), entityNode('customers', 'customers')] as any);
        edges.set([]);
        frameworkModels.set([]);
        draggingField.set(null);
        mockSchema.mockReset();
    });

    it('flips an FK -> PK drag to parent -> child and keeps the dragged field name', async () => {
        const ordersSchema = schema('orders', [
            {
                name: 'customer_id',
                data_tests: [{ relationships: { arguments: { to: "ref('customers')", field: 'id' } } }],
            },
        ] as any);
        const customersSchema = schema('customers', [{ name: 'id' }] as any);
        // dragend clears the store while the schema requests are still in flight
        mockSchema.mockImplementation(async (name: string) => {
            draggingField.set(null);
            return name === 'orders' ? ordersSchema : customersSchema;
        });

        draggingField.set({ nodeId: 'orders', nodeLabel: 'orders', fieldName: 'customer_id' } as any);
        await createFieldDragDrop(() => 'customers', () => 'customers').onFieldDrop('id', dropEvent);

        const created = get(edges);
        expect(created).toHaveLength(1);
        expect(created[0].source).toBe('customers');
        expect(created[0].target).toBe('orders');
        expect(created[0].data?.source_field).toBe('id');
        expect(created[0].data?.target_field).toBe('customer_id');
    });
});
