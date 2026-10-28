import { describe, it, expect, vi, afterEach } from 'vitest';
import {
    inferRelationships,
    getDimensions,
    getDataModel,
    saveDataModel,
    getBusinessEvents,
    createBusinessEvent,
    updateBusinessEvent,
    updateBusinessEventAnnotations,
    getBusinessEventProcesses,
    createBusinessEventProcess,
    updateBusinessEventProcess,
    resolveBusinessEventProcess,
    attachEventsToProcess,
    detachEventsFromProcess,
    generateEntitiesFromProcess,
    syncDbtTests,
    reconcileDbt,
    getModelSchema,
    getConfig,
    reloadConfig,
    updateConfig,
} from './api';
import { emitBootSummary } from './boot-diagnostics';
import { useApiStub } from './test-helpers/stub-api';
import type {
    BusinessEvent,
    BusinessEventAnnotations,
    BusinessEventSevenWs,
    CreateProcessRequest,
    DataModel,
    UpdateProcessRequest,
    AttachEventsRequest,
    DetachEventsRequest,
} from '$lib/types';

const api = useApiStub();

// The api layer logs and rethrows; keep expected failures out of test output.
vi.spyOn(console, 'error').mockImplementation(() => {});

afterEach(() => {
    vi.unstubAllEnvs();
});

const emptySevenWs = (overrides: Partial<BusinessEventSevenWs> = {}): BusinessEventSevenWs => ({
    who: [],
    what: [],
    when: [],
    where: [],
    how: [],
    how_many: [],
    why: [],
    ...overrides,
});

const processFixture = (overrides: Record<string, unknown> = {}) => ({
    id: 'proc_001',
    name: 'Test Process',
    type: 'discrete',
    event_ids: [],
    created_at: '2026-01-27T10:00:00Z',
    updated_at: '2026-01-27T10:00:00Z',
    ...overrides,
});

describe('boot request diagnostics', () => {
    const recordedSince = (before: number) => emitBootSummary().requests.slice(before);
    const recordedCount = () => emitBootSummary().requests.length;

    it('records path, method, status and content length of a boot request', async () => {
        api.route({
            'GET /api/models/orders/schema': {
                json: { columns: [] },
                headers: { 'Content-Length': '42', 'Server-Timing': 'db;dur=12.5' },
            },
        });
        const before = recordedCount();

        await getModelSchema('orders');

        const [request, ...rest] = recordedSince(before);
        expect(rest).toEqual([]);
        expect(request).toMatchObject({
            path: '/api/models/orders/schema',
            method: 'GET',
            status: 200,
            bytes: 42,
        });
        expect(request.duration).toBeGreaterThanOrEqual(0);
    });

    it('falls back to the serialized body size when there is no content length', async () => {
        const body = { columns: [] };
        api.route({ 'GET /api/models/orders/schema': { json: body } });
        const before = recordedCount();

        await getModelSchema('orders');

        expect(recordedSince(before)[0].bytes).toBe(JSON.stringify(body).length);
    });

    it('records every schema request, including repeats', async () => {
        api.route({
            'GET /api/models/orders/schema': { json: { columns: [] } },
            'GET /api/models/customers/schema': { json: { columns: [] } },
        });
        const before = recordedCount();

        await Promise.all([
            getModelSchema('orders'),
            getModelSchema('orders'),
            getModelSchema('customers'),
        ]);

        const paths = recordedSince(before).map((request) => request.path);
        expect(paths.filter((p) => p === '/api/models/orders/schema')).toHaveLength(2);
        expect(paths.filter((p) => p === '/api/models/customers/schema')).toHaveLength(1);
    });

    it('records a failed HTTP request once and still surfaces the backend error', async () => {
        api.route({
            'GET /api/infer-relationships': {
                status: 500,
                text: 'backend failed',
            },
        });
        const before = recordedCount();

        await expect(inferRelationships()).rejects.toThrow(
            'Failed to infer relationships: 500',
        );

        const requests = recordedSince(before);
        expect(requests).toHaveLength(1);
        expect(requests[0]).toMatchObject({ path: '/api/infer-relationships', status: 500 });
    });

    it('records a network failure without a status and surfaces the error', async () => {
        api.route({
            'GET /api/models/orders/schema': { networkError: new TypeError('Failed to fetch') },
        });
        const before = recordedCount();

        await expect(getModelSchema('orders')).rejects.toThrow('Failed to fetch');

        const [request] = recordedSince(before);
        expect(request.path).toBe('/api/models/orders/schema');
        expect(request.status).toBeUndefined();
    });
});

