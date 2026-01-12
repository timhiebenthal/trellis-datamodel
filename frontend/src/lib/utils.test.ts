import { describe, it, expect } from 'vitest';
import { getParallelOffset, generateSlug, getModelFolder, detectFieldSemantics, stripEntityPrefixes, formatModelNameForLabel } from './utils';
import type { DbtModel, ModelSchema } from './types';

describe('getParallelOffset', () => {
    it('returns 0 for index 0 (center)', () => {
        expect(getParallelOffset(0)).toBe(0);
    });

    it('returns positive offset for odd indices (above)', () => {
        expect(getParallelOffset(1)).toBe(20);
        expect(getParallelOffset(3)).toBe(40);
        expect(getParallelOffset(5)).toBe(60);
    });

    it('returns negative offset for even indices > 0 (below)', () => {
        expect(getParallelOffset(2)).toBe(-20);
        expect(getParallelOffset(4)).toBe(-40);
        expect(getParallelOffset(6)).toBe(-60);
    });

    it('alternates correctly: 0, +20, -20, +40, -40, ...', () => {
        const offsets = [0, 1, 2, 3, 4, 5, 6].map(getParallelOffset);
        expect(offsets).toEqual([0, 20, -20, 40, -40, 60, -60]);
    });
});

describe('generateSlug', () => {
    it('converts label to lowercase slug', () => {
        expect(generateSlug('My Entity', [])).toBe('my_entity');
    });

    it('replaces special characters with underscores', () => {
        expect(generateSlug('Hello@World!', [])).toBe('hello_world');
    });

    it('trims leading and trailing underscores', () => {
        expect(generateSlug('  Test  ', [])).toBe('test');
        expect(generateSlug('___test___', [])).toBe('test');
    });

    it('returns "entity" for empty or special-char-only input', () => {
        expect(generateSlug('', [])).toBe('entity');
        expect(generateSlug('@#$%', [])).toBe('entity');
        expect(generateSlug('   ', [])).toBe('entity');
    });

    it('ensures uniqueness by appending counter', () => {
        const existingIds = ['users', 'orders'];
        expect(generateSlug('Users', existingIds)).toBe('users_1');
        expect(generateSlug('Orders', existingIds)).toBe('orders_1');
    });

    it('increments counter until unique', () => {
        const existingIds = ['test', 'test_1', 'test_2'];
        expect(generateSlug('Test', existingIds)).toBe('test_3');
    });

    it('excludes currentId when checking uniqueness (for renaming)', () => {
        const existingIds = ['users', 'orders'];
        // When renaming 'users' to 'Users', slug should stay 'users'
        expect(generateSlug('Users', existingIds, 'users')).toBe('users');
    });

    it('handles complex labels correctly', () => {
        expect(generateSlug('User Profile (v2)', [])).toBe('user_profile_v2');
        expect(generateSlug('Data-Model_123', [])).toBe('data_model_123');
    });
});

describe('getModelFolder', () => {
    const createModel = (file_path: string): DbtModel => ({
        unique_id: 'model.project.test',
        name: 'test',
        schema: 'public',
        table: 'test',
        columns: [],
        file_path,
    });

    it('returns null for empty file_path', () => {
        expect(getModelFolder(createModel(''))).toBeNull();
        expect(getModelFolder({ ...createModel(''), file_path: undefined } as any)).toBeNull();
    });

    it('returns subfolder after models/ and main folder', () => {
        expect(getModelFolder(createModel('models/3_core/all/users.sql'))).toBe('all');
        expect(getModelFolder(createModel('models/2_int/staging/stg_users.sql'))).toBe('staging');
    });

    it('returns nested subfolders joined', () => {
        expect(getModelFolder(createModel('models/3_core/finance/reporting/revenue.sql'))).toBe('finance/reporting');
    });

    it('returns null when no subfolder exists (file directly in main folder)', () => {
        expect(getModelFolder(createModel('models/1_stg/raw.sql'))).toBeNull();
    });

    it('handles Windows-style backslashes', () => {
        expect(getModelFolder(createModel('models\\3_core\\all\\users.sql'))).toBe('all');
    });

    it('handles paths without models/ prefix', () => {
        // When there's no "models" prefix, it still skips the first folder
        expect(getModelFolder(createModel('3_core/all/test.sql'))).toBe('all');
    });
});

