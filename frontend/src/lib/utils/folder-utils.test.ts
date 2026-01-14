import { describe, it, expect } from 'vitest';
import { extractRelativePath, toggleFolderFilter } from './folder-utils';

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
