import { describe, it, expect, vi, afterEach } from 'vitest';
import { apiJson, ApiError, updateConfig, inferRelationships, getDimensions, createBusinessEvent, updateBusinessEvent, getBusinessEventProcesses, createBusinessEventProcess, updateBusinessEventProcess, resolveBusinessEventProcess, attachEventsToProcess, detachEventsFromProcess, generateEntitiesFromProcess, syncDbtTests, reconcileDbt, getModelSchema } from './api';
import type { BusinessEventType, BusinessEventSevenWs, CreateProcessRequest, UpdateProcessRequest, AttachEventsRequest, DetachEventsRequest } from '$lib/types';
import { recordBootRequest } from './boot-diagnostics';

vi.mock('./boot-diagnostics', async (importOriginal) => {
    const actual = await importOriginal<typeof import('./boot-diagnostics')>();
    return {
        ...actual,
        recordBootRequest: vi.fn(),
    };
});

describe('boot request diagnostics', () => {
    afterEach(() => {
        vi.clearAllMocks();
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
    });

    it('records duration, status, content length, and server timing for boot requests', async () => {
        const response = {
            ok: true,
            status: 200,
            headers: new Headers({
                'Content-Length': '42',
                'Server-Timing': 'db;dur=12.5,app;dur=4',
            }),
            json: vi.fn().mockResolvedValue({ columns: [] }),
        };
        vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response));
        vi.spyOn(performance, 'now').mockReturnValueOnce(100).mockReturnValueOnce(145);

        await getModelSchema('orders');

        expect(recordBootRequest).toHaveBeenCalledWith({
            url: 'http://localhost:8089/api/models/orders/schema',
            method: 'GET',
            status: 200,
            bytes: 42,
            duration: 45,
            serverTiming: [
                { name: 'db', duration: 12.5 },
                { name: 'app', duration: 4 },
            ],
        });
    });

    it('counts repeated schema requests', async () => {
        const response = {
            ok: true,
            status: 200,
            headers: new Headers(),
            json: vi.fn().mockResolvedValue({ columns: [] }),
        };
        vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response));

        await Promise.all([
            getModelSchema('orders'),
            getModelSchema('orders'),
            getModelSchema('customers'),
        ]);

        const requests = vi.mocked(recordBootRequest).mock.calls.map(([request]) => request as { url: string });
        expect(requests).toHaveLength(3);
        expect(requests.filter((request) => request.url.endsWith('/api/models/orders/schema'))).toHaveLength(2);
        expect(requests.filter((request) => request.url.endsWith('/api/models/customers/schema'))).toHaveLength(1);
    });

    it('records failed HTTP and network requests without consuming response bodies twice', async () => {
        const errorText = vi.fn().mockResolvedValue('backend failed');
        const failedResponse = {
            ok: false,
            status: 500,
            statusText: 'Internal Server Error',
            headers: new Headers(),
            text: errorText,
        };
        vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(failedResponse));

        await expect(inferRelationships()).rejects.toThrow('Failed to infer relationships: 500');
        expect(errorText).toHaveBeenCalledTimes(1);
        expect(recordBootRequest).toHaveBeenCalledWith(expect.objectContaining({
            url: 'http://localhost:8089/api/infer-relationships',
            status: 500,
        }));

        vi.mocked(recordBootRequest).mockClear();
        vi.mocked(fetch).mockRejectedValueOnce(new TypeError('Failed to fetch'));

        await expect(getModelSchema('orders')).resolves.toBeNull();
        expect(recordBootRequest).toHaveBeenCalledWith(expect.objectContaining({
            url: 'http://localhost:8089/api/models/orders/schema',
        }));
    });
});

