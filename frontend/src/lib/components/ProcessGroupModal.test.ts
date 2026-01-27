import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import { render, screen, cleanup, fireEvent, waitFor } from '@testing-library/svelte';
import ProcessGroupModal from './ProcessGroupModal.svelte';

const DOMAIN_SUGGESTIONS = ['Sales'];

describe('ProcessGroupModal', () => {
    beforeEach(() => {
        vi.stubGlobal(
            'fetch',
            vi.fn().mockResolvedValue({
                ok: true,
                json: vi.fn().mockResolvedValue({
                    id: 'proc_20260127_001',
                    name: 'Test Process',
                    type: 'discrete',
                    event_ids: ['evt_001', 'evt_002'],
                    created_at: '2026-01-27T10:00:00Z',
                    updated_at: '2026-01-27T10:00:00Z'
                })
            })
        );
    });

    afterEach(() => {
        cleanup();
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
    });

    it('renders modal when open is true', () => {
        const onSave = vi.fn();
        const onCancel = vi.fn();

        render(ProcessGroupModal, {
            open: true,
            eventIds: ['evt_001', 'evt_002'],
            domains: DOMAIN_SUGGESTIONS,
            onSave,
            onCancel
        });

        expect(screen.getByText(/group into process/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/process name/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/process type/i)).toBeInTheDocument();
    });

    it('does not render modal when open is false', () => {
        const onSave = vi.fn();
        const onCancel = vi.fn();

        render(ProcessGroupModal, {
            open: false,
            eventIds: ['evt_001', 'evt_002'],
            domains: DOMAIN_SUGGESTIONS,
            onSave,
            onCancel
        });

        expect(screen.queryByText(/group into process/i)).not.toBeInTheDocument();
    });

    it('shows event count in info banner', () => {
        const onSave = vi.fn();
        const onCancel = vi.fn();

        render(ProcessGroupModal, {
            open: true,
            eventIds: ['evt_001', 'evt_002', 'evt_003'],
            domains: DOMAIN_SUGGESTIONS,
            onSave,
            onCancel
        });

        expect(screen.getByText(/grouping 3 events/i)).toBeInTheDocument();
    });

    it('shows singular form for single event', () => {
        const onSave = vi.fn();
        const onCancel = vi.fn();

        render(ProcessGroupModal, {
            open: true,
            eventIds: ['evt_001'],
            domains: DOMAIN_SUGGESTIONS,
            onSave,
            onCancel
        });

        expect(screen.getByText(/grouping 1 event/i)).toBeInTheDocument();
    });

    it('validates process name is required', () => {
        const onSave = vi.fn();
        const onCancel = vi.fn();

        render(ProcessGroupModal, {
            open: true,
            eventIds: ['evt_001', 'evt_002'],
            domains: DOMAIN_SUGGESTIONS,
            onSave,
            onCancel
        });

        const createButton = screen.getByRole('button', { name: /create process/i });
        expect(createButton).toBeDisabled();
    });

    it('enables create button when name is provided and at least 2 events', async () => {
        const onSave = vi.fn();
        const onCancel = vi.fn();

        render(ProcessGroupModal, {
            open: true,
            eventIds: ['evt_001', 'evt_002'],
            domains: DOMAIN_SUGGESTIONS,
            onSave,
            onCancel
        });

        const nameInput = screen.getByLabelText(/process name/i);
        await fireEvent.input(nameInput, { target: { value: 'Test Process' } });
        const domainInput = screen.getByLabelText(/process domain/i);
        await fireEvent.input(domainInput, { target: { value: 'Sales' } });

        const createButton = screen.getByRole('button', { name: /create process/i });
        await waitFor(() => {
            expect(createButton).not.toBeDisabled();
        });
    });

    it('requires a domain before enabling the create button', async () => {
        const onSave = vi.fn();
        const onCancel = vi.fn();

        render(ProcessGroupModal, {
            open: true,
            eventIds: ['evt_001', 'evt_002'],
            domains: DOMAIN_SUGGESTIONS,
            onSave,
            onCancel
        });

        const nameInput = screen.getByLabelText(/process name/i);
        await fireEvent.input(nameInput, { target: { value: 'Test Process' } });

        const createButton = screen.getByRole('button', { name: /create process/i });
        expect(createButton).toBeDisabled();

        const domainInput = screen.getByLabelText(/process domain/i);
        await fireEvent.input(domainInput, { target: { value: 'Sales' } });

        await waitFor(() => {
            expect(createButton).not.toBeDisabled();
        });
    });

    it('disables create button when less than 2 events', () => {
        const onSave = vi.fn();
        const onCancel = vi.fn();

        render(ProcessGroupModal, {
            open: true,
            eventIds: ['evt_001'],
            domains: DOMAIN_SUGGESTIONS,
            onSave,
            onCancel
        });

        const nameInput = screen.getByLabelText(/process name/i);
        fireEvent.input(nameInput, { target: { value: 'Test Process' } });
        const domainInput = screen.getByLabelText(/process domain/i);
        fireEvent.input(domainInput, { target: { value: 'Sales' } });

        const createButton = screen.getByRole('button', { name: /create process/i });
        expect(createButton).toBeDisabled();
    });

    it('shows character count for process name', () => {
        const onSave = vi.fn();
        const onCancel = vi.fn();

        render(ProcessGroupModal, {
            open: true,
            eventIds: ['evt_001', 'evt_002'],
            domains: DOMAIN_SUGGESTIONS,
            onSave,
            onCancel
        });

        expect(screen.getByText(/characters remaining/i)).toBeInTheDocument();
    });

    it('calls onCancel when cancel button is clicked', async () => {
        const onSave = vi.fn();
        const onCancel = vi.fn();

        render(ProcessGroupModal, {
            open: true,
            eventIds: ['evt_001', 'evt_002'],
            domains: DOMAIN_SUGGESTIONS,
            onSave,
            onCancel
        });

        const cancelButton = screen.getByRole('button', { name: /cancel/i });
        await fireEvent.click(cancelButton);

        expect(onCancel).toHaveBeenCalledTimes(1);
    });

    it('calls onCancel when backdrop is clicked', async () => {
        const onSave = vi.fn();
        const onCancel = vi.fn();

        const { container } = render(ProcessGroupModal, {
            open: true,
            eventIds: ['evt_001', 'evt_002'],
            domains: DOMAIN_SUGGESTIONS,
            onSave,
            onCancel
        });

        const backdrop = container.querySelector('.fixed.inset-0');
        if (backdrop) {
            await fireEvent.click(backdrop);
            expect(onCancel).toHaveBeenCalledTimes(1);
        }
    });

    it('calls onSave with correct data when form is submitted', async () => {
        const onSave = vi.fn();
        const onCancel = vi.fn();

        render(ProcessGroupModal, {
            open: true,
            eventIds: ['evt_001', 'evt_002'],
            domains: DOMAIN_SUGGESTIONS,
            onSave,
            onCancel
        });

        const nameInput = screen.getByLabelText(/process name/i);
        await fireEvent.input(nameInput, { target: { value: 'Test Process' } });
        const domainInput = screen.getByLabelText(/process domain/i);
        await fireEvent.input(domainInput, { target: { value: 'Sales' } });

        const createButton = screen.getByRole('button', { name: /create process/i });
        await waitFor(() => {
            expect(createButton).not.toBeDisabled();
        });

        await fireEvent.click(createButton);

        await waitFor(() => {
            expect(global.fetch).toHaveBeenCalledWith(
                expect.stringContaining('/api/processes'),
                expect.objectContaining({
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: 'Test Process',
                        type: 'discrete',
                        domain: 'Sales',
                        event_ids: ['evt_001', 'evt_002']
                    })
                })
            );
        });

        await waitFor(() => {
            expect(onSave).toHaveBeenCalledTimes(1);
        });
    });

    it('shows error message when API call fails', async () => {
        vi.stubGlobal(
            'fetch',
            vi.fn().mockResolvedValue({
                ok: false,
                json: vi.fn().mockResolvedValue({ detail: 'Events not found' })
            })
        );

        const onSave = vi.fn();
        const onCancel = vi.fn();

        render(ProcessGroupModal, {
            open: true,
            eventIds: ['evt_001', 'evt_002'],
            domains: DOMAIN_SUGGESTIONS,
            onSave,
            onCancel
        });

        const nameInput = screen.getByLabelText(/process name/i);
        await fireEvent.input(nameInput, { target: { value: 'Test Process' } });
        const domainInput = screen.getByLabelText(/process domain/i);
        await fireEvent.input(domainInput, { target: { value: 'Sales' } });

        const createButton = screen.getByRole('button', { name: /create process/i });
        await waitFor(() => {
            expect(createButton).not.toBeDisabled();
        });

        await fireEvent.click(createButton);

        await waitFor(() => {
            expect(screen.getByText(/events not found/i)).toBeInTheDocument();
        });
    });

    it('allows selecting different process types', () => {
        const onSave = vi.fn();
        const onCancel = vi.fn();

        render(ProcessGroupModal, {
            open: true,
            eventIds: ['evt_001', 'evt_002'],
            domains: DOMAIN_SUGGESTIONS,
            onSave,
            onCancel
        });

        const typeSelect = screen.getByLabelText(/process type/i);
        expect(typeSelect).toBeInTheDocument();
        expect(typeSelect).toHaveValue('discrete');

        // Check all options are present
        const options = screen.getAllByRole('option');
        const optionValues = options.map(opt => (opt as HTMLOptionElement).value);
        expect(optionValues).toContain('discrete');
        expect(optionValues).toContain('evolving');
        expect(optionValues).toContain('recurring');
    });
});
