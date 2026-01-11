import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SchemaManager, type SchemaState } from './schema-manager';

// Mock API functions
vi.mock('$lib/api', () => ({
    getModelSchema: vi.fn(),
    updateModelSchema: vi.fn().mockResolvedValue(undefined),
}));

import { getModelSchema, updateModelSchema } from '$lib/api';

describe('SchemaManager', () => {
    let manager: SchemaManager;
    let onStateChangeMock: ReturnType<typeof vi.fn>;

    beforeEach(() => {
        vi.clearAllMocks();
        onStateChangeMock = vi.fn();
        manager = new SchemaManager(onStateChangeMock);
    });

    describe('constructor', () => {
        it('should initialize with empty state', () => {
            const state = manager.getState();

            expect(state.editableColumns).toEqual([]);
            expect(state.isLoading).toBe(false);
            expect(state.isSaving).toBe(false);
            expect(state.error).toBe(null);
            expect(state.hasUnsavedChanges).toBe(false);
            expect(state.schema).toBe(null);
            expect(state.schemaTags).toEqual([]);
            expect(state.manifestTags).toEqual([]);
            expect(state.displayTags).toEqual([]);
        });

        it('should work without state change callback', () => {
            const noCallbackManager = new SchemaManager();
            const state = noCallbackManager.getState();

            expect(state).toBeDefined();
        });
    });

    describe('getState', () => {
        it('should return a copy of state', () => {
            const state1 = manager.getState();
            const state2 = manager.getState();

            expect(state1).toEqual(state2);
            expect(state1).not.toBe(state2); // Should be a copy, not same reference
        });
    });

    describe('getEditableColumns', () => {
        it('should return copy of editable columns', () => {
            const columns1 = manager.getEditableColumns();
            const columns2 = manager.getEditableColumns();

            expect(columns1).toEqual(columns2);
            expect(columns1).not.toBe(columns2); // Should be a copy
        });
    });

    describe('hasUnsavedChanges', () => {
        it('should return false initially', () => {
            expect(manager.hasUnsavedChanges()).toBe(false);
        });
    });

    describe('isLoading', () => {
        it('should return false initially', () => {
            expect(manager.isLoading()).toBe(false);
        });
    });

    describe('isSaving', () => {
        it('should return false initially', () => {
            expect(manager.isSaving()).toBe(false);
        });
    });

    describe('hasError', () => {
        it('should return false initially', () => {
            expect(manager.hasError()).toBe(false);
        });
    });

    describe('loadSchema', () => {
        it('should set loading state on start', async () => {
            vi.mocked(getModelSchema).mockResolvedValue({
                columns: [],
                tags: [],
            });

            await manager.loadSchema('model1', null);

            const state = manager.getState();
            expect(state.isLoading).toBe(false);
            expect(state.error).toBe(null);
        });

        it('should load schema successfully', async () => {
            const mockSchema = {
                columns: [
                    { name: 'field1', data_type: 'text', description: 'Desc 1' },
                    { name: 'field2', data_type: 'integer', description: 'Desc 2' },
                ],
                tags: ['schema-tag-1', 'schema-tag-2'],
            };

            vi.mocked(getModelSchema).mockResolvedValue(mockSchema);

            await manager.loadSchema('model1', null);

            const state = manager.getState();
            expect(state.schema).toEqual(mockSchema);
            expect(state.isLoading).toBe(false);
            expect(state.error).toBe(null);
            expect(state.editableColumns).toHaveLength(2);
            expect(state.schemaTags).toEqual(['schema-tag-1', 'schema-tag-2']);
        });

        it('should handle manifest tags', async () => {
            const mockSchema = {
                columns: [],
                tags: ['schema-tag'],
            };

            vi.mocked(getModelSchema).mockResolvedValue(mockSchema);

            await manager.loadSchema('model1', null, ['manifest-tag-1', 'manifest-tag-2']);

            const state = manager.getState();
            expect(state.manifestTags).toEqual(['manifest-tag-1', 'manifest-tag-2']);
            expect(state.displayTags).toEqual(['schema-tag', 'manifest-tag-1', 'manifest-tag-2']);
        });

        it('should set hasUnsavedChanges to false on successful load', async () => {
            vi.mocked(getModelSchema).mockResolvedValue({
                columns: [],
                tags: [],
            });

            await manager.loadSchema('model1', null);

            expect(manager.hasUnsavedChanges()).toBe(false);
        });

        it('should use fallback columns when schema has no columns', async () => {
            const mockSchema = {
                columns: [],
                tags: [],
            };

            const fallbackColumns = [
                { name: 'fallback1', type: 'text' },
                { name: 'fallback2', type: 'integer' },
            ];

            vi.mocked(getModelSchema).mockResolvedValue(mockSchema);

            await manager.loadSchema('model1', null, [], fallbackColumns);

            const state = manager.getState();
            expect(state.editableColumns).toHaveLength(2);
            expect(state.editableColumns[0].name).toBe('fallback1');
            expect(state.editableColumns[0].data_type).toBe('text');
            expect(state.editableColumns[1].name).toBe('fallback2');
            expect(state.editableColumns[1].data_type).toBe('integer');
        });

        it('should use fallback columns on error', async () => {
            const error = new Error('Schema not found');
            vi.mocked(getModelSchema).mockRejectedValue(error);

            const fallbackColumns = [
                { name: 'fallback1', type: 'text' },
            ];

            await manager.loadSchema('model1', null, [], fallbackColumns);

            const state = manager.getState();
            expect(state.isLoading).toBe(false);
            expect(state.error).toBe('Schema not found');
            expect(state.schema).toBe(null);
            expect(state.editableColumns).toHaveLength(1);
            expect(state.editableColumns[0].name).toBe('fallback1');
        });

        it('should handle version parameter', async () => {
            vi.mocked(getModelSchema).mockResolvedValue({
                columns: [],
                tags: [],
            });

            await manager.loadSchema('model1', 2);

            expect(getModelSchema).toHaveBeenCalledWith('model1', 2);
        });

        it('should use null version when not provided', async () => {
            vi.mocked(getModelSchema).mockResolvedValue({
                columns: [],
                tags: [],
            });

            await manager.loadSchema('model1', undefined);

            expect(getModelSchema).toHaveBeenCalledWith('model1', undefined);
        });

        it('should merge schema and manifest tags for display', async () => {
            const mockSchema = {
                columns: [],
                tags: ['schema-tag'],
            };

            vi.mocked(getModelSchema).mockResolvedValue(mockSchema);

            await manager.loadSchema('model1', null, ['manifest-tag']);

            const state = manager.getState();
            expect(state.displayTags).toContain('schema-tag');
            expect(state.displayTags).toContain('manifest-tag');
        });

        it('should normalize tags', async () => {
            const mockSchema = {
                columns: [],
                tags: ['  tag1  ', 'tag2', ''], // Includes whitespace and empty string
            };

            vi.mocked(getModelSchema).mockResolvedValue(mockSchema);

            await manager.loadSchema('model1', null);

            const state = manager.getState();
            // normalizeTags should remove whitespace and empty tags
            expect(state.schemaTags).toEqual(['tag1', 'tag2']);
        });
    });

    describe('saveSchema', () => {
        it('should throw error if no model loaded', async () => {
            const newManager = new SchemaManager();

            await expect(newManager.saveSchema()).rejects.toThrow('No model loaded');
        });

        it('should handle save errors', async () => {
            vi.mocked(updateModelSchema).mockRejectedValueOnce(new Error('Save failed'));
            const mockSchema = {
                columns: [{ name: 'field1', data_type: 'text', description: 'Desc' }],
                tags: [],
            };

            vi.mocked(getModelSchema).mockResolvedValue(mockSchema);

            await manager.loadSchema('model1', null);
            vi.clearAllMocks();

            await expect(manager.saveSchema()).rejects.toThrow('Save failed');

            // Should update state with error
            expect(onStateChangeMock).toHaveBeenCalled();
        });

        it('should set hasUnsavedChanges to false on success', async () => {
            const mockSchema = {
                columns: [],
                tags: [],
            };

            vi.mocked(getModelSchema).mockResolvedValue(mockSchema);

            await manager.loadSchema('model1', null);

            expect(manager.hasUnsavedChanges()).toBe(false);

            manager.updateEditableColumn(0, { name: 'changed' });

            expect(manager.hasUnsavedChanges()).toBe(true);

            vi.mocked(updateModelSchema).mockResolvedValue(undefined);

            await manager.saveSchema();

            // After successful save, hasUnsavedChanges should be false
            expect(manager.hasUnsavedChanges()).toBe(false);
        });
    });

    describe('updateEditableColumn', () => {
        beforeEach(async () => {
            vi.mocked(getModelSchema).mockResolvedValue({
                columns: [
                    { name: 'field1', data_type: 'text', description: 'Desc 1' },
                    { name: 'field2', data_type: 'integer', description: 'Desc 2' },
                ],
                tags: [],
            });

            await manager.loadSchema('model1', null);
            vi.clearAllMocks();
        });

        it('should update column at index', () => {
            manager.updateEditableColumn(0, { name: 'updated-field1' });

            const columns = manager.getEditableColumns();

            expect(columns[0].name).toBe('updated-field1');
            expect(columns[1].name).toBe('field2'); // Should not affect other columns
        });

        it('should merge updates with existing column data', () => {
            manager.updateEditableColumn(0, { description: 'New description' });

            const columns = manager.getEditableColumns();

            expect(columns[0].name).toBe('field1'); // Preserved
            expect(columns[0].data_type).toBe('text'); // Preserved
            expect(columns[0].description).toBe('New description'); // Updated
        });

        it('should set hasUnsavedChanges to true', () => {
            expect(manager.hasUnsavedChanges()).toBe(false);

            manager.updateEditableColumn(0, { name: 'changed' });

            expect(manager.hasUnsavedChanges()).toBe(true);
        });
    });

    describe('addEditableColumn', () => {
        beforeEach(async () => {
            vi.mocked(getModelSchema).mockResolvedValue({
                columns: [{ name: 'field1', data_type: 'text', description: 'Desc' }],
                tags: [],
            });

            await manager.loadSchema('model1', null);
            vi.clearAllMocks();
        });

        it('should add new column with default values', () => {
            manager.addEditableColumn();

            const columns = manager.getEditableColumns();

            expect(columns).toHaveLength(2);
            expect(columns[1].name).toBe('');
            expect(columns[1].data_type).toBe('text');
            expect(columns[1].description).toBe('');
        });

        it('should set hasUnsavedChanges to true', () => {
            expect(manager.hasUnsavedChanges()).toBe(false);

            manager.addEditableColumn();

            expect(manager.hasUnsavedChanges()).toBe(true);
        });
    });

    describe('deleteEditableColumn', () => {
        beforeEach(async () => {
            vi.mocked(getModelSchema).mockResolvedValue({
                columns: [
                    { name: 'field1', data_type: 'text', description: 'Desc 1' },
                    { name: 'field2', data_type: 'integer', description: 'Desc 2' },
                    { name: 'field3', data_type: 'boolean', description: 'Desc 3' },
                ],
                tags: [],
            });

            await manager.loadSchema('model1', null);
            vi.clearAllMocks();
        });

        it('should delete column at index', () => {
            manager.deleteEditableColumn(1);

            const columns = manager.getEditableColumns();

            expect(columns).toHaveLength(2);
            expect(columns[0].name).toBe('field1');
            expect(columns[1].name).toBe('field3');
        });

        it('should set hasUnsavedChanges to true', () => {
            expect(manager.hasUnsavedChanges()).toBe(false);

            manager.deleteEditableColumn(1);

            expect(manager.hasUnsavedChanges()).toBe(true);
        });
    });

    describe('updateSchemaTags', () => {
        beforeEach(async () => {
            vi.mocked(getModelSchema).mockResolvedValue({
                columns: [],
                tags: ['schema-tag-1'],
            });

            await manager.loadSchema('model1', null, ['manifest-tag-1', 'manifest-tag-2']);
            vi.clearAllMocks();
        });

        it('should update schema tags', () => {
            manager.updateSchemaTags(['new-schema-tag']);

            const state = manager.getState();

            expect(state.schemaTags).toEqual(['new-schema-tag']);
        });

        it('should preserve manifest tags', () => {
            const stateBefore = manager.getState();
            expect(stateBefore.manifestTags).toEqual(['manifest-tag-1', 'manifest-tag-2']);

            manager.updateSchemaTags(['new-schema-tag']);

            const stateAfter = manager.getState();
            expect(stateAfter.manifestTags).toEqual(['manifest-tag-1', 'manifest-tag-2']);
        });

        it('should update display tags by combining schema and manifest', () => {
            manager.updateSchemaTags(['new-schema-tag']);

            const state = manager.getState();

            expect(state.displayTags).toContain('new-schema-tag');
            expect(state.displayTags).toContain('manifest-tag-1');
            expect(state.displayTags).toContain('manifest-tag-2');
        });

        it('should remove old schema tags from display tags', () => {
            const stateBefore = manager.getState();
            expect(stateBefore.displayTags).toContain('schema-tag-1');

            manager.updateSchemaTags(['new-schema-tag']);

            const stateAfter = manager.getState();
            expect(stateAfter.displayTags).not.toContain('schema-tag-1');
        });

        it('should set hasUnsavedChanges to true', () => {
            expect(manager.hasUnsavedChanges()).toBe(false);

            manager.updateSchemaTags(['new-tag']);

            expect(manager.hasUnsavedChanges()).toBe(true);
        });
    });

    describe('reset', () => {
        beforeEach(async () => {
            vi.mocked(getModelSchema).mockResolvedValue({
                columns: [{ name: 'field1', data_type: 'text', description: 'Desc' }],
                tags: ['tag1'],
            });

            await manager.loadSchema('model1', null, ['manifest-tag']);
            vi.clearAllMocks();
        });

        it('should reset all state to initial values', () => {
            manager.reset();

            const state = manager.getState();

            expect(state.editableColumns).toEqual([]);
            expect(state.isLoading).toBe(false);
            expect(state.isSaving).toBe(false);
            expect(state.error).toBe(null);
            expect(state.hasUnsavedChanges).toBe(false);
            expect(state.schema).toBe(null);
            expect(state.schemaTags).toEqual([]);
            expect(state.manifestTags).toEqual([]);
            expect(state.displayTags).toEqual([]);
        });

        it('should clear model name and version', async () => {
            await manager.loadSchema('model1', null);
            
            manager.reset();

            // Trying to save should fail because no model is loaded
            await expect(manager.saveSchema()).rejects.toThrow('No model loaded');
        });

        it('should not trigger unsaved changes', () => {
            manager.updateEditableColumn(0, { name: 'changed' });
            expect(manager.hasUnsavedChanges()).toBe(true);

            manager.reset();

            expect(manager.hasUnsavedChanges()).toBe(false);
        });
    });

    describe('state change callback', () => {
        it('should call callback on every state change', async () => {
            vi.mocked(getModelSchema).mockResolvedValue({
                columns: [],
                tags: [],
            });

            await manager.loadSchema('model1', null);
            manager.updateEditableColumn(0, { name: 'changed' });
            manager.addEditableColumn();

            expect(onStateChangeMock).toHaveBeenCalled();
            expect(onStateChangeMock.mock.calls.length).toBeGreaterThan(2);
        });

        it('should pass complete state to callback', () => {
            manager.updateEditableColumn(0, { name: 'changed' });

            const stateArg = onStateChangeMock.mock.calls.find(
                (call) => call[0].hasUnsavedChanges === true
            )?.[0];

            expect(stateArg).toHaveProperty('editableColumns');
            expect(stateArg).toHaveProperty('isLoading');
            expect(stateArg).toHaveProperty('isSaving');
            expect(stateArg).toHaveProperty('error');
            expect(stateArg).toHaveProperty('hasUnsavedChanges');
            expect(stateArg).toHaveProperty('schema');
            expect(stateArg).toHaveProperty('schemaTags');
            expect(stateArg).toHaveProperty('manifestTags');
            expect(stateArg).toHaveProperty('displayTags');
        });
    });
});
