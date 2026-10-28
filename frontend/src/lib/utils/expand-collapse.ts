import type { Node } from '@xyflow/svelte';

/**
 * Decide the next expand/collapse state for the navbar toggle.
 *
 * The decision is derived from what is actually rendered, not from the
 * persisted toggle flag: if the flag and the canvas ever desync (the flag
 * starts as `true` before localStorage loads, and boot may re-collapse), a
 * blind toggle would no-op. Anything collapsed means the next action is
 * "expand"; otherwise "collapse".
 */
export function nextExpandCollapseState(nodes: Node[]): boolean {
    const entityNodes = nodes.filter((n) => n.type === 'entity');
    if (entityNodes.length === 0) return true;
    return entityNodes.some((n) => (n.data as { collapsed?: boolean })?.collapsed ?? false);
}
