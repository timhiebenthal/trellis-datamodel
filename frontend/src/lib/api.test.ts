import { describe, it, expect, vi, afterEach } from 'vitest';
import { inferRelationships, addSevenWsEntry, removeSevenWsEntry, updateSevenWsEntry, getDimensions, createBusinessEvent, updateBusinessEvent, getBusinessEventProcesses, createBusinessEventProcess, updateBusinessEventProcess, resolveBusinessEventProcess, attachEventsToProcess, detachEventsFromProcess } from './api';
import type { BusinessEventType, BusinessEventSevenWs, CreateProcessRequest, UpdateProcessRequest, AttachEventsRequest, DetachEventsRequest } from '$lib/types';

describe('API Functions - 7 Ws', () => {
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
});

describe('addSevenWsEntry', () => {
    afterEach(() => {
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
    });

    it('adds entry to business event', async () => {
        const mockResponse = {
            id: 'evt_001',
            text: 'test event',
            type: 'discrete',
            annotations: {
                who: [{ id: 'ent1', text: 'customer', dimension_id: 'dim_customer' }],
                what: [],
                when: [],
                where: [],
                how: [],
                how_many: [],
                why: []
            },
            derived_entities: [],
            created_at: '2025-01-22T10:00:00Z',
            updated_at: '2025-01-22T10:00:00Z'
        };

        vi.stubGlobal(
            'fetch',
            vi.fn().mockResolvedValue({
                ok: true,
                json: vi.fn().mockResolvedValue(mockResponse)
            })
        );

        const result = await addSevenWsEntry('evt_001', 'who', 'customer', undefined, 'dim_customer');

        expect(result).toEqual(mockResponse);
        expect(global.fetch).toHaveBeenCalledWith(
            expect.stringContaining('/api/business-events/evt_001/seven-entries'),
            expect.objectContaining({
                method: 'POST',
                body: expect.stringContaining('"w_type":"who"')
            })
        );
    });

    it('handles errors when adding entry', async () => {
        vi.stubGlobal(
            'fetch',
            vi.fn().mockResolvedValue({
                ok: false,
                json: vi.fn().mockResolvedValue({ detail: 'Invalid w_type' })
            })
        );

        await expect(addSevenWsEntry('evt_001', 'invalid' as any, 'text'))
            .rejects.toThrow('Invalid w_type');
    });
});

describe('removeSevenWsEntry', () => {
    afterEach(() => {
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
    });

    it('removes entry from business event', async () => {
        const mockResponse = {
            id: 'evt_001',
            text: 'test event',
            type: 'discrete',
            annotations: {
                who: [],
                what: [],
                when: [],
                where: [],
                how: [],
                how_many: [],
                why: []
            },
            derived_entities: [],
            created_at: '2025-01-22T10:00:00Z',
            updated_at: '2025-01-22T10:00:00Z'
        };

        vi.stubGlobal(
            'fetch',
            vi.fn().mockResolvedValue({
                ok: true,
                json: vi.fn().mockResolvedValue(mockResponse)
            })
        );

        const result = await removeSevenWsEntry('evt_001', 'ent1');

        expect(result).toEqual(mockResponse);
        expect(global.fetch).toHaveBeenCalledWith(
            expect.stringContaining('/api/business-events/evt_001/seven-entries/ent1'),
            expect.objectContaining({
                method: 'DELETE'
            })
        );
    });

    it('handles errors when removing entry', async () => {
        vi.stubGlobal(
            'fetch',
            vi.fn().mockResolvedValue({
                ok: false,
                json: vi.fn().mockResolvedValue({ detail: 'Entry not found' })
            })
        );

        await expect(removeSevenWsEntry('evt_001', 'ent1'))
            .rejects.toThrow('Entry not found');
    });
});

