import type {
    BusinessEvent,
    BusinessEventAnnotations,
    BusinessEventProcess,
    BusinessEventType,
} from '$lib/types';
import { toTitleCase } from '$lib/utils/model-naming';

export const UNASSIGNED_DOMAIN_KEY = 'unassigned';

export type ProcessGroup = {
    process: BusinessEventProcess;
    events: BusinessEvent[];
};

export type DomainGroup = {
    domainKey: string;
    domainLabel: string;
    processes: ProcessGroup[];
    ungroupedEvents: BusinessEvent[];
    totalEvents: number;
};

export type EventFilters = {
    type: BusinessEventType | 'all';
    domain: string | null;
    process: string | null;
};

export function getDomainLabel(domainKey: string): string {
    return domainKey === UNASSIGNED_DOMAIN_KEY ? 'Unassigned' : toTitleCase(domainKey);
}

/** Apply type, domain and process filters (combined). */
export function filterEvents(events: BusinessEvent[], filters: EventFilters): BusinessEvent[] {
    let result = events;

    if (filters.type !== 'all') {
        result = result.filter((event) => event.type === filters.type);
    }

    if (filters.domain !== null) {
        if (filters.domain === 'unassigned') {
            result = result.filter((event) => !event.domain);
        } else {
            result = result.filter((event) => event.domain === filters.domain);
        }
    }

    if (filters.process !== null) {
        if (filters.process === 'ungrouped') {
            result = result.filter((event) => !event.process_id);
        } else {
            result = result.filter((event) => event.process_id === filters.process);
        }
    }

    return result;
}

/**
 * Group events by domain. Process membership uses ALL events (so events in processes
 * stay visible regardless of filters); ungrouped events come from the filtered list.
 */
export function buildDomainGroups(
    allEvents: BusinessEvent[],
    filteredEvents: BusinessEvent[],
    activeProcesses: BusinessEventProcess[]
): DomainGroup[] {
    const processLookup = new Map(activeProcesses.map((proc) => [proc.id, proc]));
    const eventsById = new Map(allEvents.map((event) => [event.id, event]));

    const groupsMap = new Map<string, DomainGroup>();

    function ensureGroup(key: string): DomainGroup {
        const existing = groupsMap.get(key);
        if (existing) return existing;
        const group: DomainGroup = {
            domainKey: key,
            domainLabel: getDomainLabel(key),
            processes: [],
            ungroupedEvents: [],
            totalEvents: 0,
        };
        groupsMap.set(key, group);
        return group;
    }

    activeProcesses.forEach((process) => {
        const domainKey = process.domain ?? UNASSIGNED_DOMAIN_KEY;
        const eventsForProcess = process.event_ids
            .map((eventId) => eventsById.get(eventId))
            .filter((event): event is BusinessEvent => Boolean(event));

        if (eventsForProcess.length === 0) {
            return;
        }
        const group = ensureGroup(domainKey);
        group.processes.push({ process, events: eventsForProcess });
    });

    filteredEvents.forEach((event) => {
        const domainKey = event.domain ?? UNASSIGNED_DOMAIN_KEY;
        if (event.process_id && processLookup.has(event.process_id)) {
            return;
        }
        const group = ensureGroup(domainKey);
        group.ungroupedEvents.push(event);
    });

    return Array.from(groupsMap.values())
        .map((group) => ({
            ...group,
            totalEvents:
                group.ungroupedEvents.length +
                group.processes.reduce((sum, procGroup) => sum + procGroup.events.length, 0),
        }))
        .filter((group) => group.totalEvents > 0)
        .sort((a, b) => a.domainLabel.localeCompare(b.domainLabel));
}

export function createEmptyAnnotations(): BusinessEventAnnotations {
    return {
        who: [],
        what: [],
        when: [],
        where: [],
        how: [],
        how_many: [],
        why: [],
    };
}

/** Represent a process as a pseudo-event so it can be annotated with the 7Ws form. */
export function mapProcessToEvent(process: BusinessEventProcess): BusinessEvent {
    return {
        id: process.id,
        text: process.name,
        description: process.description ?? undefined,
        type: process.type,
        domain: process.domain ?? undefined,
        created_at: process.created_at,
        updated_at: process.updated_at,
        annotations: process.annotations_superset ?? createEmptyAnnotations(),
        derived_entities: [],
    };
}

export function reorderIds(ids: string[], fromId: string, toId: string): string[] {
    const fromIndex = ids.indexOf(fromId);
    const toIndex = ids.indexOf(toId);
    if (fromIndex === -1 || toIndex === -1 || fromIndex === toIndex) {
        return ids;
    }
    const next = [...ids];
    const [moved] = next.splice(fromIndex, 1);
    next.splice(toIndex, 0, moved);
    return next;
}

export type ProcessRemovalPlan = { kind: 'update'; eventIds: string[] } | { kind: 'resolve' };

/** Removing the last event from a process resolves it; otherwise its event list shrinks. */
export function planEventRemoval(process: BusinessEventProcess, eventId: string): ProcessRemovalPlan {
    const eventIds = process.event_ids.filter((id) => id !== eventId);
    return eventIds.length > 0 ? { kind: 'update', eventIds } : { kind: 'resolve' };
}

export function buildProcessCanvasUrl(process: BusinessEventProcess, derivedIds?: string[]): string {
    const params: string[] = [];
    if (derivedIds && derivedIds.length > 0) {
        const entityParam = derivedIds.map(encodeURIComponent).join(',');
        params.push(`entities=${entityParam}`);
    }
    params.push(`processId=${encodeURIComponent(process.id)}`);
    params.push(`processName=${encodeURIComponent(process.name)}`);
    return `/canvas?${params.join('&')}`;
}

/** Map a failed events load/reload to a user-facing message. */
export function describeEventsLoadError(e: unknown, fallback: string): string {
    const errorMessage = e instanceof Error ? e.message : String(e);
    const statusCode = (e as any)?.status;

    if (statusCode === 403 || errorMessage.includes('403') || errorMessage.includes('feature_disabled') || errorMessage.includes('disabled')) {
        return 'Business events feature is disabled. Enable it in trellis.yml by setting business_events.enabled: true';
    }
    if (statusCode === 400 || errorMessage.includes('400') || errorMessage.includes('configuration')) {
        return 'Configuration error. Please check your trellis.yml file.';
    }
    if (statusCode === 404 || errorMessage.includes('404') || errorMessage.includes('not found')) {
        return 'Business events file not found. Create your first event to get started.';
    }
    if (statusCode === 500 || errorMessage.includes('500') || errorMessage.includes('parse') || errorMessage.includes('YAML')) {
        return 'Invalid business events file format. Please check the file or contact support.';
    }
    return fallback;
}

/** Map a failed annotation save to a user-facing message. */
export function describeAnnotationSaveError(e: unknown): string {
    const errorMessage = e instanceof Error ? e.message : 'Failed to save annotations';
    if (errorMessage.includes('annotation_type') || errorMessage.includes('Invalid annotation_type')) {
        return 'Invalid annotation category. Please check your entries.';
    }
    if (errorMessage.includes('Duplicate entry IDs') || errorMessage.includes('duplicate')) {
        return 'Duplicate entries detected. Please check for duplicate entries.';
    }
    if (errorMessage.includes('400') || errorMessage.includes('validation')) {
        return 'Invalid annotation data. Please check your entries.';
    }
    return errorMessage;
}
