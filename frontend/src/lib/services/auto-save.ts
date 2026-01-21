import type { Node, Edge } from '@xyflow/svelte';
import type { DataModel } from '$lib/types';
import { getApiBase, saveDataModel as apiSaveDataModel } from '$lib/api';
import { normalizeTags } from '$lib/utils';
import { get } from 'svelte/store';
import { sourceColors as sourceColorsStore } from '$lib/stores';

/**
 * AutoSave service - Manages debounced saves for node/edge state changes.
 *
 * This service handles the auto-save functionality by debouncing save requests
 * and flushing pending saves synchronously when needed.
 */
export class AutoSaveService {
    private debounceMs: number;
    private pendingSaveTimeout: ReturnType<typeof setTimeout> | null = null;
    private lastSavedState: string = '';
    // State that has been queued but not yet started.
    private queuedState: string | null = null;
    // State currently being persisted.
    private inFlightState: string | null = null;
    private isSaving: boolean = false;
    private onSavingChange?: (isSaving: boolean) => void;

    /**
     * Create an AutoSave service instance
     *
     * @param debounceMs - Delay in milliseconds before saving after state changes (default: 400ms)
     * @param onSavingChange - Optional callback for saving state changes
     */
    constructor(debounceMs: number = 400, onSavingChange?: (isSaving: boolean) => void) {
        this.debounceMs = debounceMs;
        this.onSavingChange = onSavingChange;
    }

    /**
     * Request a save operation (debounced)
     * This will wait for the configured delay before saving, unless flush() is called
     *
     * @param currentNodes - Current state of nodes
     * @param currentEdges - Current state of edges
     */
    save(currentNodes: Node[], currentEdges: Edge[]): void {
        const state = JSON.stringify({
            nodes: currentNodes,
            edges: currentEdges,
        });

        // Skip if state hasn't changed or is already queued/in-flight
        if (
            state === this.lastSavedState ||
            state === this.queuedState ||
            state === this.inFlightState
        ) {
            return;
        }

        // Clear any pending save timeout
        if (this.pendingSaveTimeout) {
            clearTimeout(this.pendingSaveTimeout);
            this.pendingSaveTimeout = null;
        }

        // Set up new debounced save
        const nodesSnapshot = structuredClone(currentNodes);
        const edgesSnapshot = structuredClone(currentEdges);
        this.queuedState = state;
        this.setSaving(true);
        this.pendingSaveTimeout = setTimeout(() => {
            this.inFlightState = this.queuedState ?? state;
            this.queuedState = null;
            void this.persistDataModel(nodesSnapshot, edgesSnapshot, state);
        }, this.debounceMs);
    }

    /**
     * Save immediately without debouncing
     * Clears any pending save and triggers immediate save
     *
     * @param currentNodes - Current state of nodes
     * @param currentEdges - Current state of edges
     */
    saveNow(currentNodes: Node[], currentEdges: Edge[]): void {
        // Clear any pending save
        if (this.pendingSaveTimeout) {
            clearTimeout(this.pendingSaveTimeout);
            this.pendingSaveTimeout = null;
        }

        const state = JSON.stringify({
            nodes: currentNodes,
            edges: currentEdges,
        });

        this.queuedState = null;
        this.inFlightState = state;
        this.setSaving(true);
        void this.persistDataModel(structuredClone(currentNodes), structuredClone(currentEdges), state);
    }