describe('apiJson', () => {
    afterEach(() => {
        vi.clearAllMocks();
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
    });

    function stubResponse(response: Record<string, unknown>) {
        const fetchMock = vi.fn().mockResolvedValue({ headers: new Headers(), ...response });
        vi.stubGlobal('fetch', fetchMock);
        return fetchMock;
    }

    async function caught(promise: Promise<unknown>): Promise<ApiError> {
        const error = await promise.then(
            () => undefined,
            (e: unknown) => e,
        );
        expect(error).toBeInstanceOf(ApiError);
        return error as ApiError;
    }

    it('returns the parsed body and sends JSON bodies', async () => {
        const fetchMock = stubResponse({
            ok: true,
            status: 200,
            text: vi.fn().mockResolvedValue('{"id":"x"}'),
        });

        await expect(apiJson('/things', { method: 'POST', body: { a: 1 } })).resolves.toEqual({ id: 'x' });
        expect(fetchMock).toHaveBeenCalledWith('http://localhost:8089/api/things', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: '{"a":1}',
        });
    });

    it('calls fetch with the URL only for a plain GET', async () => {
        const fetchMock = stubResponse({ ok: true, status: 200, json: vi.fn().mockResolvedValue([]) });

        await apiJson('/things');

        expect(fetchMock).toHaveBeenCalledWith('http://localhost:8089/api/things');
    });

    it('resolves undefined for an empty success body', async () => {
        stubResponse({ ok: true, status: 204, text: vi.fn().mockResolvedValue('') });

        await expect(apiJson('/things', { method: 'DELETE' })).resolves.toBeUndefined();
    });

    it('throws ApiError with the server detail string as message', async () => {
        stubResponse({
            ok: false,
            status: 422,
            text: vi.fn().mockResolvedValue('{"detail":"Process not found"}'),
        });

        const error = await caught(apiJson('/things'));
        expect(error.message).toBe('Process not found');
        expect(error.status).toBe(422);
        expect(error.detail).toBe('Process not found');
    });

    it('prefixes the message with errorMessage and status', async () => {
        stubResponse({
            ok: false,
            status: 500,
            text: vi.fn().mockResolvedValue('{"detail":"boom"}'),
        });

        const error = await caught(apiJson('/things', { errorMessage: 'Failed to fetch things' }));
        expect(error.message).toBe('Failed to fetch things: 500 - boom');
    });

    it('reads detail.message objects and validation error lists', async () => {
        stubResponse({
            ok: false,
            status: 400,
            json: vi.fn().mockResolvedValue({ detail: { message: 'Invalid config', field: 'x' } }),
        });
        const objectError = await caught(apiJson('/things'));
        expect(objectError.message).toBe('Invalid config');
        expect(objectError.detail).toEqual({ message: 'Invalid config', field: 'x' });

        stubResponse({
            ok: false,
            status: 422,
            json: vi.fn().mockResolvedValue({ detail: [{ msg: 'field required' }, { msg: 'bad type' }] }),
        });
        const listError = await caught(apiJson('/things'));
        expect(listError.message).toBe('field required; bad type');
    });

    it('keeps a non-JSON error body as text instead of throwing a parse error', async () => {
        stubResponse({
            ok: false,
            status: 502,
            text: vi.fn().mockResolvedValue('<html>Bad Gateway</html>'),
        });

        const error = await caught(apiJson('/things', { errorMessage: 'Failed to fetch things' }));
        expect(error.message).toBe('Failed to fetch things: 502 - <html>Bad Gateway</html>');
        expect(error.detail).toBe('<html>Bad Gateway</html>');
    });

    it('falls back to the status when the error body is unreadable', async () => {
        stubResponse({ ok: false, status: 500 });

        const error = await caught(apiJson('/things'));
        expect(error.message).toBe('Request failed: 500');
        expect(error.detail).toBeUndefined();
    });

    it('returns notFound on 404 without reading the body, and throws 404 otherwise', async () => {
        const text = vi.fn().mockResolvedValue('{"detail":"Not here"}');
        stubResponse({ ok: false, status: 404, text });

        await expect(apiJson<string[]>('/things', { notFound: [] })).resolves.toEqual([]);
        expect(text).not.toHaveBeenCalled();

        const error = await caught(apiJson('/things'));
        expect(error.status).toBe(404);
        expect(error.message).toBe('Not here');
    });

    it('propagates network failures unchanged and records them', async () => {
        const failure = new TypeError('Failed to fetch');
        vi.stubGlobal('fetch', vi.fn().mockRejectedValue(failure));

        await expect(apiJson('/things', { method: 'post' })).rejects.toBe(failure);
        expect(recordBootRequest).toHaveBeenCalledWith(expect.objectContaining({
            url: 'http://localhost:8089/api/things',
            method: 'POST',
            bytes: undefined,
        }));
    });

    it('records every request with its status', async () => {
        stubResponse({ ok: true, status: 200, json: vi.fn().mockResolvedValue({ a: 1 }) });
        await apiJson('/ok');
        stubResponse({ ok: false, status: 500, json: vi.fn().mockResolvedValue({ detail: 'x' }) });
        await expect(apiJson('/fail')).rejects.toBeInstanceOf(ApiError);

        const calls = vi.mocked(recordBootRequest).mock.calls.map(([r]) => r);
        expect(calls).toEqual([
            expect.objectContaining({ url: 'http://localhost:8089/api/ok', method: 'GET', status: 200 }),
            expect.objectContaining({ url: 'http://localhost:8089/api/fail', method: 'GET', status: 500 }),
        ]);
    });
});

describe('updateConfig conflict contract', () => {
    afterEach(() => {
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
    });

    it('throws CONFLICT: <detail JSON> on 409', async () => {
        const detail = { error: 'conflict', message: 'Changed on disk', conflict: { mtime: 1 } };
        vi.stubGlobal(
            'fetch',
            vi.fn().mockResolvedValue({ ok: false, status: 409, json: vi.fn().mockResolvedValue({ detail }) }),
        );

        const error = await updateConfig({}).catch((e: unknown) => e);
        expect(error).toBeInstanceOf(ApiError);
        expect((error as ApiError).status).toBe(409);
        expect((error as ApiError).message).toBe(`CONFLICT: ${JSON.stringify(detail)}`);
    });
});

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

