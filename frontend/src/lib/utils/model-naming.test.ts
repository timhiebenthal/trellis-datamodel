import { describe, it, expect } from 'vitest';
import { stripEntityPrefixes, formatModelNameForLabel, shouldAutoSyncGeneratedEntityLabel } from './model-naming';

describe('stripEntityPrefixes', () => {
    it('handles empty prefix array gracefully', () => {
        expect(stripEntityPrefixes('tbl_customer', [])).toBe('tbl_customer');
        expect(stripEntityPrefixes('customer', [])).toBe('customer');
    });

    it('handles undefined/null prefix array gracefully', () => {
        expect(stripEntityPrefixes('tbl_customer', undefined as any)).toBe('tbl_customer');
        expect(stripEntityPrefixes('customer', null as any)).toBe('customer');
    });

    it('handles undefined/null label gracefully', () => {
        expect(stripEntityPrefixes(undefined as any, ['tbl_'])).toBe(undefined as any);
        expect(stripEntityPrefixes(null as any, ['tbl_'])).toBe(null as any);
        expect(stripEntityPrefixes('', ['tbl_'])).toBe('');
    });

    it('strips single prefix from label', () => {
        expect(stripEntityPrefixes('tbl_customer', ['tbl_'])).toBe('customer');
        expect(stripEntityPrefixes('entity_user', ['entity_'])).toBe('user');
        expect(stripEntityPrefixes('t_order', ['t_'])).toBe('order');
    });

    it('strips first matching prefix when multiple prefixes configured', () => {
        expect(stripEntityPrefixes('tbl_customer', ['tbl_', 'entity_', 't_'])).toBe('customer');
        expect(stripEntityPrefixes('entity_user', ['tbl_', 'entity_', 't_'])).toBe('user');
        expect(stripEntityPrefixes('t_order', ['tbl_', 'entity_', 't_'])).toBe('order');
    });

    it('performs case-insensitive matching', () => {
        expect(stripEntityPrefixes('TBL_CUSTOMER', ['tbl_'])).toBe('CUSTOMER');
        expect(stripEntityPrefixes('TBL_customer', ['tbl_'])).toBe('customer');
        expect(stripEntityPrefixes('TBL_CUSTOMER', ['TBL_'])).toBe('CUSTOMER');
        expect(stripEntityPrefixes('tbl_Customer', ['TBL_'])).toBe('Customer');
    });

    it('handles edge case: label equals prefix', () => {
        // Implementation returns original label to avoid empty UI elements
        expect(stripEntityPrefixes('tbl_', ['tbl_'])).toBe('tbl_');
        expect(stripEntityPrefixes('entity_', ['entity_'])).toBe('entity_');
        expect(stripEntityPrefixes('TBL_', ['tbl_'])).toBe('TBL_');
    });

    it('returns original label when no prefix matches', () => {
        expect(stripEntityPrefixes('customer', ['tbl_', 'entity_'])).toBe('customer');
        expect(stripEntityPrefixes('user', ['tbl_', 'entity_', 't_'])).toBe('user');
        expect(stripEntityPrefixes('my_table', ['tbl_'])).toBe('my_table');
    });

    it('handles nested prefixes (only strips first match)', () => {
        expect(stripEntityPrefixes('tbl_tbl_customer', ['tbl_'])).toBe('tbl_customer');
        expect(stripEntityPrefixes('entity_entity_user', ['entity_'])).toBe('entity_user');
    });

    it('preserves original casing of remaining text', () => {
        expect(stripEntityPrefixes('tbl_CuStoMeR', ['tbl_'])).toBe('CuStoMeR');
        expect(stripEntityPrefixes('ENTITY_USER', ['entity_'])).toBe('USER');
        expect(stripEntityPrefixes('T_ORDER', ['t_'])).toBe('ORDER');
    });
});