describe('updateSevenWsEntry', () => {
    afterEach(() => {
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
    });

    it('updates entry in business event', async () => {
        const mockResponse = {
            id: 'evt_001',
            text: 'test event',
            type: 'discrete',
            annotations: {
                who: [{ id: 'ent1', text: 'customer updated', description: 'Updated description' }],
                what: [],
                when: [],
                where: [],
                how: [],
                how_many: [],
                why: []
            },
            derived_entities: [],
            created_at: '2025-01-22T10:00:00Z',
            updated_at: '2025-01-22T10:00:00Z'
        };

        vi.stubGlobal(
            'fetch',
            vi.fn().mockResolvedValue({
                ok: true,
                json: vi.fn().mockResolvedValue(mockResponse)
            })
        );

        const result = await updateSevenWsEntry('evt_001', 'ent1', 'customer updated', 'Updated description');

        expect(result).toEqual(mockResponse);
        expect(global.fetch).toHaveBeenCalledWith(
            expect.stringContaining('/api/business-events/evt_001/seven-entries/ent1'),
            expect.objectContaining({
                method: 'PUT',
                body: expect.stringContaining('"text":"customer updated"')
            })
        );
    });

    it('handles errors when updating entry', async () => {
        vi.stubGlobal(
            'fetch',
            vi.fn().mockResolvedValue({
                ok: false,
                json: vi.fn().mockResolvedValue({ detail: 'Entry not found' })
            })
        );

        await expect(updateSevenWsEntry('evt_001', 'ent1', 'text'))
            .rejects.toThrow('Entry not found');
    });
});

describe('getDimensions', () => {
    afterEach(() => {
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
    });

    it('fetches dimensions from data model', async () => {
        const mockResponse = {
            entities: [
                { id: 'dim1', label: 'Customer', entity_type: 'dimension', annotation_type: 'who' },
                { id: 'dim2', label: 'Product', entity_type: 'dimension', annotation_type: 'what' }
            ]
        };

        vi.stubGlobal(
            'fetch',
            vi.fn().mockResolvedValue({
                ok: true,
                json: vi.fn().mockResolvedValue(mockResponse)
            })
        );

        const result = await getDimensions();

        expect(result).toHaveLength(2);
        expect(result[0]).toMatchObject(mockResponse.entities[0]);
        expect(global.fetch).toHaveBeenCalledWith('http://localhost:8089/api/data-model');
    });

    it('filters dimensions by annotation_type when specified', async () => {
        const mockResponse = {
            entities: [
                { id: 'dim1', label: 'Customer', entity_type: 'dimension', annotation_type: 'who' },
                { id: 'dim2', label: 'Product', entity_type: 'dimension', annotation_type: 'what' }
            ]
        };

        vi.stubGlobal(
            'fetch',
            vi.fn().mockResolvedValue({
                ok: true,
                json: vi.fn().mockResolvedValue(mockResponse)
            })
        );

        const result = await getDimensions('who');

        expect(result).toHaveLength(1);
        expect(result[0].annotation_type).toBe('who');
        expect(global.fetch).toHaveBeenCalledWith('http://localhost:8089/api/data-model?annotation_type=who');
    });

    it('returns empty array on 404 error', async () => {
        vi.stubGlobal(
            'fetch',
            vi.fn().mockResolvedValue({
                ok: false,
                status: 404
            })
        );

        const result = await getDimensions();

        expect(result).toEqual([]);
    });
});

describe('createBusinessEvent with annotations', () => {
    afterEach(() => {
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
    });

    it('creates event with annotations data', async () => {
        const mockSevenWs: BusinessEventSevenWs = {
            who: [{ id: 'ent1', text: 'customer' }],
            what: [{ id: 'ent2', text: 'product' }],
            when: [],
            where: [],
            how: [],
            how_many: [],
            why: []
        };

        const mockResponse = {
            id: 'evt_new',
            text: 'customer buys product',
            type: 'discrete',
            annotations: mockSevenWs,
            derived_entities: [],
            created_at: '2025-01-22T10:00:00Z',
            updated_at: '2025-01-22T10:00:00Z'
        };

        vi.stubGlobal(
            'fetch',
            vi.fn().mockResolvedValue({
                ok: true,
                json: vi.fn().mockResolvedValue(mockResponse)
            })
        );

        const result = await createBusinessEvent('customer buys product', 'discrete', 'Sales', mockSevenWs);

        expect(result).toEqual(mockResponse);
        expect(global.fetch).toHaveBeenCalledWith(
            'http://localhost:8089/api/business-events',
            expect.objectContaining({
                method: 'POST',
                body: expect.stringContaining('"annotations"')
            })
        );
    });
});

