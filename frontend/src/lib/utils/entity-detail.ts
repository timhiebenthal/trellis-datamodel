import type { Edge, Node } from '@xyflow/svelte';
import type {
	AnnotationEntry,
	BusinessEventProcess,
	DraftedField,
	EntityData,
	EntityRole,
	ModelSchemaColumn
} from '$lib/types';
import { formatRelationshipKeys, formatRelationshipType } from './excel-export';

/** How many chips a chip list shows before collapsing behind "+N more". */
export const CHIP_DISPLAY_LIMIT = 6;

/** Trimmed, de-duplicated domain list; falls back to the legacy single `domain`. */
export function normalizeDomains(domains?: string[], domain?: string): string[] {
	const list = Array.isArray(domains) && domains.length > 0 ? domains : domain ? [domain] : [];
	return Array.from(new Set(list.map((item) => item.trim()).filter(Boolean)));
}

/** The chips to render: all of them, or the first `CHIP_DISPLAY_LIMIT`. */
export function visibleChips(items: string[], showAll: boolean): string[] {
	return showAll ? items : items.slice(0, CHIP_DISPLAY_LIMIT);
}

/** Sorted, trimmed set of every domain used across the canvas entities. */
export function collectUniqueDomains(nodes: Node[]): string[] {
	const domains = new Set<string>();
	nodes.forEach((node) => {
		const data = node.data as unknown as EntityData;
		const domainList = Array.isArray(data.domains) && data.domains.length > 0
			? data.domains
			: data.domain
				? [data.domain]
				: [];
		domainList.forEach((domain) => {
			if (domain && domain.trim()) {
				domains.add(domain.trim());
			}
		});
	});
	return Array.from(domains).sort();
}

/** Sorted, trimmed set of every tag used across the canvas entities. */
export function collectUniqueTags(nodes: Node[]): string[] {
	const tags = new Set<string>();
	nodes.forEach((node) => {
		const nodeTags = (node.data as unknown as EntityData)?.tags || [];
		nodeTags.forEach((tag) => {
			if (tag && tag.trim()) {
				tags.add(tag.trim());
			}
		});
	});
	return Array.from(tags).sort();
}

/**
 * Deduplicate roles by name for display (multiple entries can exist per role when
 * sourced from different processes). Case-insensitive, keyed on `role` or `label`
 * (some entries only have a label). The first entry per name wins.
 */
export function dedupeRolesByName(roles: EntityRole[]): EntityRole[] {
	const seen = new Set<string>();
	return roles.filter((role) => {
		const key = (role.role || role.label || '').toLowerCase();
		if (seen.has(key)) return false;
		seen.add(key);
		return true;
	});
}

/** Processes whose annotations reference `dimensionId` in `role`. */
export function getProcessesForRole(
	processes: BusinessEventProcess[],
	dimensionId: string,
	role: EntityRole
): BusinessEventProcess[] {
	const roleName = role.role;
	return processes.filter((proc) => {
		if (!proc.annotations_superset) return false;
		return Object.values(proc.annotations_superset).some((annotations: AnnotationEntry[]) =>
			annotations.some(
				(ann: AnnotationEntry) => ann.dimension_id === dimensionId && ann.role === roleName
			)
		);
	});
}

/**
 * Validate adding a role named `input`. Returns the new list, `null` for blank input
 * (nothing to do), or an error message when the role already exists.
 */
export function addRoleByName(roles: EntityRole[], input: string): EntityRole[] | null | { error: string } {
	const trimmed = input.trim();
	if (!trimmed) return null;
	if (roles.some((r) => r.role === trimmed)) {
		return { error: `Role "${trimmed}" already exists` };
	}
	return [...roles, { role: trimmed }];
}

/**
 * Rename every entry named `from` (one role can have several sourced entries) to `to`.
 * Returns the new list, or an error message for an empty or colliding name.
 */
export function renameRole(roles: EntityRole[], from: string, to: string): EntityRole[] | { error: string } {
	const trimmed = to.trim();
	if (!trimmed) {
		return { error: 'Role name cannot be empty' };
	}
	if (trimmed !== from && roles.some((r) => r.role === trimmed)) {
		return { error: `Role "${trimmed}" already exists` };
	}
	return roles.map((r) => (r.role === from ? { ...r, role: trimmed } : r));
}

/** Remove every entry sharing the role name. */
export function removeRoleByName(roles: EntityRole[], roleName: string): EntityRole[] {
	return roles.filter((r) => r.role !== roleName);
}

/** Move the item at `from` to index `to` (drag-to-reorder). Returns a new array. */
export function moveItem<T>(items: T[], from: number, to: number): T[] {
	const next = [...items];
	const [moved] = next.splice(from, 1);
	next.splice(to, 0, moved);
	return next;
}

