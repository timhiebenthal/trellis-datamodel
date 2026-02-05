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
			modified = true;
			const currentDomains = Array.isArray(node.data?.domains)
				? node.data?.domains
				: node.data?.domain
					? [node.data?.domain]
					: [];
			const nextDomains = Array.from(
				new Set(currentDomains.map((d) => d.trim()).filter(Boolean).concat(domain.trim()))
			);
			return {
				...node,
				data: {
					...node.data,
					domains: nextDomains.length > 0 ? nextDomains : undefined,
					domain: nextDomains.length > 0 ? nextDomains[0] : undefined,
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
 * @param entityIds - Array of entity IDs to update
 * @param tagsToAdd - Array of tags to add
 */
export function bulkAddTags(entityIds: string[], tagsToAdd: string[]): void {
	if (entityIds.length === 0 || tagsToAdd.length === 0) return;

	const currentNodes = get(nodesStore);
	let modified = false;

	const updatedNodes = currentNodes.map((node) => {
		if (entityIds.includes(node.id) && node.type === 'entity') {
			const currentTags = node.data?.tags || [];
			const newTags = Array.isArray(currentTags) ? [...currentTags] : [];

			// Add tags, avoiding duplicates
			for (const tag of tagsToAdd) {
				if (!newTags.includes(tag)) {
					newTags.push(tag);
					modified = true;
				}
			}

			return {
				...node,
				data: {
					...node.data,
					tags: newTags.length > 0 ? newTags : undefined,
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
 * @param entityIds - Array of entity IDs to update
 * @param tagsToRemove - Array of tags to remove
 */
export function bulkRemoveTags(entityIds: string[], tagsToRemove: string[]): void {
	if (entityIds.length === 0 || tagsToRemove.length === 0) return;

	const currentNodes = get(nodesStore);
	let modified = false;

	const updatedNodes = currentNodes.map((node) => {
		if (entityIds.includes(node.id) && node.type === 'entity') {
			const currentTags = node.data?.tags;
			if (!Array.isArray(currentTags)) return node;

			// If current tags array is empty, set to undefined
			if (currentTags.length === 0) {
				if (node.data?.tags !== undefined) {
					modified = true;
				}
				return {
					...node,
					data: {
						...node.data,
						tags: undefined,
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
					tags: newTags.length > 0 ? newTags : undefined,
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
