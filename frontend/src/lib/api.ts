import type {
    ModelInfo,
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
    AnnotationType,
    Dimension,
    Annotation,
    GeneratedEntitiesResult,
    BusinessEventProcess,
    CreateProcessRequest,
    UpdateProcessRequest,
    AttachEventsRequest,
    DetachEventsRequest,
    ConfigFieldMetadata,
    ConfigSchema,
    ConfigGetResponse,
    ConfigUpdateResponse,
    MetricTreeFile,
    MetricTreeResponse,
} from './types';
import { parseServerTiming, recordBootRequest } from './boot-diagnostics';
import type { ReconciliationResult } from './boot-loader';

// Re-export types for backward compatibility
export type {
    ConfigFieldMetadata,
    ConfigSchema,
    ConfigGetResponse,
    ConfigUpdateResponse,
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


/**
 * Error thrown by {@link apiJson} when the server answers with a non-2xx status.
 */
export class ApiError extends Error {
    readonly status: number;
    /** FastAPI `detail` (string, object or validation array), the raw body when it is not JSON, or undefined. */
    readonly detail: unknown;

    constructor(message: string, status: number, detail?: unknown) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
        this.detail = detail;
    }
}

export type ApiJsonOptions<T> = {
    method?: string;
    /** Serialized as JSON and sent with `Content-Type: application/json`. */
    body?: unknown;
    signal?: AbortSignal;
    /** Returned instead of throwing when the server answers 404. */
    notFound?: T;
    /**
     * Error message prefix: `${errorMessage}: ${status}[ - ${detail}]`.
     * Omit it to use the server's `detail` as the message.
     */
    errorMessage?: string;
};

function responseHeader(response: Response, name: string): string | null {
    return typeof response.headers?.get === 'function' ? response.headers.get(name) : null;
}

function serializedByteLength(value: unknown): number {
    return new TextEncoder().encode(JSON.stringify(value)).byteLength;
}

/** Human-readable text for a FastAPI `detail`: a string, `{ message }`, or a validation error list. */
function detailText(detail: unknown): string | undefined {
    if (typeof detail === 'string') return detail || undefined;
    if (Array.isArray(detail)) {
        const messages = detail
            .map((item) => (typeof item === 'string' ? item : (item as { msg?: unknown } | null)?.msg))
            .filter((msg): msg is string => typeof msg === 'string');
        return messages.length > 0 ? messages.join('; ') : undefined;
    }
    if (detail && typeof detail === 'object') {
        const message = (detail as { message?: unknown }).message;
        if (typeof message === 'string') return message;
    }
    return undefined;
}

async function readJsonBody(response: Response): Promise<unknown> {
    if (typeof response.text === 'function') {
        const text = await response.text();
        return text ? JSON.parse(text) : undefined;
    }
    if (typeof response.json === 'function') return await response.json();
    throw new Error('Response does not support JSON parsing');
}

/** Read an error body without ever throwing: parsed JSON, raw text, or undefined. */
async function readErrorBody(response: Response): Promise<unknown> {
    try {
        if (typeof response.text === 'function') {
            const text = await response.text();
            if (!text) return undefined;
            try {
                return JSON.parse(text);
            } catch {
                return text;
            }
        }
        if (typeof response.json === 'function') return await response.json();
    } catch {
        // Unreadable body: the message falls back to the status code.
    }
    return undefined;
}

/**
 * Call a JSON endpoint under the API base. Resolves with the parsed body
 * (undefined for an empty body) or throws {@link ApiError} for non-2xx
 * responses; network failures propagate unchanged. Every call is recorded
 * for boot diagnostics.
 */
