import { writable } from 'svelte/store';
import type { Node, Edge } from '@xyflow/svelte';
import type { DbtModel } from './types';

export const nodes = writable<Node[]>([]);
export const edges = writable<Edge[]>([]);
export const dbtModels = writable<DbtModel[]>([]);
export const viewMode = writable<'concept' | 'physical'>('concept');

