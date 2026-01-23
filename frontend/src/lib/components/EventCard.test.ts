import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen } from '@testing-library/svelte';
import '@testing-library/jest-dom';
import EventCard from './EventCard.svelte';
import type { BusinessEvent, BusinessEventSevenWs } from '$lib/types';

describe('EventCard', () => {
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
        seven_ws: {
            who: [{ id: 'ent1', text: 'customer' }],
            what: [{ id: 'ent2', text: 'product' }],
            when: [],
            where: [],
            how: [],
            how_many: [{ id: 'ent3', text: 'quantity' }],
            why: []
        },
        annotations: [],
        derived_entities: []
    };

    it('shows 7 Ws completion badge with correct count', () => {
        const onAnnotate = vi.fn();
        const onGenerateEntities = vi.fn();

        render(EventCard, {
            event: mockEventWith7Ws,
            onAnnotate,
            onGenerateEntities
        });

        expect(screen.getByText('3/7 Ws')).toBeInTheDocument();
    });

    it('shows green badge when all Ws are filled', () => {
        const onAnnotate = vi.fn();
        const onGenerateEntities = vi.fn();

        const eventFull: BusinessEvent = {
            ...mockEventWith7Ws,
            seven_ws: {
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
            onAnnotate,
            onGenerateEntities
        });

        const badge = screen.getByText('7/7 Ws');
        expect(badge).toHaveClass('bg-green-100', 'text-green-800');
    });

    it('shows amber badge when partial Ws are filled', () => {
        const onAnnotate = vi.fn();
        const onGenerateEntities = vi.fn();

        render(EventCard, {
            event: mockEventWith7Ws,
            onAnnotate,
            onGenerateEntities
        });

        const badge = screen.getByText('3/7 Ws');
        expect(badge).toHaveClass('bg-amber-100', 'text-amber-800');
    });

    it('shows gray badge when no Ws are filled', () => {
        const onAnnotate = vi.fn();
        const onGenerateEntities = vi.fn();

        const mockEventEmpty7Ws: BusinessEvent = {
            id: 'evt_20250122_002',
            text: 'event without 7 Ws',
            type: 'discrete',
            domain: null,
            created_at: '2025-01-22T10:00:00Z',
            updated_at: '2025-01-22T10:00:00Z',
            seven_ws: {
                who: [],
                what: [],
                when: [],
                where: [],
                how: [],
                how_many: [],
                why: []
            },
            annotations: [],
            derived_entities: []
        };

        render(EventCard, {
            event: mockEventEmpty7Ws,
            onAnnotate,
            onGenerateEntities
        });

        const badge = screen.getByText('0/7 Ws');
        expect(badge).toHaveClass('bg-gray-100', 'text-gray-800');
    });

    it('shows domain badge when domain exists', () => {
        const onAnnotate = vi.fn();
        const onGenerateEntities = vi.fn();

        render(EventCard, {
            event: mockEventWith7Ws,
            onAnnotate,
            onGenerateEntities
        });

        expect(screen.getByText('Sales')).toBeInTheDocument();
    });

    it('does not show domain badge when domain is null', () => {
        const onAnnotate = vi.fn();
        const onGenerateEntities = vi.fn();

        const mockEventNoDomain: BusinessEvent = {
            ...mockEventWith7Ws,
            domain: null
        };

        render(EventCard, {
            event: mockEventNoDomain,
            onAnnotate,
            onGenerateEntities
        });

        expect(screen.queryByText(/domain/i)).not.toBeInTheDocument();
    });
});