describe('formatModelNameForLabel with entity prefixes', () => {
    it('strips single prefix from model name', () => {
        expect(formatModelNameForLabel('tbl_customer', ['tbl_'])).toBe('Customer');
        expect(formatModelNameForLabel('entity_user', ['entity_'])).toBe('User');
    });

    it('strips first matching prefix when multiple configured', () => {
        expect(formatModelNameForLabel('tbl_customer', ['tbl_', 'entity_'])).toBe('Customer');
        expect(formatModelNameForLabel('entity_user', ['tbl_', 'entity_'])).toBe('User');
        expect(formatModelNameForLabel('t_order', ['tbl_', 'entity_', 't_'])).toBe('Order');
    });

    it('handles case-insensitive prefix matching', () => {
        expect(formatModelNameForLabel('TBL_CUSTOMER', ['tbl_'])).toBe('Customer');
        expect(formatModelNameForLabel('tbl_User', ['tbl_'])).toBe('User');
    });

    it('applies title case formatting after stripping prefix', () => {
        expect(formatModelNameForLabel('tbl_customer_name', ['tbl_'])).toBe('Customer Name');
        expect(formatModelNameForLabel('entity_user_id', ['entity_'])).toBe('User Id');
        expect(formatModelNameForLabel('t_order_line_item', ['t_'])).toBe('Order Line Item');
    });

    it('maintains backward compatibility when prefixes parameter omitted', () => {
        expect(formatModelNameForLabel('tbl_customer')).toBe('Tbl Customer');
        expect(formatModelNameForLabel('customer_name')).toBe('Customer Name');
        expect(formatModelNameForLabel('user_id')).toBe('User Id');
    });

    it('handles edge case: label equals prefix', () => {
        // Implementation returns original label to avoid empty UI elements
        // After toTitleCase conversion, trailing underscores become spaces
        expect(formatModelNameForLabel('tbl_', ['tbl_'])).toBe('Tbl ');
        expect(formatModelNameForLabel('entity_', ['entity_'])).toBe('Entity ');
    });

    it('formats names whose prefix is not configured, or that have none', () => {
        expect(formatModelNameForLabel('entity_booking', ['tbl_'])).toBe('Entity Booking');
        expect(formatModelNameForLabel('customer', ['tbl_'])).toBe('Customer');
        expect(formatModelNameForLabel('API_key', [])).toBe('Api Key');
    });

    it('handles complex model names with prefixes', () => {
        expect(formatModelNameForLabel('tbl_customer_order_details', ['tbl_'])).toBe('Customer Order Details');
        expect(formatModelNameForLabel('entity_user_profile_v2', ['entity_'])).toBe('User Profile V2');
    });
});

describe('formatModelNameForLabel with dimensional prefixes', () => {
    const prefixes = ['dim_', 'd_', 'fct_', 'fact_'];

    it('strips dimension prefixes before formatting', () => {
        expect(formatModelNameForLabel('dim_customer', prefixes)).toBe('Customer');
        expect(formatModelNameForLabel('d_order_detail', prefixes)).toBe('Order Detail');
    });

    it('strips fact prefixes before formatting', () => {
        expect(formatModelNameForLabel('fct_sales', prefixes)).toBe('Sales');
        expect(formatModelNameForLabel('fact_transactions', prefixes)).toBe('Transactions');
    });
});

describe('shouldAutoSyncGeneratedEntityLabel', () => {
    const prefixes = ['dim__', 'fact__', 'dim_', 'fact_'];

    it('returns true when the current label is empty', () => {
        expect(
            shouldAutoSyncGeneratedEntityLabel('fact__lead_gen_funnel', '', 'Acquire Process', prefixes)
        ).toBe(true);
    });

    it('returns true when the current label still matches the original generated label', () => {
        expect(
            shouldAutoSyncGeneratedEntityLabel(
                'fact__acquire_lead_generation_qualification_for_is_fs',
                'Acquire (lead Generation & Qualification For Is & Fs)',
                'Acquire (lead Generation & Qualification For Is & Fs)',
                prefixes
            )
        ).toBe(true);
    });

    it('returns true when the current label matches the auto-derived label for the current id', () => {
        expect(
            shouldAutoSyncGeneratedEntityLabel(
                'fact__lead_gen_funnel',
                'Lead Gen Funnel',
                'Acquire (lead Generation & Qualification For Is & Fs)',
                prefixes
            )
        ).toBe(true);
    });

    it('returns false when the label was manually customized', () => {
        expect(
            shouldAutoSyncGeneratedEntityLabel(
                'fact__lead_gen_funnel',
                'Custom KPI Fact',
                'Acquire (lead Generation & Qualification For Is & Fs)',
                prefixes
            )
        ).toBe(false);
    });
});
