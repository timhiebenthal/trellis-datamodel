import { describe, it, expect } from 'vitest';
import type { BusinessEvent, BusinessEventProcess } from '$lib/types';
import {
    buildDomainGroups,
    buildProcessCanvasUrl,
    createEmptyAnnotations,
    describeAnnotationSaveError,
    describeEventsLoadError,
    filterEvents,
    getDomainLabel,
    mapProcessToEvent,
    planEventRemoval,
    reorderIds,
} from './business-events';

const ev = (id: string, extra: Partial<BusinessEvent> = {}): BusinessEvent =>
    ({
        id,
        text: id,
        type: 'discrete',
        created_at: '',
        updated_at: '',
        annotations: createEmptyAnnotations(),
        derived_entities: [],
        ...extra,
    }) as BusinessEvent;

const proc = (id: string, event_ids: string[], extra: Partial<BusinessEventProcess> = {}): BusinessEventProcess =>
    ({
        id,
        name: `Process ${id}`,
        type: 'evolving',
        event_ids,
        created_at: 'c',
        updated_at: 'u',
        ...extra,
    }) as BusinessEventProcess;

describe('filterEvents', () => {
    const events = [
        ev('a', { domain: 'sales', process_id: 'p1' }),
        ev('b', { domain: 'ops', type: 'evolving' }),
        ev('c'),
    ];

    it('returns everything without filters', () => {
        expect(filterEvents(events, { type: 'all', domain: null, process: null })).toHaveLength(3);
    });

    it('filters by type, domain and process', () => {
        expect(filterEvents(events, { type: 'evolving', domain: null, process: null }).map((e) => e.id)).toEqual(['b']);
        expect(filterEvents(events, { type: 'all', domain: 'sales', process: null }).map((e) => e.id)).toEqual(['a']);
        expect(filterEvents(events, { type: 'all', domain: null, process: 'p1' }).map((e) => e.id)).toEqual(['a']);
    });

    it('supports the unassigned and ungrouped sentinels', () => {
        expect(filterEvents(events, { type: 'all', domain: 'unassigned', process: null }).map((e) => e.id)).toEqual(['c']);
        expect(filterEvents(events, { type: 'all', domain: null, process: 'ungrouped' }).map((e) => e.id)).toEqual(['b', 'c']);
    });
});

describe('buildDomainGroups', () => {
    it('groups processes and ungrouped events by domain and sorts by label', () => {
        const events = [
            ev('a', { domain: 'sales', process_id: 'p1' }),
            ev('b', { domain: 'sales', process_id: 'p1' }),
            ev('c', { domain: 'ops' }),
            ev('d'),
        ];
        const p1 = proc('p1', ['a', 'b'], { domain: 'sales' });
        const groups = buildDomainGroups(events, events, [p1]);
        expect(groups.map((g) => g.domainKey)).toEqual(['ops', 'sales', 'unassigned']);
        const sales = groups.find((g) => g.domainKey === 'sales')!;
        expect(sales.processes).toHaveLength(1);
        expect(sales.ungroupedEvents).toHaveLength(0);
        expect(sales.totalEvents).toBe(2);
        expect(groups.find((g) => g.domainKey === 'unassigned')!.domainLabel).toBe('Unassigned');
    });

    it('keeps process events visible when filters exclude them', () => {
        const events = [ev('a', { domain: 'sales', process_id: 'p1' }), ev('c', { domain: 'ops' })];
        const p1 = proc('p1', ['a'], { domain: 'sales' });
        const groups = buildDomainGroups(events, [events[1]], [p1]);
        expect(groups.map((g) => g.domainKey)).toEqual(['ops', 'sales']);
    });

    it('skips processes with no known events', () => {
        expect(buildDomainGroups([], [], [proc('p1', ['missing'])])).toEqual([]);
    });
});

describe('process helpers', () => {
    it('getDomainLabel title-cases keys', () => {
        expect(getDomainLabel('unassigned')).toBe('Unassigned');
        expect(getDomainLabel('order_to_cash')).not.toBe('order_to_cash');
    });

    it('mapProcessToEvent falls back to empty annotations', () => {
        const mapped = mapProcessToEvent(proc('p1', [], { description: 'd' }));
        expect(mapped).toMatchObject({ id: 'p1', text: 'Process p1', description: 'd', derived_entities: [] });
        expect(mapped.annotations).toEqual(createEmptyAnnotations());
    });

    it('reorderIds moves an id and ignores invalid moves', () => {
        expect(reorderIds(['a', 'b', 'c'], 'a', 'c')).toEqual(['b', 'c', 'a']);
        const ids = ['a', 'b'];
        expect(reorderIds(ids, 'a', 'a')).toBe(ids);
        expect(reorderIds(ids, 'x', 'a')).toBe(ids);
    });

    it('planEventRemoval resolves the process when the last event leaves', () => {
        expect(planEventRemoval(proc('p', ['a', 'b']), 'a')).toEqual({ kind: 'update', eventIds: ['b'] });
        expect(planEventRemoval(proc('p', ['a']), 'a')).toEqual({ kind: 'resolve' });
    });

    it('buildProcessCanvasUrl encodes params', () => {
        expect(buildProcessCanvasUrl(proc('p 1', []), ['x/y', 'z'])).toBe(
            '/canvas?entities=x%2Fy,z&processId=p%201&processName=Process%20p%201'
        );
        expect(buildProcessCanvasUrl(proc('p1', []))).toBe('/canvas?processId=p1&processName=Process%20p1');
    });
});

describe('error descriptions', () => {
    it('maps load errors by status or message and falls back', () => {
        expect(describeEventsLoadError(Object.assign(new Error('x'), { status: 403 }), 'fb')).toMatch(/disabled/);
        expect(describeEventsLoadError(new Error('bad configuration'), 'fb')).toMatch(/Configuration error/);
        expect(describeEventsLoadError(new Error('404'), 'fb')).toMatch(/not found/);
        expect(describeEventsLoadError(new Error('YAML broke'), 'fb')).toMatch(/Invalid business events/);
        expect(describeEventsLoadError(new Error('boom'), 'fb')).toBe('fb');
    });

    it('maps annotation save errors', () => {
        expect(describeAnnotationSaveError(new Error('Invalid annotation_type'))).toMatch(/annotation category/);
        expect(describeAnnotationSaveError(new Error('duplicate'))).toMatch(/Duplicate/);
        expect(describeAnnotationSaveError(new Error('400 bad'))).toMatch(/Invalid annotation data/);
        expect(describeAnnotationSaveError(new Error('other'))).toBe('other');
        expect(describeAnnotationSaveError('str')).toBe('Failed to save annotations');
    });
});
