import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import EventCard from './EventCard.svelte';
import type { BusinessEvent, BusinessEventSevenWs } from '$lib/types';

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

        expect(screen.getByText('3/7 Ws')).toBeInTheDocument();
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

        const badge = screen.getByText('7/7 Ws');
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

        const badge = screen.getByText('3/7 Ws');
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

        const badge = screen.getByText('0/7 Ws');
        expect(badge).toHaveClass('bg-gray-100', 'text-gray-800');
    });

    it('shows domain badge when domain exists', () => {
        const onEditSevenWs = vi.fn();
        const onGenerateEntities = vi.fn();
        const onDelete = vi.fn();

        render(EventCard, {
            event: mockEventWith7Ws,
            onEditSevenWs,
            onGenerateEntities,
            onDelete
        });

        expect(screen.getByText('Sales')).toBeInTheDocument();
    });

    it('does not show domain badge when domain is null', () => {
        const onEditSevenWs = vi.fn();
        const onGenerateEntities = vi.fn();
        const onDelete = vi.fn();

        const mockEventNoDomain: BusinessEvent = {
            ...mockEventWith7Ws,
            domain: undefined
        };

        render(EventCard, {
            event: mockEventNoDomain,
            onEditSevenWs,
            onGenerateEntities,
            onDelete
        });

        expect(screen.queryByText(/domain/i)).not.toBeInTheDocument();
    });
});
