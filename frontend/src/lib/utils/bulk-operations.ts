import type { Node, Edge } from '@xyflow/svelte';
import { nodes as nodesStore, edges as edgesStore, entitySelection, pushHistory } from '$lib/stores';
import { get } from 'svelte/store';

/**
 * Bulk add domain to multiple entities
 * Updates nodes store in-place, calls pushHistory() once for undo/redo
 * @param entityIds - Array of entity IDs to update
 * @param domain - Domain to add
 */
export function bulkAssignDomain(entityIds: string[], domain: string): void {
	if (entityIds.length === 0) return;

	const currentNodes = get(nodesStore);
	let modified = false;

	const updatedNodes = currentNodes.map((node) => {
		if (entityIds.includes(node.id) && node.type === 'entity') {
			const trimmedDomain = domain.trim();
			const currentDomain = node.data?.domain;

			// Only mark as modified if domain actually changes
			if (currentDomain !== trimmedDomain) {
				modified = true;
			}

			return {
				...node,
				data: {
					...node.data,
					domains: trimmedDomain ? [trimmedDomain] : undefined,
					domain: trimmedDomain || undefined,
				},
			};
		}
		return node;
	});

	if (modified) {
		nodesStore.set(updatedNodes);
		pushHistory();
	}
}

/**
 * Bulk add tags to multiple entities
 * Avoids duplicates within each entity's tag list
 * Updates nodes store in-place, calls pushHistory() once for undo/redo
 *
 * Bound entities have no `tags` field to write — it's a reconcile-owned,
 * computed display union. Additions there go to `ui_tags` instead (skipping
 * any tag already dbt-owned, since that's not the user's to track). Unbound
 * entities keep using plain `tags`, their single freely-editable field.
 *
 * @param entityIds - Array of entity IDs to update
 * @param tagsToAdd - Array of tags to add
 */
export function bulkAddTags(entityIds: string[], tagsToAdd: string[]): void {
	if (entityIds.length === 0 || tagsToAdd.length === 0) return;

	const currentNodes = get(nodesStore);
	let modified = false;

	const updatedNodes = currentNodes.map((node) => {
		if (entityIds.includes(node.id) && node.type === 'entity') {
			const isBound = Boolean(node.data?.dbt_model);
			const tagField = isBound ? 'ui_tags' : 'tags';
			const dbtTags: string[] = isBound ? ((node.data as any)?.dbt_tags || []) : [];
			const currentTags = (node.data as any)?.[tagField] || [];
			const newTags = Array.isArray(currentTags) ? [...currentTags] : [];

			// Add tags, avoiding duplicates and tags already dbt-owned
			for (const tag of tagsToAdd) {
				if (!newTags.includes(tag) && !dbtTags.includes(tag)) {
					newTags.push(tag);
					modified = true;
				}
			}

			return {
				...node,
				data: {
					...node.data,
					[tagField]: newTags.length > 0 ? newTags : undefined,
				},
			};
		}
		return node;
	});

	if (modified) {
		nodesStore.set(updatedNodes);
		pushHistory();
	}
}

/**
 * Bulk remove tags from multiple entities
 * Updates nodes store in-place, calls pushHistory() once for undo/redo
 *
 * Bound entities: removal only ever affects `ui_tags` — a dbt-owned tag in
 * `tagsToRemove` naturally has no effect, since it was never in `ui_tags` to
 * begin with (dbt wins; removing it is a schema.yml-side operation).
 * Unbound entities keep using plain `tags`.
 *
 * @param entityIds - Array of entity IDs to update
 * @param tagsToRemove - Array of tags to remove
 */
export function bulkRemoveTags(entityIds: string[], tagsToRemove: string[]): void {
	if (entityIds.length === 0 || tagsToRemove.length === 0) return;

	const currentNodes = get(nodesStore);
	let modified = false;

	const updatedNodes = currentNodes.map((node) => {
		if (entityIds.includes(node.id) && node.type === 'entity') {
			const isBound = Boolean(node.data?.dbt_model);
			const tagField = isBound ? 'ui_tags' : 'tags';
			const currentTags = (node.data as any)?.[tagField];
			if (!Array.isArray(currentTags)) return node;

			// If current tags array is empty, set to undefined
			if (currentTags.length === 0) {
				if ((node.data as any)?.[tagField] !== undefined) {
					modified = true;
				}
				return {
					...node,
					data: {
						...node.data,
						[tagField]: undefined,
					},
				};
			}

			const newTags = currentTags.filter((tag) => {
				if (tagsToRemove.includes(tag)) {
					modified = true;
					return false;
				}
				return true;
			});

			return {
				...node,
				data: {
					...node.data,
					[tagField]: newTags.length > 0 ? newTags : undefined,
				},
			};
		}
		return node;
	});

	if (modified) {
		nodesStore.set(updatedNodes);
		pushHistory();
	}
}

/**
 * Bulk delete entities by ID
 * Removes nodes and all related edges
 * Updates nodes and edges stores, calls pushHistory() once for undo/redo
 * Clears entitySelection store
 * @param entityIds - Array of entity IDs to delete
 */
export function bulkDeleteEntities(entityIds: string[]): void {
	if (entityIds.length === 0) return;

	const currentNodes = get(nodesStore);
	const currentEdges = get(edgesStore);

	// Filter out deleted entities (only delete entity nodes, preserve other node types)
	const updatedNodes = currentNodes.filter((node) => {
		if (node.type !== 'entity') return true; // Keep non-entity nodes
		return !entityIds.includes(node.id);
	});

	// Remove edges connected to deleted entities
	const updatedEdges = currentEdges.filter((edge) => {
		return !entityIds.includes(edge.source) && !entityIds.includes(edge.target);
	});

	// Only update if something changed
	const nodesChanged = updatedNodes.length < currentNodes.length;
	const edgesChanged = updatedEdges.length < currentEdges.length;

	if (nodesChanged || edgesChanged) {
		if (nodesChanged) {
			nodesStore.set(updatedNodes);
		}
		if (edgesChanged) {
			edgesStore.set(updatedEdges);
		}
		pushHistory();
	}

	// Clear selection
	entitySelection.set(new Set());
}
