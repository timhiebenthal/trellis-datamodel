import { describe, it, expect } from 'vitest';
import { extractRelativePath, toggleFolderFilter, getModelFolder } from './folder-utils';
import type { ModelInfo } from '$lib/types';

describe('extractRelativePath', () => {
    it('should return empty string for empty input', () => {
        expect(extractRelativePath('')).toBe('');
    });

    it('should return empty string for path without segments', () => {
        expect(extractRelativePath('models')).toBe('');
    });

    it('should extract relative path for nested folders', () => {
        expect(extractRelativePath('models/staging/customers')).toBe('staging/customers');
    });

    it('should extract relative path for single nested folder', () => {
        expect(extractRelativePath('models/staging')).toBe('staging');
    });

    it('should handle deeply nested paths', () => {
        expect(extractRelativePath('dbt_project/models/intermediate/staging/customers')).toBe('models/intermediate/staging/customers');
    });

    it('should return original path if no separator found', () => {
        expect(extractRelativePath('models')).toBe('');
    });
});

describe('toggleFolderFilter', () => {
    it('should add folder to empty filter array', () => {
        const result = toggleFolderFilter([], 'staging/customers');
        expect(result).toEqual(['staging/customers']);
    });

    it('should add folder to existing filter array', () => {
        const result = toggleFolderFilter(['staging/orders'], 'staging/customers');
        expect(result).toEqual(['staging/orders', 'staging/customers']);
    });

    it('should remove folder if already present', () => {
        const result = toggleFolderFilter(['staging/customers'], 'staging/customers');
        expect(result).toEqual([]);
    });

    it('should remove folder from array with multiple items', () => {
        const result = toggleFolderFilter(['staging/orders', 'staging/customers'], 'staging/orders');
        expect(result).toEqual(['staging/customers']);
    });

    it('should handle undefined or null currentFilters', () => {
        expect(toggleFolderFilter(undefined as unknown as string[], 'staging/customers')).toEqual(['staging/customers']);
        expect(toggleFolderFilter(null as unknown as string[], 'staging/customers')).toEqual(['staging/customers']);
    });

    it('should handle non-array currentFilters gracefully', () => {
        expect(toggleFolderFilter('not-an-array' as unknown as string[], 'staging/customers')).toEqual(['staging/customers']);
    });

    it('should not create duplicates', () => {
        const result = toggleFolderFilter(['staging/customers'], 'staging/customers');
        expect(result).toEqual([]);
        
        const addedAgain = toggleFolderFilter(result, 'staging/customers');
        expect(addedAgain).toEqual(['staging/customers']);
    });
});

describe('getModelFolder', () => {
    const createModel = (file_path: string): ModelInfo => ({
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

    it('returns the full folder path below models', () => {
        expect(getModelFolder(createModel('models/3_core/all/users.sql'))).toBe('3_core/all');
        expect(getModelFolder(createModel('models/2_int/staging/stg_users.sql'))).toBe('2_int/staging');
    });

    it('returns nested subfolders joined', () => {
        expect(getModelFolder(createModel('models/3_core/finance/reporting/revenue.sql'))).toBe('3_core/finance/reporting');
    });

    it('returns the top-level folder when the file is directly inside it', () => {
        expect(getModelFolder(createModel('models/1_stg/raw.sql'))).toBe('1_stg');
    });

    it('returns null for a file directly under models', () => {
        expect(getModelFolder(createModel('models/raw.sql'))).toBeNull();
    });

    it('handles Windows-style backslashes', () => {
        expect(getModelFolder(createModel('models\\3_core\\all\\users.sql'))).toBe('3_core/all');
    });

    it('handles paths without models/ prefix', () => {
        expect(getModelFolder(createModel('3_core/all/test.sql'))).toBe('3_core/all');
    });

    it('handles absolute paths containing a models segment', () => {
        expect(getModelFolder(createModel('/workspace/project/models/3-entity/dim_account.sql'))).toBe('3-entity');
    });

    it('strips a leading Bruin assets segment', () => {
        expect(getModelFolder(createModel('assets/02_core/dim__customer.sql'))).toBe('02_core');
        expect(getModelFolder(createModel('assets/00_ingest/raw__page_views.asset.yml'))).toBe('00_ingest');
    });

    it('keeps nested folders below a Bruin assets segment', () => {
        expect(getModelFolder(createModel('assets/a/b/x.sql'))).toBe('a/b');
    });

    it('returns null for a Bruin asset directly under assets', () => {
        expect(getModelFolder(createModel('assets/x.sql'))).toBeNull();
    });

    it('does not strip an assets folder below dbt models', () => {
        expect(getModelFolder(createModel('models/assets/x.sql'))).toBe('assets');
    });
});
