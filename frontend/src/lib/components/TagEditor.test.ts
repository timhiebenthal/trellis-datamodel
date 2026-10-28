import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup, fireEvent, waitFor } from '@testing-library/svelte';
import TagEditor from './TagEditor.svelte';

describe('TagEditor Component', () => {
    const mockOnUpdate = vi.fn();

    beforeEach(() => {
        mockOnUpdate.mockClear();
    });

    afterEach(() => cleanup());

    function renderEditor(props: {
        tags?: string[];
        readOnlyTags?: string[];
        canEdit?: boolean;
        isBatchMode?: boolean;
    } = {}) {
        return render(TagEditor, {
            props: {
                tags: [],
                canEdit: true,
                isBatchMode: false,
                onUpdate: mockOnUpdate,
                ...props,
            },
        });
    }

    const addButton = () => screen.getByRole('button', { name: 'Add new tag' });
    const removeButtons = () => screen.queryAllByRole('button', { name: /^Remove .* tag/ });

    async function openInput() {
        await fireEvent.click(addButton());
        return (await screen.findByRole('textbox', { name: 'Add new tag' })) as HTMLInputElement;
    }

    describe('Initial Rendering', () => {
        it('renders only the add button when no tags are provided', () => {
            renderEditor({ tags: [] });

            expect(removeButtons()).toHaveLength(0);
            expect(addButton()).toBeInTheDocument();
        });

        it('renders every provided tag', () => {
            renderEditor({ tags: ['core', 'pii', 'staging'] });

            expect(screen.getByText('core')).toBeInTheDocument();
            expect(screen.getByText('pii')).toBeInTheDocument();
            expect(screen.getByText('staging')).toBeInTheDocument();
            expect(removeButtons()).toHaveLength(3);
        });

        it('normalizes tags (trims, removes duplicates, removes empty, keeps case)', () => {
            renderEditor({ tags: ['  core  ', '  ', 'core', 'staging', '', 'PII'] });

            // getByText throws on duplicates, so this also proves 'core' is rendered once
            expect(screen.getByText('core')).toBeInTheDocument();
            expect(screen.getByText('staging')).toBeInTheDocument();
            expect(screen.getByText('PII')).toBeInTheDocument();
            expect(removeButtons()).toHaveLength(3);
        });

        it('hides add button and remove buttons when canEdit is false', () => {
            renderEditor({ tags: ['core'], canEdit: false });

            expect(screen.getByText('core')).toBeInTheDocument();
            expect(removeButtons()).toHaveLength(0);
            expect(screen.queryByRole('button', { name: 'Add new tag' })).not.toBeInTheDocument();
        });

        it('shows the add button when canEdit is true', () => {
            renderEditor();

            expect(addButton()).toBeInTheDocument();
        });

        it('gives read-only tags no remove button while other tags stay removable', () => {
            renderEditor({ tags: ['nightly', 'pii'], readOnlyTags: ['nightly'] });

            expect(screen.getByText('nightly')).toBeInTheDocument();
            expect(screen.queryByRole('button', { name: 'Remove nightly tag' })).not.toBeInTheDocument();
            expect(screen.getByRole('button', { name: 'Remove pii tag' })).toBeInTheDocument();
        });
    });

    describe('Add Tag Functionality', () => {
        it('adds tag when pressing Enter', async () => {
            renderEditor();
            const input = await openInput();

            await fireEvent.input(input, { target: { value: 'core' } });
            await fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

            expect(mockOnUpdate).toHaveBeenCalledTimes(1);
            expect(mockOnUpdate).toHaveBeenCalledWith(['core']);
        });

        it('appends to existing tags when a comma is typed', async () => {
            renderEditor({ tags: ['existing'] });
            const input = await openInput();

            await fireEvent.input(input, { target: { value: 'core' } });
            await fireEvent.keyDown(input, { key: ',', code: 'Comma' });

            expect(mockOnUpdate).toHaveBeenCalledTimes(1);
            expect(mockOnUpdate).toHaveBeenCalledWith(['existing', 'core']);
        });

        it('trims whitespace when adding tags', async () => {
            renderEditor();
            const input = await openInput();

            await fireEvent.input(input, { target: { value: '  core  ' } });
            await fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

            expect(mockOnUpdate).toHaveBeenCalledWith(['core']);
        });

        it('does not add empty tags', async () => {
            renderEditor();
            const input = await openInput();

            await fireEvent.input(input, { target: { value: '   ' } });
            await fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

            expect(mockOnUpdate).not.toHaveBeenCalled();
        });

        it('does not add duplicate tags', async () => {
            renderEditor({ tags: ['core'] });
            const input = await openInput();

            await fireEvent.input(input, { target: { value: 'core' } });
            await fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

            expect(mockOnUpdate).not.toHaveBeenCalled();
        });

        it('clears input after adding tag', async () => {
            renderEditor();
            const input = await openInput();

            await fireEvent.input(input, { target: { value: 'core' } });
            await fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

            await waitFor(() => expect(input).toHaveValue(''));
        });

        it('adds the pending text as a tag when the input loses focus', async () => {
            renderEditor();
            const input = await openInput();

            await fireEvent.input(input, { target: { value: 'pii' } });
            await fireEvent.blur(input);

            expect(mockOnUpdate).toHaveBeenCalledWith(['pii']);
            expect(screen.queryByRole('textbox', { name: 'Add new tag' })).not.toBeInTheDocument();
        });
    });

    describe('Remove Tag Functionality', () => {
        it('removes only the clicked tag', async () => {
            renderEditor({ tags: ['core', 'staging'] });

            await fireEvent.click(screen.getByRole('button', { name: 'Remove core tag' }));

            expect(mockOnUpdate).toHaveBeenCalledTimes(1);
            expect(mockOnUpdate).toHaveBeenCalledWith(['staging']);
        });
    });

    describe('Keyboard Shortcuts', () => {
        it('closes the input and discards its text when Escape is pressed', async () => {
            renderEditor();
            const input = await openInput();

            await fireEvent.input(input, { target: { value: 'draft' } });
            await fireEvent.keyDown(input, { key: 'Escape', code: 'Escape' });

            await waitFor(() => {
                expect(screen.queryByRole('textbox', { name: 'Add new tag' })).not.toBeInTheDocument();
            });
            expect(addButton()).toBeInTheDocument();
            expect(mockOnUpdate).not.toHaveBeenCalled();
        });
    });

    describe('Batch Mode', () => {
        it('shows batch-specific placeholder and remove labels in batch mode', async () => {
            renderEditor({ tags: ['core'], isBatchMode: true });

            expect(
                screen.getByRole('button', { name: 'Remove core tag from all selected' }),
            ).toBeInTheDocument();

            await openInput();
            expect(screen.getByPlaceholderText(/all selected/)).toBeInTheDocument();
        });

        it('shows regular placeholder when not in batch mode', async () => {
            renderEditor({ tags: ['core'] });

            expect(screen.getByRole('button', { name: 'Remove core tag' })).toBeInTheDocument();

            await openInput();
            const placeholder = screen.getByPlaceholderText(/Enter tag/);
            expect(placeholder.getAttribute('placeholder')).not.toContain('all selected');
        });
    });
});