describe('model schema', () => {
    it('returns the schema', async () => {
        const schema = { columns: [{ name: 'id', type: 'integer' }] };
        api.route({ 'GET /api/models/orders/schema': { json: schema } });

        await expect(getModelSchema('orders')).resolves.toEqual(schema);
    });

    it('returns null when the model has no schema (404)', async () => {
        api.route({ 'GET /api/models/orders/schema': { status: 404 } });

        await expect(getModelSchema('orders')).resolves.toBeNull();
    });

    it('surfaces a server error instead of reporting a missing schema', async () => {
        api.route({ 'GET /api/models/orders/schema': { status: 500 } });

        await expect(getModelSchema('orders')).rejects.toThrow('Failed to fetch schema: 500');
    });
});

describe('relationship inference', () => {
    it('returns relationships when the API responds with an array', async () => {
        const rel = {
            source: 'lead',
            target: 'customer',
            source_field: 'lead_id',
            target_field: 'lead_id',
        };
        api.route({ 'GET /api/infer-relationships': { json: [rel] } });

        await expect(inferRelationships()).resolves.toEqual([rel]);
    });

    it('unwraps relationships from an object response', async () => {
        const rel = { source: 'a', target: 'b', source_field: 'x', target_field: 'y' };
        api.route({ 'GET /api/infer-relationships': { json: { relationships: [rel] } } });

        await expect(inferRelationships()).resolves.toEqual([rel]);
    });

    it('returns an empty array when inference is not configured (400)', async () => {
        api.route({ 'GET /api/infer-relationships': { status: 400, text: '' } });

        await expect(inferRelationships()).resolves.toEqual([]);
    });
});

describe('framework-neutral sync endpoints', () => {
    // Only the neutral routes are registered; a call to the legacy
    // /api/sync-dbt-tests or /api/reconcile-dbt paths would fail as unrouted.
    it('syncDbtTests syncs through POST /api/sync-tests', async () => {
        api.route({ 'POST /api/sync-tests': { json: { message: 'ok' } } });

        await expect(syncDbtTests()).resolves.toEqual({ message: 'ok' });
    });

    it('reconcileDbt reconciles through POST /api/reconcile', async () => {
        api.route({ 'POST /api/reconcile': { json: { status: 'success', changed: true } } });

        await expect(reconcileDbt()).resolves.toEqual({ status: 'success', changed: true });
    });

    it('reconcileDbt reports no change when the endpoint is missing (404)', async () => {
        api.route({ 'POST /api/reconcile': { status: 404 } });

        await expect(reconcileDbt()).resolves.toEqual({ status: 'success', changed: false });
    });

    it('reconcileDbt reports an error without throwing when the backend fails (500)', async () => {
        api.route({ 'POST /api/reconcile': { status: 500 } });

        await expect(reconcileDbt()).resolves.toEqual({ status: 'error', changed: false });
    });

    it('reconcileDbt reports an error without throwing on a network failure', async () => {
        api.route({ 'POST /api/reconcile': { networkError: new TypeError('Failed to fetch') } });

        await expect(reconcileDbt()).resolves.toEqual({ status: 'error', changed: false });
    });
});

