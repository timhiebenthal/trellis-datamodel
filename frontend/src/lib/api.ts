import type {
    DbtModel,
    DataModel,
    DraftedField,
    ConfigStatus,
    ConfigInfo,
    ModelSchema,
    ModelSchemaColumn,
    Relationship,
    ExposuresResponse,
    LineageResponse,
} from './types';

/**
 * API base URL. Uses relative URL when served from the same origin (production),
 * or can be configured via PUBLIC_API_URL environment variable for development.
 *
 * To override, set PUBLIC_API_URL in your .env file:
 *   PUBLIC_API_URL=http://your-backend-url/api
 */
export function getApiBase(): string {
    // Prefer Vite/SvelteKit public env var (build-time)
    // Falls back to legacy PUBLIC_API_URL, then relative /api
    const maybe =
        import.meta.env?.VITE_PUBLIC_API_URL ??
        import.meta.env?.PUBLIC_API_URL ??
        '';
    if (typeof maybe === 'string' && maybe.length > 0) {
        return maybe;
    }
    if (import.meta.env?.DEV) {
        const devTarget = import.meta.env?.VITE_DEV_API_TARGET ?? 'http://localhost:8089';
        return `${devTarget.replace(/\/+$/g, '')}/api`;
    }
    // Use relative URL - works when frontend is served by backend
    return '/api';
}

const API_BASE = getApiBase();

export async function getManifest(): Promise<DbtModel[]> {
    try {
        // Short-circuit in test/smoke environments to avoid console 500s when backend is absent
        const isSmokeMode =
            import.meta.env?.MODE === 'test' ||
            import.meta.env?.VITE_SMOKE_TEST === 'true' ||
            import.meta.env?.PUBLIC_SMOKE_TEST === 'true' ||
            (typeof window !== 'undefined' && Boolean((window as any).__SMOKE_TEST__));
        if (isSmokeMode) {
            return [];
        }

        const res = await fetch(`${API_BASE}/manifest`);
        if (!res.ok) {
            if (res.status === 404) return [];
            throw new Error(`Failed to fetch manifest: ${res.status}`);
        }
        const data = await res.json();
        return data.models || [];
    } catch (e) {
        console.error("Error fetching manifest:", e);
        return [];
    }
}

export async function getDataModel(): Promise<DataModel> {
    try {
        const isSmokeMode =
            import.meta.env?.MODE === 'test' ||
            import.meta.env?.VITE_SMOKE_TEST === 'true' ||
            import.meta.env?.PUBLIC_SMOKE_TEST === 'true' ||
            (typeof window !== 'undefined' && Boolean((window as any).__SMOKE_TEST__));
        if (isSmokeMode) {
            return { version: 0.1, entities: [], relationships: [] };
        }

        const res = await fetch(`${API_BASE}/data-model`);
        if (!res.ok) {
            throw new Error(`Failed to fetch data model: ${res.status}`);
        }
        return await res.json();
    } catch (e) {
        console.error("Error fetching data model:", e);
        throw e;
    }
}

export async function saveDataModel(model: DataModel): Promise<void> {
    try {
        const res = await fetch(`${API_BASE}/data-model`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(model),
        });

        if (!res.ok) {
            const errorText = await res.text();
            throw new Error(`Failed to save data model: ${res.status} - ${errorText}`);
        }
    } catch (e) {
        console.error("Error saving data model:", e);
        throw e;
    }
}

export async function getConfigStatus(): Promise<ConfigStatus> {
    try {
        const res = await fetch(`${API_BASE}/config-status`);
        if (!res.ok) {
            throw new Error(`Failed to fetch config status: ${res.status}`);
        }
        return await res.json();
    } catch (e) {
        console.error("Error fetching config status:", e);
        throw e;
    }
}

export async function getConfigInfo(): Promise<ConfigInfo> {
    try {
        const res = await fetch(`${API_BASE}/config-info`);
        if (!res.ok) {
            throw new Error(`Failed to fetch config info: ${res.status}`);
        }
        return await res.json();
    } catch (e) {
        console.error("Error fetching config info:", e);
        throw e;
    }
}

export async function inferRelationships(): Promise<Relationship[]> {
    try {
        const res = await fetch(`${API_BASE}/infer-relationships`);
        if (!res.ok) {
            throw new Error(`Failed to infer relationships: ${res.status}`);
        }
        return await res.json();
    } catch (e) {
        console.error("Error inferring relationships:", e);
        throw e;
    }
}

export async function syncDbtTests(): Promise<{ message: string }> {
    try {
        const res = await fetch(`${API_BASE}/sync-dbt-tests`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({}),
        });

        if (!res.ok) {
            throw new Error(`Failed to sync dbt tests: ${res.status}`);
        }
        return await res.json();
    } catch (e) {
        console.error("Error syncing dbt tests:", e);
        throw e;
    }
}

export async function getExposures(): Promise<ExposuresResponse> {
    try {
        const res = await fetch(`${API_BASE}/exposures`);
        if (!res.ok) {
            throw new Error(`Failed to fetch exposures: ${res.status}`);
        }
        return await res.json();
    } catch (e) {
        console.error("Error fetching exposures:", e);
        throw e;
    }
}

export async function getLineage(modelId: string): Promise<LineageResponse | null> {
    try {
        const res = await fetch(`${API_BASE}/lineage/${encodeURIComponent(modelId)}`);
        if (!res.ok) {
            if (res.status === 404) return null;
            throw new Error(`Failed to fetch lineage: ${res.status}`);
        }
        return await res.json();
    } catch (e) {
        console.error("Error fetching lineage:", e);
        // Return null on error to allow modal to handle error display
        return null;
    }
}

