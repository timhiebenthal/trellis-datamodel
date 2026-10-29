export const DEFAULT_NODE_WIDTH = 320;
export const DEFAULT_PANEL_HEIGHT = 200;
export const MIN_NODE_WIDTH = 280;
export const MAX_NODE_WIDTH = 600;
export const MIN_PANEL_HEIGHT = 120;
export const MAX_PANEL_HEIGHT = 600;

export type ResizeDimension = 'width' | 'height';

/**
 * Node-data patch for a resize drag: the initial size plus the pointer delta,
 * clamped to the allowed range (`width` for the node, `panelHeight` for the column panel).
 */
export function computeResizePatch(
	type: ResizeDimension,
	initial: number,
	delta: number,
): { width: number } | { panelHeight: number } {
	if (type === 'width') {
		return { width: Math.min(MAX_NODE_WIDTH, Math.max(MIN_NODE_WIDTH, initial + delta)) };
	}
	return { panelHeight: Math.min(MAX_PANEL_HEIGHT, Math.max(MIN_PANEL_HEIGHT, initial + delta)) };
}
