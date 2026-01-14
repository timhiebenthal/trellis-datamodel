import type { DbtModel, ModelSchema, ModelSchemaColumn } from '$lib/types';
import { getModelSchema, updateModelSchema } from '$lib/api';
import { normalizeTags } from '$lib/utils';

/**
 * Schema manager state for tracking schema editing lifecycle.
 */
export interface SchemaState {
    /** Currently editable columns (may differ from loaded schema) */
    editableColumns: ModelSchemaColumn[];
    /** Whether schema is currently loading */
    isLoading: boolean;
    /** Whether schema is currently saving */
    isSaving: boolean;
    /** Error message if any */
    error: string | null;
    /** Whether there are unsaved changes */
    hasUnsavedChanges: boolean;
    /** Loaded schema if available */
    schema: ModelSchema | null;
    /** Schema tags (explicit, not inherited) */
    schemaTags: string[];
    /** Manifest tags (may include inherited tags) */
    manifestTags: string[];
    /** Combined display tags (for UI) */
    displayTags: string[];
}

/**
 * SchemaManager - Handles loading, editing, and saving of model schemas.
 *
 * This service manages the lifecycle of schema editing for bound dbt models,
 * including:
 * - Loading schema from the backend
 * - Managing editable columns
 * - Tracking unsaved changes
 * - Saving schema updates
 * - Error handling and loading states
 *
 * Key distinction: Schema tags (explicit in schema.yml) vs Manifest tags (may include inherited).
 * Only schema tags are persisted to avoid re-inheriting inherited tags on save.
 */
export class SchemaManager {
    private state: SchemaState;
    private modelName: string | null = null;
    private version: number | null = null;
    private modelManifestTags: string[] = [];
    private onStateChange?: (state: SchemaState) => void;

    /**
     * Create a SchemaManager instance
     *
     * @param onStateChange - Optional callback for state changes
     */
    constructor(onStateChange?: (state: SchemaState) => void) {
        this.state = {
            editableColumns: [],
            isLoading: false,
            isSaving: false,
            error: null,
            hasUnsavedChanges: false,
            schema: null,
            schemaTags: [],
            manifestTags: [],
            displayTags: [],
        };
        this.onStateChange = onStateChange;
    }

    /**
     * Get current schema state
     *
     * @returns Current state
     */
    getState(): SchemaState {
        return { ...this.state };
    }

    /**
     * Get editable columns
     *
     * @returns Array of editable columns
     */
    getEditableColumns(): ModelSchemaColumn[] {
        return [...this.state.editableColumns];
    }

    /**
     * Check if there are unsaved changes
     *
     * @returns True if there are unsaved changes
     */
    hasUnsavedChanges(): boolean {
        return this.state.hasUnsavedChanges;
    }

    /**
     * Check if currently loading
     *
     * @returns True if loading
     */
    isLoading(): boolean {
        return this.state.isLoading;
    }

    /**
     * Check if currently saving
     *
     * @returns True if saving
     */
    isSaving(): boolean {
        return this.state.isSaving;
    }

    /**
     * Check if there's an error
     *
     * @returns True if there's an error
     */
    hasError(): boolean {
        return this.state.error !== null;
    }

    /**
     * Load schema for a model
     *
     * @param modelName - Name of the model to load
     * @param version - Optional version of the model
     * @param manifestTags - Tags from the manifest (may include inherited tags)
     * @param fallbackColumns - Fallback columns from manifest if schema loading fails
     */
    async loadSchema(
        modelName: string,
        version: number | null | undefined,
        manifestTags: string[] = [],
        fallbackColumns?: DbtModel['columns'],
    ): Promise<void> {
        this.modelName = modelName;
        this.version = version ?? null;
        this.modelManifestTags = manifestTags;

        this.updateState({ isLoading: true, error: null });

        try {
            const schema = await getModelSchema(modelName, version ?? undefined);

            if (!schema) {
                throw new Error('Schema not found');
            }

            const hasSchemaColumns =
                Array.isArray(schema.columns) && schema.columns.length > 0;

            const editableColumns = hasSchemaColumns
                ? schema.columns.map((col) => ({
                    name: col.name,
                    data_type: col.data_type,
                    description: col.description,
                }))
                : fallbackColumns
                    ? fallbackColumns.map((col) => ({
                        name: col.name,
                        data_type: col.type || 'text',
                        description: '',
                    }))
                    : [];

            // Sync tags from dbt schema
            const schemaTags = normalizeTags(schema.tags);
            const tagsManifest = normalizeTags(manifestTags);

            // Combine for display: schema tags (explicit) + manifest tags (may include inherited)
            const displayTags = [...new Set([...schemaTags, ...tagsManifest])];

            this.updateState({
                schema,
                editableColumns,
                schemaTags,
                manifestTags: tagsManifest,
                displayTags,
                isLoading: false,
                hasUnsavedChanges: false,
            });
        } catch (e) {
            console.error('Error loading schema:', e);

            // Fallback to manifest columns on error
            const editableColumns = fallbackColumns
                ? fallbackColumns.map((col) => ({
                    name: col.name,
                    data_type: col.type || 'text',
                    description: '',
                }))
                : [];

            const schemaTags = normalizeTags([]);
            const tagsManifest = normalizeTags(manifestTags);
            const displayTags = [...tagsManifest];

            this.updateState({
                schema: null,
                editableColumns,
                schemaTags,
                manifestTags: tagsManifest,
                displayTags,
                isLoading: false,
                error: e instanceof Error ? e.message : 'Failed to load schema',
            });
        }
    }

