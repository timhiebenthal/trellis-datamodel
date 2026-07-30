import type { Node, Edge } from '@xyflow/svelte';
import type { DataModel, EntityRole } from '$lib/types';
import { getApiBase, saveDataModel as apiSaveDataModel } from '$lib/api';
import { normalizeTags } from '$lib/utils';
import { get } from 'svelte/store';
import { sourceColors as sourceColorsStore, modelingStyle as modelingStyleStore } from '$lib/stores';

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
        const matchLast = state === this.lastSavedState;
        const matchQueued = state === this.queuedState;
        const matchInFlight = state === this.inFlightState;

        // Skip if state hasn't changed or is already queued/in-flight
        if (matchLast || matchQueued || matchInFlight) {
            return;
        }

        // Clear any pending save timeout
        if (this.pendingSaveTimeout) {
            clearTimeout(this.pendingSaveTimeout);
            this.pendingSaveTimeout = null;
        }

        // Set up new debounced save
        let nodesSnapshot: Node[];
        let edgesSnapshot: Edge[];
        try {
            // structuredClone can fail on non-serializable values in nodes/edges.
            // JSON clone drops functions and complex types but is safe for payloads.
            nodesSnapshot = JSON.parse(JSON.stringify(currentNodes)) as Node[];
            edgesSnapshot = JSON.parse(JSON.stringify(currentEdges)) as Edge[];
        } catch (e) {
            console.error('Save snapshot failed', e);
            return;
        }
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
        // Use JSON clone to handle Svelte 5 Proxy objects that structuredClone can't handle
        void this.persistDataModel(
            JSON.parse(JSON.stringify(currentNodes)) as Node[],
            JSON.parse(JSON.stringify(currentEdges)) as Edge[],
            state
        );
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
                    const isBound = Boolean(n.data?.dbt_model);
                    const uiTags = normalizeTags((n.data as any)?.ui_tags);

                    const source_system = ((n.data as any)?.source_system) as string[] | undefined;
                    const annotation_type = ((n.data as any)?.annotation_type) as string | undefined;
                    const roles = ((n.data as any)?.roles) as EntityRole[] | undefined;
                    const domain = ((n.data as any)?.domain) as string | undefined;
                    const domains = ((n.data as any)?.domains) as string[] | undefined;
                    const isDimensional = get(modelingStyleStore) === 'dimensional_model';
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
                        // Bound entities: `dbt_tags`/`tags` mirror schema.yml and are
                        // reconcile-owned; autosave must never write them, only
                        // `ui_tags` (user-added). Unbound entities: `tags` remains
                        // the single freely-editable field.
                        ...(isBound
                            ? { ui_tags: uiTags.length > 0 ? uiTags : undefined }
                            : { tags: displayTags.length > 0 ? displayTags : undefined }),
                    };
                    // Only include entity_type for dimensional modeling
                    if (isDimensional) {
                        entity.entity_type = ((n.data as any)?.entity_type) || 'unclassified';
                    }

                    // Include domain if present
                    if (domain && domain.trim()) {
                        entity.domain = domain.trim();
                    }
                    if (Array.isArray(domains) && domains.length > 0) {
                        entity.domains = domains;
                        if (!entity.domain) {
                            entity.domain = domains[0];
                        }
                    }

                    // Include annotation_type if present (for dimensions created from business events)
                    if (annotation_type) {
                        entity.annotation_type = annotation_type;
                    }
                    if (roles !== undefined) {
                        entity.roles = roles;
                    }

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
            const draftedCounts = (dataModel.entities ?? [])
                .map((e) => (Array.isArray((e as any).drafted_fields) ? (e as any).drafted_fields.length : 0));
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
