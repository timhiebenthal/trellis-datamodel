import { writable, get } from 'svelte/store';
import type { Node, Edge } from '@xyflow/svelte';
import type { DbtModel, FieldDragState } from './types';

export const nodes = writable<Node[]>([]);
export const edges = writable<Edge[]>([]);
export const dbtModels = writable<DbtModel[]>([]);
export const viewMode = writable<'conceptual' | 'logical' | 'exposures' | 'bus_matrix'>('conceptual');
export const modelingStyle = writable<'dimensional_model' | 'entity_model'>('entity_model');
export const configStatus = writable<any>(null);
export const labelPrefixes = writable<string[]>([]);
export const dimensionPrefixes = writable<string[]>([]);
export const factPrefixes = writable<string[]>([]);

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
            nodes: structuredClone(get(nodes)),
            edges: structuredClone(get(edges)),
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
        nodes: structuredClone(get(nodes)),
        edges: structuredClone(get(edges)),
    }];
    historyIndex = 0;
    updateCanUndoRedo();
}

export function undo() {
    if (historyIndex <= 0) return;

    isUndoRedoAction = true;
    historyIndex--;
    const state = history[historyIndex];
    nodes.set(structuredClone(state.nodes));
    edges.set(structuredClone(state.edges));
    updateCanUndoRedo();
    isUndoRedoAction = false;
}

export function redo() {
    if (historyIndex >= history.length - 1) return;

    isUndoRedoAction = true;
    historyIndex++;
    const state = history[historyIndex];
    nodes.set(structuredClone(state.nodes));
    edges.set(structuredClone(state.edges));
    updateCanUndoRedo();
    isUndoRedoAction = false;
}

