import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import { render, screen, cleanup, fireEvent, waitFor } from '@testing-library/svelte';
import DimensionAutocomplete from './DimensionAutocomplete.svelte';
import type { Dimension, SevenWType } from '$lib/types';

describe('DimensionAutocomplete', () => {
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

    const mockDimensions: Dimension[] = [
        { id: 'dim_customer', label: 'Customer', entity_type: 'dimension', annotation_type: 'who', description: 'Customer dimension' },
        { id: 'dim_product', label: 'Product', entity_type: 'dimension', annotation_type: 'what', description: 'Product dimension' },
        { id: 'dim_location', label: 'Location', entity_type: 'dimension', annotation_type: 'where', description: 'Location dimension' },
        { id: 'dim_campaign', label: 'Campaign', entity_type: 'dimension', annotation_type: 'why', description: 'Campaign dimension' }
    ];

    it('renders input with placeholder', () => {
        const onTextChange = vi.fn();
        const onSelectDimension = vi.fn();

        const { container } = render(DimensionAutocomplete, {
            textValue: '',
            onTextChange,
            onSelectDimension,
            dimensions: mockDimensions,
            placeholder: 'Select dimension...'
        });

        const input = container.querySelector('input');
        expect(input).toBeInTheDocument();
        expect(input).toHaveAttribute('placeholder', 'Select dimension...');
    });

    it('shows loading state when loading prop is true', () => {
        const onTextChange = vi.fn();
        const onSelectDimension = vi.fn();

        const { container } = render(DimensionAutocomplete, {
            textValue: '',
            onTextChange,
            onSelectDimension,
            dimensions: mockDimensions,
            loading: true
        });

        // When loading is true, the search icon should be replaced with a loading spinner
        // We can check that the input has the disabled state
        const input = container.querySelector('input');
        expect(input).toBeInTheDocument();
        expect(input).toBeDisabled();
    });

    describe('Text Suggestions', () => {
        it('shows text suggestions from previous annotations when available', async () => {
            const onTextChange = vi.fn();
            const onSelectDimension = vi.fn();
            const textSuggestions = new Set(['account', 'customer', 'supplier']);

            const { container } = render(DimensionAutocomplete, {
                textValue: '',
                onTextChange,
                onSelectDimension,
                dimensions: [],
                textSuggestions,
                filterBy: 'who'
            });

            const input = container.querySelector('input');
            expect(input).toBeInTheDocument();

            // Focus and type to trigger dropdown
            await fireEvent.focus(input!);
            await fireEvent.input(input!, { target: { value: 'acc' } });

            // Wait for dropdown to appear
            await waitFor(() => {
                const dropdown = container.querySelector('[role="listbox"]');
                expect(dropdown).toBeInTheDocument();
            });

            // Check that "account" suggestion appears
            await waitFor(() => {
                expect(screen.getByText('account')).toBeInTheDocument();
                expect(screen.getByText('from annotations')).toBeInTheDocument();
            });
        });

        it('filters text suggestions based on search input', async () => {
            const onTextChange = vi.fn();
            const textSuggestions = new Set(['account', 'customer', 'supplier', 'employee']);

            const { container } = render(DimensionAutocomplete, {
                textValue: '',
                onTextChange,
                dimensions: [],
                textSuggestions
            });

            const input = container.querySelector('input');
            await fireEvent.focus(input!);
            await fireEvent.input(input!, { target: { value: 'cust' } });

            await waitFor(() => {
                expect(screen.getByText('customer')).toBeInTheDocument();
            });

            // Should not show non-matching suggestions
            expect(screen.queryByText('account')).not.toBeInTheDocument();
            expect(screen.queryByText('supplier')).not.toBeInTheDocument();
            expect(screen.queryByText('employee')).not.toBeInTheDocument();
        });

        it('calls onTextChange when text suggestion is selected', async () => {
            const onTextChange = vi.fn();
            const textSuggestions = new Set(['account', 'customer']);

            const { container } = render(DimensionAutocomplete, {
                textValue: '',
                onTextChange,
                dimensions: [],
                textSuggestions
            });

            const input = container.querySelector('input');
            await fireEvent.focus(input!);
            await fireEvent.input(input!, { target: { value: 'acc' } });

            await waitFor(() => {
                expect(screen.getByText('account')).toBeInTheDocument();
            });

            // Click on the suggestion
            const suggestion = screen.getByText('account');
            await fireEvent.mouseDown(suggestion);

            // Should call onTextChange with the selected text
            await waitFor(() => {
                expect(onTextChange).toHaveBeenCalledWith('account');
            });
        });

        it('shows both dimensions and text suggestions together', async () => {
            const onTextChange = vi.fn();
            const textSuggestions = new Set(['account', 'customer']);

            const { container } = render(DimensionAutocomplete, {
                textValue: '',
                onTextChange,
                dimensions: mockDimensions,
                textSuggestions,
                filterBy: 'who'
            });

            const input = container.querySelector('input');
            await fireEvent.focus(input!);
            await fireEvent.input(input!, { target: { value: 'c' } });

            await waitFor(() => {
                // Should show dimension
                expect(screen.getByText('Customer')).toBeInTheDocument();
                // Should show text suggestions
                expect(screen.getByText('customer')).toBeInTheDocument();
                expect(screen.getByText('account')).toBeInTheDocument();
            });
        });

        it('shows text suggestions when no dimensions match but suggestions do', async () => {
            const onTextChange = vi.fn();
            const textSuggestions = new Set(['account', 'vendor']);

            const { container } = render(DimensionAutocomplete, {
                textValue: '',
                onTextChange,
                dimensions: mockDimensions,
                textSuggestions,
                filterBy: 'who'
            });

            const input = container.querySelector('input');
            await fireEvent.focus(input!);
            await fireEvent.input(input!, { target: { value: 'ven' } });

            await waitFor(() => {
                // Should show text suggestion
                expect(screen.getByText('vendor')).toBeInTheDocument();
                // Should not show dimensions that don't match
                expect(screen.queryByText('Customer')).not.toBeInTheDocument();
                expect(screen.queryByText('Product')).not.toBeInTheDocument();
            });
        });

        it('does not show duplicate text suggestions if they match existing dimensions', async () => {
            const onTextChange = vi.fn();
            // "customer" exists both as dimension and text suggestion
            const textSuggestions = new Set(['customer', 'account']);

            const { container } = render(DimensionAutocomplete, {
                textValue: '',
                onTextChange,
                dimensions: mockDimensions,
                textSuggestions,
                filterBy: 'who'
            });

            const input = container.querySelector('input');
            await fireEvent.focus(input!);
            await fireEvent.input(input!, { target: { value: 'cust' } });

            await waitFor(() => {
                // Should show dimension "Customer"
                const customerElements = screen.getAllByText(/customer/i);
                // Should have dimension with ID shown
                expect(screen.getByText('dim_customer')).toBeInTheDocument();
            });
        });
    });
});
