import type { Edge, Node } from '@xyflow/svelte';
import type { Entity, ModelInfo } from '$lib/types';
import { readModelRef } from './entity-compat';

export type BootGraphNodeData = Record<string, unknown>;

export interface ActiveModelMetadata {
	id: string;
	name: string;
	version: number | null;
}

export interface BootGraphIndex {
	readonly modelsById: ReadonlyMap<string, ModelInfo>;
	readonly entitiesById: ReadonlyMap<string, Entity>;
	readonly nodesById: ReadonlyMap<string, Node<BootGraphNodeData>>;
	readonly activeModelsByNodeId: ReadonlyMap<string, ActiveModelMetadata | null>;
	readonly activeModelIdsByNodeId: ReadonlyMap<string, string | null>;
	readonly nodes: readonly Node<BootGraphNodeData>[];
}

export interface BootGraphIndexInput {
	models: readonly ModelInfo[];
	entities: readonly Entity[];
	nodes: readonly Node<BootGraphNodeData>[];
	activeModelIds?: ReadonlyMap<string, string | null>;
}

export interface BootGraphTransformOptions {
	/**
	 * Active model selection is ephemeral UI state. It is intentionally kept
	 * here rather than written into a node's persisted data.
	 */
	activeModelIds?: ReadonlyMap<string, string | null>;
	/**
	 * Undefined means no filter is active. A set means only these node IDs
	 * should be displayed.
	 */
	visibleNodeIds?: ReadonlySet<string>;
}

export interface BootGraphResult {
	readonly nodes: readonly Node<BootGraphNodeData>[];
	readonly edges: readonly Edge[];
	readonly activeModelsByNodeId: ReadonlyMap<string, ActiveModelMetadata | null>;
	readonly activeModelIdsByNodeId: ReadonlyMap<string, string | null>;
}

function getDefaultActiveModelId(entity: Entity): string | null {
	return readModelRef(entity) ?? entity.additional_models?.[0] ?? null;
}

function getActiveModelIds(
	nodes: readonly Node<BootGraphNodeData>[],
	entitiesById: ReadonlyMap<string, Entity>,
	explicitActiveModelIds?: ReadonlyMap<string, string | null>,
): Map<string, string | null> {
	const activeModelIds = new Map<string, string | null>();

	for (const node of nodes) {
		const entity = entitiesById.get(node.id);
		const explicitModelId = explicitActiveModelIds?.get(node.id);
		activeModelIds.set(
			node.id,
			explicitActiveModelIds?.has(node.id)
				? (explicitModelId ?? null)
				: entity
					? getDefaultActiveModelId(entity)
					: null,
		);
	}

	return activeModelIds;
}

function getActiveModelMetadata(
	activeModelIds: ReadonlyMap<string, string | null>,
	modelsById: ReadonlyMap<string, ModelInfo>,
): Map<string, ActiveModelMetadata | null> {
	const activeModels = new Map<string, ActiveModelMetadata | null>();

	for (const [nodeId, modelId] of activeModelIds) {
		const model = modelId ? modelsById.get(modelId) : undefined;
		activeModels.set(
			nodeId,
			model
				? {
						id: model.unique_id,
						name: model.name,
						version: model.version ?? null,
					}
				: null,
		);
	}

	return activeModels;
}

/**
 * Builds all boot-time indexes with one pass over each source collection.
 * The original arrays and objects are retained so unchanged graph updates
 * can use structural sharing.
 */
export function buildBootGraphIndex(input: BootGraphIndexInput): BootGraphIndex {
	const modelsById = new Map<string, ModelInfo>();
	for (const model of input.models) {
		modelsById.set(model.unique_id, model);
	}

	const entitiesById = new Map<string, Entity>();
	for (const entity of input.entities) {
		entitiesById.set(entity.id, entity);
	}

	const nodesById = new Map<string, Node<BootGraphNodeData>>();
	for (const node of input.nodes) {
		nodesById.set(node.id, node);
	}

	const activeModelIdsByNodeId = getActiveModelIds(
		input.nodes,
		entitiesById,
		input.activeModelIds,
	);

	return {
		modelsById,
		entitiesById,
		nodesById,
		activeModelsByNodeId: getActiveModelMetadata(activeModelIdsByNodeId, modelsById),
		activeModelIdsByNodeId,
		nodes: input.nodes,
	};
}

function activeModelSelectionChanged(
	nodeId: string,
	previous: ReadonlyMap<string, string | null>,
	next: ReadonlyMap<string, string | null>,
): boolean {
	return previous.get(nodeId) !== next.get(nodeId);
}

function hasActiveFilter(
	visibleNodeIds: ReadonlySet<string> | undefined,
	nodes: readonly Node<BootGraphNodeData>[],
): boolean {
	if (!visibleNodeIds) return false;
	if (visibleNodeIds.size !== nodes.length) return true;
	return nodes.some((node) => !visibleNodeIds.has(node.id));
}

/**
 * Applies ephemeral active-model and visibility changes without mutating the
 * indexed graph. Unchanged nodes and edges retain their original references.
 */
export function transformBootGraph(
	index: BootGraphIndex,
	edges: readonly Edge[],
	options: BootGraphTransformOptions = {},
): BootGraphResult {
	const nextActiveModelIds = options.activeModelIds
		? getActiveModelIds(index.nodes, index.entitiesById, options.activeModelIds)
		: index.activeModelIdsByNodeId;
	const nextActiveModels = options.activeModelIds
		? getActiveModelMetadata(nextActiveModelIds, index.modelsById)
		: index.activeModelsByNodeId;
	const changedNodeIds = new Set<string>();

	if (options.activeModelIds) {
		for (const node of index.nodes) {
			if (activeModelSelectionChanged(node.id, index.activeModelIdsByNodeId, nextActiveModelIds)) {
				changedNodeIds.add(node.id);
			}
		}
	}

	const filtering = hasActiveFilter(options.visibleNodeIds, index.nodes);
	const visibleNodeIds = options.visibleNodeIds;
	const nodes = filtering
		? index.nodes
				.filter((node) => visibleNodeIds?.has(node.id))
				.map((node) =>
					changedNodeIds.has(node.id) ? { ...node, data: node.data } : node,
				)
		: changedNodeIds.size === 0
			? index.nodes
			: index.nodes.map((node) =>
					changedNodeIds.has(node.id) ? { ...node, data: node.data } : node,
				);

	const edgesChanged = (edge: Edge): boolean => {
		const activeModelChanged =
			changedNodeIds.has(edge.source) || changedNodeIds.has(edge.target);
		return activeModelChanged;
	};
	const edgesVisible = (edge: Edge): boolean =>
		!filtering ||
		(visibleNodeIds?.has(edge.source) === true && visibleNodeIds.has(edge.target));
	const filteredEdges = filtering ? edges.filter(edgesVisible) : edges;
	const outputEdges =
		changedNodeIds.size === 0
			? filteredEdges
			: filteredEdges.map((edge) =>
					edgesChanged(edge) ? { ...edge, data: edge.data } : edge,
				);

	const unchanged =
		!filtering &&
		changedNodeIds.size === 0 &&
		nextActiveModelIds === index.activeModelIdsByNodeId;

	return {
		nodes: unchanged ? index.nodes : nodes,
		edges: unchanged ? edges : outputEdges,
		activeModelsByNodeId: nextActiveModels,
		activeModelIdsByNodeId: nextActiveModelIds,
	};
}
