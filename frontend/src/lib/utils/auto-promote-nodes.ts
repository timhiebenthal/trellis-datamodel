import type { Node } from '@xyflow/svelte';
import type { DbtModel, EntityData } from '$lib/types';
import { promoteDraftsAgainstModel } from './field-promotion';
import { readModelRef } from './entity-compat';

export function autoPromoteAllNodes(
	nodes: Node[],
	frameworkModels: DbtModel[],
): { nodes: Node[]; changed: boolean } {
	let changed = false;
	const byUniqueId = new Map(frameworkModels.map((m) => [m.unique_id, m]));
	const next = nodes.map((node) => {
		if (node.type !== 'entity') return node;
		const data = node.data as unknown as EntityData;
		const modelRef = data ? readModelRef(data) : undefined;
		if (!modelRef) return node;
		const model = byUniqueId.get(modelRef);
		const promoted = promoteDraftsAgainstModel(data.drafted_fields, model);
		if (promoted === data.drafted_fields) return node;
		changed = true;
		return { ...node, data: { ...data, drafted_fields: promoted } };
	});
	return { nodes: changed ? next : nodes, changed };
}
