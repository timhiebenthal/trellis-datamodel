import { normalizeTags } from '$lib/utils';
import { readFrameworkTags, readModelRef } from './entity-compat';

export interface CanvasFilterState {
	selectedDomains: string[];
	selectedTags: string[];
}

export interface CanvasEntityMetadata {
	id?: string;
	domain?: string;
	domains?: string[];
	tags?: unknown;
	framework_tags?: string[];
	dbt_tags?: string[];
	ui_tags?: unknown;
	model_ref?: string;
	dbt_model?: string;
	additional_models?: string[];
}

export interface CanvasFrameworkModel {
	unique_id: string;
	tags?: unknown;
}

/**
 * Evaluates only Canvas domain and tag filters.
 *
 * URL-selected entity subsets are intentionally handled by the caller, before
 * this predicate is applied.
 */
export function matchesCanvasFilters(
	entity: CanvasEntityMetadata,
	filters: CanvasFilterState,
	frameworkModels: readonly CanvasFrameworkModel[] = [],
): boolean {
	if (filters.selectedDomains.length > 0) {
		const entityDomains = [
			...(entity.domain ? [entity.domain] : []),
			...(entity.domains ?? []),
		];

		if (!entityDomains.some((domain) => filters.selectedDomains.includes(domain))) {
			return false;
		}
	}

	if (filters.selectedTags.length > 0) {
		const boundModelIds = new Set(
			[readModelRef(entity), ...(entity.additional_models ?? [])].filter(
				(modelId): modelId is string => Boolean(modelId),
			),
		);
		const modelTags = frameworkModels
			.filter((model) => boundModelIds.has(model.unique_id))
			.flatMap((model) => normalizeTags(model.tags));
		const entityTags = [
			...normalizeTags(entity.tags),
			...normalizeTags(readFrameworkTags(entity)),
			...normalizeTags(entity.ui_tags),
		];
		const allTags = new Set([...modelTags, ...entityTags]);

		if (!filters.selectedTags.some((tag) => allTags.has(tag))) {
			return false;
		}
	}

	return true;
}
