import type { BusinessEvent, BusinessEventAnnotations, BusinessEventProcess } from './types';

/** All dimension_id values linked from 7 Ws annotations. */
export function collectDimensionIdsFromAnnotations(
    ann: BusinessEventAnnotations | undefined
): string[] {
    if (!ann) return [];
    const buckets = [ann.who, ann.what, ann.when, ann.where, ann.how, ann.why, ann.how_many];
    const ids: string[] = [];
    for (const bucket of buckets) {
        for (const entry of bucket || []) {
            if (entry.dimension_id) ids.push(entry.dimension_id);
        }
    }
    return ids;
}

/**
 * Entity IDs to show when opening the canvas filtered for one business event:
 * derived entities plus every canvas entity referenced via annotation links.
 */
export function getCanvasFilterEntityIdsForEvent(event: BusinessEvent): string[] {
    const ids = new Set<string>();
    for (const entry of event.derived_entities ?? []) {
        const id = typeof entry === 'string' ? entry : entry.entity_id;
        if (id) ids.add(id);
    }
    for (const id of collectDimensionIdsFromAnnotations(event.annotations)) {
        ids.add(id);
    }
    return Array.from(ids);
}

/** Union of filter IDs for all events in a process group (for fallback when process has no derived_entities). */
export function getCanvasFilterEntityIdsForEvents(events: BusinessEvent[]): string[] {
    const ids = new Set<string>();
    for (const event of events) {
        for (const id of getCanvasFilterEntityIdsForEvent(event)) {
            ids.add(id);
        }
    }
    return Array.from(ids);
}

/**
 * Process-level canvas filter: derived process entities plus dimensions linked in annotations_superset.
 */
export function getCanvasFilterEntityIdsForProcess(process: BusinessEventProcess): string[] {
    const ids = new Set<string>();
    for (const entry of process.derived_entities ?? []) {
        const id = typeof entry === 'string' ? entry : entry.entity_id;
        if (id) ids.add(id);
    }
    for (const id of collectDimensionIdsFromAnnotations(process.annotations_superset)) {
        ids.add(id);
    }
    return Array.from(ids);
}

/** Full set for “view on canvas” from a process group: process + every member event (deduped). */
export function getCanvasFilterEntityIdsForProcessGroup(
    process: BusinessEventProcess,
    memberEvents: BusinessEvent[]
): string[] {
    const ids = new Set<string>();
    for (const id of getCanvasFilterEntityIdsForProcess(process)) ids.add(id);
    for (const id of getCanvasFilterEntityIdsForEvents(memberEvents)) ids.add(id);
    return Array.from(ids);
}
