import { describe, it, expect } from 'vitest';
import { getParallelOffset, generateSlug, getModelFolder } from './utils';
import type { DbtModel } from './types';

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
        // When renaming 'users' to 'Users', the slug should stay 'users'
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

