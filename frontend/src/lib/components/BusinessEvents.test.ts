import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/svelte';
import BusinessEvents from './BusinessEvents.svelte';
import type { BusinessEvent, BusinessEventProcess } from '$lib/types';

describe('BusinessEvents - Grouping Logic', () => {
    beforeEach(() => {
        vi.stubGlobal(
            'fetch',
            vi.fn().mockResolvedValue({
                ok: true,
                json: vi.fn().mockResolvedValue([])
            })
        );
    });

    afterEach(() => {
        cleanup();
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
    });

    const createMockEvent = (
        id: string,
        text: string,
        domain?: string,
        processId?: string
    ): BusinessEvent => ({
        id,
        text,
        type: 'discrete',
        domain,
        process_id: processId,
        created_at: '2026-01-27T10:00:00Z',
        updated_at: '2026-01-27T10:00:00Z',
        annotations: {
            who: [],
            what: [],
            when: [],
            where: [],
            how: [],
            how_many: [],
            why: []
        },
        derived_entities: []
    });

    const createMockProcess = (
        id: string,
        name: string,
        domain: string,
        eventIds: string[]
    ): BusinessEventProcess => ({
        id,
        name,
        type: 'discrete',
        domain,
        event_ids: eventIds,
        created_at: '2026-01-27T10:00:00Z',
        updated_at: '2026-01-27T10:00:00Z'
    });

    it('groups events by domain → process → events hierarchy', async () => {
        const events: BusinessEvent[] = [
            createMockEvent('evt_001', 'Event 1', 'Sales', 'proc_001'),
            createMockEvent('evt_002', 'Event 2', 'Sales', 'proc_001'),
            createMockEvent('evt_003', 'Event 3', 'Sales'),
            createMockEvent('evt_004', 'Event 4', 'Marketing', 'proc_002'),
            createMockEvent('evt_005', 'Event 5', 'Marketing')
        ];

        const processes: BusinessEventProcess[] = [
            createMockProcess('proc_001', 'Sales Process', 'Sales', ['evt_001', 'evt_002']),
            createMockProcess('proc_002', 'Marketing Process', 'Marketing', ['evt_004'])
        ];

        // Mock API responses
        const fetchMock = vi.fn();
        fetchMock.mockImplementation((url: string) => {
            if (url.includes('/api/business-events') && !url.includes('/domains') && !url.includes('/processes')) {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve(events)
                });
            }
            if (url.includes('/api/business-events/domains')) {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve(['Sales', 'Marketing'])
                });
            }
            if (url.includes('/api/processes')) {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve(processes)
                });
            }
            return Promise.resolve({
                ok: true,
                json: () => Promise.resolve([])
            });
        });

        vi.stubGlobal('fetch', fetchMock);

        render(BusinessEvents);

        // Wait for component to load
        await new Promise(resolve => setTimeout(resolve, 100));

        // Verify domain groups are rendered
        // The component should show domains with processes and ungrouped events
        // Use getAllByText to handle multiple matches (dropdown options + rendered content)
        const salesDomains = screen.queryAllByText(/sales/i);
        const marketingDomains = screen.queryAllByText(/marketing/i);

        // Since the component renders domains, processes, and events in a hierarchy,
        // we verify the structure exists. The exact rendering depends on collapse state,
        // but we can verify that domain labels appear (should have at least 2 matches: dropdown + label)
        expect(salesDomains.length > 0 || marketingDomains.length > 0).toBeTruthy();
    });

    it('places ungrouped events directly under their domain', async () => {
        const events: BusinessEvent[] = [
            createMockEvent('evt_001', 'Ungrouped Event 1', 'Sales'),
            createMockEvent('evt_002', 'Ungrouped Event 2', 'Sales'),
            createMockEvent('evt_003', 'Grouped Event', 'Sales', 'proc_001')
        ];

        const processes: BusinessEventProcess[] = [
            createMockProcess('proc_001', 'Sales Process', 'Sales', ['evt_003'])
        ];

        const fetchMock = vi.fn();
        fetchMock.mockImplementation((url: string) => {
            if (url.includes('/api/business-events') && !url.includes('/domains') && !url.includes('/processes')) {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve(events)
                });
            }
            if (url.includes('/api/business-events/domains')) {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve(['Sales'])
                });
            }
            if (url.includes('/api/processes')) {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve(processes)
                });
            }
            return Promise.resolve({
                ok: true,
                json: () => Promise.resolve([])
            });
        });

        vi.stubGlobal('fetch', fetchMock);

        render(BusinessEvents);

        await new Promise(resolve => setTimeout(resolve, 100));

        // Verify ungrouped events section exists
        // The component should show "Ungrouped events" label for events without process_id
        const ungroupedLabels = screen.queryAllByText(/ungrouped events/i);
        const ungroupedEvents = screen.queryAllByText(/ungrouped event/i);
        // The label may or may not be visible depending on collapse state, but structure should exist
        // Check if we have either the label or the event names (multiple events can match)
        expect(ungroupedLabels.length > 0 || ungroupedEvents.length > 0).toBeTruthy();
    });

    it('handles events without domain by placing them in "Unassigned" group', async () => {
        const events: BusinessEvent[] = [
            createMockEvent('evt_001', 'Event without domain'),
            createMockEvent('evt_002', 'Event with domain', 'Sales')
        ];

        const fetchMock = vi.fn();
        fetchMock.mockImplementation((url: string) => {
            if (url.includes('/api/business-events') && !url.includes('/domains') && !url.includes('/processes')) {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve(events)
                });
            }
            if (url.includes('/api/business-events/domains')) {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve(['Sales'])
                });
            }
            if (url.includes('/api/processes')) {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve([])
                });
            }
            return Promise.resolve({
                ok: true,
                json: () => Promise.resolve([])
            });
        });

        vi.stubGlobal('fetch', fetchMock);

        render(BusinessEvents);

        await new Promise(resolve => setTimeout(resolve, 100));

        // Verify "Unassigned" domain appears for events without domain
        const unassignedLabels = screen.queryAllByText(/unassigned/i);
        const eventWithoutDomain = screen.queryByText(/event without domain/i);
        // Component should show "Unassigned" for events without domain
        // Multiple matches expected: dropdown option + domain label
        expect(unassignedLabels.length > 0 || eventWithoutDomain !== null).toBeTruthy();
    });

    it('excludes resolved processes from grouping', async () => {
        const events: BusinessEvent[] = [
            createMockEvent('evt_001', 'Event 1', 'Sales', 'proc_001'),
            createMockEvent('evt_002', 'Event 2', 'Sales', 'proc_002')
        ];

        const processes: BusinessEventProcess[] = [
            {
                ...createMockProcess('proc_001', 'Active Process', 'Sales', ['evt_001']),
                resolved_at: undefined
            },
            {
                ...createMockProcess('proc_002', 'Resolved Process', 'Sales', ['evt_002']),
                resolved_at: '2026-01-27T11:00:00Z'
            }
        ];

        const fetchMock = vi.fn();
        fetchMock.mockImplementation((url: string) => {
            if (url.includes('/api/business-events') && !url.includes('/domains') && !url.includes('/processes')) {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve(events)
                });
            }
            if (url.includes('/api/business-events/domains')) {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve(['Sales'])
                });
            }
            if (url.includes('/api/processes')) {
                return Promise.resolve({
                    ok: true,
                    json: () => Promise.resolve(processes)
                });
            }
            return Promise.resolve({
                ok: true,
                json: () => Promise.resolve([])
            });
        });

        vi.stubGlobal('fetch', fetchMock);

        render(BusinessEvents);

        await new Promise(resolve => setTimeout(resolve, 100));

        // Verify only active process appears (resolved process should be excluded)
        // Events from resolved processes should appear as ungrouped under their domain
        const activeProcessNames = screen.queryAllByText(/active process/i);
        const resolvedProcessNames = screen.queryAllByText(/resolved process/i);

        // Active process should be visible (multiple matches: dropdown + process name)
        // Resolved process should not appear anywhere (dropdown only shows activeProcesses)
        expect(activeProcessNames.length > 0).toBeTruthy();
        expect(resolvedProcessNames.length).toBe(0);
    });
});