describe('updateBusinessEvent with annotations', () => {
    afterEach(() => {
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
    });

    it('updates event with annotations data', async () => {
        const mockSevenWs: BusinessEventSevenWs = {
            who: [{ id: 'ent1', text: 'customer updated' }],
            what: [],
            when: [],
            where: [],
            how: [],
            how_many: [],
            why: []
        };

        const mockResponse = {
            id: 'evt_001',
            text: 'customer buys product',
            type: 'discrete',
            annotations: mockSevenWs,
            derived_entities: [],
            created_at: '2025-01-22T10:00:00Z',
            updated_at: '2025-01-22T11:00:00Z'
        };

        vi.stubGlobal(
            'fetch',
            vi.fn().mockResolvedValue({
                ok: true,
                json: vi.fn().mockResolvedValue(mockResponse)
            })
        );

        const result = await updateBusinessEvent('evt_001', { annotations: mockSevenWs });

        expect(result).toEqual(mockResponse);
        expect(global.fetch).toHaveBeenCalledWith(
            'http://localhost:8089/api/business-events/evt_001',
            expect.objectContaining({
                method: 'PUT',
                body: expect.stringContaining('"annotations"')
            })
        );
    });
});

describe('inferRelationships error handling', () => {
    afterEach(() => {
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
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

describe('Business Event Process API Functions', () => {
    afterEach(() => {
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
    });

    describe('getBusinessEventProcesses', () => {
        it('fetches all processes', async () => {
            const mockProcesses = [
                {
                    id: 'proc_001',
                    name: 'Order Fulfillment',
                    type: 'discrete',
                    event_ids: ['evt_001', 'evt_002'],
                    created_at: '2026-01-27T10:00:00Z',
                    updated_at: '2026-01-27T10:00:00Z'
                }
            ];

            vi.stubGlobal(
                'fetch',
                vi.fn().mockResolvedValue({
                    ok: true,
                    json: vi.fn().mockResolvedValue(mockProcesses)
                })
            );

            const result = await getBusinessEventProcesses();

            expect(result).toEqual(mockProcesses);
            expect(global.fetch).toHaveBeenCalledWith(
                'http://localhost:8089/api/processes'
            );
        });

        it('handles array response format', async () => {
            const mockProcesses = [
                {
                    id: 'proc_001',
                    name: 'Test Process',
                    type: 'discrete',
                    event_ids: [],
                    created_at: '2026-01-27T10:00:00Z',
                    updated_at: '2026-01-27T10:00:00Z'
                }
            ];

            vi.stubGlobal(
                'fetch',
                vi.fn().mockResolvedValue({
                    ok: true,
                    json: vi.fn().mockResolvedValue(mockProcesses)
                })
            );

            const result = await getBusinessEventProcesses();
            expect(result).toEqual(mockProcesses);
        });

        it('handles wrapped response format', async () => {
            const mockProcesses = [
                {
                    id: 'proc_001',
                    name: 'Test Process',
                    type: 'discrete',
                    event_ids: [],
                    created_at: '2026-01-27T10:00:00Z',
                    updated_at: '2026-01-27T10:00:00Z'
                }
            ];

            vi.stubGlobal(
                'fetch',
                vi.fn().mockResolvedValue({
                    ok: true,
                    json: vi.fn().mockResolvedValue({ processes: mockProcesses })
                })
            );

            const result = await getBusinessEventProcesses();
            expect(result).toEqual(mockProcesses);
        });

        it('handles errors when fetching processes', async () => {
            vi.stubGlobal(
                'fetch',
                vi.fn().mockResolvedValue({
                    ok: false,
                    status: 500,
                    statusText: 'Internal Server Error',
                    json: vi.fn().mockResolvedValue({ detail: 'Server error' })
                })
            );

            await expect(getBusinessEventProcesses())
                .rejects.toThrow('Failed to fetch business event processes');
        });
    });

    describe('createBusinessEventProcess', () => {
        it('creates a new process', async () => {
            const request: CreateProcessRequest = {
                name: 'Order Fulfillment',
                type: 'discrete',
                event_ids: ['evt_001', 'evt_002']
            };

            const mockResponse = {
                id: 'proc_001',
                name: 'Order Fulfillment',
                type: 'discrete',
                event_ids: ['evt_001', 'evt_002'],
                created_at: '2026-01-27T10:00:00Z',
                updated_at: '2026-01-27T10:00:00Z'
            };

            vi.stubGlobal(
                'fetch',
                vi.fn().mockResolvedValue({
                    ok: true,
                    json: vi.fn().mockResolvedValue(mockResponse)
                })
            );

            const result = await createBusinessEventProcess(request);

            expect(result).toEqual(mockResponse);
            expect(global.fetch).toHaveBeenCalledWith(
                'http://localhost:8089/api/processes',
                expect.objectContaining({
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(request)
                })
            );
        });

        it('creates process without event_ids', async () => {
            const request: CreateProcessRequest = {
                name: 'New Process',
                type: 'evolving'
            };

            const mockResponse = {
                id: 'proc_002',
                name: 'New Process',
                type: 'evolving',
                event_ids: [],
                created_at: '2026-01-27T10:00:00Z',
                updated_at: '2026-01-27T10:00:00Z'
            };

            vi.stubGlobal(
                'fetch',
                vi.fn().mockResolvedValue({
                    ok: true,
                    json: vi.fn().mockResolvedValue(mockResponse)
                })
            );

            const result = await createBusinessEventProcess(request);
            expect(result).toEqual(mockResponse);
        });

        it('handles errors when creating process', async () => {
            const request: CreateProcessRequest = {
                name: 'Test Process',
                type: 'discrete',
                event_ids: ['evt_invalid']
            };

            vi.stubGlobal(
                'fetch',
                vi.fn().mockResolvedValue({
                    ok: false,
                    status: 404,
                    statusText: 'Not Found',
                    json: vi.fn().mockResolvedValue({ detail: 'Events not found' })
                })
            );

            await expect(createBusinessEventProcess(request))
                .rejects.toThrow('Events not found');
        });
    });

    describe('updateBusinessEventProcess', () => {
        it('updates process name', async () => {
            const request: UpdateProcessRequest = {
                name: 'Updated Process Name'
            };

            const mockResponse = {
                id: 'proc_001',
                name: 'Updated Process Name',
                type: 'discrete',
                event_ids: ['evt_001'],
                created_at: '2026-01-27T10:00:00Z',
                updated_at: '2026-01-27T11:00:00Z'
            };

            vi.stubGlobal(
                'fetch',
                vi.fn().mockResolvedValue({
                    ok: true,
                    json: vi.fn().mockResolvedValue(mockResponse)
                })
            );

            const result = await updateBusinessEventProcess('proc_001', request);

            expect(result).toEqual(mockResponse);
            expect(global.fetch).toHaveBeenCalledWith(
                'http://localhost:8089/api/processes/proc_001',
                expect.objectContaining({
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(request)
                })
            );
        });

        it('updates process type', async () => {
            const request: UpdateProcessRequest = {
                type: 'evolving'
            };

            const mockResponse = {
                id: 'proc_001',
                name: 'Test Process',
                type: 'evolving',
                event_ids: ['evt_001'],
                created_at: '2026-01-27T10:00:00Z',
                updated_at: '2026-01-27T11:00:00Z'
            };

            vi.stubGlobal(
                'fetch',
                vi.fn().mockResolvedValue({
                    ok: true,
                    json: vi.fn().mockResolvedValue(mockResponse)
                })
            );

            const result = await updateBusinessEventProcess('proc_001', request);
            expect(result.type).toBe('evolving');
        });

        it('handles errors when updating process', async () => {
            const request: UpdateProcessRequest = {
                name: 'Updated Name'
            };

            vi.stubGlobal(
                'fetch',
                vi.fn().mockResolvedValue({
                    ok: false,
                    status: 404,
                    statusText: 'Not Found',
                    json: vi.fn().mockResolvedValue({ detail: 'Process not found' })
                })
            );

            await expect(updateBusinessEventProcess('proc_invalid', request))
                .rejects.toThrow('Process not found');
        });
    });

    describe('resolveBusinessEventProcess', () => {
        it('resolves a process', async () => {
            const mockResponse = {
                id: 'proc_001',
                name: 'Test Process',
                type: 'discrete',
                event_ids: [],
                created_at: '2026-01-27T10:00:00Z',
                updated_at: '2026-01-27T11:00:00Z',
                resolved_at: '2026-01-27T11:00:00Z'
            };

            vi.stubGlobal(
                'fetch',
                vi.fn().mockResolvedValue({
                    ok: true,
                    json: vi.fn().mockResolvedValue(mockResponse)
                })
            );

            const result = await resolveBusinessEventProcess('proc_001');

            expect(result).toEqual(mockResponse);
            expect(result.resolved_at).toBeDefined();
            expect(global.fetch).toHaveBeenCalledWith(
                'http://localhost:8089/api/processes/proc_001/resolve',
                expect.objectContaining({
                    method: 'POST'
                })
            );
        });

        it('handles errors when resolving process', async () => {
            vi.stubGlobal(
                'fetch',
                vi.fn().mockResolvedValue({
                    ok: false,
                    status: 404,
                    statusText: 'Not Found',
                    json: vi.fn().mockResolvedValue({ detail: 'Process not found' })
                })
            );

            await expect(resolveBusinessEventProcess('proc_invalid'))
                .rejects.toThrow('Process not found');
        });
    });

    describe('attachEventsToProcess', () => {
        it('attaches events to a process', async () => {
            const request: AttachEventsRequest = {
                event_ids: ['evt_003', 'evt_004']
            };

            const mockResponse = {
                id: 'proc_001',
                name: 'Test Process',
                type: 'discrete',
                event_ids: ['evt_001', 'evt_002', 'evt_003', 'evt_004'],
                created_at: '2026-01-27T10:00:00Z',
                updated_at: '2026-01-27T11:00:00Z'
            };

            vi.stubGlobal(
                'fetch',
                vi.fn().mockResolvedValue({
                    ok: true,
                    json: vi.fn().mockResolvedValue(mockResponse)
                })
            );

            const result = await attachEventsToProcess('proc_001', request);

            expect(result).toEqual(mockResponse);
            expect(result.event_ids).toContain('evt_003');
            expect(result.event_ids).toContain('evt_004');
            expect(global.fetch).toHaveBeenCalledWith(
                'http://localhost:8089/api/processes/proc_001/attach',
                expect.objectContaining({
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(request)
                })
            );
        });

        it('handles errors when attaching events', async () => {
            const request: AttachEventsRequest = {
                event_ids: ['evt_invalid']
            };

            vi.stubGlobal(
                'fetch',
                vi.fn().mockResolvedValue({
                    ok: false,
                    status: 404,
                    statusText: 'Not Found',
                    json: vi.fn().mockResolvedValue({ detail: 'Events not found' })
                })
            );

            await expect(attachEventsToProcess('proc_001', request))
                .rejects.toThrow('Events not found');
        });
    });

    describe('detachEventsFromProcess', () => {
        it('detaches events from a process', async () => {
            const request: DetachEventsRequest = {
                event_ids: ['evt_002']
            };

            const mockResponse = {
                id: 'proc_001',
                name: 'Test Process',
                type: 'discrete',
                event_ids: ['evt_001'],
                created_at: '2026-01-27T10:00:00Z',
                updated_at: '2026-01-27T11:00:00Z'
            };

            vi.stubGlobal(
                'fetch',
                vi.fn().mockResolvedValue({
                    ok: true,
                    json: vi.fn().mockResolvedValue(mockResponse)
                })
            );

            const result = await detachEventsFromProcess('proc_001', request);

            expect(result).toEqual(mockResponse);
            expect(result.event_ids).not.toContain('evt_002');
            expect(global.fetch).toHaveBeenCalledWith(
                'http://localhost:8089/api/processes/proc_001/detach',
                expect.objectContaining({
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(request)
                })
            );
        });

        it('handles errors when detaching events', async () => {
            const request: DetachEventsRequest = {
                event_ids: ['evt_002']
            };

            vi.stubGlobal(
                'fetch',
                vi.fn().mockResolvedValue({
                    ok: false,
                    status: 404,
                    statusText: 'Not Found',
                    json: vi.fn().mockResolvedValue({ detail: 'Process not found' })
                })
            );

            await expect(detachEventsFromProcess('proc_invalid', request))
                .rejects.toThrow('Process not found');
        });
    });
});
