import type { Node } from '@xyflow/svelte';
import type { EntityData } from '$lib/types';
import { formatEntityType, formatAnnotationType, formatRelationshipType, formatRelationshipKeys } from './excel-export';

/**
 * Prepares a value for a GFM pipe table cell: single-line text and no raw `|` characters.
 * Newlines break table rows; unescaped `|` adds spurious columns (e.g. DH1 | DH2 origins).
 * HTML entity `&#124;` renders as a pipe in virtually all Markdown viewers and avoids
 * backslash-escape quirks across renderers.
 */
function markdownTableCell(value: unknown): string {
	const s = String(value ?? '')
		.replace(/\r\n|\n|\r/g, ' ')
		.replace(/\t/g, ' ');
	return s.replace(/\|/g, '&#124;');
}

/**
 * Formats entity data as markdown document.
 *
 * @param entity - Entity data from EntityDetailModal
 * @param attributes - Attributes array from entityAttributes derived state
 * @param edges - All edges from edges store
 * @param allNodes - All nodes for relationship lookup
 * @param entityId - The entity ID (fallback if not in entity object)
 * @returns Formatted markdown string
 */
export function formatEntityAsMarkdown(
	entity: EntityData,
	attributes: Array<{ name: string; type: string; description?: string; origin?: string }>,
	edges: any[],
	allNodes: Node[],
	entityId: string,
	isDimensional: boolean = true
): string {
	const lines: string[] = [];

	// Title
	lines.push(`# ${entity.label}`);
	lines.push('');

	// Metadata section
	if (isDimensional) {
		lines.push(`**Type:** ${formatEntityType(entity.entity_type)}`);
	}
	lines.push(`**7W Annotation:** ${formatAnnotationType(entity.annotation_type)}`);
	lines.push(`**Domain(s):** ${entity.domains?.join(', ') || entity.domain || '-'}`);
	lines.push(`**Tags:** ${entity.tags?.join(', ') || '-'}`);
	lines.push(`**Source Systems:** ${entity.source_system?.join(', ') || '-'}`);
	lines.push(`**Description:** ${entity.description || '-'}`);
	lines.push(`**dbt Model:** ${entity.dbt_model || '-'}`);
	lines.push(`**Additional Models:** ${entity.additional_models?.join(', ') || '-'}`);
	lines.push('');

	// Attributes section
	lines.push('## Attributes');
	lines.push('');

	if (attributes.length === 0) {
		lines.push('No attributes defined');
	} else {
		lines.push('| Name | Type | Description | Origin |');
		lines.push('|------|------|-------------|--------|');

		for (const attr of attributes) {
			const name = markdownTableCell(attr.name);
			const type = markdownTableCell(attr.type);
			const description = markdownTableCell(attr.description ?? '');
			const origin = markdownTableCell(attr.origin ?? '');
			lines.push(`| ${name} | ${type} | ${description} | ${origin} |`);
		}
	}

	lines.push('');

	// Relationships section
	lines.push('## Relationships');
	lines.push('');

	// Filter edges where source or target matches entityId
	const relevantEdges = edges.filter(
		edge => edge.source === entityId || edge.target === entityId
	);

	if (relevantEdges.length === 0) {
		lines.push('No relationships defined');
	} else {
		for (const edge of relevantEdges) {
			const isOutgoing = edge.source === entityId;
			const relatedEntityId = isOutgoing ? edge.target : edge.source;
			const relatedEntity = allNodes.find(n => n.id === relatedEntityId);
			const relatedEntityName = relatedEntity?.data?.label || relatedEntityId;
			// Prefer the concrete join keys (source_field = target_field); fall back to the
			// business label, then "-", when keys are unavailable.
			const joinKeys = formatRelationshipKeys(edge.data);
			const via = joinKeys ?? `"${edge.data?.label || '-'}"`;
			const relationshipType = formatRelationshipType(edge.data?.type || 'unknown');
			const direction = isOutgoing ? 'Outgoing' : 'Incoming';

			lines.push(`- **${relatedEntityName}** via ${via} (${relationshipType}, ${direction})`);
		}
	}

	lines.push('');

	return lines.join('\n');
}
