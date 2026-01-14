import type {
    DbtModel,
    DataModel,
    DraftedField,
    ConfigStatus,
    ConfigInfo,
    ModelSchema,
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
        const res = await fetch(`${API_BASE}/config/status`);
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
        const res = await fetch(`${API_BASE}/config/info`);
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
        const res = await fetch(`${API_BASE}/lineage?model_id=${modelId}`);
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
): Promise<ModelSchema> {
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
