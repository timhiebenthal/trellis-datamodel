/**
 * API Layer Verification Tests for Role-Playing Dimension Feature
 *
 * Tests verify that the API layer correctly handles:
 * 1. Entity `roles` field (string array on dimension entities)
 * 2. Annotation `role` field (string on individual annotation entries)
 * 3. Serialization and deserialization of both fields
 * 4. Error handling for malformed data
 * 5. Backward compatibility
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
    getDataModel,
    saveDataModel,
    getBusinessEvents,
    updateBusinessEvent,
    updateBusinessEventAnnotations,
} from './api';
import type { DataModel, Entity, BusinessEvent, BusinessEventAnnotations } from './types';

describe('API Layer - Role-Playing Dimension Verification', () => {
    let fetchMock: ReturnType<typeof vi.fn>;

    beforeEach(() => {
        fetchMock = vi.fn();
        global.fetch = fetchMock;
        // Disable smoke test mode
        import.meta.env.MODE = 'development';
        import.meta.env.VITE_SMOKE_TEST = 'false';
        import.meta.env.PUBLIC_SMOKE_TEST = 'false';
        if (typeof window !== 'undefined') {
            (window as any).__SMOKE_TEST__ = false;
        }
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    describe('getDataModel() - Entity roles field deserialization', () => {
        it('should correctly deserialize entities with roles field', async () => {
            const mockResponse: DataModel = {
                version: 0.1,
                entities: [
                    {
                        id: 'dim_date',
                        label: 'Date',
                        entity_type: 'dimension',
                        annotation_type: 'when',
                        roles: ['order_date', 'ship_date', 'delivery_date'],
                        position: { x: 0, y: 0 },
                    },
                    {
                        id: 'dim_location',
                        label: 'Location',
                        entity_type: 'dimension',
                        annotation_type: 'where',
                        roles: ['origin', 'destination'],
                        position: { x: 100, y: 0 },
                    },
                ],
                relationships: [],
            };

            fetchMock.mockResolvedValueOnce({
                ok: true,
                json: async () => mockResponse,
            });

            const result = await getDataModel();

            expect(result.entities).toHaveLength(2);
            expect(result.entities[0].roles).toEqual(['order_date', 'ship_date', 'delivery_date']);
            expect(result.entities[1].roles).toEqual(['origin', 'destination']);
        });

        it('should handle entities without roles field (backward compatibility)', async () => {
            const mockResponse: DataModel = {
                version: 0.1,
                entities: [
                    {
                        id: 'dim_customer',
                        label: 'Customer',
                        entity_type: 'dimension',
                        position: { x: 0, y: 0 },
                        // No roles field
                    },
                ],
                relationships: [],
            };

            fetchMock.mockResolvedValueOnce({
                ok: true,
                json: async () => mockResponse,
            });

            const result = await getDataModel();

            expect(result.entities).toHaveLength(1);
            expect(result.entities[0].roles).toBeUndefined();
        });

        it('should handle entities with empty roles array', async () => {
            const mockResponse: DataModel = {
                version: 0.1,
                entities: [
                    {
                        id: 'dim_date',
                        label: 'Date',
                        entity_type: 'dimension',
                        roles: [],
                        position: { x: 0, y: 0 },
                    },
                ],
                relationships: [],
            };

            fetchMock.mockResolvedValueOnce({
                ok: true,
                json: async () => mockResponse,
            });

            const result = await getDataModel();

            expect(result.entities[0].roles).toEqual([]);
        });

        it('should handle mix of entities with and without roles', async () => {
            const mockResponse: DataModel = {
                version: 0.1,
                entities: [
                    {
                        id: 'dim_date',
                        label: 'Date',
                        entity_type: 'dimension',
                        roles: ['created_date', 'modified_date'],
                        position: { x: 0, y: 0 },
                    },
                    {
                        id: 'dim_customer',
                        label: 'Customer',
                        entity_type: 'dimension',
                        position: { x: 100, y: 0 },
                        // No roles
                    },
                    {
                        id: 'fact_sales',
                        label: 'Sales',
                        entity_type: 'fact',
                        position: { x: 200, y: 0 },
                        // Facts don't have roles
                    },
                ],
                relationships: [],
            };

            fetchMock.mockResolvedValueOnce({
                ok: true,
                json: async () => mockResponse,
            });

            const result = await getDataModel();

            expect(result.entities[0].roles).toEqual(['created_date', 'modified_date']);
            expect(result.entities[1].roles).toBeUndefined();
            expect(result.entities[2].roles).toBeUndefined();
        });
    });

    describe('saveDataModel() - Entity roles field serialization', () => {
        it('should correctly serialize entities with roles field', async () => {
            const dataModel: DataModel = {
                version: 0.1,
                entities: [
                    {
                        id: 'dim_date',
                        label: 'Date',
                        entity_type: 'dimension',
                        roles: ['order_date', 'ship_date'],
                        position: { x: 0, y: 0 },
                    },
                ],
                relationships: [],
            };

            fetchMock.mockResolvedValueOnce({
                ok: true,
                json: async () => ({}),
            });

            await saveDataModel(dataModel);

            expect(fetchMock).toHaveBeenCalledWith(
                expect.stringContaining('/data-model'),
                expect.objectContaining({
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: expect.any(String),
                })
            );

            const sentData = JSON.parse(fetchMock.mock.calls[0][1].body);
            expect(sentData.entities[0].roles).toEqual(['order_date', 'ship_date']);
        });

        it('should serialize entities without roles field', async () => {
            const dataModel: DataModel = {
                version: 0.1,
                entities: [
                    {
                        id: 'dim_customer',
                        label: 'Customer',
                        entity_type: 'dimension',
                        position: { x: 0, y: 0 },
                    },
                ],
                relationships: [],
            };

            fetchMock.mockResolvedValueOnce({
                ok: true,
                json: async () => ({}),
            });

            await saveDataModel(dataModel);

            const sentData = JSON.parse(fetchMock.mock.calls[0][1].body);
            expect(sentData.entities[0]).not.toHaveProperty('roles');
        });

        it('should handle empty roles array correctly', async () => {
            const dataModel: DataModel = {
                version: 0.1,
                entities: [
                    {
                        id: 'dim_date',
                        label: 'Date',
                        entity_type: 'dimension',
                        roles: [],
                        position: { x: 0, y: 0 },
                    },
                ],
                relationships: [],
            };

            fetchMock.mockResolvedValueOnce({
                ok: true,
                json: async () => ({}),
            });

            await saveDataModel(dataModel);

            const sentData = JSON.parse(fetchMock.mock.calls[0][1].body);
            expect(sentData.entities[0].roles).toEqual([]);
        });
    });

    describe('getBusinessEvents() - Annotation role field deserialization', () => {
        it('should correctly deserialize annotations with role field', async () => {
            const mockEvents: BusinessEvent[] = [
                {
                    id: 'evt_001',
                    text: 'Order placed',
                    type: 'discrete',
                    created_at: '2026-01-01T00:00:00Z',
                    updated_at: '2026-01-01T00:00:00Z',
                    annotations: {
                        who: [],
                        what: [],
                        when: [
                            {
                                id: 'ann_001',
                                text: 'Order Date',
                                role: 'order_date',
                                dimension_id: 'dim_date',
                            },
                            {
                                id: 'ann_002',
                                text: 'Ship Date',
                                role: 'ship_date',
                                dimension_id: 'dim_date',
                            },
                        ],
                        where: [
                            {
                                id: 'ann_003',
                                text: 'Origin',
                                role: 'origin',
                                dimension_id: 'dim_location',
                            },
                        ],
                        how: [],
                        why: [],
                        how_many: [],
                    },
                    derived_entities: [],
                },
            ];

            fetchMock.mockResolvedValueOnce({
                ok: true,
                json: async () => mockEvents,
            });

            const result = await getBusinessEvents();

            expect(result).toHaveLength(1);
            expect(result[0].annotations?.when[0].role).toBe('order_date');
            expect(result[0].annotations?.when[1].role).toBe('ship_date');
            expect(result[0].annotations?.where[0].role).toBe('origin');
        });

        it('should handle annotations without role field (backward compatibility)', async () => {
            const mockEvents: BusinessEvent[] = [
                {
                    id: 'evt_001',
                    text: 'Customer created',
                    type: 'discrete',
                    created_at: '2026-01-01T00:00:00Z',
                    updated_at: '2026-01-01T00:00:00Z',
                    annotations: {
                        who: [
                            {
                                id: 'ann_001',
                                text: 'Customer',
                                dimension_id: 'dim_customer',
                                // No role field
                            },
                        ],
                        what: [],
                        when: [],
                        where: [],
                        how: [],
                        why: [],
                        how_many: [],
                    },
                    derived_entities: [],
                },
            ];

            fetchMock.mockResolvedValueOnce({
                ok: true,
                json: async () => mockEvents,
            });

            const result = await getBusinessEvents();

            expect(result[0].annotations?.who[0].role).toBeUndefined();
        });

        it('should handle mix of annotations with and without role', async () => {
            const mockEvents: BusinessEvent[] = [
                {
                    id: 'evt_001',
                    text: 'Order shipped',
                    type: 'discrete',
                    created_at: '2026-01-01T00:00:00Z',
                    updated_at: '2026-01-01T00:00:00Z',
                    annotations: {
                        who: [
                            {
                                id: 'ann_001',
                                text: 'Customer',
                                dimension_id: 'dim_customer',
                                // No role - single-role dimension
                            },
                        ],
                        what: [],
                        when: [
                            {
                                id: 'ann_002',
                                text: 'Order Date',
                                role: 'order_date',
                                dimension_id: 'dim_date',
                            },
                            {
                                id: 'ann_003',
                                text: 'Ship Date',
                                role: 'ship_date',
                                dimension_id: 'dim_date',
                            },
                        ],
                        where: [],
                        how: [],
                        why: [],
                        how_many: [],
                    },
                    derived_entities: [],
                },
            ];

            fetchMock.mockResolvedValueOnce({
                ok: true,
                json: async () => mockEvents,
            });

            const result = await getBusinessEvents();

            expect(result[0].annotations?.who[0].role).toBeUndefined();
            expect(result[0].annotations?.when[0].role).toBe('order_date');
            expect(result[0].annotations?.when[1].role).toBe('ship_date');
        });
    });

    describe('updateBusinessEvent() - Annotation role field serialization', () => {
        it('should correctly serialize annotations with role field', async () => {
            const updates: Partial<BusinessEvent> = {
                annotations: {
                    who: [],
                    what: [],
                    when: [
                        {
                            id: 'ann_001',
                            text: 'Order Date',
                            role: 'order_date',
                            dimension_id: 'dim_date',
                        },
                    ],
                    where: [],
                    how: [],
                    why: [],
                    how_many: [],
                },
            };

            fetchMock.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ id: 'evt_001', ...updates } as BusinessEvent),
            });

            await updateBusinessEvent('evt_001', updates);

            const sentData = JSON.parse(fetchMock.mock.calls[0][1].body);
            expect(sentData.annotations.when[0].role).toBe('order_date');
        });

        it('should serialize annotations without role field', async () => {
            const updates: Partial<BusinessEvent> = {
                annotations: {
                    who: [
                        {
                            id: 'ann_001',
                            text: 'Customer',
                            dimension_id: 'dim_customer',
                        },
                    ],
                    what: [],
                    when: [],
                    where: [],
                    how: [],
                    why: [],
                    how_many: [],
                },
            };

            fetchMock.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ id: 'evt_001', ...updates } as BusinessEvent),
            });

            await updateBusinessEvent('evt_001', updates);

            const sentData = JSON.parse(fetchMock.mock.calls[0][1].body);
            expect(sentData.annotations.who[0]).not.toHaveProperty('role');
        });
    });

    describe('updateBusinessEventAnnotations() - Annotation role field serialization', () => {
        it('should correctly serialize full annotations structure with roles', async () => {
            const annotations: BusinessEventAnnotations = {
                who: [],
                what: [],
                when: [
                    {
                        id: 'ann_001',
                        text: 'Order Date',
                        role: 'order_date',
                        dimension_id: 'dim_date',
                    },
                    {
                        id: 'ann_002',
                        text: 'Delivery Date',
                        role: 'delivery_date',
                        dimension_id: 'dim_date',
                    },
                ],
                where: [
                    {
                        id: 'ann_003',
                        text: 'Origin',
                        role: 'origin',
                        dimension_id: 'dim_location',
                    },
                ],
                how: [],
                why: [],
                how_many: [],
            };

            fetchMock.mockResolvedValueOnce({
                ok: true,
                json: async () => ({ id: 'evt_001', annotations } as BusinessEvent),
            });

            await updateBusinessEventAnnotations('evt_001', annotations);

            const sentData = JSON.parse(fetchMock.mock.calls[0][1].body);
            expect(sentData.annotations.when[0].role).toBe('order_date');
            expect(sentData.annotations.when[1].role).toBe('delivery_date');
            expect(sentData.annotations.where[0].role).toBe('origin');
        });
    });

    describe('Error Handling', () => {
        it('should handle malformed roles data (non-array)', async () => {
            const mockResponse = {
                version: 0.1,
                entities: [
                    {
                        id: 'dim_date',
                        label: 'Date',
                        entity_type: 'dimension',
                        roles: 'invalid_not_array', // Should be array
                        position: { x: 0, y: 0 },
                    },
                ],
                relationships: [],
            };

            fetchMock.mockResolvedValueOnce({
                ok: true,
                json: async () => mockResponse,
            });

            const result = await getDataModel();

            // API should pass through data as-is
            // Type checking happens at TypeScript compile time
            expect(result.entities[0]).toHaveProperty('roles');
        });

        it('should handle malformed role data (non-string)', async () => {
            const mockResponse = [
                {
                    id: 'evt_001',
                    text: 'Test',
                    type: 'discrete',
                    created_at: '2026-01-01T00:00:00Z',
                    updated_at: '2026-01-01T00:00:00Z',
                    annotations: {
                        who: [],
                        what: [],
                        when: [
                            {
                                id: 'ann_001',
                                text: 'Date',
                                role: 123, // Should be string
                                dimension_id: 'dim_date',
                            },
                        ],
                        where: [],
                        how: [],
                        why: [],
                        how_many: [],
                    },
                    derived_entities: [],
                },
            ];

            fetchMock.mockResolvedValueOnce({
                ok: true,
                json: async () => mockResponse,
            });

            const result = await getBusinessEvents();

            // API should pass through data as-is
            expect(result[0].annotations?.when[0]).toHaveProperty('role');
        });
    });

    describe('End-to-End Flow', () => {
        it('should handle complete round-trip with roles data', async () => {
            // Step 1: Fetch data model with roles
            const fetchedModel: DataModel = {
                version: 0.1,
                entities: [
                    {
                        id: 'dim_date',
                        label: 'Date',
                        entity_type: 'dimension',
                        roles: ['order_date', 'ship_date'],
                        position: { x: 0, y: 0 },
                    },
                ],
                relationships: [],
            };

            fetchMock.mockResolvedValueOnce({
                ok: true,
                json: async () => fetchedModel,
            });

            const dataModel = await getDataModel();
            expect(dataModel.entities[0].roles).toEqual(['order_date', 'ship_date']);

            // Step 2: Modify roles
            dataModel.entities[0].roles = ['order_date', 'ship_date', 'delivery_date'];

            // Step 3: Save back
            fetchMock.mockResolvedValueOnce({
                ok: true,
                json: async () => ({}),
            });

            await saveDataModel(dataModel);

            const sentData = JSON.parse(fetchMock.mock.calls[1][1].body);
            expect(sentData.entities[0].roles).toEqual(['order_date', 'ship_date', 'delivery_date']);
        });

        it('should handle complete round-trip with annotation roles', async () => {
            // Step 1: Fetch business events with role annotations
            const fetchedEvents: BusinessEvent[] = [
                {
                    id: 'evt_001',
                    text: 'Order placed',
                    type: 'discrete',
                    created_at: '2026-01-01T00:00:00Z',
                    updated_at: '2026-01-01T00:00:00Z',
                    annotations: {
                        who: [],
                        what: [],
                        when: [
                            {
                                id: 'ann_001',
                                text: 'Order Date',
                                role: 'order_date',
                                dimension_id: 'dim_date',
                            },
                        ],
                        where: [],
                        how: [],
                        why: [],
                        how_many: [],
                    },
                    derived_entities: [],
                },
            ];

            fetchMock.mockResolvedValueOnce({
                ok: true,
                json: async () => fetchedEvents,
            });

            const events = await getBusinessEvents();
            expect(events[0].annotations?.when[0].role).toBe('order_date');

            // Step 2: Add another role-playing annotation
            events[0].annotations!.when.push({
                id: 'ann_002',
                text: 'Ship Date',
                role: 'ship_date',
                dimension_id: 'dim_date',
            });

            // Step 3: Update event
            fetchMock.mockResolvedValueOnce({
                ok: true,
                json: async () => events[0],
            });

            await updateBusinessEvent('evt_001', {
                annotations: events[0].annotations,
            });

            const sentData = JSON.parse(fetchMock.mock.calls[1][1].body);
            expect(sentData.annotations.when).toHaveLength(2);
            expect(sentData.annotations.when[0].role).toBe('order_date');
            expect(sentData.annotations.when[1].role).toBe('ship_date');
        });
    });
});
