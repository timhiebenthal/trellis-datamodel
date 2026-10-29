import type { EntityRole } from '$lib/types';

/**
 * Role names to display for an entity: `role` (falling back to `label`),
 * empty ones dropped, deduplicated case-insensitively keeping the first spelling.
 */
export function uniqueRoleNames(roles: EntityRole[] | undefined): string[] {
	const names = (roles || []).map((r) => r.role || r.label || '');
	const seen = new Set<string>();
	return names.filter((role) => {
		if (!role) return false;
		const key = role.toLowerCase();
		if (seen.has(key)) return false;
		seen.add(key);
		return true;
	});
}
