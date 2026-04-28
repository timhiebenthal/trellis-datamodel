import type { Entity } from '$lib/types';

export type SortDirection = 'asc' | 'desc';

/**
 * Group entities by their domain field(s)
 * Entities without domains go into "Unassigned" group
 * All groups are sorted by label according to sortDirection (default 'asc')
 *
 * @param entities - Array of entities to group
 * @param sortDirection - Sort direction for entities within each group
 * @returns Map with domain keys and entity arrays as values
 */
export function groupEntitiesByDomain(entities: Entity[], sortDirection: SortDirection = 'asc'): Map<string, Entity[]> {
	const groupMap = new Map<string, Entity[]>();

	function getDomainsForGrouping(entity: Entity): string[] {
		const domains = Array.isArray(entity.domains)
			? entity.domains.map((domain) => domain.trim()).filter(Boolean)
			: [];
		if (domains.length > 0) {
			return Array.from(new Set(domains));
		}
		const singleDomain = entity.domain?.trim();
		return singleDomain ? [singleDomain] : [];
	}

	entities.forEach((entity) => {
		const domains = getDomainsForGrouping(entity);
		const targetDomains = domains.length > 0 ? domains : ['Unassigned'];

		targetDomains.forEach((domain) => {
			if (!groupMap.has(domain)) {
				groupMap.set(domain, []);
			}

			groupMap.get(domain)!.push(entity);
		});
	});

	// De-duplicate and sort every group by label
	groupMap.forEach((group, key) => {
		const uniqueMap = new Map<string, Entity>();
		group.forEach((entity) => {
			if (!uniqueMap.has(entity.id)) {
				uniqueMap.set(entity.id, entity);
			}
		});
		const sorted = Array.from(uniqueMap.values()).sort((a, b) => {
			const cmp = a.label.localeCompare(b.label);
			return sortDirection === 'desc' ? -cmp : cmp;
		});
		groupMap.set(key, sorted);
	});

	return groupMap;
}

const TYPE_GROUP_ORDER = ['Dimensions', 'Facts', 'Unclassified'] as const;
const TYPE_GROUP_LABELS: Record<string, string> = {
	dimension: 'Dimensions',
	fact: 'Facts',
	unclassified: 'Unclassified',
};

/**
 * Group entities by their entity_type (Dimensions / Facts / Unclassified)
 * Entities with missing entity_type go into "Unclassified"
 * Groups appear in order: Dimensions, Facts, Unclassified (empty groups omitted)
 *
 * @param entities - Array of entities to group
 * @param sortDirection - Sort direction for entities within each group
 * @returns Map with type-group keys and entity arrays as values
 */
export function groupEntitiesByType(entities: Entity[], sortDirection: SortDirection = 'asc'): Map<string, Entity[]> {
	const groupMap = new Map<string, Entity[]>();

	entities.forEach((entity) => {
		const key = TYPE_GROUP_LABELS[entity.entity_type ?? 'unclassified'] ?? 'Unclassified';
		if (!groupMap.has(key)) {
			groupMap.set(key, []);
		}
		groupMap.get(key)!.push(entity);
	});

	// Sort each group by label
	groupMap.forEach((group, key) => {
		const sorted = [...group].sort((a, b) => {
			const cmp = a.label.localeCompare(b.label);
			return sortDirection === 'desc' ? -cmp : cmp;
		});
		groupMap.set(key, sorted);
	});

	// Return in canonical order (Dimensions → Facts → Unclassified)
	const ordered = new Map<string, Entity[]>();
	TYPE_GROUP_ORDER.forEach((key) => {
		if (groupMap.has(key)) ordered.set(key, groupMap.get(key)!);
	});
	return ordered;
}

/**
 * Group entities by their tags
 * Entities with multiple tags appear in multiple groups
 * Entities without tags go into "Unassigned" group
 * Within each group, entities are sorted alphabetically by label
 *
 * @param entities - Array of entities to group
 * @returns Map with tag keys and entity arrays as values
 */
export function groupEntitiesByTag(entities: Entity[]): Map<string, Entity[]> {
	const groupMap = new Map<string, Entity[]>();

	entities.forEach((entity) => {
		const entityTags = entity.tags && entity.tags.length > 0 ? entity.tags : ['Unassigned'];

		entityTags.forEach((tag) => {
			if (!groupMap.has(tag)) {
				groupMap.set(tag, []);
			}

			groupMap.get(tag)!.push(entity);
		});
	});

	// Sort each group alphabetically by label, and remove duplicates within groups
	groupMap.forEach((group) => {
		// Remove duplicates by entity id
		const uniqueMap = new Map<string, Entity>();
		group.forEach((entity) => {
			uniqueMap.set(entity.id, entity);
		});

		// Replace with unique sorted entities
		const sortedEntities = Array.from(uniqueMap.values());
		sortedEntities.sort((a, b) => a.label.localeCompare(b.label));

		// Update the map with sorted unique entities
		const index = Array.from(groupMap.keys()).indexOf(
			Array.from(groupMap.entries()).find(([, v]) => v === group)?.[0] || ''
		);
		if (index !== -1) {
			const key = Array.from(groupMap.keys())[index];
			groupMap.set(key, sortedEntities);
		}
	});

	return groupMap;
}
