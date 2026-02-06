import type { Node } from '@xyflow/svelte';
import type { EntityData } from '$lib/types';
import { formatEntityType, formatAnnotationType, formatRelationshipType } from './excel-export';

/**
 * Escapes pipe characters in markdown table cells to prevent breaking table formatting.
 *
 * @param text - The text to escape
 * @returns Text with pipes escaped as \|
 */
function escapePipes(text: string): string {
	return text.replace(/\|/g, '\\|');
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
	attributes: Array<{ name: string; type: string; description?: string }>,
	edges: any[],
	allNodes: Node[],
	entityId: string
): string {
	const lines: string[] = [];

	// Title
	lines.push(`# ${entity.label}`);
	lines.push('');

	// Metadata section
	lines.push(`**Type:** ${formatEntityType(entity.entity_type)}`);
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
		lines.push('| Name | Type | Description |');
		lines.push('|------|------|-------------|');

		for (const attr of attributes) {
			const name = escapePipes(attr.name);
			const type = escapePipes(attr.type);
			const description = escapePipes(attr.description || '');
			lines.push(`| ${name} | ${type} | ${description} |`);
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
			const relationshipLabel = edge.label || '-';
			const relationshipType = formatRelationshipType(edge.data?.type || 'unknown');
			const direction = isOutgoing ? 'Outgoing' : 'Incoming';

			lines.push(`- **${relatedEntityName}** via "${relationshipLabel}" (${relationshipType}, ${direction})`);
		}
	}

	lines.push('');

	return lines.join('\n');
}
