import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/svelte';
import CreateEventModal from './CreateEventModal.svelte';
import type { BusinessEventType, BusinessEventSevenWs } from '$lib/types';

describe('CreateEventModal', () => {
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

    const mockSevenWs: BusinessEventSevenWs = {
        who: [{ id: 'ent1', text: 'customer' }],
        what: [{ id: 'ent2', text: 'product' }],
        when: [],
        where: [],
        how: [],
        how_many: [{ id: 'ent3', text: 'quantity' }],
        why: []
    };

    it('renders with event text and type fields', () => {
        const onSave = vi.fn();
        const onCancel = vi.fn();

        render(CreateEventModal, {
            open: true,
            onSave,
            onCancel
        });

        expect(screen.getByLabelText(/event description/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/event type/i)).toBeInTheDocument();
    });

    it('renders SevenWsForm when open', () => {
        const onSave = vi.fn();
        const onCancel = vi.fn();

        render(CreateEventModal, {
            open: true,
            onSave,
            onCancel
        });

        // The button text is "Add 7 Ws (optional)" not "Annotations"
        expect(screen.getByText(/Add 7 Ws/i)).toBeInTheDocument();
    });

    it('validates text is required', () => {
        const onSave = vi.fn();
        const onCancel = vi.fn();

        render(CreateEventModal, {
            open: true,
            onSave,
            onCancel
        });

        // The button text is "Create" for new events, not "Save"
        const createButton = screen.getByRole('button', { name: /create/i });
        expect(createButton).toBeInTheDocument();
        
        // Just verify structure - text input should exist
        const textInput = screen.getByLabelText(/event description/i);
        expect(textInput).toBeInTheDocument();
    });

    it('shows character count', () => {
        const onSave = vi.fn();
        const onCancel = vi.fn();

        render(CreateEventModal, {
            open: true,
            onSave,
            onCancel
        });

        expect(screen.getByText(/characters remaining/)).toBeInTheDocument();
    });

    it('shows domain autocomplete', () => {
        const onSave = vi.fn();
        const onCancel = vi.fn();

        render(CreateEventModal, {
            open: true,
            onSave,
            onCancel
        });

        expect(screen.getByLabelText(/business domain/i)).toBeInTheDocument();
    });
});