export async function apiJson<T>(path: string, opts: ApiJsonOptions<T> = {}): Promise<T> {
    const url = `${API_BASE}${path}`;
    const method = (opts.method ?? 'GET').toUpperCase();
    const init: RequestInit = {};
    if (opts.method) init.method = opts.method;
    if (opts.body !== undefined) {
        init.headers = { 'Content-Type': 'application/json' };
        init.body = JSON.stringify(opts.body);
    }
    if (opts.signal) init.signal = opts.signal;

    const startedAt = performance.now();
    let response: Response;
    try {
        response = Object.keys(init).length > 0 ? await fetch(url, init) : await fetch(url);
    } catch (error) {
        recordBootRequest({
            url,
            method,
            bytes: undefined,
            duration: performance.now() - startedAt,
            serverTiming: [],
        });
        throw error;
    }

    const record = (body?: unknown): void => {
        const contentLength = responseHeader(response, 'content-length');
        const parsedContentLength = contentLength === null ? undefined : Number(contentLength);
        recordBootRequest({
            url,
            method,
            status: response.status,
            bytes: Number.isFinite(parsedContentLength)
                ? parsedContentLength
                : body === undefined
                  ? undefined
                  : serializedByteLength(body),
            duration: performance.now() - startedAt,
            serverTiming: parseServerTiming(responseHeader(response, 'server-timing')),
        });
    };

    if (response.status === 404 && opts.notFound !== undefined) {
        record();
        return opts.notFound;
    }

    let body: unknown;
    try {
        body = response.ok ? await readJsonBody(response) : await readErrorBody(response);
    } finally {
        record(body);
    }
    if (response.ok) return body as T;

    const detail =
        body !== null && typeof body === 'object' && !Array.isArray(body) && 'detail' in body
            ? (body as { detail: unknown }).detail
            : body;
    const text = detailText(detail);
    const message = opts.errorMessage
        ? `${opts.errorMessage}: ${response.status}${text ? ` - ${text}` : ''}`
        : (text ?? `Request failed: ${response.status}`);
    throw new ApiError(message, response.status, detail);
}

/** Accept both a bare list and a `{ [key]: [...] }` wrapper. */
function listFrom<T>(payload: unknown, key: string): T[] {
    if (Array.isArray(payload)) return payload as T[];
    const wrapped = (payload as Record<string, unknown> | null | undefined)?.[key];
    return Array.isArray(wrapped) ? (wrapped as T[]) : [];
}

function isSmokeMode(): boolean {
    return (
        import.meta.env?.MODE === 'test' ||
        import.meta.env?.VITE_SMOKE_TEST === 'true' ||
        import.meta.env?.PUBLIC_SMOKE_TEST === 'true' ||
        (typeof window !== 'undefined' && Boolean((window as any).__SMOKE_TEST__))
    );
}

export async function getManifest(): Promise<ModelInfo[]> {
    try {
        // Short-circuit in test/smoke environments to avoid console 500s when backend is absent
        if (isSmokeMode()) {
            return [];
        }
        const data = await apiJson<{ models?: ModelInfo[] }>('/manifest', {
            notFound: {},
            errorMessage: 'Failed to fetch manifest',
        });
        return data.models || [];
    } catch (e) {
        console.error("Error fetching manifest:", e);
        return [];
    }
}

function fetchDataModelOnce(): Promise<DataModel> {
    return apiJson<DataModel>('/data-model', { errorMessage: 'Failed to fetch data model' });
}

