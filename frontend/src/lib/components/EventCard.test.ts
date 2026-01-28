import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/svelte';
import EventCard from './EventCard.svelte';
import type { BusinessEvent, BusinessEventProcess } from '$lib/types';

describe('EventCard', () => {
    beforeEach(() => {
        vi.stubGlobal(
            'fetch',
            vi.fn().mockResolvedValue({
                ok: true,
                json: vi.fn().mockResolvedValue({
                    entities: [],
                    relationships: []
                })
            })
        );
    });

    afterEach(() => {
        cleanup();
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
    });

    const mockEventWith7Ws: BusinessEvent = {
        id: 'evt_20250122_001',
        text: 'customer buys product',
        type: 'discrete',
        domain: 'Sales',
        created_at: '2025-01-22T10:00:00Z',
        updated_at: '2025-01-22T10:00:00Z',
        annotations: {
            who: [{ id: 'ent1', text: 'customer' }],
            what: [{ id: 'ent2', text: 'product' }],
            when: [],
            where: [],
            how: [],
            how_many: [{ id: 'ent3', text: 'quantity' }],
            why: []
        },
        derived_entities: []
    };

    it('shows 7 Ws completion badge with correct count', () => {
        const onEditSevenWs = vi.fn();
        const onGenerateEntities = vi.fn();
        const onDelete = vi.fn();

        render(EventCard, {
            event: mockEventWith7Ws,
            onEditSevenWs,
            onGenerateEntities,
            onDelete
        });

        expect(screen.getByText('3/7')).toBeInTheDocument();
    });

    it('shows green badge when all Ws are filled', () => {
        const onEditSevenWs = vi.fn();
        const onGenerateEntities = vi.fn();
        const onDelete = vi.fn();

        const eventFull: BusinessEvent = {
            ...mockEventWith7Ws,
            annotations: {
                who: [{ id: 'ent1', text: 'customer' }],
                what: [{ id: 'ent2', text: 'product' }],
                when: [{ id: 'ent3', text: '2025-01-22' }],
                where: [{ id: 'ent4', text: 'store' }],
                how: [{ id: 'ent5', text: 'online' }],
                how_many: [{ id: 'ent6', text: 'quantity' }],
                why: [{ id: 'ent7', text: 'campaign' }]
            }
        };

        render(EventCard, {
            event: eventFull,
            onEditSevenWs,
            onGenerateEntities,
            onDelete
        });

        const badge = screen.getByText('7/7');
        expect(badge).toHaveClass('bg-green-100', 'text-green-800');
    });

    it('shows amber badge when partial Ws are filled', () => {
        const onEditSevenWs = vi.fn();
        const onGenerateEntities = vi.fn();
        const onDelete = vi.fn();

        render(EventCard, {
            event: mockEventWith7Ws,
            onEditSevenWs,
            onGenerateEntities,
            onDelete
        });

        const badge = screen.getByText('3/7');
        expect(badge).toHaveClass('bg-amber-100', 'text-amber-800');
    });

    it('shows gray badge when no Ws are filled', () => {
        const onEditSevenWs = vi.fn();
        const onGenerateEntities = vi.fn();
        const onDelete = vi.fn();

        const mockEventEmpty7Ws: BusinessEvent = {
            id: 'evt_20250122_002',
            text: 'event without 7 Ws',
            type: 'discrete',
            domain: undefined,
            created_at: '2025-01-22T10:00:00Z',
            updated_at: '2025-01-22T10:00:00Z',
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
        };

        render(EventCard, {
            event: mockEventEmpty7Ws,
            onEditSevenWs,
            onGenerateEntities,
            onDelete
        });

        const badge = screen.queryByText('0/7');
        expect(badge).not.toBeInTheDocument();
    });

    it('does not render domain or process badges', () => {
        const onEditSevenWs = vi.fn();
        const onGenerateEntities = vi.fn();
        const onDelete = vi.fn();
        const onResolveProcess = vi.fn();

        const process: BusinessEventProcess = {
            id: 'proc_20250122_001',
            name: 'Customer Journey',
            type: 'discrete',
            domain: 'Sales',
            event_ids: [mockEventWith7Ws.id],
            created_at: '2025-01-22T10:00:00Z',
            updated_at: '2025-01-22T10:00:00Z'
        };

        render(EventCard, {
            event: mockEventWith7Ws,
            process,
            onEditSevenWs,
            onGenerateEntities,
            onDelete,
            onResolveProcess
        });

        expect(screen.queryByText('Sales')).not.toBeInTheDocument();
        expect(screen.queryByText(process.name)).not.toBeInTheDocument();
    });
});
