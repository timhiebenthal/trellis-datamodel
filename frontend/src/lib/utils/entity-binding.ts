import type { Node } from '@xyflow/svelte';
import type { EntityData, ModelInfo, Relationship } from '$lib/types';
import { isEntityNode } from '$lib/types';
import { classifyModelTypeFromPrefixes, extractModelNameFromUniqueId } from './model-naming';
import { readModelRef } from './entity-compat';
import { get } from 'svelte/store';
import { factPrefixes, dimensionPrefixes, nodes as nodesStore, pushHistory } from '$lib/stores';

export type EntityBindingOptions = {
	dimensionPrefixes?: string[];
	factPrefixes?: string[];
};

export type EntityBindingResult = {
	node: Node;
	changed: boolean;
};

/**
 * Apply the existing canvas binding semantics to one entity node.
 *
 * An unbound entity receives a primary model. A bound entity receives a new
 * unique additional model. The input node is returned unchanged for duplicate
 * selections so callers can avoid unnecessary saves.
 */
export function bindModelToNode(
	node: Node,
	model: ModelInfo,
	options: EntityBindingOptions = {},
): EntityBindingResult {
	const data = node.data as unknown as EntityData;
	const primaryModel = readModelRef(data);
	const additionalModels = Array.isArray(data.additional_models) ? data.additional_models : [];
	const allBoundModels = primaryModel ? [primaryModel, ...additionalModels] : additionalModels;

	if (!model.unique_id || allBoundModels.includes(model.unique_id)) {
		return { node, changed: false };
	}

	const nextData: EntityData = {
		...data,
		...(primaryModel
			? { additional_models: [...additionalModels, model.unique_id] }
			: {
					model_ref: model.unique_id,
					...migrateUserTags(data),
					...(data.description?.trim()
						? {}
						: model.description?.trim()
							? { description: model.description }
							: {}),
					...inferEntityType(model, options),
				}),
	};

	return {
		node: { ...node, data: nextData as unknown as Record<string, unknown> },
		changed: true,
	};
}

function migrateUserTags(data: EntityData): Pick<EntityData, 'ui_tags'> {
	const existingUiTags = Array.isArray(data.ui_tags) ? data.ui_tags : [];
	const existingTags = Array.isArray(data.tags) ? data.tags : [];
	const uiTags = Array.from(new Set([...existingUiTags, ...existingTags]));
	return uiTags.length > 0 ? { ui_tags: uiTags } : {};
}

function inferEntityType(
	model: ModelInfo,
	options: EntityBindingOptions,
): Pick<EntityData, 'entity_type'> {
	const inferred = classifyModelTypeFromPrefixes(
		model.name,
		options.dimensionPrefixes ?? [],
		options.factPrefixes ?? [],
	);
	return inferred ? { entity_type: inferred } : {};
}

/**
 * Bind a model to an entity in the shared node store and create one undo step.
 * Autosave observes the store mutation through the existing layout service.
 */
export function bindEntityToModel(entityId: string, model: ModelInfo): boolean {
	const currentNodes = get(nodesStore);
	const target = currentNodes.find((node) => node.id === entityId && node.type === 'entity');
	if (!target) return false;

	const result = bindModelToNode(target, model, {
		dimensionPrefixes: get(dimensionPrefixes),
		factPrefixes: get(factPrefixes),
	});
	if (!result.changed) return false;

	nodesStore.set(currentNodes.map((node) => (node.id === entityId ? result.node : node)));
	pushHistory();
	return true;
}

/** Short display name of a bound model: the last dot-separated segment of its unique_id. */
export function modelShortName(modelId: string): string {
	return modelId.includes('.') ? modelId.split('.').pop()! : modelId;
}

/**
 * Point every edge endpoint that references `oldId` at `newId`. Edge IDs are kept
 * stable on purpose: changing them caused duplicates on reload.
 */
export function renameNodeInEdges<E extends { source: string; target: string }>(
	edges: E[],
	oldId: string,
	newId: string,
): E[] {
	return edges.map((edge) => {
		const updatedEdge = { ...edge };
		if (edge.source === oldId) {
			updatedEdge.source = newId;
		}
		if (edge.target === oldId) {
			updatedEdge.target = newId;
		}
		return updatedEdge;
	});
}

/** Give node `oldId` the id `newId` and merge `dataPatch` into its data. */
export function renameNode<N extends Node>(
	nodes: N[],
	oldId: string,
	newId: string,
	dataPatch: Record<string, unknown>,
): N[] {
	return nodes.map((node) => {
		if (node.id === oldId) {
			return { ...node, id: newId, data: { ...node.data, ...dataPatch } };
		}
		return node;
	});
}

/**
 * Map model names (and entity IDs) to the canvas entity they are bound to, so
 * inferred relationships (expressed in model names) can be remapped to entities.
 *
 * The entity being bound is passed explicitly: it may have been renamed from
 * `currentId` to `finalId` and its new models are not on the canvas yet.
 */
export function buildModelToEntityMap(
	nodes: Node[],
	currentId: string,
	finalId: string,
	currentNodeModels: string[],
): Record<string, string> {
	const modelToEntity: Record<string, string> = {};
	for (const node of nodes) {
		const isCurrent = node.id === currentId || node.id === finalId;
		const nodeIdToMatch = isCurrent ? finalId : node.id;
		let boundModels: string[] = [];
		if (isCurrent) {
			boundModels = currentNodeModels;
		} else {
			const primary = isEntityNode(node) ? readModelRef(node.data) : undefined;
			const additional = (node.data?.additional_models as string[]) || [];
			if (primary) {
				boundModels = [primary, ...additional];
			}
		}

		for (const boundModel of boundModels) {
			if (boundModel && typeof boundModel === 'string') {
				// Versioned models map by base name (the backend returns base_model_name).
				modelToEntity[extractModelNameFromUniqueId(boundModel)] = nodeIdToMatch;
			}
		}
		// Also map entity ID to itself
		modelToEntity[nodeIdToMatch] = nodeIdToMatch;
	}
	return modelToEntity;
}

/**
 * Remap inferred relationships to entity IDs and keep only those that touch
 * `entityId` and whose both ends exist on the canvas.
 */
export function remapInferredRelationships(
	inferred: Relationship[],
	modelToEntity: Record<string, string>,
	entityId: string,
	nodeIds: string[],
): Relationship[] {
	const remapped: Relationship[] = [];
	for (const rel of inferred) {
		const source = modelToEntity[rel.source] || rel.source;
		const target = modelToEntity[rel.target] || rel.target;
		if (source !== entityId && target !== entityId) continue;
		if (!nodeIds.includes(source) || !nodeIds.includes(target)) continue;
		remapped.push({ ...rel, source, target });
	}
	return remapped;
}
