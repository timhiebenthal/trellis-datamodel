import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import { get } from 'svelte/store';
import { frameworkModels, folderFilter, tagFilter, nodes, activeFramework } from '$lib/stores';
import { FRAMEWORK_DISPLAY_KEYS } from '$lib/utils/framework-display';
import { getModelFolder } from '$lib/utils';
import Sidebar from './Sidebar.svelte';

// Mock DbtModel data
const mockModels = [
    {
        unique_id: 'model.project.users',
        name: 'users',
        schema: 'public',
        table: 'users',
        file_path: 'models/3_core/all/users.sql',
        tags: ['core', 'pii'],
        columns: [],
        resource_type: 'model'
    },
    {
        unique_id: 'model.project.orders',
        name: 'orders',
        schema: 'public',
        table: 'orders',
        file_path: 'models/3_core/all/orders.sql',
        tags: ['core'],
        columns: [],
        resource_type: 'model'
    },
    {
        unique_id: 'model.project.staging_users',
        name: 'stg_users',
        schema: 'public',
        table: 'stg_users',
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
        frameworkModels.set(mockModels);
        folderFilter.set([]);
        tagFilter.set([]);
        nodes.set(mockNodes);
    });

    it('initializes with correct mock data', () => {
        expect(get(frameworkModels)).toHaveLength(3);
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
        // Use the utility function from utils.ts
        const model1 = { file_path: 'models/3_core/all/users.sql' } as any;
        const model2 = { file_path: 'models/2_int/staging/stg_users.sql' } as any;
        const model3 = { file_path: 'models/1_stg/raw.sql' } as any;
        const model4 = { file_path: '' } as any;

        expect(getModelFolder(model1)).toBe('all');
        expect(getModelFolder(model2)).toBe('staging');
        expect(getModelFolder(model3)).toBeNull();
        expect(getModelFolder(model4)).toBeNull();
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

describe('Sidebar — framework-driven header', () => {
    beforeEach(() => {
        frameworkModels.set([]);
        folderFilter.set([]);
        tagFilter.set([]);
        nodes.set([]);
    });

    it('falls back to neutral branding for a framework with no branding of its own', () => {
        // Proves the header is genuinely framework-driven rather than dbt-assumed:
        // an unrecognised framework must not silently render dbt's icon and label.
        activeFramework.set('some-other-framework');
        render(Sidebar, { props: {} });

        expect(document.body.textContent).not.toContain('dbt Models');

        const icon = document.querySelector('img[alt="framework icon"]') as HTMLImageElement | null;
        expect(icon).toBeTruthy();
        expect(icon?.getAttribute('src')).toContain('/icons/framework.svg');
        expect(icon?.getAttribute('src')).not.toContain('getdbt.com');
    });

    it('renders the dbt icon and "dbt Models" label unchanged when framework is "dbt-core"', () => {
        activeFramework.set('dbt-core');
        render(Sidebar, { props: {} });

        expect(document.body.textContent).toContain('dbt Models');

        const icon = document.querySelector('img[alt="dbt icon"]') as HTMLImageElement | null;
        expect(icon).toBeTruthy();
        expect(icon?.getAttribute('src')).toBe('https://www.getdbt.com/favicon.ico');
    });

    it('does not hardcode any framework beyond the one Trellis implements', () => {
        // The display map is scaffolding for future adapters; entries may only be
        // added alongside a working adapter, so it cannot drift into advertising
        // frameworks that raise "unknown framework" at runtime.
        expect(FRAMEWORK_DISPLAY_KEYS).toEqual(['dbt-core']);
    });
});
