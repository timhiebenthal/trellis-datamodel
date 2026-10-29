import type { Edge } from '@xyflow/svelte';
import type { EntityNodeData, ModelInfo } from '$lib/types';
import { readModelRef } from './entity-compat';

/** The model a field-drag endpoint resolves to: just enough to fetch its schema. */
export type FieldDragModel = { name: string; version?: number | null };

/**
 * Pick the model used for FK/PK detection on one end of a field drag: the
 * node's ephemeral active model if published, else its primary model, else its
 * first additional model.
 */
export function resolveActiveModel(
	nodeData: EntityNodeData | undefined,
	models: ModelInfo[],
): FieldDragModel | null {
	if (nodeData?._activeModelName) {
		return {
			name: nodeData._activeModelName as string,
			version: nodeData._activeModelVersion as number | null | undefined,
		};
	}
	const primaryModelRef = readModelRef(nodeData ?? {});
	if (primaryModelRef) {
		return models.find((m) => m.unique_id === primaryModelRef) || null;
	}
	const firstAdditional = (nodeData?.additional_models as string[] | undefined)?.[0] || null;
	if (firstAdditional) {
		return models.find((m) => m.unique_id === firstAdditional) || null;
	}
	return null;
}

/** True when an edge already links exactly these two fields in this direction. */
export function hasFieldEdge(
	edges: Edge[],
	sourceNodeId: string,
	targetNodeId: string,
	sourceField: string | undefined,
	targetField: string,
): boolean {
	return edges.some(
		(e) =>
			e.source === sourceNodeId &&
			e.target === targetNodeId &&
			e.data?.source_field === sourceField &&
			e.data?.target_field === targetField,
	);
}

/** A generic (field-less) edge between the two entities, in either direction. */
export function findGenericEdge(edges: Edge[], nodeA: string, nodeB: string): Edge | undefined {
	return edges.find(
		(e) =>
			((e.source === nodeA && e.target === nodeB) ||
				(e.source === nodeB && e.target === nodeA)) &&
			!e.data?.source_field &&
			!e.data?.target_field,
	);
}

/** Reuse a generic edge for a field link, enforcing the direction of the drag. */
export function assignFieldsToEdge(
	edges: Edge[],
	edgeId: string,
	sourceNodeId: string,
	targetNodeId: string,
	sourceField: string,
	targetField: string,
): Edge[] {
	return edges.map((e) => {
		if (e.id === edgeId) {
			return {
				...e,
				source: sourceNodeId,
				target: targetNodeId,
				data: {
					...e.data,
					source_field: sourceField,
					target_field: targetField,
				},
			};
		}
		return e;
	});
}

/**
 * Relationship type for a field link when FK/PK semantics are unavailable
 * (greenfield): fact -> dimension puts the FK on the source (many_to_one),
 * everything else defaults to one_to_many.
 */
export function inferGreenfieldRelationshipType(
	sourceEntityType: string,
	targetEntityType: string,
): 'one_to_many' | 'many_to_one' {
	if (sourceEntityType === 'fact' && targetEntityType === 'dimension') {
		return 'many_to_one';
	}
	return 'one_to_many';
}
