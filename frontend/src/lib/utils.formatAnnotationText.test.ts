/**
 * Unit Tests for formatAnnotationText Utility
 *
 * Tests the core utility function that formats annotation display text
 * with optional role information for Role-Playing Dimension feature.
 */

import { describe, it, expect } from 'vitest';
import { formatAnnotationText } from '../utils';

describe('formatAnnotationText', () => {
    describe('Basic Functionality', () => {
        it('formats with role as "Dimension (Role)"', () => {
            const result = formatAnnotationText({
                text: 'Date',
                role: 'order_date'
            });
            expect(result).toBe('Date (order_date)');
        });

        it('formats without role as "Dimension"', () => {
            const result = formatAnnotationText({
                text: 'Customer'
            });
            expect(result).toBe('Customer');
        });

        it('formats with undefined role as "Dimension"', () => {
            const result = formatAnnotationText({
                text: 'Product',
                role: undefined
            });
            expect(result).toBe('Product');
        });
    });

    describe('Edge Cases - Empty/Whitespace Roles', () => {
        it('handles empty role string', () => {
            const result = formatAnnotationText({
                text: 'Date',
                role: ''
            });
            expect(result).toBe('Date');
        });

        it('handles whitespace-only role', () => {
            const result = formatAnnotationText({
                text: 'Date',
                role: '   '
            });
            expect(result).toBe('Date');
        });

        it('handles tab and newline characters in role', () => {
            const result = formatAnnotationText({
                text: 'Location',
                role: '\t\n'
            });
            expect(result).toBe('Location');
        });
    });

    describe('Real-World Role Names', () => {
        it('handles snake_case role names', () => {
            const result = formatAnnotationText({
                text: 'Date',
                role: 'order_date'
            });
            expect(result).toBe('Date (order_date)');
        });

        it('handles camelCase role names', () => {
            const result = formatAnnotationText({
                text: 'Date',
                role: 'orderDate'
            });
            expect(result).toBe('Date (orderDate)');
        });

        it('handles PascalCase role names', () => {
            const result = formatAnnotationText({
                text: 'Date',
                role: 'OrderDate'
            });
            expect(result).toBe('Date (OrderDate)');
        });

        it('handles kebab-case role names', () => {
            const result = formatAnnotationText({
                text: 'Date',
                role: 'order-date'
            });
            expect(result).toBe('Date (order-date)');
        });

        it('handles multi-word role names', () => {
            const result = formatAnnotationText({
                text: 'Date',
                role: 'order_placement_date'
            });
            expect(result).toBe('Date (order_placement_date)');
        });
    });

    describe('Role-Playing Dimension Examples', () => {
        it('formats Date dimension with order_date role', () => {
            const result = formatAnnotationText({
                text: 'Date',
                role: 'order_date'
            });
            expect(result).toBe('Date (order_date)');
        });

        it('formats Date dimension with ship_date role', () => {
            const result = formatAnnotationText({
                text: 'Date',
                role: 'ship_date'
            });
            expect(result).toBe('Date (ship_date)');
        });

        it('formats Date dimension with delivery_date role', () => {
            const result = formatAnnotationText({
                text: 'Date',
                role: 'delivery_date'
            });
            expect(result).toBe('Date (delivery_date)');
        });

        it('formats Location dimension with origin role', () => {
            const result = formatAnnotationText({
                text: 'Location',
                role: 'origin'
            });
            expect(result).toBe('Location (origin)');
        });

        it('formats Location dimension with destination role', () => {
            const result = formatAnnotationText({
                text: 'Location',
                role: 'destination'
            });
            expect(result).toBe('Location (destination)');
        });
    });

    describe('Special Characters in Text', () => {
        it('handles dimension text with spaces', () => {
            const result = formatAnnotationText({
                text: 'Order Date',
                role: 'created'
            });
            expect(result).toBe('Order Date (created)');
        });

        it('handles dimension text with numbers', () => {
            const result = formatAnnotationText({
                text: 'Date v2',
                role: 'order_date'
            });
            expect(result).toBe('Date v2 (order_date)');
        });

        it('handles dimension text with parentheses', () => {
            const result = formatAnnotationText({
                text: 'Date (Legacy)',
                role: 'order_date'
            });
            expect(result).toBe('Date (Legacy) (order_date)');
        });
    });

    describe('Special Characters in Role Names', () => {
        it('handles role with underscores', () => {
            const result = formatAnnotationText({
                text: 'Date',
                role: 'order_placement_date'
            });
            expect(result).toBe('Date (order_placement_date)');
        });

        it('handles role with numbers', () => {
            const result = formatAnnotationText({
                text: 'Date',
                role: 'date_v2'
            });
            expect(result).toBe('Date (date_v2)');
        });

        it('handles role with periods', () => {
            const result = formatAnnotationText({
                text: 'Location',
                role: 'location.origin'
            });
            expect(result).toBe('Location (location.origin)');
        });
    });

    describe('Whitespace Handling', () => {
        it('preserves leading whitespace in role (no auto-trim)', () => {
            // Note: formatAnnotationText only uses trim() to check if role is non-empty,
            // but does NOT trim the actual role value in the output
            const result = formatAnnotationText({
                text: 'Date',
                role: '  order_date'
            });
            expect(result).toBe('Date (  order_date)');
        });

        it('preserves trailing whitespace in role (no auto-trim)', () => {
            const result = formatAnnotationText({
                text: 'Date',
                role: 'order_date  '
            });
            expect(result).toBe('Date (order_date  )');
        });

        it('preserves both leading and trailing whitespace', () => {
            const result = formatAnnotationText({
                text: 'Date',
                role: '  order_date  '
            });
            expect(result).toBe('Date (  order_date  )');
        });

        it('preserves internal whitespace in role', () => {
            const result = formatAnnotationText({
                text: 'Date',
                role: 'order placement date'
            });
            expect(result).toBe('Date (order placement date)');
        });
    });

    describe('Long Role Names', () => {
        it('handles very long role names', () => {
            const longRole = 'this_is_a_very_long_role_name_that_exceeds_fifty_characters_easily';
            const result = formatAnnotationText({
                text: 'Date',
                role: longRole
            });
            expect(result).toBe(`Date (${longRole})`);
        });

        it('handles role name with 100 characters', () => {
            const longRole = 'a'.repeat(100);
            const result = formatAnnotationText({
                text: 'Date',
                role: longRole
            });
            expect(result).toBe(`Date (${longRole})`);
        });
    });

    describe('Type Safety', () => {
        it('handles entry with only text property', () => {
            const result = formatAnnotationText({
                text: 'Customer'
            });
            expect(result).toBe('Customer');
        });

        it('handles entry with text and role properties', () => {
            const result = formatAnnotationText({
                text: 'Date',
                role: 'order_date'
            });
            expect(result).toBe('Date (order_date)');
        });
    });

    describe('Consistency Across Annotation Types', () => {
        it('formats consistently for who annotations', () => {
            const result = formatAnnotationText({
                text: 'Person',
                role: 'buyer'
            });
            expect(result).toBe('Person (buyer)');
        });

        it('formats consistently for what annotations', () => {
            const result = formatAnnotationText({
                text: 'Product',
                role: 'main_item'
            });
            expect(result).toBe('Product (main_item)');
        });

        it('formats consistently for when annotations', () => {
            const result = formatAnnotationText({
                text: 'Date',
                role: 'timestamp'
            });
            expect(result).toBe('Date (timestamp)');
        });

        it('formats consistently for where annotations', () => {
            const result = formatAnnotationText({
                text: 'Location',
                role: 'warehouse'
            });
            expect(result).toBe('Location (warehouse)');
        });

        it('formats consistently for how annotations', () => {
            const result = formatAnnotationText({
                text: 'Method',
                role: 'payment'
            });
            expect(result).toBe('Method (payment)');
        });

        it('formats consistently for how_many annotations', () => {
            const result = formatAnnotationText({
                text: 'Metric',
                role: 'quantity'
            });
            expect(result).toBe('Metric (quantity)');
        });

        it('formats consistently for why annotations', () => {
            const result = formatAnnotationText({
                text: 'Reason',
                role: 'campaign'
            });
            expect(result).toBe('Reason (campaign)');
        });
    });
});
