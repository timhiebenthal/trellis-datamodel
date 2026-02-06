import type { Entity } from '$lib/types';

/**
 * Group entities by their domain field(s)
 * Entities without domains go into "Unassigned" group
 * "Unassigned" entities are sorted alphabetically by label
 *
 * @param entities - Array of entities to group
 * @returns Map with domain keys and entity arrays as values
 */
export function groupEntitiesByDomain(entities: Entity[]): Map<string, Entity[]> {
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

	// De-duplicate within groups (multi-domain can add the same entity multiple times)
	groupMap.forEach((group, key) => {
		const uniqueMap = new Map<string, Entity>();
		group.forEach((entity) => {
			if (!uniqueMap.has(entity.id)) {
				uniqueMap.set(entity.id, entity);
			}
		});
		groupMap.set(key, Array.from(uniqueMap.values()));
	});

	// Sort "Unassigned" group alphabetically by label
	if (groupMap.has('Unassigned')) {
		const unassignedGroup = groupMap.get('Unassigned')!;
		unassignedGroup.sort((a, b) => a.label.localeCompare(b.label));
	}

	return groupMap;
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
