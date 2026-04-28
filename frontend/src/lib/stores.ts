import { writable, get } from 'svelte/store';
import type { Node, Edge } from '@xyflow/svelte';
import type { DbtModel, EntityListFilters, FieldDragState } from './types';

/**
 * Deep clone that handles Svelte 5 Proxy objects (which structuredClone cannot clone).
 * Falls back to JSON serialization which unwraps Proxy objects.
 */
function deepClone<T>(obj: T): T {
    try {
        return structuredClone(obj);
    } catch {
        // structuredClone fails on Proxy objects, use JSON serialization as fallback
        return JSON.parse(JSON.stringify(obj));
    }
}

export const nodes = writable<Node[]>([]);
export const edges = writable<Edge[]>([]);
export const dbtModels = writable<DbtModel[]>([]);
export const viewMode = writable<'conceptual' | 'logical' | 'exposures' | 'bus_matrix' | 'business_events'>('conceptual');
export const modelingStyle = writable<'dimensional_model' | 'entity_model'>('dimensional_model');
export const configStatus = writable<any>(null);
export const labelPrefixes = writable<string[]>([]);
export const dimensionPrefixes = writable<string[]>([]);
export const factPrefixes = writable<string[]>([]);

// Source colors from canvas_layout.yml
export const sourceColors = writable<Record<string, string>>({});

// Filter and grouping stores
export const folderFilter = writable<string[]>([]);
export const tagFilter = writable<string[]>([]);
export const entityTypeFilter = writable<string | null>(null); // 'dimension' | 'fact' | 'unclassified' | null
export const modelBoundFilter = writable<'bound' | 'unbound' | null>(null); // Filter by model bound status
export const groupByFolder = writable<boolean>(true);

// Exposure filter stores
export const exposureTypeFilter = writable<string[]>([]);
export const exposureOwnerFilter = writable<string[]>([]);
export const exposureEntityFilter = writable<string | null>(null); // Filter by specific entity ID

// Entity list view stores
// Modal management
export const entityDetailModal = writable<{
	open: boolean;
	entityId: string | null;
}>({ open: false, entityId: null });

export const bulkEditModal = writable<{
	open: boolean;
	selectedEntityIds: string[];
}>({ open: false, selectedEntityIds: [] });

// Filter state
export const entityListFilters = writable<EntityListFilters>({
	searchTerm: '',
	selectedDomains: [],
	selectedTags: [],
	selectedEntityTypes: [],
	sortDirection: 'asc',
	groupByEntityType: false,
});

// Bulk selection
export const entitySelection = writable<Set<string>>(new Set());

// Collapse state for domain groups
export const entityListCollapseState = writable<Record<string, boolean>>({});

// Drag-and-drop state for field linking
export const draggingField = writable<FieldDragState | null>(null);

// Global modals (rendered outside SvelteFlow to avoid viewport transform affecting position:fixed)
export const lineageModal = writable<{ open: boolean; modelId: string | null }>({
    open: false,
    modelId: null,
});

export function openLineageModal(modelId: string) {
    lineageModal.set({ open: true, modelId });
}

export function closeLineageModal() {
    lineageModal.set({ open: false, modelId: null });
}

export const sourceEditorModal = writable<{
    open: boolean;
    entityLabel: string;
    entityId: string;
    sources: string[];
}>({
    open: false,
    entityLabel: '',
    entityId: '',
    sources: [],
});

export function openSourceEditorModal(entityLabel: string, entityId: string, sources: string[]) {
    sourceEditorModal.set({ open: true, entityLabel, entityId, sources });
}

export function closeSourceEditorModal() {
    sourceEditorModal.set({ open: false, entityLabel: '', entityId: '', sources: [] });
}

export const deleteConfirmModal = writable<{
    open: boolean;
    entityLabel: string;
    entityIds: string[];
}>({
    open: false,
    entityLabel: '',
    entityIds: [],
});

export function openDeleteConfirmModal(entityLabel: string, entityIds: string[]) {
    deleteConfirmModal.set({ open: true, entityLabel, entityIds });
}

export function closeDeleteConfirmModal() {
    deleteConfirmModal.set({ open: false, entityLabel: '', entityIds: [] });
}

// Undo/Redo history management
interface HistoryState {
    nodes: Node[];
    edges: Edge[];
}

const MAX_HISTORY = 50;
let history: HistoryState[] = [];
let historyIndex = -1;
let isUndoRedoAction = false;
let pushDebounceTimeout: ReturnType<typeof setTimeout> | null = null;

export const canUndo = writable(false);
export const canRedo = writable(false);

function updateCanUndoRedo() {
    canUndo.set(historyIndex > 0);
    canRedo.set(historyIndex < history.length - 1);
}

export function pushHistory() {
    if (isUndoRedoAction) return;

    // Debounce rapid changes (e.g., dragging)
    if (pushDebounceTimeout) clearTimeout(pushDebounceTimeout);
    pushDebounceTimeout = setTimeout(() => {
        const state: HistoryState = {
            nodes: deepClone(get(nodes)),
            edges: deepClone(get(edges)),
        };

        // Remove any redo states if we're not at the end
        if (historyIndex < history.length - 1) {
            history = history.slice(0, historyIndex + 1);
        }

        history.push(state);
        if (history.length > MAX_HISTORY) {
            history.shift();
        } else {
            historyIndex++;
        }
        updateCanUndoRedo();
    }, 300);
}

export function initHistory() {
    history = [{
        nodes: deepClone(get(nodes)),
        edges: deepClone(get(edges)),
    }];
    historyIndex = 0;
    updateCanUndoRedo();
}

export function undo() {
    if (historyIndex <= 0) return;

    isUndoRedoAction = true;
    historyIndex--;
    const state = history[historyIndex];
    nodes.set(deepClone(state.nodes));
    edges.set(deepClone(state.edges));
    updateCanUndoRedo();
    isUndoRedoAction = false;
}

export function redo() {
    if (historyIndex >= history.length - 1) return;

    isUndoRedoAction = true;
    historyIndex++;
    const state = history[historyIndex];
    nodes.set(deepClone(state.nodes));
    edges.set(deepClone(state.edges));
    updateCanUndoRedo();
    isUndoRedoAction = false;
}