export interface EntityRelationshipRow {
	edgeId: string;
	relatedId: string;
	relatedName: string;
	isOutgoing: boolean;
	cardinality: string;
	keys: string | null;
	label: string;
}

/**
 * Read-only relationships for an entity, derived from the edges that touch it.
 * Mirrors the markdown/Excel export: related entity, direction, cardinality, join keys.
 */
export function buildEntityRelationships(
	entityId: string | undefined,
	edges: Edge[],
	nodes: Node[]
): EntityRelationshipRow[] {
	const id = entityId;
	if (!id) return [];
	return edges
		.filter((e) => e.source === id || e.target === id)
		.map((e) => {
			const isOutgoing = e.source === id;
			const relatedId = isOutgoing ? e.target : e.source;
			const relatedName = (nodes.find((n) => n.id === relatedId)?.data?.label as string) || relatedId;
			const sourceName = (nodes.find((n) => n.id === e.source)?.data?.label as string) || e.source;
			const targetName = (nodes.find((n) => n.id === e.target)?.data?.label as string) || e.target;
			const data = e.data as Record<string, unknown> | undefined;
			return {
				edgeId: e.id,
				relatedId,
				relatedName,
				isOutgoing,
				cardinality: formatRelationshipType((data?.type as string) || 'unknown'),
				keys: formatRelationshipKeys(data, sourceName, targetName),
				label: (data?.label as string) || ''
			};
		});
}

/** The editable form values the dirty check compares against the stored entity. */
export interface EntityFormSnapshot {
	entityName: string;
	entityDescription: string;
	entityDomains: string[];
	entityTags: string[];
	entitySourceSystems: string[];
	sourceInput: string;
	entityType: string;
	annotationType: string | undefined;
	entityRoles: EntityRole[];
	materializedEditCount: number;
	editableDraftedFields: DraftedField[];
}

/**
 * Whether the form differs from the stored entity data.
 *
 * NOTE: like the original inline check, this sorts `form.entityTags`,
 * `form.entitySourceSystems` and `form.entityRoles` IN PLACE — the modal's chip
 * order has always relied on that side effect, so it is preserved deliberately.
 */
export function hasEntityFormChanges(data: EntityData, form: EntityFormSnapshot): boolean {
	const initialDomains = normalizeDomains(data.domains, data.domain);
	const nextDomains = normalizeDomains(form.entityDomains);
	return (
		form.entityName !== (data.label || '') ||
		form.entityDescription !== (data.description || '') ||
		JSON.stringify(nextDomains.sort()) !== JSON.stringify(initialDomains.sort()) ||
		JSON.stringify(form.entityTags.sort()) !== JSON.stringify([...(data.tags || [])].sort()) ||
		JSON.stringify(form.entitySourceSystems.sort()) !==
			JSON.stringify([...(data.source_system || [])].sort()) ||
		form.sourceInput.trim().length > 0 ||
		form.entityType !== (data.entity_type || 'unclassified') ||
		form.annotationType !== data.annotation_type ||
		JSON.stringify(form.entityRoles.sort()) !== JSON.stringify([...(data.roles || [])].sort()) ||
		form.materializedEditCount > 0 ||
		JSON.stringify(form.editableDraftedFields) !== JSON.stringify(data?.drafted_fields || [])
	);
}

type ModelColumn = { name: string; type?: string; description?: string };

/** Description precedence for a materialized column: staged edit > live schema.yml > manifest. */
export function resolveColumnDescription(
	column: ModelColumn,
	edits: Map<string, string>,
	liveDescriptions: Map<string, string>
): string {
	return edits.get(column.name) ?? liveDescriptions.get(column.name) ?? column.description ?? '';
}

/** schema.yml columns to write on save: every materialized column with resolved descriptions. */
export function buildSchemaColumnsForSave(
	columns: ModelColumn[] | undefined,
	edits: Map<string, string>,
	liveDescriptions: Map<string, string>
): ModelSchemaColumn[] {
	return (columns ?? []).map((c) => ({
		name: c.name,
		data_type: c.type,
		description: resolveColumnDescription(c, edits, liveDescriptions)
	}));
}

/** schema.yml columns after materializing `draft`: existing columns plus the draft. */
export function buildMaterializeColumns(
	columns: ModelColumn[] | undefined,
	draft: DraftedField
): ModelSchemaColumn[] {
	return [
		...(columns ?? []).map((c) => ({
			name: c.name,
			data_type: c.type,
			description: c.description ?? ''
		})),
		{
			name: draft.name,
			data_type: draft.datatype && draft.datatype !== 'unknown' ? draft.datatype : 'text',
			description: draft.description ?? ''
		}
	];
}