describe('getDimensions', () => {
    const entities = [
        { id: 'dim1', label: 'Customer', entity_type: 'dimension', annotation_type: 'who' },
        { id: 'dim2', label: 'Product', entity_type: 'dimension', annotation_type: 'what' },
    ];

    it('returns the dimensions of the data model', async () => {
        api.route({ 'GET /api/data-model': { json: { entities } } });

        await expect(getDimensions()).resolves.toEqual(entities);
    });

    it('returns only dimensions, not facts', async () => {
        api.route({
            'GET /api/data-model': {
                json: { entities: [...entities, { id: 'fact1', entity_type: 'fact' }] },
            },
        });

        const result = await getDimensions();

        expect(result.map((e) => e.id)).toEqual(['dim1', 'dim2']);
    });

    it('filters dimensions by annotation_type when specified', async () => {
        api.route({
            'GET /api/data-model?annotation_type=who': { json: { entities } },
        });

        const result = await getDimensions('who');

        expect(result.map((e) => e.id)).toEqual(['dim1']);
    });

    it('returns an empty array when there is no data model (404)', async () => {
        api.route({ 'GET /api/data-model': { status: 404 } });

        await expect(getDimensions()).resolves.toEqual([]);
    });

    it('throws on other HTTP failures', async () => {
        api.route({ 'GET /api/data-model': { status: 500 } });

        await expect(getDimensions()).rejects.toThrow('Failed to fetch dimensions: 500');
    });
});

describe('business events', () => {
    const sevenWs = emptySevenWs({ who: [{ id: 'ent1', text: 'customer' }] });

    it('createBusinessEvent sends the annotations and returns the created event', async () => {
        const created = {
            id: 'evt_new',
            text: 'customer buys product',
            type: 'discrete',
            annotations: sevenWs,
            derived_entities: [],
        };
        api.route({ 'POST /api/business-events': { json: created } });

        const result = await createBusinessEvent('customer buys product', 'discrete', 'Sales', sevenWs);

        expect(result).toEqual(created);
        expect(api.sent[0].body).toEqual({
            text: 'customer buys product',
            type: 'discrete',
            domain: 'Sales',
            annotations: sevenWs,
        });
    });

    it('updateBusinessEvent sends the annotations and returns the updated event', async () => {
        const updated = { id: 'evt_001', text: 'customer buys product', annotations: sevenWs };
        api.route({ 'PUT /api/business-events/evt_001': { json: updated } });

        const result = await updateBusinessEvent('evt_001', { annotations: sevenWs });

        expect(result).toEqual(updated);
        expect(api.sent[0].body).toEqual({ annotations: sevenWs });
    });

    it('surfaces the backend error detail when creation fails', async () => {
        api.route({ 'POST /api/business-events': { status: 400, json: { detail: 'Text is required' } } });

        await expect(createBusinessEvent('')).rejects.toThrow('Text is required');
    });

    it('lists events from either a bare array or an { events } wrapper', async () => {
        const events = [{ id: 'evt_001' }];
        api.route({ 'GET /api/business-events': { json: { events } } });
        await expect(getBusinessEvents()).resolves.toEqual(events);

        api.route({ 'GET /api/business-events': { json: events } });
        await expect(getBusinessEvents()).resolves.toEqual(events);
    });

    it('preserves the HTTP status on list failures', async () => {
        api.route({ 'GET /api/business-events': { status: 503, json: { detail: 'down' } } });

        await expect(getBusinessEvents()).rejects.toMatchObject({
            message: 'Failed to fetch business events: down',
            status: 503,
        });
    });
});

