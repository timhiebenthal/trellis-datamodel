import type { OriginEntry } from '$lib/types';

export function stringifyOrigin(entries?: OriginEntry[]): string {
	if (!entries?.length) {
		return '';
	}

	return entries
		.flatMap((entry) =>
			Object.entries(entry).map(([key, value]) => (key ? `${key}: ${value}` : value))
		)
		.join(' | ');
}
