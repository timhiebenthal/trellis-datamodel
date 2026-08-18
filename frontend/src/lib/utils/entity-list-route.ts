const ENTITY_LIST_PATH = '/entity-list';
const CANVAS_PATH = '/canvas';

export function getEntityDetailPath(entityId: string): string {
	return `${ENTITY_LIST_PATH}/${encodeURIComponent(entityId)}`;
}

export function getCanvasFilterPath(entityIds: string[]): string {
	if (entityIds.length === 0) return CANVAS_PATH;
	return `${CANVAS_PATH}?entities=${encodeURIComponent(entityIds.join(','))}`;
}

export function getEntityIdFromPath(pathname: string): string | null {
	const match = pathname.match(/^\/entity-list\/([^/]+)\/?$/);
	if (!match) return null;

	try {
		return decodeURIComponent(match[1]);
	} catch {
		return null;
	}
}

export function isEntityDetailPath(pathname: string): boolean {
	return getEntityIdFromPath(pathname) !== null;
}
