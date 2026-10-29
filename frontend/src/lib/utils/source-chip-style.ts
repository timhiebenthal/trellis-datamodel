const FALLBACK_COLORS = [
	'#3B82F6', // blue-500
	'#8B5CF6', // violet-500
	'#EC4899', // pink-500
	'#F59E0B', // amber-500
	'#10B981', // emerald-500
	'#EF4444', // red-500
	'#06B6D4', // cyan-500
	'#6366F1', // indigo-500
];

/**
 * Inline style for a source-system chip: the configured colour from
 * canvas_layout.yml `source_colors`, or a deterministic fallback hashed from the name.
 */
export function getSourceChipStyle(
	sourceSystem: string,
	sourceColors: Record<string, string>,
): string {
	const customColor = sourceColors[sourceSystem];
	if (customColor) {
		return `background-color: ${customColor}; color: white; border: 1px solid ${customColor};`;
	}

	let hash = 0;
	for (let i = 0; i < sourceSystem.length; i++) {
		hash = sourceSystem.charCodeAt(i) + ((hash << 5) - hash);
	}
	const bgColor = FALLBACK_COLORS[Math.abs(hash) % FALLBACK_COLORS.length];

	return `background-color: ${bgColor}20; color: ${bgColor}; border: 1px solid ${bgColor}40;`;
}
