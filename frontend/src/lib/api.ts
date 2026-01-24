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
    BusinessEvent,
    BusinessEventType,
    BusinessEventAnnotations,
    AnnotationEntry,
    SevenWType,
    AnnotationType,
    Dimension,
    Annotation,
    GeneratedEntitiesResult,
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
        const trimmed = maybe.replace(/\/+$/g, '');
        if (trimmed.endsWith('/api')) {
            return trimmed;
        }
        if (typeof window !== 'undefined') {
            try {
                const rawUrl = new URL(trimmed, window.location.origin);
                if (rawUrl.origin === window.location.origin) {
                    const path = rawUrl.pathname.replace(/\/+$/g, '');
                    if (path === '' || path === '/') {
                        return `${rawUrl.origin}/api`;
                    }
                }
            } catch {
                // fall through to trimmed
            }
        }
        return trimmed;
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

async function fetchDataModelOnce(): Promise<DataModel> {
    const res = await fetch(`${API_BASE}/data-model`);
    if (!res.ok) {
        throw new Error(`Failed to fetch data model: ${res.status}`);
    }
    return await res.json();
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

        try {
            return await fetchDataModelOnce();
        } catch (e) {
            if (e instanceof TypeError && e.message.includes('Failed to fetch')) {
                return await fetchDataModelOnce();
            }
            throw e;
        }
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
            if (res.status === 400) {
                // Treat config/schema absence as a non-fatal case for the UI/tests
                return [];
            }
            const errorText = await res.text();
            const details = errorText ? ` - ${errorText}` : '';
            throw new Error(
                `Failed to infer relationships: ${res.status} ${res.statusText}${details}`,
            );
        }
        const payload = await res.json();
        const relationships = Array.isArray(payload)
            ? payload
            : Array.isArray((payload as any)?.relationships)
              ? (payload as any).relationships
              : [];
        return relationships;
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
        const encodedModel = encodeURIComponent(modelName);
        const url = version
            ? `${API_BASE}/models/${encodedModel}/schema?version=${version}`
            : `${API_BASE}/models/${encodedModel}/schema`;
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
        const encodedModel = encodeURIComponent(modelName);
        const url = version
            ? `${API_BASE}/models/${encodedModel}/schema?version=${version}`
            : `${API_BASE}/models/${encodedModel}/schema`;
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

export async function reloadConfig(): Promise<{ status: string; message: string }> {
    try {
        const res = await fetch(`${API_BASE}/config/reload`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        if (!res.ok) {
            const error = await res.json();
            throw new Error(error.detail?.message || `Status: ${res.status}`);
        }

        return await res.json();
    } catch (e) {
        const message = e instanceof Error ? e.message : String(e);
        throw new Error(message);
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

/**
 * Business Events API functions
 */

/**
 * Fetch all business events.
 * @returns Promise containing array of BusinessEvent objects
 */
export async function getBusinessEvents(): Promise<BusinessEvent[]> {
    try {
        const res = await fetch(`${API_BASE}/business-events`);
        if (!res.ok) {
            // Try to get error detail from response
            let errorDetail = res.statusText;
            try {
                const errorData = await res.json();
                errorDetail = errorData.detail || errorData.message || errorDetail;
            } catch {
                // If JSON parsing fails, use statusText
            }
            const error = new Error(`Failed to fetch business events: ${errorDetail}`);
            (error as any).status = res.status;
            (error as any).statusText = res.statusText;
            throw error;
        }
        const data = await res.json();
        // Handle both { events: [...] } and direct array response
        return Array.isArray(data) ? data : (data.events || []);
    } catch (e) {
        // Re-throw with status code preserved
        if (e instanceof Error && (e as any).status) {
            throw e;
        }
        const message = e instanceof Error ? e.message : String(e);
        throw new Error(`Error fetching business events: ${message}`);
    }
}

/**
 * Get unique domain values from all business events for autocomplete.
 * @returns Promise containing array of unique domain strings
 */
export async function getBusinessEventDomains(): Promise<string[]> {
    try {
        const res = await fetch(`${API_BASE}/business-events/domains`);
        if (!res.ok) {
            // Try to get error detail from response
            let errorDetail = res.statusText;
            try {
                const errorData = await res.json();
                errorDetail = errorData.detail || errorData.message || errorDetail;
            } catch {
                // If JSON parsing fails, use statusText
            }
            const error = new Error(`Failed to fetch business event domains: ${errorDetail}`);
            (error as any).status = res.status;
            (error as any).statusText = res.statusText;
            throw error;
        }
        return await res.json();
    } catch (e) {
        // Re-throw with status code preserved
        if (e instanceof Error && (e as any).status) {
            throw e;
        }
        const message = e instanceof Error ? e.message : String(e);
        throw new Error(`Error fetching business event domains: ${message}`);
    }
}

/**
 * Create a new business event.
 * @param text - Event description text
 * @param type - Event type (discrete, evolving, recurring)
 * @param domain - Optional business domain (e.g., "Sales", "Marketing")
 * @param sevenWs - Optional 7 Ws structure for the event
 * @returns Promise containing the created BusinessEvent
 */
export async function createBusinessEvent(
    text: string,
    type: BusinessEventType,
    domain?: string,
    annotations?: BusinessEventAnnotations
): Promise<BusinessEvent> {
    try {
        const body: any = { text, type, domain: domain || null };
        if (annotations) {
            body.annotations = annotations;
        }

        const res = await fetch(`${API_BASE}/business-events`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!res.ok) {
            const error = await res.json();
            throw new Error(error.detail || `Failed to create business event: ${res.statusText}`);
        }
        return await res.json();
    } catch (e) {
        const message = e instanceof Error ? e.message : String(e);
        throw new Error(`Error creating business event: ${message}`);
    }
}

/**
 * Update an existing business event.
 * @param id - Event ID to update
 * @param updates - Dictionary with fields to update (text, type, domain, annotations, derived_entities)
 * @returns Promise containing the updated BusinessEvent
 */
export async function updateBusinessEvent(
    id: string,
    updates: Partial<BusinessEvent>
): Promise<BusinessEvent> {
    try {
        const res = await fetch(`${API_BASE}/business-events/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updates),
        });
        if (!res.ok) {
            const error = await res.json();
            throw new Error(error.detail || `Failed to update business event: ${res.statusText}`);
        }
        return await res.json();
    } catch (e) {
        const message = e instanceof Error ? e.message : String(e);
        throw new Error(`Error updating business event: ${message}`);
    }
}

/**
 * Update the annotations structure for a business event.
 * @param id - Event ID to update
 * @param annotations - Complete annotations structure to replace existing
 * @returns Promise containing the updated BusinessEvent
 */
export async function updateBusinessEventAnnotations(
    id: string,
    annotations: BusinessEventAnnotations
): Promise<BusinessEvent> {
    try {
        const res = await fetch(`${API_BASE}/business-events/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ annotations: annotations }),
        });
        if (!res.ok) {
            const error = await res.json();
            throw new Error(error.detail || `Failed to update annotations: ${res.statusText}`);
        }
        return await res.json();
    } catch (e) {
        const message = e instanceof Error ? e.message : String(e);
        throw new Error(`Error updating annotations: ${message}`);
    }
}

