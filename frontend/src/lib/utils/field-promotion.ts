import type { ModelInfo, DraftedField } from '$lib/types';

export function promoteDraftsAgainstModel(
	drafted: DraftedField[] | undefined,
	model: ModelInfo | undefined,
): DraftedField[] | undefined {
	if (drafted === undefined) return undefined;
	if (!model || !model.columns || model.columns.length === 0) return drafted;
	const materialized = new Set(model.columns.map((c) => c.name));
	const filtered = drafted.filter((d) => !materialized.has(d.name));
	return filtered.length === drafted.length ? drafted : filtered;
}
