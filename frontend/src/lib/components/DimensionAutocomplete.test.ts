import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/svelte';
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
});
