export interface ServerTimingMetric {
    name: string;
    duration?: number;
    description?: string;
}

export interface BootPhaseSummary {
    name: string;
    status: 'finished' | 'failed';
    duration: number;
}

export interface BootRequestSummary {
    path: string;
    method: string;
    status?: number;
    bytes?: number;
    duration: number;
}

export interface BootSummary {
    phases: BootPhaseSummary[];
    requests: BootRequestSummary[];
    counts: {
        phases: number;
        requests: number;
    };
}

export interface BootRequest {
    url: string;
    method?: string;
    status?: number;
    bytes?: number;
    duration?: number;
    serverTiming?: string | ServerTimingMetric[];
    [key: string]: unknown;
}

interface BootPhase {
    id: string;
    name: string;
    startMark: string;
    endMark: string;
    startTime: number;
    completed: boolean;
    status?: BootPhaseSummary['status'];
    duration?: number;
}

const phases: BootPhase[] = [];
const requests: BootRequestSummary[] = [];
let phaseSequence = 0;

function currentTime(): number {
    return typeof performance !== 'undefined' ? performance.now() : Date.now();
}

function safePhaseName(name: string): string {
    return name.trim().replace(/[^a-zA-Z0-9_.:-]/g, '-').slice(0, 100);
}

function markPhase(phase: BootPhase, status: BootPhaseSummary['status']): BootPhaseSummary {
    performance.mark(phase.endMark);
    performance.measure(`trellis-boot:${phase.name}:${phase.id}`, {
        start: phase.startMark,
        end: phase.endMark,
    });

    const summary: BootPhaseSummary = {
        name: phase.name,
        status,
        duration: Math.max(0, currentTime() - phase.startTime),
    };
    phase.completed = true;
    phase.status = status;
    phase.duration = summary.duration;
    return summary;
}

export function startBootPhase(name: string): string {
    const phaseName = safePhaseName(name);
    const id = `${phaseName}-${++phaseSequence}`;
    const phase: BootPhase = {
        id,
        name: phaseName,
        startMark: `trellis-boot:${id}:start`,
        endMark: `trellis-boot:${id}:end`,
        startTime: currentTime(),
        completed: false,
    };

    performance.mark(phase.startMark);
    phases.push(phase);
    return id;
}

function finishPhase(phaseId: string, status: BootPhaseSummary['status']): BootPhaseSummary | undefined {
    const phase = phases.find((candidate) => candidate.id === phaseId && !candidate.completed);
    if (!phase) {
        return undefined;
    }

    return markPhase(phase, status);
}

export function finishBootPhase(phaseId: string): BootPhaseSummary | undefined {
    return finishPhase(phaseId, 'finished');
}

export function failBootPhase(phaseId: string, _error?: unknown): BootPhaseSummary | undefined {
    return finishPhase(phaseId, 'failed');
}

function splitServerTiming(header: string): string[] {
    const entries: string[] = [];
    let entry = '';
    let quoted = false;

    for (const character of header) {
        if (character === '"') {
            quoted = !quoted;
        }
        if (character === ',' && !quoted) {
            entries.push(entry);
            entry = '';
        } else {
            entry += character;
        }
    }
    entries.push(entry);
    return entries;
}

export function parseServerTiming(header: string | null | undefined): ServerTimingMetric[] {
    if (!header) {
        return [];
    }

    return splitServerTiming(header)
        .map((entry) => entry.trim())
        .filter(Boolean)
        .map((entry) => {
            const [namePart, ...parameters] = entry.split(';');
            const metric: ServerTimingMetric = { name: namePart.trim() };

            for (const parameter of parameters) {
                const separator = parameter.indexOf('=');
                if (separator === -1) {
                    continue;
                }

                const key = parameter.slice(0, separator).trim().toLowerCase();
                const value = parameter.slice(separator + 1).trim();
                if (key === 'dur') {
                    const duration = Number(value);
                    if (Number.isFinite(duration)) {
                        metric.duration = duration;
                    }
                } else if (key === 'desc') {
                    metric.description = value.replace(/^"(.*)"$/, '$1');
                }
            }

            return metric;
        })
        .filter((metric) => metric.name.length > 0);
}

function requestPath(url: string): string {
    try {
        return new URL(url, typeof location !== 'undefined' ? location.origin : 'http://localhost').pathname;
    } catch {
        return url.split(/[?#]/, 1)[0];
    }
}

function finiteNonNegative(value: unknown): number | undefined {
    return typeof value === 'number' && Number.isFinite(value) && value >= 0 ? value : undefined;
}

export function recordBootRequest(request: BootRequest): BootRequestSummary;
export function recordBootRequest(url: string, request?: Omit<BootRequest, 'url'>): BootRequestSummary;
export function recordBootRequest(
    requestOrUrl: BootRequest | string,
    requestMetadata: Omit<BootRequest, 'url'> = {},
): BootRequestSummary {
    const request: BootRequest =
        typeof requestOrUrl === 'string' ? { ...requestMetadata, url: requestOrUrl } : requestOrUrl;
    const summary: BootRequestSummary = {
        path: requestPath(request.url),
        method: sanitizeMethod(request.method),
        duration: finiteNonNegative(request.duration) ?? 0,
    };

    if (typeof request.status === 'number' && Number.isFinite(request.status)) {
        summary.status = request.status;
    }
    const bytes = finiteNonNegative(request.bytes);
    if (bytes !== undefined) {
        summary.bytes = bytes;
    }

    requests.push(summary);
    return summary;
}

function sanitizeMethod(method: unknown): string {
    if (typeof method !== 'string') {
        return 'GET';
    }
    const normalized = method.trim().toUpperCase();
    return /^[A-Z]+$/.test(normalized) ? normalized : 'GET';
}

function debugEnabled(search?: string): boolean {
    const currentSearch = search ?? (typeof location !== 'undefined' ? location.search : '');
    return new URLSearchParams(currentSearch).get('trellisDebug') === 'boot';
}

function publicPhases(): BootPhaseSummary[] {
    return phases
        .filter((phase) => phase.completed && phase.status !== undefined && phase.duration !== undefined)
        .map((phase) => ({
            name: phase.name,
            status: phase.status as BootPhaseSummary['status'],
            duration: phase.duration as number,
        }));
}

export function emitBootSummary(options?: { search?: string }): BootSummary {
    const summary: BootSummary = {
        phases: publicPhases(),
        requests: requests.map((request) => ({ ...request })),
        counts: {
            phases: phases.filter((phase) => phase.completed).length,
            requests: requests.length,
        },
    };

    if (debugEnabled(options?.search)) {
        console.groupCollapsed('Trellis boot diagnostics');
        console.log(summary);
        console.groupEnd();
    }

    return summary;
}
