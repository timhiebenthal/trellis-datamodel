import type { Node } from '@xyflow/svelte';
import type { DbtModel, EntityData } from '$lib/types';
import { promoteDraftsAgainstModel } from './field-promotion';

export function autoPromoteAllNodes(
	nodes: Node[],
	dbtModels: DbtModel[],
): { nodes: Node[]; changed: boolean } {
	let changed = false;
	const byUniqueId = new Map(dbtModels.map((m) => [m.unique_id, m]));
	const next = nodes.map((node) => {
		if (node.type !== 'entity') return node;
		const data = node.data as unknown as EntityData;
		if (!data?.dbt_model) return node;
		const model = byUniqueId.get(data.dbt_model);
		const promoted = promoteDraftsAgainstModel(data.drafted_fields, model);
		if (promoted === data.drafted_fields) return node;
		changed = true;
		return { ...node, data: { ...data, drafted_fields: promoted } };
	});
	return { nodes: changed ? next : nodes, changed };
}