describe('detectFieldSemantics', () => {
    const createSchema = (modelName: string, columns: Array<{ name: string; data_tests?: any[] }>): ModelSchema => ({
        model_name: modelName,
        description: '',
        columns: columns.map(col => ({
            name: col.name,
            data_tests: col.data_tests,
        })),
        file_path: `models/${modelName}.yml`,
    });

    it('detects FK when field has relationship test', () => {
        const schemas = new Map<string, ModelSchema>();
        schemas.set('orders', createSchema('orders', [
            {
                name: 'user_id',
                data_tests: [{
                    relationships: {
                        arguments: {
                            to: "ref('users')",
                            field: 'id',
                        },
                    },
                }],
            },
        ]));

        const result = detectFieldSemantics('orders', 'user_id', 'users', schemas);
        expect(result).toBe('fk');
    });

    it('detects PK when field is referenced by other model', () => {
        const schemas = new Map<string, ModelSchema>();
        schemas.set('users', createSchema('users', [
            { name: 'id' },
        ]));
        schemas.set('orders', createSchema('orders', [
            {
                name: 'user_id',
                data_tests: [{
                    relationships: {
                        arguments: {
                            to: "ref('users')",
                            field: 'id',
                        },
                    },
                }],
            },
        ]));

        const result = detectFieldSemantics('users', 'id', 'orders', schemas);
        expect(result).toBe('pk');
    });

    it('detects PK with legacy test format (no arguments block)', () => {
        const schemas = new Map<string, ModelSchema>();
        schemas.set('users', createSchema('users', [
            { name: 'id' },
        ]));
        schemas.set('orders', createSchema('orders', [
            {
                name: 'user_id',
                data_tests: [{
                    relationships: {
                        to: "ref('users')",
                        field: 'id',
                    },
                }],
            },
        ]));

        const result = detectFieldSemantics('users', 'id', 'orders', schemas);
        expect(result).toBe('pk');
    });

    it('returns unknown when field has no relationship test and is not referenced', () => {
        const schemas = new Map<string, ModelSchema>();
        schemas.set('users', createSchema('users', [
            { name: 'id' },
            { name: 'name' },
        ]));
        schemas.set('orders', createSchema('orders', [
            { name: 'user_id' },
        ]));

        const result = detectFieldSemantics('users', 'name', 'orders', schemas);
        expect(result).toBe('unknown');
    });

    it('returns unknown when schema is missing', () => {
        const schemas = new Map<string, ModelSchema>();

        const result = detectFieldSemantics('users', 'id', 'orders', schemas);
        expect(result).toBe('unknown');
    });

    it('returns unknown when field is missing from schema', () => {
        const schemas = new Map<string, ModelSchema>();
        schemas.set('users', createSchema('users', [
            { name: 'id' },
        ]));

        const result = detectFieldSemantics('users', 'nonexistent', 'orders', schemas);
        expect(result).toBe('unknown');
    });

    it('returns unknown when other model schema is missing (for PK detection)', () => {
        const schemas = new Map<string, ModelSchema>();
        schemas.set('users', createSchema('users', [
            { name: 'id' },
        ]));

        const result = detectFieldSemantics('users', 'id', 'orders', schemas);
        expect(result).toBe('unknown');
    });

    it('handles multiple relationship tests correctly', () => {
        const schemas = new Map<string, ModelSchema>();
        schemas.set('orders', createSchema('orders', [
            {
                name: 'user_id',
                data_tests: [
                    {
                        relationships: {
                            arguments: {
                                to: "ref('users')",
                                field: 'id',
                            },
                        },
                    },
                    {
                        not_null: {},
                    },
                ],
            },
        ]));

        const result = detectFieldSemantics('orders', 'user_id', 'users', schemas);
        expect(result).toBe('fk');
    });
});

// ===== Entity Prefix Tests (Stream L) =====

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

    it('handles complex model names with prefixes', () => {
        expect(formatModelNameForLabel('tbl_customer_order_details', ['tbl_'])).toBe('Customer Order Details');
        expect(formatModelNameForLabel('entity_user_profile_v2', ['entity_'])).toBe('User Profile V2');
    });
});