describe('Business Event Process API Functions', () => {
    describe('getBusinessEventProcesses', () => {
        it('returns processes from an array response', async () => {
            const processes = [processFixture({ name: 'Order Fulfillment', event_ids: ['evt_001', 'evt_002'] })];
            api.route({ 'GET /api/processes': { json: processes } });

            await expect(getBusinessEventProcesses()).resolves.toEqual(processes);
        });

        it('returns processes from a wrapped response', async () => {
            const processes = [processFixture()];
            api.route({ 'GET /api/processes': { json: { processes } } });

            await expect(getBusinessEventProcesses()).resolves.toEqual(processes);
        });

        it('throws when fetching fails', async () => {
            api.route({
                'GET /api/processes': { status: 500, json: { detail: 'Server error' } },
            });

            await expect(getBusinessEventProcesses()).rejects.toThrow(
                'Failed to fetch business event processes',
            );
        });
    });

    describe('createBusinessEventProcess', () => {
        it('sends the request payload and returns the created process', async () => {
            const request: CreateProcessRequest = {
                name: 'Order Fulfillment',
                type: 'discrete',
                event_ids: ['evt_001', 'evt_002'],
                domain: 'sales',
            };
            const created = processFixture({ ...request });
            api.route({ 'POST /api/processes': { json: created } });

            await expect(createBusinessEventProcess(request)).resolves.toEqual(created);
            expect(api.sent[0].body).toEqual(request);
        });

        it('creates a process without event_ids', async () => {
            const request: CreateProcessRequest = { name: 'New Process', type: 'evolving', domain: 'Test Domain' };
            const created = processFixture({ id: 'proc_002', name: 'New Process', type: 'evolving' });
            api.route({ 'POST /api/processes': { json: created } });

            await expect(createBusinessEventProcess(request)).resolves.toEqual(created);
        });

        it('surfaces the backend error detail', async () => {
            api.route({
                'POST /api/processes': { status: 404, json: { detail: 'Events not found' } },
            });

            await expect(
                createBusinessEventProcess({
                    name: 'Test Process',
                    type: 'discrete',
                    domain: 'Test Domain',
                    event_ids: ['evt_invalid'],
                }),
            ).rejects.toThrow('Events not found');
        });
    });

    describe('updateBusinessEventProcess', () => {
        it('sends the changes and returns the updated process', async () => {
            const request: UpdateProcessRequest = { name: 'Updated Process Name', domain: 'marketing' };
            const updated = processFixture({ ...request });
            api.route({ 'PUT /api/processes/proc_001': { json: updated } });

            await expect(updateBusinessEventProcess('proc_001', request)).resolves.toEqual(updated);
            expect(api.sent[0].body).toEqual(request);
        });

        it('can change the process type', async () => {
            api.route({
                'PUT /api/processes/proc_001': { json: processFixture({ type: 'evolving' }) },
            });

            const result = await updateBusinessEventProcess('proc_001', { type: 'evolving' });

            expect(result.type).toBe('evolving');
        });

        it('surfaces the backend error detail', async () => {
            api.route({
                'PUT /api/processes/proc_invalid': { status: 404, json: { detail: 'Process not found' } },
            });

            await expect(
                updateBusinessEventProcess('proc_invalid', { name: 'Updated Name' }),
            ).rejects.toThrow('Process not found');
        });
    });

    describe('resolveBusinessEventProcess', () => {
        it('returns the resolved process', async () => {
            const resolved = processFixture({ resolved_at: '2026-01-27T11:00:00Z' });
            api.route({ 'POST /api/processes/proc_001/resolve': { json: resolved } });

            const result = await resolveBusinessEventProcess('proc_001');

            expect(result).toEqual(resolved);
            expect(result.resolved_at).toBeDefined();
        });

        it('surfaces the backend error detail', async () => {
            api.route({
                'POST /api/processes/proc_invalid/resolve': {
                    status: 404,
                    json: { detail: 'Process not found' },
                },
            });

            await expect(resolveBusinessEventProcess('proc_invalid')).rejects.toThrow(
                'Process not found',
            );
        });
    });

    describe('attachEventsToProcess', () => {
        it('sends the event ids and returns the process with them attached', async () => {
            const request: AttachEventsRequest = { event_ids: ['evt_003', 'evt_004'] };
            const attached = processFixture({ event_ids: ['evt_001', 'evt_002', 'evt_003', 'evt_004'] });
            api.route({ 'POST /api/processes/proc_001/attach': { json: attached } });

            const result = await attachEventsToProcess('proc_001', request);

            expect(result.event_ids).toEqual(attached.event_ids);
            expect(api.sent[0].body).toEqual(request);
        });

        it('surfaces the backend error detail', async () => {
            api.route({
                'POST /api/processes/proc_001/attach': {
                    status: 404,
                    json: { detail: 'Events not found' },
                },
            });

            await expect(
                attachEventsToProcess('proc_001', { event_ids: ['evt_invalid'] }),
            ).rejects.toThrow('Events not found');
        });
    });

    describe('detachEventsFromProcess', () => {
        it('sends the event ids and returns the process without them', async () => {
            const request: DetachEventsRequest = { event_ids: ['evt_002'] };
            api.route({
                'POST /api/processes/proc_001/detach': {
                    json: processFixture({ event_ids: ['evt_001'] }),
                },
            });

            const result = await detachEventsFromProcess('proc_001', request);

            expect(result.event_ids).toEqual(['evt_001']);
            expect(api.sent[0].body).toEqual(request);
        });

        it('surfaces the backend error detail', async () => {
            api.route({
                'POST /api/processes/proc_invalid/detach': {
                    status: 404,
                    json: { detail: 'Process not found' },
                },
            });

            await expect(
                detachEventsFromProcess('proc_invalid', { event_ids: ['evt_002'] }),
            ).rejects.toThrow('Process not found');
        });
    });

    describe('generateEntitiesFromProcess', () => {
        it('returns the generated entities and relationships', async () => {
            const generated = {
                entities: [
                    { id: 'order_fact', label: 'Order', entity_type: 'fact', tags: ['sales'] },
                    { id: 'customer_dim', label: 'Customer', entity_type: 'dimension', tags: ['sales'] },
                ],
                relationships: [
                    { source: 'order_fact', target: 'customer_dim', label: 'has', type: 'many_to_one' },
                ],
                errors: [],
            };
            api.route({ 'POST /api/processes/proc_001/generate-entities': { json: generated } });

            await expect(generateEntitiesFromProcess('proc_001')).resolves.toEqual(generated);
        });

        it('returns an empty result when nothing is generated', async () => {
            api.route({
                'POST /api/processes/proc_002/generate-entities': {
                    json: { entities: [], relationships: [] },
                },
            });

            const result = await generateEntitiesFromProcess('proc_002');

            expect(result.entities).toEqual([]);
            expect(result.relationships).toEqual([]);
        });

        it('surfaces the backend error detail', async () => {
            api.route({
                'POST /api/processes/proc_invalid/generate-entities': {
                    status: 404,
                    json: { detail: 'Process not found' },
                },
            });

            await expect(generateEntitiesFromProcess('proc_invalid')).rejects.toThrow(
                'Process not found',
            );
        });

        it('wraps network errors with context', async () => {
            api.route({
                'POST /api/processes/proc_001/generate-entities': {
                    networkError: new Error('Network error'),
                },
            });

            await expect(generateEntitiesFromProcess('proc_001')).rejects.toThrow(
                'Error generating entities from process: Network error',
            );
        });
    });
});

