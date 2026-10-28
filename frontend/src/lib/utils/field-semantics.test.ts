import { describe, it, expect } from 'vitest';
import { detectFieldSemantics } from './field-semantics';
import type { ModelSchema } from '$lib/types';

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