    /**
     * Save current schema changes
     *
     * @param description - Optional description to save
     * @returns Promise that resolves when save is complete
     */
    async saveSchema(description?: string): Promise<void> {
        if (!this.modelName) {
            throw new Error('No model loaded - call loadSchema first');
        }


        this.updateState({ isSaving: true, error: null });

        try {
            // Only save schema tags (explicit), not manifest tags (which may be inherited)
            const tagsToSave = this.state.schemaTags;

            await updateModelSchema(
                this.modelName,
                this.state.editableColumns.map((col) => ({
                    name: col.name,
                    data_type: col.data_type,
                    description: col.description,
                })),
                description,
                tagsToSave.length > 0 ? tagsToSave : undefined,
                this.version ?? undefined,
            );

            this.updateState({
                isSaving: false,
                hasUnsavedChanges: false,
            });
        } catch (e: any) {
            console.error('Error saving schema:', e);
            this.updateState({
                isSaving: false,
                error: e.message || 'Failed to save schema',
            });
            throw e;
        }
    }

    /**
     * Update a specific editable column
     *
     * @param index - Index of column to update
     * @param updates - Partial updates to apply
     */
    updateEditableColumn(index: number, updates: Partial<ModelSchemaColumn>): void {
        const newColumns = this.state.editableColumns.map((col, i) =>
            i === index ? { ...col, ...updates } : col,
        );
        this.updateState({
            editableColumns: newColumns,
            hasUnsavedChanges: true,
        });
    }

    /**
     * Add a new editable column
     */
    addEditableColumn(): void {
        const newColumn: ModelSchemaColumn = {
            name: '',
            data_type: 'text',
            description: '',
        };
        this.updateState({
            editableColumns: [...this.state.editableColumns, newColumn],
            hasUnsavedChanges: true,
        });
    }

    /**
     * Delete an editable column
     *
     * @param index - Index of column to delete
     */
    deleteEditableColumn(index: number): void {
        const newColumns = this.state.editableColumns.filter((_, i) => i !== index);
        this.updateState({
            editableColumns: newColumns,
            hasUnsavedChanges: true,
        });
    }

    /**
     * Update schema tags (when user adds/removes tags in UI)
     *
     * @param newSchemaTags - New set of schema tags
     */
    updateSchemaTags(newSchemaTags: string[]): void {
        const displayTags = [...new Set([...newSchemaTags, ...this.state.manifestTags])];
        this.updateState({
            schemaTags: newSchemaTags,
            displayTags,
            hasUnsavedChanges: true,
        });
    }

    /**
     * Reset schema manager (clear all state)
     */
    reset(): void {
        this.modelName = null;
        this.version = null;
        this.modelManifestTags = [];
        this.updateState({
            editableColumns: [],
            isLoading: false,
            isSaving: false,
            error: null,
            hasUnsavedChanges: false,
            schema: null,
            schemaTags: [],
            manifestTags: [],
            displayTags: [],
        });
    }

    /**
     * Update state and trigger change callback
     *
     * @param updates - Partial state updates
     */
    private updateState(updates: Partial<SchemaState>): void {
        this.state = { ...this.state, ...updates };
        if (this.onStateChange) {
            this.onStateChange(this.getState());
        }
    }
}