describe('role-playing dimensions through the data model', () => {
    const dimension = (id: string, extra: Record<string, unknown> = {}) => ({
        id,
        label: id,
        entity_type: 'dimension' as const,
        position: { x: 0, y: 0 },
        ...extra,
    });
    const model = (entities: any[]): DataModel => ({ version: 0.1, entities, relationships: [] });

    // getDataModel short-circuits to an empty model in the test environment.
    const useRealDataModelFetch = () => vi.stubEnv('MODE', 'development');

    describe('reading entity roles', () => {
        it('returns the roles of each dimension', async () => {
            useRealDataModelFetch();
            api.route({
                'GET /api/data-model': {
                    json: model([
                        dimension('dim_date', { roles: ['order_date', 'ship_date', 'delivery_date'] }),
                        dimension('dim_location', { roles: ['origin', 'destination'] }),
                    ]),
                },
            });

            const result = await getDataModel();

            expect(result.entities.map((e) => e.roles)).toEqual([
                ['order_date', 'ship_date', 'delivery_date'],
                ['origin', 'destination'],
            ]);
        });

        it('leaves roles undefined for entities that have none (backward compatibility)', async () => {
            useRealDataModelFetch();
            api.route({
                'GET /api/data-model': {
                    json: model([
                        dimension('dim_date', { roles: ['created_date', 'modified_date'] }),
                        dimension('dim_customer'),
                        { id: 'fact_sales', label: 'Sales', entity_type: 'fact', position: { x: 0, y: 0 } },
                    ]),
                },
            });

            const result = await getDataModel();

            expect(result.entities[0].roles).toEqual(['created_date', 'modified_date']);
            expect(result.entities[1].roles).toBeUndefined();
            expect(result.entities[2].roles).toBeUndefined();
        });

        it('keeps an empty roles array as empty', async () => {
            useRealDataModelFetch();
            api.route({ 'GET /api/data-model': { json: model([dimension('dim_date', { roles: [] })]) } });

            const result = await getDataModel();

            expect(result.entities[0].roles).toEqual([]);
        });

        it('passes malformed roles through untouched rather than dropping them', async () => {
            useRealDataModelFetch();
            api.route({
                'GET /api/data-model': {
                    json: model([dimension('dim_date', { roles: 'invalid_not_array' })]),
                },
            });

            const result = await getDataModel();

            expect(result.entities[0].roles).toBe('invalid_not_array');
        });
    });

    describe('saving entity roles', () => {
        it('sends roles as part of the saved payload', async () => {
            api.route({ 'POST /api/data-model': { json: {} } });
            const payload = model([dimension('dim_date', { roles: ['order_date', 'ship_date'] })]);

            await saveDataModel(payload);

            expect(api.sent[0].body).toEqual(payload);
        });

        it('does not invent a roles field for entities without one', async () => {
            api.route({ 'POST /api/data-model': { json: {} } });

            await saveDataModel(model([dimension('dim_customer')]));

            expect(api.sent[0].body.entities[0]).not.toHaveProperty('roles');
        });

        it('preserves an empty roles array', async () => {
            api.route({ 'POST /api/data-model': { json: {} } });

            await saveDataModel(model([dimension('dim_date', { roles: [] })]));

            expect(api.sent[0].body.entities[0].roles).toEqual([]);
        });

        it('throws with the backend message when the save is rejected', async () => {
            api.route({ 'POST /api/data-model': { status: 422, text: 'invalid roles' } });

            await expect(saveDataModel(model([]))).rejects.toThrow(
                'Failed to save data model: 422 - invalid roles',
            );
        });

        it('round-trips edited roles: fetch, modify, save', async () => {
            useRealDataModelFetch();
            api.route({
                'GET /api/data-model': {
                    json: model([dimension('dim_date', { roles: ['order_date', 'ship_date'] })]),
                },
                'POST /api/data-model': { json: {} },
            });

            const fetched = await getDataModel();
            expect(fetched.entities[0].roles).toEqual(['order_date', 'ship_date']);
            fetched.entities[0].roles = ['order_date', 'ship_date', 'delivery_date'];
            await saveDataModel(fetched);

            const saved = api.sent.find((r) => r.method === 'POST')!;
            expect(saved.body.entities[0].roles).toEqual(['order_date', 'ship_date', 'delivery_date']);
        });
    });

    describe('annotation roles on business events', () => {
        const event = (annotations: BusinessEventAnnotations): BusinessEvent => ({
            id: 'evt_001',
            text: 'Order placed',
            type: 'discrete',
            created_at: '2026-01-01T00:00:00Z',
            updated_at: '2026-01-01T00:00:00Z',
            annotations,
            derived_entities: [],
        });
        const orderDate = { id: 'ann_001', text: 'Order Date', role: 'order_date', dimension_id: 'dim_date' };
        const shipDate = { id: 'ann_002', text: 'Ship Date', role: 'ship_date', dimension_id: 'dim_date' };
        const customer = { id: 'ann_003', text: 'Customer', dimension_id: 'dim_customer' };

        it('returns the role on each annotation and none where absent', async () => {
            api.route({
                'GET /api/business-events': {
                    json: [
                        event(
                            emptySevenWs({
                                who: [customer],
                                when: [orderDate, shipDate],
                                where: [
                                    { id: 'ann_004', text: 'Origin', role: 'origin', dimension_id: 'dim_location' },
                                ],
                            }),
                        ),
                    ],
                },
            });

            const [result] = await getBusinessEvents();

            expect(result.annotations?.who[0].role).toBeUndefined();
            expect(result.annotations?.when.map((a) => a.role)).toEqual(['order_date', 'ship_date']);
            expect(result.annotations?.where[0].role).toBe('origin');
        });

        it('passes a malformed (non-string) role through untouched', async () => {
            api.route({
                'GET /api/business-events': {
                    json: [event(emptySevenWs({ when: [{ ...orderDate, role: 123 } as any] }))],
                },
            });

            const [result] = await getBusinessEvents();

            expect(result.annotations?.when[0].role).toBe(123);
        });

        it('updateBusinessEvent sends annotation roles', async () => {
            const annotations = emptySevenWs({ when: [orderDate] });
            api.route({ 'PUT /api/business-events/evt_001': { json: event(annotations) } });

            await updateBusinessEvent('evt_001', { annotations });

            expect(api.sent[0].body.annotations.when[0].role).toBe('order_date');
        });

        it('updateBusinessEvent does not invent a role for annotations without one', async () => {
            const annotations = emptySevenWs({ who: [customer] });
            api.route({ 'PUT /api/business-events/evt_001': { json: event(annotations) } });

            await updateBusinessEvent('evt_001', { annotations });

            expect(api.sent[0].body.annotations.who[0]).not.toHaveProperty('role');
        });

        it('updateBusinessEventAnnotations sends the full annotation structure with roles', async () => {
            const annotations = emptySevenWs({
                when: [orderDate, { ...shipDate, id: 'ann_005', role: 'delivery_date' }],
                where: [{ id: 'ann_006', text: 'Origin', role: 'origin', dimension_id: 'dim_location' }],
            });
            api.route({ 'PUT /api/business-events/evt_001': { json: event(annotations) } });

            await updateBusinessEventAnnotations('evt_001', annotations);

            expect(api.sent[0].body).toEqual({ annotations });
        });

        it('round-trips an added role-playing annotation: fetch, modify, update', async () => {
            api.route({
                'GET /api/business-events': { json: [event(emptySevenWs({ when: [orderDate] }))] },
                'PUT /api/business-events/evt_001': { json: {} },
            });

            const [fetched] = await getBusinessEvents();
            expect(fetched.annotations?.when[0].role).toBe('order_date');
            fetched.annotations!.when.push(shipDate);
            await updateBusinessEvent('evt_001', { annotations: fetched.annotations });

            const saved = api.sent.find((r) => r.method === 'PUT')!;
            expect(saved.body.annotations.when.map((a: any) => a.role)).toEqual(['order_date', 'ship_date']);
        });
    });
});

describe('config API error bodies', () => {
    it('getConfig returns the 400 configuration error message instead of throwing', async () => {
        api.route({
            'GET /api/config': {
                status: 400,
                json: {
                    detail: 'No config file found. Please create trellis.yml in the current directory.',
                    error: 'configuration_error',
                },
            },
        });

        const response = await getConfig();

        expect(response.config).toEqual({});
        expect(response.error).toBe(
            'No config file found. Please create trellis.yml in the current directory.',
        );
    });

    it('reloadConfig throws the message of a string detail', async () => {
        api.route({
            'POST /api/config/reload': {
                status: 400,
                json: { detail: 'Invalid YAML in trellis.yml', error: 'configuration_error' },
            },
        });

        await expect(reloadConfig()).rejects.toThrow('Invalid YAML in trellis.yml');
    });

    it('updateConfig throws the message of a 422 validation error', async () => {
        api.route({
            'PUT /api/config': {
                status: 422,
                json: { detail: 'Config validation failed: framework', error: 'validation_error' },
            },
        });

        await expect(updateConfig({ framework: 'x' })).rejects.toThrow(
            'Config validation failed: framework',
        );
    });
});