/**
 * Get dimensions from the data model (filtered by entity_type=dimension).
 * @param filterByType - Optional annotation type filter (annotation_type)
 * @returns Promise containing array of Dimension objects
 */
export async function getDimensions(filterByType?: AnnotationType): Promise<Dimension[]> {
    try {
        let url = `${API_BASE}/data-model`;
        const params = new URLSearchParams();
        if (filterByType) {
            params.append('annotation_type', filterByType);
        }
        const queryString = params.toString();
        if (queryString) {
            url += `?${queryString}`;
        }

        const res = await fetch(url);
        if (!res.ok) {
            // Treat missing data model as empty result
            if (res.status === 404) return [];
            throw new Error(`Failed to fetch dimensions: ${res.status}`);
        }

        const data = await res.json();
        // Filter entities to return only dimensions
        const entities = data.entities || [];
        return entities
            .filter((e: Dimension) => e.entity_type === 'dimension')
            .filter((e: Dimension) => {
                // If annotation_type filter specified, only return matching dimensions
                if (filterByType) {
                    return e.annotation_type === filterByType;
                }
                return true;
            });
    } catch (e) {
        const message = e instanceof Error ? e.message : String(e);
        throw new Error(`Error fetching dimensions: ${message}`);
    }
}

/**
 * Add a new 7 Ws entry to a business event.
 * @param eventId - Event ID to add entry to
 * @param wType - W category ('who', 'what', 'when', 'where', 'how', 'how_many', 'why')
 * @param text - Entry text
 * @param description - Optional entry description
 * @param dimensionId - Optional reference to existing dimension in data_model.yml
 * @returns Promise containing the updated BusinessEvent
 */
export async function addAnnotationEntry(
    eventId: string,
    wType: SevenWType,
    text: string,
    description?: string,
    dimensionId?: string
): Promise<BusinessEvent> {
    try {
        const body: any = { w_type: wType, text };
        if (description !== undefined) body.description = description;
        if (dimensionId !== undefined) body.dimension_id = dimensionId;

        const res = await fetch(`${API_BASE}/business-events/${eventId}/seven-entries`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!res.ok) {
            const error = await res.json();
            throw new Error(error.detail || `Failed to add 7 Ws entry: ${res.statusText}`);
        }
        return await res.json();
    } catch (e) {
        const message = e instanceof Error ? e.message : String(e);
        throw new Error(`Error adding 7 Ws entry: ${message}`);
    }
}

/**
 * Update an existing 7 Ws entry in a business event.
 * @param eventId - Event ID containing the entry
 * @param entryId - Entry ID to update
 * @param text - New entry text
 * @param description - Optional new entry description
 * @param dimensionId - Optional new dimension_id reference
 * @returns Promise containing the updated BusinessEvent
 */
