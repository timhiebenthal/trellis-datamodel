import * as XLSX from 'xlsx';
import type { Node } from '@xyflow/svelte';
import type { AnnotationType, EntityData } from '$lib/types';

/**
 * Sanitizes a filename by removing or replacing special characters.
 * Removes: & / \ : * ? " < > |
 * Keeps: spaces, alphanumeric characters, hyphens, underscores
 * Truncates to 200 characters if needed.
 *
 * @param name - The filename to sanitize
 * @returns A safe filename string
 */
export function sanitizeFilename(name: string): string {
	// Replace special characters with empty string or safe alternatives
	let sanitized = name
		.replace(/[&/\\:*?"<>|]/g, '')
		.trim();

	// Truncate to 200 characters if needed
	if (sanitized.length > 200) {
		sanitized = sanitized.substring(0, 200);
	}

	return sanitized;
}

/** Excel worksheet tab names cannot contain these characters (see spec / Excel limits). */
const SHEET_NAME_FORBIDDEN = /[\[\]:*?/\\]/g;
const MAX_SHEET_NAME_LEN = 31;

/**
 * Produces a unique Excel sheet name from an entity label (≤31 chars, no forbidden characters).
 * Mutates `usedNames` to record the returned name.
 */
export function sanitizeSheetName(label: string, usedNames: Set<string>): string {
	let base = label.replace(SHEET_NAME_FORBIDDEN, '').trim();
	if (base.length === 0) {
		base = 'Entity';
	}

	let counter = 1;
	while (true) {
		const suffix = counter === 1 ? '' : `_${counter}`;
		const maxBaseLen = MAX_SHEET_NAME_LEN - suffix.length;
		const truncatedBase = base.slice(0, Math.max(1, maxBaseLen));
		const candidate = (truncatedBase + suffix).slice(0, MAX_SHEET_NAME_LEN);
		if (!usedNames.has(candidate)) {
			usedNames.add(candidate);
			return candidate;
		}
		counter += 1;
	}
}

/**
 * Returns the current date in YYYYMMDD format.
 *
 * @returns Date string in YYYYMMDD format (e.g., "20250205")
 */
export function getDateString(): string {
	const now = new Date();
	const year = now.getFullYear();
	const month = String(now.getMonth() + 1).padStart(2, '0');
	const day = String(now.getDate()).padStart(2, '0');
	return `${year}${month}${day}`;
}

/**
 * Formats an entity type string to a human-readable format.
 *
 * @param type - The entity type ('dimension', 'fact', 'unclassified', or undefined)
 * @returns Formatted entity type string
 */
export function formatEntityType(type?: string): string {
	const typeMap: Record<string, string> = {
		dimension: 'Dimension',
		fact: 'Fact',
		unclassified: 'Unclassified'
	};

	return typeMap[type || ''] || 'Unclassified';
}

/**
 * Formats an annotation type to a human-readable format.
 *
 * @param type - The annotation type or undefined
 * @returns Formatted annotation type string
 */
export function formatAnnotationType(type?: AnnotationType): string {
	const typeMap: Record<string, string> = {
		who: 'Who',
		what: 'What',
		when: 'When',
		where: 'Where',
		how: 'How',
		why: 'Why',
		how_many: 'How Many'
	};

	return typeMap[type || ''] || 'None';
}

/**
 * Formats a relationship type to a standard notation.
 *
 * @param type - The relationship type string
 * @returns Formatted relationship type (e.g., '1:N', 'N:1', '1:1', 'N:N')
 */
export function formatRelationshipType(type: string): string {
	const typeMap: Record<string, string> = {
		one_to_many: '1:N',
		many_to_one: 'N:1',
		one_to_one: '1:1',
		many_to_many: 'N:N'
	};

	return typeMap[type] || 'Unknown';
}

/**
 * Formats the concrete join keys of a relationship edge as a fully-qualified
 * `source_model.source_field = target_model.target_field` expression, matching the
 * canvas lineage view (e.g. `invoice_recipient.invoice_recipient_id = dim__lead.customer_number`).
 *
 * Keys come from `data.source_field` / `data.target_field`. The table qualifier comes from
 * `data.models[0].source_model_name` / `target_model_name`, falling back to the supplied
 * entity names (the canvas does the same), lowercased to match the lineage rendering. When a
 * qualifier is unavailable the field is emitted unprefixed. Returns null when either key is
 * missing so callers can fall back to the business label.
 *
 * @param data - The edge `data` object
 * @param sourceName - Fallback name for the source side (e.g. the source entity label)
 * @param targetName - Fallback name for the target side (e.g. the target entity label)
 * @returns A qualified `source = target` join expression, or null when keys are unavailable
 */
export function formatRelationshipKeys(
	data: Record<string, unknown> | null | undefined,
	sourceName?: string | null,
	targetName?: string | null
): string | null {
	const sourceField = data?.source_field as string | undefined;
	const targetField = data?.target_field as string | undefined;
	if (!sourceField || !targetField) {
		return null;
	}

	const models = data?.models as Array<Record<string, unknown>> | undefined;
	const sourceModel = (models?.[0]?.source_model_name as string | undefined) || sourceName || undefined;
	const targetModel = (models?.[0]?.target_model_name as string | undefined) || targetName || undefined;

	const sourceExpr = sourceModel ? `${sourceModel.toLowerCase()}.${sourceField}` : sourceField;
	const targetExpr = targetModel ? `${targetModel.toLowerCase()}.${targetField}` : targetField;

	return `${sourceExpr} = ${targetExpr}`;
}

/**
 * Generates Overview sheet with entity metadata in key-value format
 * @param entity - Entity data from EntityDetailModal
 * @returns Configured XLSX worksheet with bold headers and column widths
 * @note Cell styling (bold headers) requires SheetJS Pro. Community Edition ignores the .s property.
 */
export function generateOverviewSheet(entity: EntityData, isDimensional: boolean = true): XLSX.WorkSheet {
	// Create 2-column array: Field | Value
	const overviewData: (string | undefined)[][] = [
		['Field', 'Value'],
		['Entity Name', entity.label],
		...(isDimensional ? [['Entity Type', formatEntityType(entity.entity_type)]] : []),
		['Annotation (7W)', formatAnnotationType(entity.annotation_type)],
		['Domain(s)', entity.domains?.join(', ') || entity.domain || '-'],
		['Tags', entity.tags?.join(', ') || '-'],
		['Source Systems', entity.source_system?.join(', ') || '-'],
		['Description', entity.description || '-'],
		['dbt Model', entity.dbt_model || '-'],
		['Additional Models', entity.additional_models?.join(', ') || '-']
	];

	const ws = XLSX.utils.aoa_to_sheet(overviewData);

	// Attempt to set bold headers (requires SheetJS Pro for cell styling)
	// This code is kept for future compatibility but has no effect in Community Edition
	const range = XLSX.utils.decode_range(ws['!ref'] || 'A1');
	for (let col = range.s.c; col <= range.e.c; col++) {
		const cell_address = XLSX.utils.encode_cell({ r: 0, c: col });
		if (!ws[cell_address]) continue;
		if (!ws[cell_address].s) ws[cell_address].s = {};
		ws[cell_address].s.font = { bold: true };
	}

	// Set column widths
	ws['!cols'] = [{ wch: 20 }, { wch: 60 }];

	return ws;
}

/**
 * Generates Relationships sheet showing connected entities
 * @param edges - All edges from edges store
 * @param entityId - Current entity ID to filter relationships
 * @param allNodes - All nodes for looking up entity labels
 * @returns Configured XLSX worksheet with bold headers and column widths
 * @note Cell styling (bold headers) requires SheetJS Pro. Community Edition ignores the .s property.
 */
export function generateRelationshipsSheet(
	edges: any[], // Edge type from @xyflow/svelte
	entityId: string,
	allNodes: Node[]
): XLSX.WorkSheet {
	// Filter edges where source or target matches entityId
	const relevantEdges = edges.filter(
		edge => edge.source === entityId || edge.target === entityId
	);

	// Create 4-column array: Related Entity | Relationship Label | Relationship Type | Direction
	const relationshipsData = [
		['Related Entity', 'Relationship Label', 'Relationship Type', 'Direction'],
		...relevantEdges.map(edge => {
			const isOutgoing = edge.source === entityId;
			const relatedEntityId = isOutgoing ? edge.target : edge.source;
			const relatedEntity = allNodes.find(n => n.id === relatedEntityId);
			const sourceName = (allNodes.find(n => n.id === edge.source)?.data?.label as string) || edge.source;
			const targetName = (allNodes.find(n => n.id === edge.target)?.data?.label as string) || edge.target;

			return [
				relatedEntity?.data?.label || relatedEntityId,
				formatRelationshipKeys(edge.data, sourceName, targetName) ?? (edge.data?.label || '-'),
				formatRelationshipType(edge.data?.type || 'unknown'),
				isOutgoing ? 'Outgoing' : 'Incoming'
			];
		})
	];

	// If no relationships, show message
	if (relevantEdges.length === 0) {
		relationshipsData.push(['No relationships defined', '', '', '']);
	}

	const ws = XLSX.utils.aoa_to_sheet(relationshipsData);

	// Attempt to set bold headers (requires SheetJS Pro for cell styling)
	// This code is kept for future compatibility but has no effect in Community Edition
	const range = XLSX.utils.decode_range(ws['!ref'] || 'A1');
	for (let col = range.s.c; col <= range.e.c; col++) {
		const cell_address = XLSX.utils.encode_cell({ r: 0, c: col });
		if (!ws[cell_address]) continue;
		if (!ws[cell_address].s) ws[cell_address].s = {};
		ws[cell_address].s.font = { bold: true };
	}

	// Set column widths
	ws['!cols'] = [{ wch: 25 }, { wch: 30 }, { wch: 20 }, { wch: 15 }];

	return ws;
}

/**
 * Generates Attributes sheet with tabular list of entity fields
 * @param attributes - Array of attributes from entityAttributes derived state
 * @returns Configured XLSX worksheet with bold headers and column widths
 * @note Cell styling (bold headers) requires SheetJS Pro. Community Edition ignores the .s property.
 */
export function generateAttributesSheet(
	attributes: Array<{ name: string; type: string; description?: string; origin?: string }>
): XLSX.WorkSheet {
	// Create 4-column array: Name | Type | Description | Origin
	const attributesData = [
		['Name', 'Type', 'Description', 'Origin'],
		...attributes.map(attr => [
			attr.name,
			attr.type,
			attr.description || '',
			attr.origin || ''
		])
	];

	// If no attributes, show message
	if (attributes.length === 0) {
		attributesData.push(['No attributes defined', '', '', '']);
	}

	const ws = XLSX.utils.aoa_to_sheet(attributesData);

	// Attempt to set bold headers (requires SheetJS Pro for cell styling)
	// This code is kept for future compatibility but has no effect in Community Edition
	const range = XLSX.utils.decode_range(ws['!ref'] || 'A1');
	for (let col = range.s.c; col <= range.e.c; col++) {
		const cell_address = XLSX.utils.encode_cell({ r: 0, c: col });
		if (!ws[cell_address]) continue;
		if (!ws[cell_address].s) ws[cell_address].s = {};
		ws[cell_address].s.font = { bold: true };
	}

	// Set column widths
	ws['!cols'] = [{ wch: 25 }, { wch: 15 }, { wch: 40 }, { wch: 35 }];

	return ws;
}

/**
 * Exports entity data to Excel (.xlsx) file with three sheets
 * @param entity - Entity data from EntityDetailModal
 * @param attributes - Attributes array from entityAttributes derived state
 * @param edges - All edges from edges store
 * @param allNodes - All nodes for relationship lookup
 * @param entityId - The entity ID (fallback if not in entity object)
 * @throws Error if Excel generation or download fails
 */
export function exportEntityToExcel(
	entity: EntityData,
	attributes: Array<{ name: string; type: string; description?: string; origin?: string }>,
	edges: any[],
	allNodes: Node[],
	entityId: string,
	isDimensional: boolean = true
): void {
	try {
		// Generate three sheets using generators
		const overviewSheet = generateOverviewSheet(entity, isDimensional);
		const attributesSheet = generateAttributesSheet(attributes);
		const relationshipsSheet = generateRelationshipsSheet(edges, entityId, allNodes);

		// Create workbook
		const wb = XLSX.utils.book_new();

		// Append sheets with proper names
		XLSX.utils.book_append_sheet(wb, overviewSheet, 'Overview');
		XLSX.utils.book_append_sheet(wb, attributesSheet, 'Attributes');
		XLSX.utils.book_append_sheet(wb, relationshipsSheet, 'Relationships');

		// Generate filename with sanitized entity name and date
		const filename = `${sanitizeFilename(entity.label)}_export_${getDateString()}.xlsx`;

		// Trigger download
		XLSX.writeFile(wb, filename);
	} catch (error) {
		console.error('Excel export failed:', error);
		throw new Error(
			`Failed to export entity to Excel: ${error instanceof Error ? error.message : 'Unknown error'}`
		);
	}
}

/**
 * Generates a "Data Model Overview" sheet with:
 *  1. A short explanation of the model structure (entity/relationship counts, export date).
 *  2. An entity directory table: Name | Type | Description | Domains | Tags.
 *  3. A relationships table: From | To | Label | Type.
 */
export function generateDataModelOverviewSheet(
	entityNodes: Node[],
	edges: any[],
	isDimensional: boolean = true
): XLSX.WorkSheet {
	const entityCount = entityNodes.length;
	const relCount = edges.length;

	const rows: (string | number | undefined)[][] = [];

	// --- Section 1: About this export ---
	rows.push(['About this Data Model Export']);
	rows.push(['Exported on', getDateString()]);
	rows.push(['Total entities', entityCount]);
	if (isDimensional) {
		const factCount = entityNodes.filter(
			(n) => (n.data as unknown as EntityData).entity_type === 'fact'
		).length;
		const dimensionCount = entityNodes.filter(
			(n) => (n.data as unknown as EntityData).entity_type === 'dimension'
		).length;
		rows.push(['  Facts', factCount]);
		rows.push(['  Dimensions', dimensionCount]);
		rows.push(['  Unclassified', entityCount - factCount - dimensionCount]);
	}
	rows.push(['Total relationships', relCount]);
	rows.push([]);
	rows.push([
		'Structure: each following tab contains the attributes (Name / Type / Description) of one entity.'
	]);
	rows.push([]);

	// --- Section 2: Entity directory ---
	rows.push(['Entity Directory']);
	if (isDimensional) {
		rows.push(['Name', 'Type', 'Description', 'Domains', 'Tags']);
	} else {
		rows.push(['Name', 'Description', 'Domains', 'Tags']);
	}
	for (const node of entityNodes) {
		const d = node.data as unknown as EntityData;
		const domains = Array.isArray(d.domains) && d.domains.length > 0
			? d.domains.join(', ')
			: d.domain ?? '';
		if (isDimensional) {
			rows.push([
				d.label ?? '',
				formatEntityType(d.entity_type),
				d.description ?? '',
				domains,
				d.tags?.join(', ') ?? ''
			]);
		} else {
			rows.push([
				d.label ?? '',
				d.description ?? '',
				domains,
				d.tags?.join(', ') ?? ''
			]);
		}
	}
	rows.push([]);

	// --- Section 3: Relationships ---
	rows.push(['Relationships']);
	rows.push(['From', 'To', 'Label', 'Type']);
	if (edges.length === 0) {
		rows.push(['No relationships defined', '', '', '']);
	} else {
		const nodeById = new Map(entityNodes.map((n) => [n.id, (n.data as unknown as EntityData).label ?? n.id]));
		for (const edge of edges) {
			rows.push([
				nodeById.get(edge.source) ?? edge.source,
				nodeById.get(edge.target) ?? edge.target,
				formatRelationshipKeys(edge.data, nodeById.get(edge.source), nodeById.get(edge.target)) ?? (edge.data?.label ?? ''),
				formatRelationshipType(edge.data?.type ?? 'unknown')
			]);
		}
	}

	const ws = XLSX.utils.aoa_to_sheet(rows);
	ws['!cols'] = [{ wch: 30 }, { wch: 16 }, { wch: 55 }, { wch: 28 }, { wch: 30 }];
	return ws;
}

function draftedFieldsToAttributes(
	entity: EntityData
): Array<{ name: string; type: string; description?: string; origin?: string }> {
	const fields = entity.drafted_fields ?? [];
	return fields.map((f) => ({
		name: f.name,
		type: f.datatype,
		description: f.description,
		origin: f.origin
	}));
}

/**
 * Exports all entities to a single workbook.
 * Sheet 1 ("Overview"): model summary, entity directory, and relationship list.
 * Remaining sheets: one tab per entity showing its attributes (Name / Type / Description).
 * @param edges SvelteFlow edge objects — used for the overview relationships table.
 */
export function exportDataModelToExcel(nodes: Node[], edges: any[], isDimensional: boolean = true): void {
	try {
		const entityNodes = nodes.filter((n) => n.type === 'entity');
		const wb = XLSX.utils.book_new();
		const usedSheetNames = new Set<string>();

		// Always include the overview sheet first
		const overviewSheet = generateDataModelOverviewSheet(entityNodes, edges, isDimensional);
		XLSX.utils.book_append_sheet(wb, overviewSheet, sanitizeSheetName('Overview', usedSheetNames));

		if (entityNodes.length === 0) {
			const ws = XLSX.utils.aoa_to_sheet([['No entities in this data model.']]);
			XLSX.utils.book_append_sheet(wb, ws, sanitizeSheetName('Entities', usedSheetNames));
		} else {
			for (const node of entityNodes) {
				const data = node.data as unknown as EntityData;
				const sheetName = sanitizeSheetName(data.label || 'Entity', usedSheetNames);
				const attributes = draftedFieldsToAttributes(data);
				const sheet = generateAttributesSheet(attributes);
				XLSX.utils.book_append_sheet(wb, sheet, sheetName);
			}
		}

		const filename = `DataModel_export_${getDateString()}.xlsx`;
		XLSX.writeFile(wb, filename);
	} catch (error) {
		console.error('Data model Excel export failed:', error);
		throw new Error(
			`Failed to export data model to Excel: ${error instanceof Error ? error.message : 'Unknown error'}`
		);
	}
}
