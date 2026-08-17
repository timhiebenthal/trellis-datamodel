import type { Node } from '@xyflow/svelte';
import type { EntityData, ModelInfo } from '$lib/types';
import { classifyModelTypeFromPrefixes } from '$lib/utils';
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
