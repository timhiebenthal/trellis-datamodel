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
    // Use relative URL - works when frontend is served by the backend
    return '/api';
}

const API_BASE = getApiBase();

export async function getManifest(): Promise<DbtModel[]> {
    try {
        const res = await fetch(`${API_BASE}/manifest`);
        if (!res.ok) {
            if (res.status === 404) return []; // Handle missing manifest gracefully
            throw new Error(`Status: ${res.status}`);
        }
        const data = await res.json();
        return data.models;
    } catch (e) {
        console.error("Error fetching manifest:", e);
        return [];
    }
}

export async function getBusMatrix(
    dimensionId?: string,
    factId?: string,
    tag?: string
): Promise<{ dimensions: any[], facts: any[], connections: any[] }> {
    try {
        const params = new URLSearchParams();
        if (dimensionId) params.append('dimension_id', dimensionId);
        if (factId) params.append('fact_id', factId);
        if (tag) params.append('tag', tag);
        
        const res = await fetch(`${API_BASE}/bus-matrix?${params.toString()}`);
        if (!res.ok) {
            if (res.status === 404) return { dimensions: [], facts: [], connections: [] };
            throw new Error(`Status: ${res.status}`);
        }
        const data = await res.json();
        return data;
    } catch (e) {
        console.error("Error fetching BUS Matrix:", e);
        return { dimensions: [], facts: [], connections: [] };
    }
}

export async function getDataModel(): Promise<DataModel> {
    try {
        const res = await fetch(`${API_BASE}/data-model`);
        if (!res.ok) throw new Error(`Status: ${res.status}`);
        return await res.json();
    } catch (e) {
        console.error("Error fetching data model:", e);
        // Return empty default
        return { version: 0.1, entities: [], relationships: [] };
    }
}

export async function saveDataModel(dataModel: DataModel): Promise<void> {
    const res = await fetch(`${API_BASE}/data-model`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(dataModel)
    });
    if (!res.ok) throw new Error(`Failed to save data model: ${res.status}`);
}

export async function getConfigStatus(): Promise<ConfigStatus> {
    try {
        const res = await fetch(`${API_BASE}/config-status`);
        if (!res.ok) throw new Error(`Status: ${res.status}`);
        return await res.json();
    } catch (e) {
        console.error("Error fetching config status:", e);
        return {
            config_present: false,
            config_filename: 'trellis.yml',
            dbt_project_path: '',
            manifest_path: '',
            catalog_path: '',
            manifest_exists: false,
            catalog_exists: false,
            data_model_exists: false,
        };
    }
}

export async function getConfigInfo(): Promise<ConfigInfo | null> {
    try {
        const res = await fetch(`${API_BASE}/config-info`);
        if (!res.ok) throw new Error(`Status: ${res.status}`);
        return await res.json();
    } catch (e) {
        console.error("Error fetching config info:", e);
        return null;
    }
}

export async function saveDbtSchema(entityId: string, modelName: string, fields: DraftedField[], description?: string, tags?: string[]): Promise<{ status: string; file_path: string; message: string }> {
    const res = await fetch(`${API_BASE}/dbt-schema`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            entity_id: entityId, 
            model_name: modelName, 
            fields,
            description,
            tags
        })
    });
    if (!res.ok) {
        const error = await res.text();
        throw new Error(`Failed to save dbt schema: ${error}`);
    }
    return await res.json();
}

export async function inferRelationships(options?: { includeUnbound?: boolean }): Promise<Relationship[]> {
    try {
        const params = options?.includeUnbound ? '?include_unbound=true' : '';
        const res = await fetch(`${API_BASE}/infer-relationships${params}`);
        if (!res.ok) {
            // Handle 400 (no schema files) and 404 (endpoint not found) gracefully
            if (res.status === 400 || res.status === 404) return [];
            throw new Error(`Status: ${res.status}`);
        }
        const data = await res.json();
        return data.relationships || [];
    } catch (e) {
        // Don't log expected errors (400 = no schema files, 404 = endpoint not found)
        const errorMessage = e instanceof Error ? e.message : String(e);
        if (!errorMessage.includes('400') && !errorMessage.includes('404')) {
            console.error("Error inferring relationships:", e);
        }
        return [];
    }
}

export async function syncDbtTests(): Promise<{ status: string; message: string; files: string[] }> {
    const res = await fetch(`${API_BASE}/sync-dbt-tests`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
    });
    if (!res.ok) {
        const error = await res.text();
        throw new Error(`Failed to sync dbt tests: ${error}`);
    }
    return await res.json();
}

export async function getModelSchema(modelName: string, version?: number): Promise<ModelSchema | null> {
    try {
        const params = version !== undefined ? `?version=${version}` : "";
        const res = await fetch(`${API_BASE}/models/${modelName}/schema${params}`);
        if (!res.ok) {
            if (res.status === 404) return null; // Model not found
            throw new Error(`Status: ${res.status}`);
        }
        return await res.json();
    } catch (e) {
        console.error("Error fetching model schema:", e);
        return null;
    }
}

export async function updateModelSchema(modelName: string, columns: { name: string; data_type?: string; description?: string }[], description?: string, tags?: string[], version?: number): Promise<{ status: string; message: string; file_path: string }> {
    const res = await fetch(`${API_BASE}/models/${modelName}/schema`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ columns, description, tags, version })
    });
    if (!res.ok) {
        const error = await res.text();
        throw new Error(`Failed to update model schema: ${error}`);
    }
    return await res.json();
}

export async function getExposures(): Promise<ExposuresResponse> {
    const endpointUrl = `${API_BASE}/exposures`;
    try {
        const res = await fetch(endpointUrl);
        if (!res.ok) {
            if (res.status === 404) {
                // Return empty response if endpoint doesn't exist yet
                return { exposures: [], entityUsage: {} };
            }
            throw new Error(`Status: ${res.status}`);
        }
        const jsonData = await res.json();
        return jsonData;
    } catch (e) {
        console.error("Error fetching exposures:", e);
        // Return empty response on error
        return { exposures: [], entityUsage: {} };
    }
}

export async function getLineage(modelId: string): Promise<LineageResponse | null> {
    try {
        const res = await fetch(`${API_BASE}/lineage/${encodeURIComponent(modelId)}`);
        if (!res.ok) {
            if (res.status === 404) {
                // Model not found - return null to allow modal to handle gracefully
                return null;
            }
            // For 500 errors, throw with error message
            const error = await res.text();
            throw new Error(error || `Failed to fetch lineage: ${res.status}`);
        }
        return await res.json();
    } catch (e) {
        console.error("Error fetching lineage:", e);
        // Return null on error to allow modal to handle error display
        return null;
    }
}