    /**
     * Flush any pending save synchronously
     * Used before critical operations like page navigation
     *
     * @param currentNodes - Current state of nodes
     * @param currentEdges - Current state of edges
     * @returns Promise that resolves when save is complete
     */
    async flushSync(currentNodes: Node[], currentEdges: Edge[]): Promise<void> {
        const state = JSON.stringify({
            nodes: currentNodes,
            edges: currentEdges,
        });

        // Cancel pending save if exists (do this first, before early return)
        if (this.pendingSaveTimeout) {
            clearTimeout(this.pendingSaveTimeout);
            this.pendingSaveTimeout = null;
        }

        if (
            state === this.lastSavedState ||
            state === this.queuedState ||
            state === this.inFlightState
        ) {
            return;
        }

        this.queuedState = state;
        this.inFlightState = state;
        this.setSaving(true);
        const payload = JSON.stringify(
            this.buildDataModelFromState(currentNodes, currentEdges),
        );
        const url = `${getApiBase()}/data-model`;

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: payload,
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            this.lastSavedState = state;
            this.inFlightState = null;
            this.queuedState = null;
            this.setSaving(false);
        } catch (e) {
            console.error('Sync save failed', e);
            this.inFlightState = null;
            this.queuedState = null;
            this.setSaving(false);
            throw e;
        }
    }

    /**
     * Check if there are unsaved changes
     *
     * @param currentNodes - Current state of nodes
     * @param currentEdges - Current state of edges
     * @returns True if there are unsaved changes
     */
    hasUnsavedChanges(currentNodes: Node[], currentEdges: Edge[]): boolean {
        const state = JSON.stringify({
            nodes: currentNodes,
            edges: currentEdges,
        });

        const baseline = this.inFlightState ?? this.lastSavedState;
        return baseline !== '' && baseline !== state;
    }

    /**
     * Set the debounce delay
     *
     * @param ms - New debounce delay in milliseconds
     */
    setDebounceMs(ms: number): void {
        this.debounceMs = ms;
    }

    /**
     * Check if currently saving
     *
     * @returns True if a save is in progress
     */
    isSavingActive(): boolean {
        return this.isSaving || this.pendingSaveTimeout !== null || this.inFlightState !== null;
    }

    /**
     * Get the last saved state string
     *
     * @returns The last saved state string
     */
    getLastSavedState(): string {
        return this.lastSavedState;
    }

    /**
     * Clear the last saved state (useful when loading new state)
     */
    clearLastSavedState(): void {
        this.lastSavedState = '';
    }

    /**
     * Build data model from node/edge state
     *
     * @param currentNodes - Current nodes
     * @param currentEdges - Current edges
     * @returns DataModel object ready for saving
     */
    private buildDataModelFromState(
        currentNodes: Node[],
        currentEdges: Edge[],
    ): DataModel {
        // Read source colors from store to include in save payload
        const sourceColors = get(sourceColorsStore);

        return {
            version: 0.1,
            source_colors: Object.keys(sourceColors).length > 0 ? sourceColors : undefined,
            entities: currentNodes
                .filter((n) => n.type === 'entity')
                .map((n) => {
                    const displayTags = normalizeTags(n.data?.tags);
                    const schemaTags = normalizeTags((n.data as any)?._schemaTags);
                    const isBound = Boolean(n.data?.dbt_model);

                    // For bound models, persist only explicit schema tags (user-defined).
                    // Inherited/manifest tags live in _manifestTags and should not be written back.
                    const tagsToPersist = isBound
                        ? schemaTags.length > 0
                            ? schemaTags
                            : undefined
                        : displayTags.length > 0
                            ? displayTags
                            : undefined;

                    const entity_type = ((n.data as any)?.entity_type) || 'unclassified';
                    const source_system = ((n.data as any)?.source_system) as string[] | undefined;
                    const entity: any = {
                        id: n.id,
                        label: ((n.data.label as string) || '').trim() || 'Entity',
                        description: n.data.description as string | undefined,
                        dbt_model: n.data.dbt_model as string | undefined,
                        additional_models: n.data?.additional_models as string[] | undefined,
                        drafted_fields: n.data?.drafted_fields as any[] | undefined,
                        position: n.position,
                        width: n.data?.width as number | undefined,
                        panel_height: n.data?.panelHeight as number | undefined,
                        collapsed: (n.data?.collapsed as boolean) ?? false,
                        // Persist display tags only; schema writes rely on _schemaTags.
                        tags: tagsToPersist,
                        // Include entity_type with default "unclassified" if not set
                        entity_type: entity_type,
                    };
                    
                    // Only persist source_system for unbound entities
                    // Bound entities get source_system from lineage
                    if (!isBound && source_system && source_system.length > 0) {
                        entity.source_system = source_system;
                    }
                    
                    return entity;
                }),
            relationships: currentEdges.flatMap((e) => {
                // If edge has multiple model relationships, expand them
                const models = (e.data?.models as any[]) || [];
                if (models.length > 0) {
                    // Create one relationship per model
                    return models.map((m) => ({
                        source: e.source,
                        target: e.target,
                        label: (e.data?.label as string) || '',
                        type:
                            (e.data?.type as
                                | 'one_to_many'
                                | 'many_to_one'
                                | 'one_to_one'
                                | 'many_to_many') || 'one_to_many',
                        source_field: m.source_field as string | undefined,
                        target_field: m.target_field as string | undefined,
                        source_model_name: m.source_model_name as string | undefined,
                        source_model_version: m.source_model_version as number | null | undefined,
                        target_model_name: m.target_model_name as string | undefined,
                        target_model_version: m.target_model_version as number | null | undefined,
                        label_dx: e.data?.label_dx as number | undefined,
                        label_dy: e.data?.label_dy as number | undefined,
                    }));
                } else {
                    // Fallback: single relationship from edge-level data
                    return [{
                        source: e.source,
                        target: e.target,
                        label: (e.data?.label as string) || '',
                        type:
                            (e.data?.type as
                                | 'one_to_many'
                                | 'many_to_one'
                                | 'one_to_one'
                                | 'many_to_many') || 'one_to_many',
                        source_field: e.data?.source_field as string | undefined,
                        target_field: e.data?.target_field as string | undefined,
                        label_dx: e.data?.label_dx as number | undefined,
                        label_dy: e.data?.label_dy as number | undefined,
                    }];
                }
            }),
        };
    }

    /**
     * Persist data model to API
     *
     * @param nodesSnapshot - Snapshot of nodes to save
     * @param edgesSnapshot - Snapshot of edges to save
     * @param stateString - State string to compare against
     */
    private async persistDataModel(
        nodesSnapshot: Node[],
        edgesSnapshot: Edge[],
        stateString: string,
    ): Promise<void> {
        try {
            const dataModel = this.buildDataModelFromState(nodesSnapshot, edgesSnapshot);
            await apiSaveDataModel(dataModel);
            this.lastSavedState = stateString;
            this.inFlightState = null;
            this.queuedState = null;
        } catch (e) {
            console.error('Save failed', e);
            this.inFlightState = null;
            this.queuedState = null;
            // Don't throw - this is called from void context (debounced/fire-and-forget)
            // Errors are logged and state is cleaned up
        } finally {
            this.setSaving(false);
            this.pendingSaveTimeout = null;
            this.inFlightState = null;
        }
    }

    /**
     * Update the saving state and trigger callback if provided
     *
     * @param saving - Whether a save is in progress
     */
    private setSaving(saving: boolean): void {
        this.isSaving = saving;
        if (this.onSavingChange) {
            this.onSavingChange(saving);
        }
    }

}