describe('framework-neutral endpoint paths', () => {
    afterEach(() => {
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
    });

    it('syncDbtTests calls /api/sync-tests, not the legacy /api/sync-dbt-tests path', async () => {
        vi.stubGlobal(
            'fetch',
            vi.fn().mockResolvedValue({
                ok: true,
                json: vi.fn().mockResolvedValue({ message: 'ok' }),
            }),
        );

        await syncDbtTests();

        expect(global.fetch).toHaveBeenCalledWith(
            'http://localhost:8089/api/sync-tests',
            expect.objectContaining({ method: 'POST' }),
        );
        const calledUrl = (global.fetch as any).mock.calls[0][0];
        expect(calledUrl).not.toContain('/sync-dbt-tests');
    });

    it('reconcileDbt calls /api/reconcile, not the legacy /api/reconcile-dbt path', async () => {
        vi.stubGlobal(
            'fetch',
            vi.fn().mockResolvedValue({
                ok: true,
                json: vi.fn().mockResolvedValue({ status: 'success', changed: false }),
            }),
        );

        await expect(reconcileDbt()).resolves.toEqual({ status: 'success', changed: false });

        expect(global.fetch).toHaveBeenCalledWith(
            'http://localhost:8089/api/reconcile',
            expect.objectContaining({ method: 'POST' }),
        );
        const calledUrl = (global.fetch as any).mock.calls[0][0];
        expect(calledUrl).not.toContain('/reconcile-dbt');
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
                event_ids: ['evt_001', 'evt_002'],
                domain: 'sales'
            };

            const mockResponse = {
                id: 'proc_001',
                name: 'Order Fulfillment',
                type: 'discrete',
                event_ids: ['evt_001', 'evt_002'],
                domain: 'sales',
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
                type: 'evolving',
                domain: 'Test Domain',
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
                domain: 'Test Domain',
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
                name: 'Updated Process Name',
                domain: 'marketing'
            };

            const mockResponse = {
                id: 'proc_001',
                name: 'Updated Process Name',
                type: 'discrete',
                event_ids: ['evt_001'],
                domain: 'marketing',
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

    describe('generateEntitiesFromProcess', () => {
        it('generates entities from a process', async () => {
            const mockResponse = {
                entities: [
                    {
                        id: 'order_fact',
                        label: 'Order',
                        entity_type: 'fact',
                        tags: ['sales']
                    },
                    {
                        id: 'customer_dim',
                        label: 'Customer',
                        entity_type: 'dimension',
                        tags: ['sales']
                    }
                ],
                relationships: [
                    {
                        source: 'order_fact',
                        target: 'customer_dim',
                        label: 'has',
                        type: 'many_to_one'
                    }
                ],
                errors: []
            };

            vi.stubGlobal(
                'fetch',
                vi.fn().mockResolvedValue({
                    ok: true,
                    json: vi.fn().mockResolvedValue(mockResponse)
                })
            );

            const result = await generateEntitiesFromProcess('proc_001');

            expect(result).toEqual(mockResponse);
            expect(result.entities).toHaveLength(2);
            expect(result.relationships).toHaveLength(1);
            expect(global.fetch).toHaveBeenCalledWith(
                'http://localhost:8089/api/processes/proc_001/generate-entities',
                expect.objectContaining({
                    method: 'POST'
                })
            );
        });

        it('handles empty response', async () => {
            vi.stubGlobal(
                'fetch',
                vi.fn().mockResolvedValue({
                    ok: true,
                    json: vi.fn().mockResolvedValue({ entities: [], relationships: [] })
                })
            );

            const result = await generateEntitiesFromProcess('proc_002');

            expect(result.entities).toEqual([]);
            expect(result.relationships).toEqual([]);
        });

        it('handles errors when generating from process', async () => {
            vi.stubGlobal(
                'fetch',
                vi.fn().mockResolvedValue({
                    ok: false,
                    status: 404,
                    statusText: 'Not Found',
                    json: vi.fn().mockResolvedValue({ detail: 'Process not found' })
                })
            );

            await expect(generateEntitiesFromProcess('proc_invalid'))
                .rejects.toThrow('Process not found');
        });

        it('handles network errors', async () => {
            vi.stubGlobal(
                'fetch',
                vi.fn().mockRejectedValue(new Error('Network error'))
            );

            await expect(generateEntitiesFromProcess('proc_001'))
                .rejects.toThrow('Error generating entities from process: Network error');
        });
    });
});