export async function getModelSchema(
    modelName: string,
    version?: number
): Promise<ModelSchema | null> {
    try {
        const url = version
            ? `${API_BASE}/schema?model_name=${modelName}&version=${version}`
            : `${API_BASE}/schema?model_name=${modelName}`;
        const res = await fetch(url);
        if (!res.ok) {
            if (res.status === 404) return null;
            throw new Error(`Failed to fetch schema: ${res.status}`);
        }
        return await res.json();
    } catch (e) {
        console.error("Error fetching schema:", e);
        return null;
    }
}

export async function updateModelSchema(
    modelName: string,
    version: number | undefined,
    columns: ModelSchemaColumn[]
): Promise<ModelSchema> {
    try {
        const url = version
            ? `${API_BASE}/schema?model_name=${modelName}&version=${version}`
            : `${API_BASE}/schema?model_name=${modelName}`;
        const res = await fetch(url, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ columns }),
        });
        if (!res.ok) {
            throw new Error(`Failed to update schema: ${res.status}`);
        }
        return await res.json();
    } catch (e) {
        console.error("Error updating schema:", e);
        throw e;
    }
}

export async function getSourceSystemSuggestions(): Promise<string[]> {
    try {
        const res = await fetch(`${API_BASE}/source-systems/suggestions`);
        if (!res.ok) {
            // Return empty array on error
            return [];
        }
        const data = await res.json();
        return data.suggestions || [];
    } catch (e) {
        console.error("Error fetching source system suggestions:", e);
        return [];
    }
}

// Config API
export interface ConfigFieldMetadata {
    type: string;
    enum_values?: string[];
    default: any;
    required: boolean;
    description: string;
    beta: boolean;
}

export interface ConfigSchema {
    fields: Record<string, ConfigFieldMetadata>;
    beta_flags: string[];
}

export interface ConfigGetResponse {
    config: Record<string, any>;
    schema_metadata: ConfigSchema;
    file_info?: {
        path: string;
        mtime: number;
        hash: string;
        backup_path?: string;
    };
    error?: string;
}

export interface ConfigUpdateResponse {
    config: Record<string, any>;
    file_info: {
        path: string;
        mtime: number;
        hash: string;
    };
}

export async function getConfig(): Promise<ConfigGetResponse> {
    try {
        const res = await fetch(`${API_BASE}/config`);
        if (!res.ok) throw new Error(`Status: ${res.status}`);
        return await res.json();
    } catch (e) {
        console.error("Error fetching config:", e);
        return {
            config: {},
            schema_metadata: { fields: {}, beta_flags: [] },
            error: e instanceof Error ? e.message : "Failed to load config",
        };
    }
}

export async function getConfigSchema(): Promise<ConfigSchema> {
    try {
        const res = await fetch(`${API_BASE}/config/schema`);
        if (!res.ok) throw new Error(`Status: ${res.status}`);
        return await res.json();
    } catch (e) {
        console.error("Error fetching config schema:", e);
        return { fields: {}, beta_flags: [] };
    }
}

export async function updateConfig(
    config: Record<string, any>,
    expected_mtime?: number,
    expected_hash?: string
): Promise<ConfigUpdateResponse> {
    const body: any = { config };
    if (expected_mtime !== undefined) body.expected_mtime = expected_mtime;
    if (expected_hash !== undefined) body.expected_hash = expected_hash;

    const res = await fetch(`${API_BASE}/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    });

    if (res.status === 409) {
        const error = await res.json();
        throw new Error(`CONFLICT: ${JSON.stringify(error.detail)}`);
    }

    if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail?.message || `Status: ${res.status}`);
    }

    return await res.json();
}

export async function validateConfig(config: Record<string, any>): Promise<{ valid: boolean; error?: string }> {
    try {
        const res = await fetch(`${API_BASE}/config/validate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });

        if (!res.ok) {
            const error = await res.json();
            throw new Error(error.detail?.message || `Status: ${res.status}`);
        }

        return await res.json();
    } catch (e) {
        const message = e instanceof Error ? e.message : String(e);
        // If it's not a CONFLICT, rethrow
        if (!message.startsWith('CONFLICT:')) {
            console.error("Error validating config:", e);
            return { valid: false, error: message };
        }
        throw e;
    }
}

/**
 * Fetch Bus Matrix data showing dimension-fact connections.
 * 
 * @param dimensionId - Optional filter by specific dimension entity ID
 * @param factId - Optional filter by specific fact entity ID
 * @param tag - Optional filter by tag (entities must have this tag)
 * @returns Promise containing dimensions, facts, and their connections
 */
export async function getBusMatrix(
    dimensionId?: string,
    factId?: string,
    tag?: string
): Promise<{
    dimensions: Array<{ id: string; label: string; tags?: string[] }>;
    facts: Array<{ id: string; label: string; tags?: string[] }>;
    connections: Array<{ dimension_id: string; fact_id: string }>;
}> {
    const params = new URLSearchParams();
    if (dimensionId) params.append('dimension_id', dimensionId);
    if (factId) params.append('fact_id', factId);
    if (tag) params.append('tag', tag);

    const queryString = params.toString();
    const url = `${API_BASE}/bus-matrix${queryString ? `?${queryString}` : ''}`;

    const res = await fetch(url);
    if (!res.ok) {
        throw new Error(`Failed to fetch bus matrix: ${res.statusText}`);
    }
    return await res.json();
}