export async function updateAnnotationEntry(
    eventId: string,
    entryId: string,
    text: string,
    description?: string,
    dimensionId?: string
): Promise<BusinessEvent> {
    try {
        const body: any = { text };
        if (description !== undefined) body.description = description;
        if (dimensionId !== undefined) body.dimension_id = dimensionId;

        const res = await fetch(`${API_BASE}/business-events/${eventId}/seven-entries/${entryId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });
        if (!res.ok) {
            const error = await res.json();
            throw new Error(error.detail || `Failed to update 7 Ws entry: ${res.statusText}`);
        }
        return await res.json();
    } catch (e) {
        const message = e instanceof Error ? e.message : String(e);
        throw new Error(`Error updating 7 Ws entry: ${message}`);
    }
}

/**
 * Remove a 7 Ws entry from a business event.
 * @param eventId - Event ID containing the entry
 * @param entryId - Entry ID to remove
 * @returns Promise containing the updated BusinessEvent
 */
export async function removeAnnotationEntry(
    eventId: string,
    entryId: string
): Promise<BusinessEvent> {
    try {
        const res = await fetch(`${API_BASE}/business-events/${eventId}/seven-entries/${entryId}`, {
            method: 'DELETE',
        });
        if (!res.ok) {
            const error = await res.json();
            throw new Error(error.detail || `Failed to remove 7 Ws entry: ${res.statusText}`);
        }
        return await res.json();
    } catch (e) {
        const message = e instanceof Error ? e.message : String(e);
        throw new Error(`Error removing 7 Ws entry: ${message}`);
    }
}

export const addSevenWsEntry = addAnnotationEntry;
export const updateSevenWsEntry = updateAnnotationEntry;
export const removeSevenWsEntry = removeAnnotationEntry;

/**
 * Delete a business event.
 * @param id - Event ID to delete
 */
export async function deleteBusinessEvent(id: string): Promise<void> {
    try {
        const res = await fetch(`${API_BASE}/business-events/${id}`, {
            method: 'DELETE',
        });
        if (!res.ok) {
            const error = await res.json();
            throw new Error(error.detail || `Failed to delete business event: ${res.statusText}`);
        }
    } catch (e) {
        const message = e instanceof Error ? e.message : String(e);
        throw new Error(`Error deleting business event: ${message}`);
    }
}

/**
 * Add an annotation to a business event.
 * @param eventId - Event ID
 * @param text - Annotated text segment
 * @param type - Annotation type ('dimension' or 'fact')
 * @param startPos - Start position in event text
 * @param endPos - End position in event text
 * @returns Promise containing the updated BusinessEvent
 */
export async function addAnnotation(
    eventId: string,
    text: string,
    type: 'dimension' | 'fact',
    startPos: number,
    endPos: number
): Promise<BusinessEvent> {
    try {
        const res = await fetch(`${API_BASE}/business-events/${eventId}/annotations`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, type, start_pos: startPos, end_pos: endPos }),
        });
        if (!res.ok) {
            const error = await res.json();
            throw new Error(error.detail || `Failed to add annotation: ${res.statusText}`);
        }
        return await res.json();
    } catch (e) {
        const message = e instanceof Error ? e.message : String(e);
        throw new Error(`Error adding annotation: ${message}`);
    }
}

/**
 * Remove an annotation from a business event.
 * @param eventId - Event ID
 * @param index - Index of annotation to remove
 * @returns Promise containing the updated BusinessEvent
 */
export async function removeAnnotation(
    eventId: string,
    index: number
): Promise<BusinessEvent> {
    try {
        const res = await fetch(`${API_BASE}/business-events/${eventId}/annotations/${index}`, {
            method: 'DELETE',
        });
        if (!res.ok) {
            const error = await res.json();
            throw new Error(error.detail || `Failed to remove annotation: ${res.statusText}`);
        }
        return await res.json();
    } catch (e) {
        const message = e instanceof Error ? e.message : String(e);
        throw new Error(`Error removing annotation: ${message}`);
    }
}

/**
 * Generate entities from a business event.
 * Supports both annotation-based and 7 Ws-based entity generation.
 * @param eventId - Event ID to generate entities from
 * @returns Promise containing GeneratedEntitiesResult
 */
export async function generateEntitiesFromEvent(
    eventId: string
): Promise<GeneratedEntitiesResult> {
    try {
        const res = await fetch(`${API_BASE}/business-events/${eventId}/generate-entities`, {
            method: 'POST',
        });
        if (!res.ok) {
            const error = await res.json();
            throw new Error(error.detail || `Failed to generate entities: ${res.statusText}`);
        }
        const data = await res.json();
        // Handle both direct response and wrapped response formats
        return Array.isArray(data?.entities) ? data : { entities: [], relationships: [], errors: [] };
    } catch (e) {
        const message = e instanceof Error ? e.message : String(e);
        throw new Error(`Error generating entities: ${message}`);
    }
}
