import type { Entity } from '$lib/types';

/**
 * Simple fuzzy/substring match for search term
 * Case-insensitive, matches on entity label
 */
function matchesSearchTerm(label: string, searchTerm: string): boolean {
	if (!searchTerm) return true;
	const trimmedSearch = searchTerm.trim().toLowerCase();
	return label.toLowerCase().includes(trimmedSearch);
}

/**
 * Filter entities based on search term, domains, and tags
 * Logic:
 * - Search term: Case-insensitive substring match on label (must pass)
 * - Domains: OR logic - entity matches if any domain is in selectedDomains, or if selectedDomains is empty show all (must pass)
 * - Tags: OR logic - entity matches if ANY tag in entity.tags matches ANY tag in selectedTags, or if selectedTags is empty show all (must pass)
 * - Combine: AND logic - entity must pass all three filters
 *
 * @param entities - Array of entities to filter
 * @param filters - Filter criteria object
 * @returns Filtered array of entities
 */
export function filterEntities(
	entities: Entity[],
	filters: {
		searchTerm: string;
		selectedDomains: string[];
		selectedTags: string[];
		selectedEntityTypes?: Array<'dimension' | 'fact' | 'unclassified'>;
	}
): Entity[] {
	const result = entities.filter((entity) => {
		// Filter by search term (case-insensitive substring match on label)
		if (!matchesSearchTerm(entity.label, filters.searchTerm)) {
			return false;
		}

		// Filter by entity type (OR logic within types; if empty, show all)
		if (filters.selectedEntityTypes && filters.selectedEntityTypes.length > 0) {
			const effectiveType: 'dimension' | 'fact' | 'unclassified' =
				entity.entity_type ?? 'unclassified';
			if (!filters.selectedEntityTypes.includes(effectiveType)) {
				return false;
			}
		}

		// Filter by domains (OR logic: if selectedDomains is empty, show all)
		if (filters.selectedDomains.length > 0) {
			const entityDomains = Array.isArray(entity.domains) && entity.domains.length > 0
				? entity.domains
				: entity.domain !== undefined
					? [entity.domain]
					: [];
			const hasMatchingDomain = entityDomains.some((domain) =>
				filters.selectedDomains.includes(domain)
			);
			if (!hasMatchingDomain) {
				return false;
			}
		}

		// Filter by tags (OR logic: if selectedTags is empty, show all)
		if (filters.selectedTags.length > 0) {
			const entityTags = entity.tags || [];
			const hasMatchingTag = entityTags.some((tag) => filters.selectedTags.includes(tag));
			if (!hasMatchingTag) {
				return false;
			}
		}

		return true;
	});

	return result;
}