export async function getDataModel(): Promise<DataModel> {
    if (isSmokeMode()) {
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
}

export async function saveDataModel(model: DataModel): Promise<void> {
    await apiJson('/data-model', {
        method: 'POST',
        body: model,
        errorMessage: 'Failed to save data model',
    });
}

export function getConfigStatus(): Promise<ConfigStatus> {
    return apiJson<ConfigStatus>('/config-status', { errorMessage: 'Failed to fetch config status' });
}

export function getConfigInfo(): Promise<ConfigInfo> {
    return apiJson<ConfigInfo>('/config-info', { errorMessage: 'Failed to fetch config info' });
}

export async function inferRelationships(): Promise<Relationship[]> {
    try {
        const payload = await apiJson<unknown>('/infer-relationships', {
            errorMessage: 'Failed to infer relationships',
        });
        return listFrom<Relationship>(payload, 'relationships');
    } catch (e) {
        // Treat config/schema absence as a non-fatal case for the UI/tests
        if (e instanceof ApiError && e.status === 400) return [];
        throw e;
    }
}

export function syncDbtTests(): Promise<{ message: string; warnings?: string[] }> {
    return apiJson('/sync-tests', {
        method: 'POST',
        body: {},
        errorMessage: 'Failed to sync relationship tests',
    });
}

export function getExposures(): Promise<ExposuresResponse> {
    return apiJson<ExposuresResponse>('/exposures', { errorMessage: 'Failed to fetch exposures' });
}

export async function getLineage(modelId: string): Promise<LineageResponse | null> {
    try {
        return await apiJson<LineageResponse | null>(`/lineage/${encodeURIComponent(modelId)}`, {
            notFound: null,
            errorMessage: 'Failed to fetch lineage',
        });
    } catch (e) {
        console.error("Error fetching lineage:", e);
        // Return null on error to allow modal to handle error display
        return null;
    }
}

function schemaPath(modelName: string, version?: number): string {
    const encodedModel = encodeURIComponent(modelName);
    return version
        ? `/models/${encodedModel}/schema?version=${version}`
        : `/models/${encodedModel}/schema`;
}

export async function getModelSchema(
    modelName: string,
    version?: number
): Promise<ModelSchema | null> {
    try {
        return await apiJson<ModelSchema | null>(schemaPath(modelName, version), {
            notFound: null,
            errorMessage: 'Failed to fetch schema',
        });
    } catch (e) {
        console.error("Error fetching schema:", e);
        return null;
    }
}

export function updateModelSchema(
    modelName: string,
    version: number | undefined,
    columns: ModelSchemaColumn[]
): Promise<ModelSchema> {
    return apiJson<ModelSchema>(schemaPath(modelName, version), {
        method: 'POST',
        body: { columns },
        errorMessage: 'Failed to update schema',
    });
}

export async function getSourceSystemSuggestions(): Promise<string[]> {
    try {
        const data = await apiJson<{ suggestions?: string[] }>('/source-systems/suggestions');
        return data.suggestions || [];
    } catch (e) {
        console.error("Error fetching source system suggestions:", e);
        return [];
    }
}

// Config API
export async function getConfig(): Promise<ConfigGetResponse> {
    try {
        return await apiJson<ConfigGetResponse>('/config');
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
        return await apiJson<ConfigSchema>('/config/schema');
    } catch (e) {
        console.error("Error fetching config schema:", e);
        return { fields: {}, beta_flags: [] };
    }
}

/**
 * Save the config. A 409 (file changed on disk) is thrown as an ApiError whose
 * message is `CONFLICT: <JSON of detail>`; the config page parses that format.
 */
export async function updateConfig(
    config: Record<string, any>,
    expected_mtime?: number,
    expected_hash?: string
): Promise<ConfigUpdateResponse> {
    const body: Record<string, unknown> = { config };
    if (expected_mtime !== undefined) body.expected_mtime = expected_mtime;
    if (expected_hash !== undefined) body.expected_hash = expected_hash;

    try {
        return await apiJson<ConfigUpdateResponse>('/config', { method: 'PUT', body });
    } catch (e) {
        if (e instanceof ApiError && e.status === 409) {
            throw new ApiError(`CONFLICT: ${JSON.stringify(e.detail)}`, e.status, e.detail);
        }
        throw e;
    }
}

export async function validateConfig(config: Record<string, any>): Promise<{ valid: boolean; error?: string }> {
    try {
        return await apiJson<{ valid: boolean; error?: string }>('/config/validate', {
            method: 'POST',
            body: config,
        });
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

export function reloadConfig(): Promise<{ status: string; message: string }> {
    return apiJson('/config/reload', { method: 'POST' });
}

/**
 * Fetch Bus Matrix data showing dimension-fact connections.
 *
 * @param dimensionId - Optional filter by specific dimension entity ID
 * @param factId - Optional filter by specific fact entity ID
 * @param tag - Optional filter by tag (entities must have this tag)
 * @returns Promise containing dimensions, facts, and their connections
 */
export function getBusMatrix(
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
    return apiJson(`/bus-matrix${queryString ? `?${queryString}` : ''}`, {
        errorMessage: 'Failed to fetch bus matrix',
    });
}

/**
 * Business Events API functions
 */

/**
 * Fetch all business events.
 * Errors are ApiError instances, so callers can branch on `status`.
 * @returns Promise containing array of BusinessEvent objects
 */
export async function getBusinessEvents(): Promise<BusinessEvent[]> {
    const data = await apiJson<unknown>('/business-events', {
        errorMessage: 'Failed to fetch business events',
    });
    // Handle both { events: [...] } and direct array response
    return listFrom<BusinessEvent>(data, 'events');
}

/**
 * Get unique domain values from all business events for autocomplete.
 * @returns Promise containing array of unique domain strings
 */
export function getBusinessEventDomains(): Promise<string[]> {
    return apiJson<string[]>('/business-events/domains', {
        errorMessage: 'Failed to fetch business event domains',
    });
}

/**
 * Create a new business event.
 * @param text - Event description text
 * @param type - Event type (discrete, evolving, recurring)
 * @param domain - Optional business domain (e.g., "Sales", "Marketing")
 * @param sevenWs - Optional 7 Ws structure for the event
 * @returns Promise containing the created BusinessEvent
 */
export function createBusinessEvent(
    text: string,
    type?: BusinessEventType,
    domain?: string,
    annotations?: BusinessEventAnnotations,
    description?: string
): Promise<BusinessEvent> {
    const body: Record<string, unknown> = { text, ...(type !== undefined ? { type } : {}), domain: domain || null };
    if (description) {
        body.description = description;
    }
    if (annotations) {
        body.annotations = annotations;
    }
    return apiJson<BusinessEvent>('/business-events', { method: 'POST', body });
}

/**
 * Update an existing business event.
 * @param id - Event ID to update
 * @param updates - Dictionary with fields to update (text, type, domain, annotations, derived_entities)
 * @returns Promise containing the updated BusinessEvent
 */
export function updateBusinessEvent(
    id: string,
    updates: Partial<BusinessEvent>
): Promise<BusinessEvent> {
    return apiJson<BusinessEvent>(`/business-events/${id}`, { method: 'PUT', body: updates });
}

/**
 * Update the annotations structure for a business event.
 * @param id - Event ID to update
 * @param annotations - Complete annotations structure to replace existing
 * @returns Promise containing the updated BusinessEvent
 */
export function updateBusinessEventAnnotations(
    id: string,
    annotations: BusinessEventAnnotations
): Promise<BusinessEvent> {
    return apiJson<BusinessEvent>(`/business-events/${id}`, {
        method: 'PUT',
        body: { annotations: annotations },
    });
}

/**
 * Get dimensions from the data model (filtered by entity_type=dimension).
 * @param filterByType - Optional annotation type filter (annotation_type)
 * @returns Promise containing array of Dimension objects
 */
export async function getDimensions(filterByType?: AnnotationType, includeAllEntities = false): Promise<Dimension[]> {
    let path = '/data-model';
    const params = new URLSearchParams();
    if (filterByType) {
        params.append('annotation_type', filterByType);
    }
    const queryString = params.toString();
    if (queryString) {
        path += `?${queryString}`;
    }

    // Treat missing data model as empty result
    const data = await apiJson<{ entities?: Dimension[] }>(path, {
        notFound: { entities: [] },
        errorMessage: 'Failed to fetch dimensions',
    });
    const entities = data.entities || [];
    return entities
        .filter((e: Dimension) => includeAllEntities || e.entity_type === 'dimension')
        .filter((e: Dimension) => {
            // annotation_type filter only applies for dimensional mode
            if (!includeAllEntities && filterByType) {
                return e.annotation_type === filterByType;
            }
            return true;
        });
}

/**
 * Delete a business event.
 * @param id - Event ID to delete
 */
export async function deleteBusinessEvent(id: string): Promise<void> {
    await apiJson(`/business-events/${id}`, { method: 'DELETE' });
}

/** Abort fetch if the server never responds (avoids an endless “Generating preview…” spinner). */
function previewGenerateTimeoutSignal(ms: number): AbortSignal {
    if (typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function') {
        return AbortSignal.timeout(ms);
    }
    const c = new AbortController();
    setTimeout(() => c.abort(), ms);
    return c.signal;
}

function combinePreviewSignals(user: AbortSignal | undefined, timeoutMs: number): AbortSignal {
    const t = previewGenerateTimeoutSignal(timeoutMs);
    if (!user) {
        return t;
    }
    const anyFn = (AbortSignal as unknown as { any?: (signals: AbortSignal[]) => AbortSignal }).any;
    if (typeof anyFn === 'function') {
        return anyFn([user, t]);
    }
    return t;
}

/**
 * POST a generate-entities endpoint. Server errors surface as ApiError with the
 * server's detail; timeouts and network failures get a contextual message.
 */
async function generateEntities(path: string, context: string, userSignal?: AbortSignal): Promise<GeneratedEntitiesResult> {
    const signal = combinePreviewSignals(userSignal, 120_000);
    try {
        const data = await apiJson<GeneratedEntitiesResult | null>(path, { method: 'POST', signal });
        // Handle both direct response and wrapped response formats
        return Array.isArray(data?.entities) ? data : { entities: [], relationships: [], errors: [] };
    } catch (e) {
        if (e instanceof ApiError) throw e;
        const name = e instanceof Error ? e.name : '';
        if (name === 'AbortError' || name === 'TimeoutError') {
            throw new Error(
                `${context}: request timed out or was cancelled (check that the API is running).`
            );
        }
        const message = e instanceof Error ? e.message : String(e);
        throw new Error(`${context}: ${message}`);
    }
}

/**
 * Generate entities from a business event.
 * Supports both annotation-based and 7 Ws-based entity generation.
 * @param eventId - Event ID to generate entities from
 * @returns Promise containing GeneratedEntitiesResult
 */
export function generateEntitiesFromEvent(
    eventId: string,
    options?: { signal?: AbortSignal }
): Promise<GeneratedEntitiesResult> {
    return generateEntities(
        `/business-events/${eventId}/generate-entities`,
        'Error generating entities',
        options?.signal,
    );
}

/**
 * Generate entities from a business event process.
 * Uses the process's annotations_superset (union of all member event annotations).
 * @param processId - Process ID to generate entities from
 * @returns Promise containing GeneratedEntitiesResult
 */
export function generateEntitiesFromProcess(
    processId: string,
    options?: { signal?: AbortSignal }
): Promise<GeneratedEntitiesResult> {
    return generateEntities(
        `/processes/${processId}/generate-entities`,
        'Error generating entities from process',
        options?.signal,
    );
}

/**
 * Business Event Process API functions
 */

/**
 * Fetch all business event processes.
 * @returns Promise containing array of BusinessEventProcess objects
 */
export async function getBusinessEventProcesses(): Promise<BusinessEventProcess[]> {
    const data = await apiJson<unknown>('/processes', {
        errorMessage: 'Failed to fetch business event processes',
    });
    // Handle both { processes: [...] } and direct array response
    return listFrom<BusinessEventProcess>(data, 'processes');
}

/**
 * Create a new business event process.
 * @param request - CreateProcessRequest with name, type, and optional event_ids
 * @returns Promise containing the created BusinessEventProcess
 */
export function createBusinessEventProcess(
    request: CreateProcessRequest
): Promise<BusinessEventProcess> {
    return apiJson<BusinessEventProcess>('/processes', { method: 'POST', body: request });
}

/**
 * Update an existing business event process.
 * @param processId - Process ID to update
 * @param request - UpdateProcessRequest with fields to update (name, type)
 * @returns Promise containing the updated BusinessEventProcess
 */
export function updateBusinessEventProcess(
    processId: string,
    request: UpdateProcessRequest
): Promise<BusinessEventProcess> {
    return apiJson<BusinessEventProcess>(`/processes/${processId}`, { method: 'PUT', body: request });
}

/**
 * Resolve (ungroup) a business event process.
 * This removes the grouping by setting resolved_at and removing process_id from member events.
 * @param processId - Process ID to resolve
 * @returns Promise containing the resolved BusinessEventProcess
 */
export function resolveBusinessEventProcess(
    processId: string
): Promise<BusinessEventProcess> {
    return apiJson<BusinessEventProcess>(`/processes/${processId}/resolve`, { method: 'POST' });
}

/**
 * Attach events to a business event process.
 * @param processId - Process ID
 * @param request - AttachEventsRequest with event_ids list
 * @returns Promise containing the updated BusinessEventProcess
 */
export function attachEventsToProcess(
    processId: string,
    request: AttachEventsRequest
): Promise<BusinessEventProcess> {
    return apiJson<BusinessEventProcess>(`/processes/${processId}/attach`, { method: 'POST', body: request });
}

/**
 * Detach events from a business event process.
 * @param processId - Process ID
 * @param request - DetachEventsRequest with event_ids list
 * @returns Promise containing the updated BusinessEventProcess
 */
export function detachEventsFromProcess(
    processId: string,
    request: DetachEventsRequest
): Promise<BusinessEventProcess> {
    return apiJson<BusinessEventProcess>(`/processes/${processId}/detach`, { method: 'POST', body: request });
}

export async function reconcileDbt(): Promise<ReconciliationResult> {
    const fallback: ReconciliationResult = { status: 'success', changed: false };
    try {
        const result = await apiJson<ReconciliationResult>('/reconcile', {
            method: 'POST',
            notFound: fallback,
            errorMessage: 'Failed to reconcile models',
        });
        return {
            status: result.status,
            changed: result.changed,
        };
    } catch (e) {
        console.error('Error reconciling models:', e);
        return fallback;
    }
}

/**
 * Metric Tree API functions
 */

/**
 * Fetch the metric tree document.
 * @returns Promise containing the tree plus the semantic-model catalog
 */
export function getMetricTree(): Promise<MetricTreeResponse> {
    return apiJson<MetricTreeResponse>('/metric-tree', { errorMessage: 'Failed to fetch metric tree' });
}

/**
 * Save the metric tree document.
 * @param payload - version, metrics and influences to persist
 * @returns Promise containing the status and any validation warnings
 */
export function saveMetricTree(
    payload: MetricTreeFile
): Promise<{ status: string; warnings: string[] }> {
    return apiJson('/metric-tree', {
        method: 'POST',
        body: payload,
        errorMessage: 'Failed to save metric tree',
    });
}
