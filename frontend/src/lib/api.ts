import type {
    DbtModel,
    DataModel,
    DraftedField,
    ConfigStatus,
    ConfigInfo,
    ModelSchema,
    Relationship,
    ExposuresResponse,
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
    // #region agent log
    const endpointUrl = `${API_BASE}/exposures`;
    fetch('http://127.0.0.1:7242/ingest/24cc0f53-14db-4775-8467-7fbdba4920ff',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'api.ts:184',message:'getExposures called',data:{endpointUrl,apiBase:API_BASE},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
    // #endregion agent log
    try {
        const res = await fetch(endpointUrl);
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/24cc0f53-14db-4775-8467-7fbdba4920ff',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'api.ts:186',message:'fetch response received',data:{status:res.status,ok:res.ok,statusText:res.statusText},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
        // #endregion agent log
        if (!res.ok) {
            if (res.status === 404) {
                // #region agent log
                fetch('http://127.0.0.1:7242/ingest/24cc0f53-14db-4775-8467-7fbdba4920ff',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'api.ts:189',message:'endpoint returned 404',data:{endpointUrl},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
                // #endregion agent log
                // Return empty response if endpoint doesn't exist yet
                return { exposures: [], entityUsage: {} };
            }
            // #region agent log
            fetch('http://127.0.0.1:7242/ingest/24cc0f53-14db-4775-8467-7fbdba4920ff',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'api.ts:193',message:'endpoint returned error status',data:{status:res.status,statusText:res.statusText},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
            // #endregion agent log
            throw new Error(`Status: ${res.status}`);
        }
        const jsonData = await res.json();
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/24cc0f53-14db-4775-8467-7fbdba4920ff',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'api.ts:197',message:'successful response parsed',data:{exposuresCount:jsonData.exposures?.length||0,entityUsageKeys:Object.keys(jsonData.entityUsage||{}).length},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
        // #endregion agent log
        return jsonData;
    } catch (e) {
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/24cc0f53-14db-4775-8467-7fbdba4920ff',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'api.ts:200',message:'exception caught in getExposures',data:{error:e instanceof Error?e.message:String(e)},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
        // #endregion agent log
        console.error("Error fetching exposures:", e);
        // Return empty response on error
        return { exposures: [], entityUsage: {} };
    }
}
