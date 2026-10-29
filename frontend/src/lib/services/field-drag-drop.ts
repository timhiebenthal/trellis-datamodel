import { get } from 'svelte/store';
import type { EntityFlowNode, ModelSchema, Relationship } from '$lib/types';
import { isEntityNode } from '$lib/types';
import { draggingField, edges, frameworkModels, nodes } from '$lib/stores';
import { getModelSchema } from '$lib/api';
import { detectFieldSemantics } from '$lib/utils/field-semantics';
import { mergeRelationshipIntoEdges } from '$lib/utils/relationship-edges';
import {
	assignFieldsToEdge,
	findGenericEdge,
	hasFieldEdge,
	inferGreenfieldRelationshipType,
	resolveActiveModel,
} from '$lib/utils/field-relationship';

/**
 * Field-to-field drag/drop handlers for one entity node. Dragging a field onto a
 * field of another entity creates (or reuses) a relationship edge between them.
 * Getters are used so a renamed node keeps working with its current id/label.
 */
export function createFieldDragDrop(getNodeId: () => string, getNodeLabel: () => string) {
	function onFieldDragStart(fieldName: string, e: DragEvent) {
		e.stopPropagation(); // Prevent node drag
		if (!e.dataTransfer) return;
		e.dataTransfer.effectAllowed = 'link';
		e.dataTransfer.setData('text/plain', fieldName); // Required for drag to work

		draggingField.set({
			nodeId: getNodeId(),
			fieldName: fieldName,
			nodeLabel: getNodeLabel(),
		});
	}

	function onFieldDragEnd(e: DragEvent) {
		e.stopPropagation();
		draggingField.set(null);
	}

	function onFieldDragOver(e: DragEvent) {
		const dragging = get(draggingField);
		if (!dragging) return;
		if (dragging.nodeId === getNodeId()) return; // Same entity, no link
		e.preventDefault();
		e.stopPropagation(); // Prevent bubble to canvas
		if (e.dataTransfer) {
			e.dataTransfer.dropEffect = 'link';
		}
	}

	async function onFieldDrop(targetFieldName: string, e: DragEvent) {
		e.preventDefault();
		e.stopPropagation(); // Prevent bubble to canvas
		const dragging = get(draggingField);
		const targetNodeId = getNodeId();
		if (!dragging || dragging.nodeId === targetNodeId) return;

		const sourceNodeId = dragging.nodeId;
		const currentEdges = get(edges);

		if (hasFieldEdge(currentEdges, sourceNodeId, targetNodeId, dragging.fieldName, targetFieldName)) {
			console.warn('Blocked duplicate field connection');
			draggingField.set(null);
			return;
		}

		// Reuse a generic (field-less) edge between the two entities if there is one
		const genericEdge = findGenericEdge(currentEdges, sourceNodeId, targetNodeId);
		if (genericEdge) {
			edges.set(
				assignFieldsToEdge(
					currentEdges,
					genericEdge.id,
					sourceNodeId,
					targetNodeId,
					dragging.fieldName,
					targetFieldName,
				),
			);
			draggingField.set(null);
			return;
		}

		// Active model information for both ends (prefers ephemeral active model data)
		const currentNodes = get(nodes);
		const findData = (nodeId: string) =>
			currentNodes.find((n): n is EntityFlowNode => isEntityNode(n) && n.id === nodeId)?.data;
		const sourceNodeData = findData(sourceNodeId);
		const targetNodeData = findData(targetNodeId);
		const models = get(frameworkModels);
		const sourceActiveModel = resolveActiveModel(sourceNodeData, models);
		const targetActiveModel = resolveActiveModel(targetNodeData, models);

		/**
		 * Relationship Direction Rules:
		 *
		 * Relationships must always be named from the "1" side to the "*" side (parent → child).
		 * - one_to_many: source = 1 (parent), target = * (child)
		 * - many_to_one: source = * (child), target = 1 (parent)
		 * - one_to_one: source = FK holder, target = referenced table
		 *
		 * Auto-Detection from dbt:
		 * When both entities have bound dbt models, we detect FK/PK semantics to determine parent/child:
		 * - If source field is FK and target field is PK → flip direction (FK points to PK, so PK is parent)
		 * - If source field is PK and target field is FK → keep direction (PK is parent, FK is child)
		 * - Otherwise → use drag direction as fallback
		 *
		 * Manual Override:
		 * Users can manually swap direction using the swap button in the relationship editor.
		 */
		let finalSource = sourceNodeId;
		let finalTarget = targetNodeId;
		let finalSourceField = dragging.fieldName;
		let finalTargetField = targetFieldName;
		let relationshipType: Relationship['type'] = 'one_to_many';
		const sourceEntityType = (sourceNodeData?.entity_type as string | undefined) || 'unclassified';
		const targetEntityType = (targetNodeData?.entity_type as string | undefined) || 'unclassified';

		if (sourceActiveModel && targetActiveModel) {
			try {
				// Fetch schemas for both models to detect FK/PK semantics
				const sourceSchema = await getModelSchema(
					sourceActiveModel.name,
					sourceActiveModel.version ?? undefined,
				);
				const targetSchema = await getModelSchema(
					targetActiveModel.name,
					targetActiveModel.version ?? undefined,
				);

				if (sourceSchema && targetSchema) {
					const modelSchemas = new Map<string, ModelSchema>();
					modelSchemas.set(sourceActiveModel.name, sourceSchema);
					modelSchemas.set(targetActiveModel.name, targetSchema);

					const sourceSemantics = detectFieldSemantics(
						sourceActiveModel.name,
						finalSourceField,
						targetActiveModel.name,
						modelSchemas,
					);
					const targetSemantics = detectFieldSemantics(
						targetActiveModel.name,
						finalTargetField,
						sourceActiveModel.name,
						modelSchemas,
					);

					// Rule: Relationships always go from parent (PK holder) to child (FK holder)
					if (sourceSemantics === 'fk' && targetSemantics === 'pk') {
						// Flip direction: FK → PK becomes PK → FK (parent → child)
						finalSource = targetNodeId;
						finalTarget = sourceNodeId;
						finalSourceField = targetFieldName;
						// Deliberately re-reads the store after the awaits (pre-existing behaviour).
						finalTargetField = get(draggingField)!.fieldName;
						relationshipType = 'one_to_many';
					} else {
						// PK → FK is already parent → child; unknown/both-PK/both-FK fall back
						// to the drag direction.
						relationshipType = 'one_to_many';
					}
				}
			} catch (error) {
				// Fall back to drag direction on error (e.g., schema fetch fails, network error)
				console.warn('Error detecting FK/PK semantics, using drag direction:', error);
			}
		}
		// If models aren't bound (greenfield), use drag direction - user can manually swap if needed
		if (!sourceActiveModel || !targetActiveModel) {
			relationshipType = inferGreenfieldRelationshipType(sourceEntityType, targetEntityType);
		}

		const relationship = {
			source: finalSource,
			target: finalTarget,
			label: '',
			type: relationshipType,
			source_field: finalSourceField,
			target_field: finalTargetField,
			source_model_name: finalSource === sourceNodeId ? sourceActiveModel?.name : targetActiveModel?.name,
			source_model_version:
				finalSource === sourceNodeId
					? (sourceActiveModel?.version ?? null)
					: (targetActiveModel?.version ?? null),
			target_model_name: finalTarget === targetNodeId ? targetActiveModel?.name : sourceActiveModel?.name,
			target_model_version:
				finalTarget === targetNodeId
					? (targetActiveModel?.version ?? null)
					: (sourceActiveModel?.version ?? null),
		};

		// Merge relationship into edges (will aggregate by entity pair)
		edges.set(mergeRelationshipIntoEdges(get(edges), relationship));

		draggingField.set(null);
	}

	return { onFieldDragStart, onFieldDragEnd, onFieldDragOver, onFieldDrop };
}
