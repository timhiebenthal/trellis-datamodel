import type { DbtModel, DataModel, DraftedField, ConfigStatus, ModelSchema, Relationship } from './types';

/**
 * API base URL. Can be configured via PUBLIC_API_URL environment variable.
 * Defaults to http://localhost:8000/api for local development.
 * 
 * To override, set PUBLIC_API_URL in your .env file:
 *   PUBLIC_API_URL=http://your-backend-url/api
 */
function getApiBase(): string {
    // Try to access the environment variable if available
    try {
        // @ts-ignore - dynamic import not available at build time
        if (typeof import.meta.env?.PUBLIC_API_URL === 'string' && import.meta.env.PUBLIC_API_URL) {
            return import.meta.env.PUBLIC_API_URL;
        }
    } catch {
        // Ignore - env not available
    }
    return 'http://localhost:8000/api';
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
            dbt_project_path: '',
            manifest_path: '',
            catalog_path: '',
            manifest_exists: false,
            catalog_exists: false,
            data_model_exists: false,
        };
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

export async function inferRelationships(): Promise<Relationship[]> {
    try {
        const res = await fetch(`${API_BASE}/infer-relationships`);
        if (!res.ok) {
            if (res.status === 404) return []; // Handle gracefully
            throw new Error(`Status: ${res.status}`);
        }
        const data = await res.json();
        return data.relationships || [];
    } catch (e) {
        console.error("Error inferring relationships:", e);
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

export async function getModelSchema(modelName: string): Promise<ModelSchema | null> {
    try {
        const res = await fetch(`${API_BASE}/models/${modelName}/schema`);
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

export async function updateModelSchema(modelName: string, columns: { name: string; data_type?: string; description?: string }[], description?: string, tags?: string[]): Promise<{ status: string; message: string; file_path: string }> {
    const res = await fetch(`${API_BASE}/models/${modelName}/schema`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ columns, description, tags })
    });
    if (!res.ok) {
        const error = await res.text();
        throw new Error(`Failed to update model schema: ${error}`);
    }
    return await res.json();
}
