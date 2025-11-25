import { writable } from 'svelte/store';
import type { Node, Edge } from '@xyflow/svelte';
import type { DbtModel } from './types';

export const nodes = writable<Node[]>([]);
export const edges = writable<Edge[]>([]);
export const dbtModels = writable<DbtModel[]>([]);
export const viewMode = writable<'concept' | 'physical'>('concept');
export const configStatus = writable<any>(null);

// Drag-and-drop state for field linking
export interface FieldDragState {
    nodeId: string;
    fieldName: string;
    nodeLabel: string;
}
export const draggingField = writable<FieldDragState | null>(null);

