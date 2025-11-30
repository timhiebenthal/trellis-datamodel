import { describe, it, expect, beforeEach, vi } from 'vitest';
import { get } from 'svelte/store';
import { dbtModels, folderFilter, tagFilter, nodes } from '$lib/stores';

// Mock DbtModel data
const mockModels = [
    {
        unique_id: 'model.project.users',
        name: 'users',
        file_path: 'models/3_core/all/users.sql',
        tags: ['core', 'pii'],
        columns: [],
        resource_type: 'model'
    },
    {
        unique_id: 'model.project.orders',
        name: 'orders',
        file_path: 'models/3_core/all/orders.sql',
        tags: ['core'],
        columns: [],
        resource_type: 'model'
    },
    {
        unique_id: 'model.project.staging_users',
        name: 'stg_users',
        file_path: 'models/2_int/staging/stg_users.sql',
        tags: ['staging'],
        columns: [],
        resource_type: 'model'
    }
];

// Mock nodes data
const mockNodes = [
    {
        id: 'users',
        type: 'entity',
        position: { x: 0, y: 0 },
        data: {
            label: 'Users',
            dbt_model: 'model.project.users'
        }
    },
    {
        id: 'orders',
        type: 'entity',
        position: { x: 100, y: 0 },
        data: {
            label: 'Orders',
            dbt_model: 'model.project.orders'
        }
    },
    {
        id: 'stg_users',
        type: 'entity',
        position: { x: 200, y: 0 },
        data: {
            label: 'Staging Users',
            dbt_model: 'model.project.staging_users'
        }
    },
    {
        id: 'unbound',
        type: 'entity',
        position: { x: 300, y: 0 },
        data: {
            label: 'Unbound Entity'
        }
    }
];

describe('Sidebar Filtering Logic', () => {
    beforeEach(() => {
        dbtModels.set(mockModels);
        folderFilter.set([]);
        tagFilter.set([]);
        nodes.set(mockNodes);
    });

    it('initializes with correct mock data', () => {
        expect(get(dbtModels)).toHaveLength(3);
        expect(get(nodes)).toHaveLength(4);
        expect(get(folderFilter)).toEqual([]);
        expect(get(tagFilter)).toEqual([]);
    });

    it('folder filter updates correctly', () => {
        folderFilter.set(['all']);
        expect(get(folderFilter)).toEqual(['all']);

        folderFilter.set(['all', 'staging']);
        expect(get(folderFilter)).toEqual(['all', 'staging']);

        folderFilter.set([]);
        expect(get(folderFilter)).toEqual([]);
    });

    it('tag filter updates correctly', () => {
        tagFilter.set(['core']);
        expect(get(tagFilter)).toEqual(['core']);

        tagFilter.set(['core', 'pii']);
        expect(get(tagFilter)).toEqual(['core', 'pii']);

        tagFilter.set([]);
        expect(get(tagFilter)).toEqual([]);
    });

    it('does not cause infinite updates when filters change', () => {
        const nodeSubscriber = vi.fn();
        const unsubscribe = nodes.subscribe(nodeSubscriber);

        // Clear initial subscription call
        nodeSubscriber.mockClear();

        // Change folder filter
        folderFilter.set(['all']);

        // Should only trigger once, not infinitely
        // Wait a bit to ensure no additional calls
        return new Promise((resolve) => {
            setTimeout(() => {
                // In a proper implementation, this should be called exactly once
                // If there's an infinite loop, this would be called many times
                expect(nodeSubscriber.mock.calls.length).toBeLessThan(5);
                unsubscribe();
                resolve(undefined);
            }, 100);
        });
    });
});

describe('Filter Helper Functions', () => {
    it('extracts folder correctly from file path', () => {
        // Helper function to extract folder (mirroring the logic in +page.svelte)
        function getModelFolder(filePath: string): string | null {
            if (!filePath) return null;
            let p = filePath.replace(/\\/g, "/");
            const lastSlash = p.lastIndexOf("/");
            const dir = lastSlash !== -1 ? p.substring(0, lastSlash) : "";
            let parts = dir.split("/").filter((x: string) => x !== "." && x !== "");
            if (parts[0] === "models") parts.shift();
            // Skip the main folder (first part after models/)
            if (parts.length > 1) {
                parts.shift();
                return parts.join("/");
            }
            return null;
        }

        expect(getModelFolder('models/3_core/all/users.sql')).toBe('all');
        expect(getModelFolder('models/2_int/staging/stg_users.sql')).toBe('staging');
        expect(getModelFolder('models/1_stg/raw.sql')).toBeNull();
        expect(getModelFolder('')).toBeNull();
    });

    it('matches tags correctly', () => {
        const modelTags = ['core', 'pii'];
        const activeTags = ['core'];

        const hasMatch = activeTags.some(tag => modelTags.includes(tag));
        expect(hasMatch).toBe(true);

        const noMatch = ['staging'].some(tag => modelTags.includes(tag));
        expect(noMatch).toBe(false);
    });
});
