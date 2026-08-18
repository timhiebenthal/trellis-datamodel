import type {
    ConfigInfo,
    ConfigStatus,
    DataModel,
    ExposuresResponse,
    ModelInfo,
    Relationship,
} from './types';

export interface ReconciliationResult {
    status: string;
    changed: boolean;
}

export interface BootLoaderSources {
    getConfigStatus: () => Promise<ConfigStatus>;
    getConfigInfo: () => Promise<ConfigInfo>;
    getManifest: () => Promise<ModelInfo[]>;
    reconcile: () => Promise<ReconciliationResult>;
    getDataModel: () => Promise<DataModel>;
    getExposures: () => Promise<ExposuresResponse>;
    inferRelationships: () => Promise<Relationship[]>;
}

export interface BootCore {
    status: ConfigStatus;
    config: ConfigInfo;
    models: ModelInfo[];
    reconciliation: ReconciliationResult;
    dataModel: DataModel;
}

export interface BootDiagnostic {
    phase: 'exposures' | 'relationships';
    status: 'failed';
}

export interface BootSession {
    core: Promise<BootCore>;
    optional: {
        exposures: Promise<ExposuresResponse | null>;
        relationships: Promise<Relationship[]>;
    };
    diagnostics: () => BootDiagnostic[];
}

function exposuresAreAvailable(config: ConfigInfo): boolean {
    return Boolean(config.exposures_enabled ?? config.capabilities?.exposures);
}

export function createBootLoader(sources: BootLoaderSources): BootSession {
    const diagnostics: BootDiagnostic[] = [];

    // These requests have no dependency on one another. Starting them before
    // awaiting either response removes the serial status/config waterfall.
    const statusPromise = sources.getConfigStatus();
    const configPromise = sources.getConfigInfo();
    const modelsPromise = sources.getManifest();

    const reconciliationPromise = modelsPromise.then(() => sources.reconcile());
    const core = Promise.all([
        statusPromise,
        configPromise,
        modelsPromise,
        reconciliationPromise,
    ]).then(async ([status, config, models, reconciliation]) => ({
        status,
        config,
        models,
        reconciliation,
        dataModel: await sources.getDataModel(),
    }));

    const exposures = configPromise
        .then((config) => (exposuresAreAvailable(config) ? sources.getExposures() : null))
        .catch(() => {
            diagnostics.push({ phase: 'exposures', status: 'failed' });
            return null;
        });

    const relationships = core
        .then((loaded) =>
            loaded.dataModel.relationships.length === 0
                ? sources.inferRelationships()
                : [],
        )
        .catch(() => {
            diagnostics.push({ phase: 'relationships', status: 'failed' });
            return [];
        });

    return {
        core,
        optional: { exposures, relationships },
        diagnostics: () => diagnostics.map((diagnostic) => ({ ...diagnostic })),
    };
}
