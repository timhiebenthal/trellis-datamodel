import { describe, expect, it, vi } from 'vitest';
import type {
    ConfigInfo,
    ConfigStatus,
    DataModel,
    ExposuresResponse,
    ModelInfo,
    Relationship,
} from './types';
import { createBootLoader, type BootLoaderSources } from './boot-loader';

type Deferred<T> = {
    promise: Promise<T>;
    resolve: (value: T) => void;
    reject: (reason?: unknown) => void;
};

function deferred<T>(): Deferred<T> {
    let resolve!: (value: T) => void;
    let reject!: (reason?: unknown) => void;
    const promise = new Promise<T>((resolvePromise, rejectPromise) => {
        resolve = resolvePromise;
        reject = rejectPromise;
    });
    return { promise, resolve, reject };
}

const status = {} as ConfigStatus;
const config = { capabilities: { exposures: true } } as ConfigInfo;
const models = [] as ModelInfo[];
const dataModel: DataModel = {
    version: 0.1,
    entities: [{ id: 'orders', label: 'Orders', position: { x: 0, y: 0 } }],
    relationships: [],
};
const exposures = { exposures: [], entityUsage: {} } as ExposuresResponse;
const relationships = [] as Relationship[];

function sources(overrides: Partial<BootLoaderSources> = {}): BootLoaderSources {
    return {
        getConfigStatus: vi.fn().mockResolvedValue(status),
        getConfigInfo: vi.fn().mockResolvedValue(config),
        getManifest: vi.fn().mockResolvedValue(models),
        reconcile: vi.fn().mockResolvedValue({ status: 'success', changed: false }),
        getDataModel: vi.fn().mockResolvedValue(dataModel),
        getExposures: vi.fn().mockResolvedValue(exposures),
        inferRelationships: vi.fn().mockResolvedValue(relationships),
        ...overrides,
    };
}

describe('boot loader', () => {
    it('independent status/config requests start before either resolves', () => {
        const statusRequest = deferred<ConfigStatus>();
        const configRequest = deferred<ConfigInfo>();
        const getConfigStatus = vi.fn(() => statusRequest.promise);
        const getConfigInfo = vi.fn(() => configRequest.promise);

        createBootLoader(
            sources({
                getConfigStatus,
                getConfigInfo,
            }),
        );

        expect(getConfigStatus).toHaveBeenCalledTimes(1);
        expect(getConfigInfo).toHaveBeenCalledTimes(1);
    });

    it('core entities publish before exposure and relationship promises resolve', async () => {
        const exposureRequest = deferred<ExposuresResponse>();
        const relationshipRequest = deferred<Relationship[]>();
        const session = createBootLoader(
            sources({
                getExposures: vi.fn(() => exposureRequest.promise),
                inferRelationships: vi.fn(() => relationshipRequest.promise),
            }),
        );

        const core = await session.core;

        expect(core.dataModel.entities).toHaveLength(1);
        expect(await Promise.race([
            session.optional.exposures.then(() => 'resolved'),
            Promise.resolve('pending'),
        ])).toBe('pending');
        expect(await Promise.race([
            session.optional.relationships.then(() => 'resolved'),
            Promise.resolve('pending'),
        ])).toBe('pending');

        exposureRequest.resolve(exposures);
        relationshipRequest.resolve(relationships);
        await expect(session.optional.exposures).resolves.toEqual(exposures);
        await expect(session.optional.relationships).resolves.toEqual(relationships);
    });

    it('failed optional work records diagnostics but does not erase core content', async () => {
        const exposureFailure = new Error('exposures unavailable');
        const relationshipFailure = new Error('relationships unavailable');
        const session = createBootLoader(
            sources({
                getExposures: vi.fn().mockRejectedValue(exposureFailure),
                inferRelationships: vi.fn().mockRejectedValue(relationshipFailure),
            }),
        );

        const core = await session.core;
        expect(core.dataModel.entities[0]?.id).toBe('orders');
        await expect(session.optional.exposures).resolves.toBeNull();
        await expect(session.optional.relationships).resolves.toEqual([]);
        expect(session.diagnostics()).toEqual([
            { phase: 'exposures', status: 'failed' },
            { phase: 'relationships', status: 'failed' },
        ]);
    });

    it('reconciliation returns and consumes only the state required before the data-model read', async () => {
        const calls: string[] = [];
        const reconcile = vi.fn(async () => {
            calls.push('reconcile');
            return { status: 'success', changed: true };
        });
        const getDataModel = vi.fn(async () => {
            calls.push('data-model');
            return dataModel;
        });

        const session = createBootLoader(
            sources({
                reconcile,
                getDataModel,
            }),
        );

        const core = await session.core;

        expect(core.reconciliation).toEqual({ status: 'success', changed: true });
        expect(calls).toEqual(['reconcile', 'data-model']);
        await expect(reconcile.mock.results[0]?.value).resolves.not.toHaveProperty('data_model');
    });
});
