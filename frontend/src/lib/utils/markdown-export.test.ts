import { describe, it, expect, beforeEach } from 'vitest';
import { formatEntityAsMarkdown } from './markdown-export';
import type { EntityData } from '$lib/types';
import type { Node } from '@xyflow/svelte';

describe('markdown-export utilities', () => {
	let mockEntity: EntityData;
	let mockAttributes: Array<{ name: string; type: string; description?: string; origin?: string }>;
	let mockEdges: any[];
	let mockNodes: Node[];

	beforeEach(() => {
		mockEntity = {
			label: 'Customer',
			entity_type: 'dimension',
			annotation_type: 'who',
			domains: ['Sales', 'Marketing'],
			tags: ['pii', 'core'],
			source_system: ['CRM', 'ERP'],
			description: 'Main customer entity',
			dbt_model: 'model.project.customer',
			additional_models: ['model.project.customer_history']
		};

		mockAttributes = [
			{ name: 'customer_id', type: 'int', description: 'Primary key' },
			{ name: 'customer_name', type: 'varchar', description: 'Full name' },
			{ name: 'email', type: 'varchar', description: 'Email address' }
		];

		mockEdges = [
			{
				id: 'edge1',
				source: 'customer',
				target: 'order',
				data: { label: 'has', type: 'one_to_many' }
			},
			{
				id: 'edge2',
				source: 'address',
				target: 'customer',
				data: { label: 'lives_at', type: 'many_to_one' }
			}
		];

		mockNodes = [
			{ id: 'customer', data: { label: 'Customer' } },
			{ id: 'order', data: { label: 'Order' } },
			{ id: 'address', data: { label: 'Address' } }
		];
	});

	describe('formatEntityAsMarkdown - Complete Entity', () => {
		it('should generate markdown with all fields populated', () => {
			const result = formatEntityAsMarkdown(mockEntity, mockAttributes, mockEdges, mockNodes, 'customer');

			// Check title
			expect(result).toContain('# Customer');

			// Check metadata section
			expect(result).toContain('**Type:** Dimension');
			expect(result).toContain('**7W Annotation:** Who');
			expect(result).toContain('**Domain(s):** Sales, Marketing');
			expect(result).toContain('**Tags:** pii, core');
			expect(result).toContain('**Source Systems:** CRM, ERP');
			expect(result).toContain('**Description:** Main customer entity');
			expect(result).toContain('**dbt Model:** model.project.customer');
			expect(result).toContain('**Additional Models:** model.project.customer_history');

			// Check attributes section
			expect(result).toContain('## Attributes');
			expect(result).toContain('| Name | Type | Description | Origin |');
			expect(result).toContain('| customer_id | int | Primary key |  |');
			expect(result).toContain('| customer_name | varchar | Full name |');

			// Check relationships section
			expect(result).toContain('## Relationships');
			expect(result).toContain('Order');
			expect(result).toContain('Address');
		});

		it('should include markdown table separator', () => {
			const result = formatEntityAsMarkdown(mockEntity, mockAttributes, mockEdges, mockNodes, 'customer');

			// Check for table separator
			expect(result).toContain('|------|------|-------------|--------|');
		});

		it('should have proper line breaks between sections', () => {
			const result = formatEntityAsMarkdown(mockEntity, mockAttributes, mockEdges, mockNodes, 'customer');

			// Should have blank lines between sections
			const lines = result.split('\n');
			expect(lines.length).toBeGreaterThan(10);

			// Check structure: title, blank, metadata lines, blank, attributes, etc.
			expect(lines[0]).toBe('# Customer');
			expect(lines[1]).toBe('');
		});
	});

	describe('formatEntityAsMarkdown - Minimal Entity', () => {
		it('should handle entity with minimal data', () => {
			const minimalEntity: EntityData = {
				label: 'SimpleEntity'
			};

			const result = formatEntityAsMarkdown(minimalEntity, [], [], [], 'simple');

			// Should still have title and sections
			expect(result).toContain('# SimpleEntity');
			expect(result).toContain('**Type:** Unclassified');
			expect(result).toContain('**7W Annotation:** None');
			expect(result).toContain('## Attributes');
			expect(result).toContain('## Relationships');
			expect(result).toContain('No attributes defined');
			expect(result).toContain('No relationships defined');
		});

		it('should use fallback values for undefined fields', () => {
			const entity: EntityData = {
				label: 'Test'
			};

			const result = formatEntityAsMarkdown(entity, [], [], [], 'test');

			// All optional fields should show as "-"
			expect(result).toContain('**Domain(s):** -');
			expect(result).toContain('**Tags:** -');
			expect(result).toContain('**Source Systems:** -');
			expect(result).toContain('**Description:** -');
			expect(result).toContain('**dbt Model:** -');
			expect(result).toContain('**Additional Models:** -');
		});
	});

	describe('formatEntityAsMarkdown - Empty Collections', () => {
		it('should handle empty attributes array', () => {
			const result = formatEntityAsMarkdown(mockEntity, [], mockEdges, mockNodes, 'customer');

			expect(result).toContain('## Attributes');
			expect(result).toContain('No attributes defined');
			expect(result).not.toContain('| Name | Type | Description | Origin |');
		});

		it('should handle empty relationships array', () => {
			const result = formatEntityAsMarkdown(mockEntity, mockAttributes, [], mockNodes, 'customer');

			expect(result).toContain('## Relationships');
			expect(result).toContain('No relationships defined');
		});

		it('should handle entity with no outgoing or incoming edges', () => {
			const isolatedEdges = [
				{
					id: 'edge1',
					source: 'other1',
					target: 'other2',
					data: { label: 'unrelated', type: 'one_to_one' }
				}
			];

			const result = formatEntityAsMarkdown(mockEntity, mockAttributes, isolatedEdges, mockNodes, 'customer');

			expect(result).toContain('No relationships defined');
		});

		it('should handle both empty attributes and relationships', () => {
			const result = formatEntityAsMarkdown(mockEntity, [], [], mockNodes, 'customer');

			expect(result).toContain('No attributes defined');
			expect(result).toContain('No relationships defined');
		});
	});

	describe('formatEntityAsMarkdown - Special Characters', () => {
		it('should encode pipe characters in attribute names as HTML entities', () => {
			const attributesWithPipes = [
				{ name: 'field|with|pipes', type: 'varchar', description: 'Test field' }
			];

			const result = formatEntityAsMarkdown(mockEntity, attributesWithPipes, [], mockNodes, 'customer');

			expect(result).toContain('field&#124;with&#124;pipes');
			expect(result).not.toContain('field|with|pipes');
		});

		it('should encode pipe characters in attribute types as HTML entities', () => {
			const attributesWithPipes = [
				{ name: 'field', type: 'varchar|int', description: 'Test field' }
			];

			const result = formatEntityAsMarkdown(mockEntity, attributesWithPipes, [], mockNodes, 'customer');

			expect(result).toContain('varchar&#124;int');
		});

		it('should encode pipe characters in descriptions as HTML entities', () => {
			const attributesWithPipes = [
				{ name: 'field', type: 'varchar', description: 'A|B|C description' }
			];

			const result = formatEntityAsMarkdown(mockEntity, attributesWithPipes, [], mockNodes, 'customer');

			expect(result).toContain('A&#124;B&#124;C');
		});

		// Real-world origin lines often use " | " between warehouse hops; raw pipes must not split GFM tables.
		it.each([
			{
				label: 'NIP status (DH1 | DH2 / alt)',
				name: 'refund_status_code',
				origin:
					'DH1: DATA_MART_MAIN.T_DIM_NIP_STATUS.REFUND_STATUS | DH2: CBUS_CUSTOMER_REFUND_MASTER.REFUND_STATUS / CBUS_REFUND.REFUND_STATUS',
				expectEncoded: 'DH1: DATA_MART_MAIN.T_DIM_NIP_STATUS.REFUND_STATUS &#124; DH2:',
			},
			{
				label: 'appointment (DH1 | DH2)',
				name: 'activity_id',
				origin: 'DH1: CORE.T_DYN_APPOINTMENT.ACTIVITYID | DH2: CBUS_APPOINTMENT.APPOINTMENT_AID',
				expectEncoded: 'DH1: CORE.T_DYN_APPOINTMENT.ACTIVITYID &#124; DH2: CBUS_APPOINTMENT.APPOINTMENT_AID',
			},
			{
				label: 'minimal split',
				name: 'x',
				origin: 'A | B',
				expectEncoded: 'A &#124; B',
			},
		])(
			'should encode pipes in origin without extra table columns ($label)',
			({ name, origin, expectEncoded }) => {
				const attributes = [{ name, type: 'text', description: 'd', origin }];
				const result = formatEntityAsMarkdown(mockEntity, attributes, [], mockNodes, 'customer');
				const row = result.split('\n').find((l) => l.startsWith(`| ${name} `));
				expect(row).toBeDefined();
				expect((row!.match(/\|/g) || []).length).toBe(5);
				expect(row).toContain(expectEncoded);
			}
		);

		it('should flatten newlines in table cells so one row stays one line', () => {
			const attributes = [
				{
					name: 'x',
					type: 'text',
					description: 'Line1\nLine2',
					origin: 'a\nb'
				}
			];
			const result = formatEntityAsMarkdown(mockEntity, attributes, [], mockNodes, 'customer');
			const row = result.split('\n').find((l) => l.startsWith('| x |'));
			expect(row).toBeDefined();
			expect(row).toContain('Line1 Line2');
			expect(row).toContain('a b');
			expect(row).not.toContain('\n');
		});

		it('should handle asterisks in entity labels', () => {
			const entityWithAsterisks: EntityData = {
				label: 'Customer*Special',
				domains: ['Sales*Ops']
			};

			const result = formatEntityAsMarkdown(entityWithAsterisks, [], [], mockNodes, 'customer');

			// Asterisks should appear as-is in markdown (they're for bold, but context matters)
			expect(result).toContain('Customer*Special');
		});

		it('should handle brackets in descriptions', () => {
			const entityWithBrackets: EntityData = {
				label: 'Test',
				description: 'Field [deprecated] in use'
			};

			const result = formatEntityAsMarkdown(entityWithBrackets, [], [], mockNodes, 'test');

			expect(result).toContain('Field [deprecated] in use');
		});

		it('should handle multiple special characters in single field', () => {
			const attributesWithSpecialChars = [
				{
					name: 'field_|*test',
					type: 'varchar|text',
					description: 'Contains |pipes* and [brackets]'
				}
			];

			const result = formatEntityAsMarkdown(mockEntity, attributesWithSpecialChars, [], mockNodes, 'customer');

			expect(result).toContain('field_&#124;*test');
			expect(result).toContain('varchar&#124;text');
			expect(result).toContain('[brackets]');
		});
	});

	describe('formatEntityAsMarkdown - Relationships', () => {
		it('should list outgoing relationships correctly', () => {
			const result = formatEntityAsMarkdown(mockEntity, [], mockEdges, mockNodes, 'customer');

			expect(result).toContain('- **Order** via "has" (1:N, Outgoing)');
		});

		it('should list incoming relationships correctly', () => {
			const result = formatEntityAsMarkdown(mockEntity, [], mockEdges, mockNodes, 'customer');

			expect(result).toContain('- **Address** via "lives_at" (N:1, Incoming)');
		});

		it('should handle relationship without label', () => {
			const edgesWithoutLabel = [
				{
					id: 'edge1',
					source: 'customer',
					target: 'order',
					data: { label: null, type: 'one_to_many' }
				}
			];

			const result = formatEntityAsMarkdown(mockEntity, [], edgesWithoutLabel, mockNodes, 'customer');

			expect(result).toContain('- **Order** via "-" (1:N, Outgoing)');
		});

		it('should show concrete join keys (source = target) when available, without quotes', () => {
			const edgesWithKeys = [
				{
					id: 'edge1',
					source: 'customer',
					target: 'order',
					data: {
						label: 'customer',
						type: 'one_to_many',
						source_field: 'invoice_recipient_id',
						target_field: 'customer_number'
					}
				}
			];

			const result = formatEntityAsMarkdown(mockEntity, [], edgesWithKeys, mockNodes, 'customer');

			expect(result).toContain('- **Order** via invoice_recipient_id = customer_number (1:N, Outgoing)');
		});

		it('should prefer join keys over the business label', () => {
			const edgesWithKeys = [
				{
					id: 'edge1',
					source: 'customer',
					target: 'order',
					data: {
						label: 'places',
						type: 'one_to_many',
						source_field: 'customer_id',
						target_field: 'customer_id'
					}
				}
			];

			const result = formatEntityAsMarkdown(mockEntity, [], edgesWithKeys, mockNodes, 'customer');

			expect(result).toContain('via customer_id = customer_id');
			expect(result).not.toContain('via "places"');
		});

		it('should fall back to the label when only one join key is present', () => {
			const edgesPartialKeys = [
				{
					id: 'edge1',
					source: 'customer',
					target: 'order',
					data: {
						label: 'has',
						type: 'one_to_many',
						source_field: 'customer_id'
					}
				}
			];

			const result = formatEntityAsMarkdown(mockEntity, [], edgesPartialKeys, mockNodes, 'customer');

			expect(result).toContain('- **Order** via "has" (1:N, Outgoing)');
		});

		it('should handle relationship without data.type', () => {
			const edgesWithoutType = [
				{
					id: 'edge1',
					source: 'customer',
					target: 'order',
					data: { label: 'related_to' }
				}
			];

			const result = formatEntityAsMarkdown(mockEntity, [], edgesWithoutType, mockNodes, 'customer');

			expect(result).toContain('related_to');
			expect(result).toContain('Unknown');
		});

		it('should handle related entity not in nodes', () => {
			const edgesWithMissingNode = [
				{
					id: 'edge1',
					source: 'customer',
					target: 'unknown_entity',
					data: { label: 'relates_to', type: 'one_to_many' }
				}
			];

			const result = formatEntityAsMarkdown(mockEntity, [], edgesWithMissingNode, mockNodes, 'customer');

			// Should fallback to entity ID if not found
			expect(result).toContain('unknown_entity');
		});

		it('should format different relationship types', () => {
			const edges = [
				{
					id: 'edge1',
					source: 'customer',
					target: 'order',
					data: { label: 'one_many', type: 'one_to_many' }
				},
				{
					id: 'edge2',
					source: 'order',
					target: 'customer',
					data: { label: 'many_one', type: 'many_to_one' }
				},
				{
					id: 'edge3',
					source: 'customer',
					target: 'profile',
					data: { label: 'one_one', type: 'one_to_one' }
				}
			];

			const nodes: Node[] = [
				{ id: 'customer', data: { label: 'Customer' } },
				{ id: 'order', data: { label: 'Order' } },
				{ id: 'profile', data: { label: 'Profile' } }
			];

			const result = formatEntityAsMarkdown(mockEntity, [], edges, nodes, 'customer');

			expect(result).toContain('1:N');
			expect(result).toContain('N:1');
			expect(result).toContain('1:1');
		});
	});

	describe('formatEntityAsMarkdown - Placeholder Handling', () => {
		it('should use "-" for null domains', () => {
			const entity: EntityData = {
				label: 'Test',
				domains: null as any
			};

			const result = formatEntityAsMarkdown(entity, [], [], mockNodes, 'test');

			expect(result).toContain('**Domain(s):** -');
		});

		it('should use "-" for undefined tags', () => {
			const entity: EntityData = {
				label: 'Test',
				tags: undefined
			};

			const result = formatEntityAsMarkdown(entity, [], [], mockNodes, 'test');

			expect(result).toContain('**Tags:** -');
		});

		it('should use "-" for empty source_system array', () => {
			const entity: EntityData = {
				label: 'Test',
				source_system: []
			};

			const result = formatEntityAsMarkdown(entity, [], [], mockNodes, 'test');

			expect(result).toContain('**Source Systems:** -');
		});

		it('should use "-" for null description', () => {
			const entity: EntityData = {
				label: 'Test',
				description: null as any
			};

			const result = formatEntityAsMarkdown(entity, [], [], mockNodes, 'test');

			expect(result).toContain('**Description:** -');
		});

		it('should handle attribute with missing optional description', () => {
			const attributes = [{ name: 'field', type: 'varchar' }];

			const result = formatEntityAsMarkdown(mockEntity, attributes, [], mockNodes, 'customer');

			// Should have empty cell for description
			expect(result).toContain('| field | varchar |');
		});
	});

	describe('formatEntityAsMarkdown - Table Format Correctness', () => {
		it('should maintain proper markdown table structure', () => {
			const result = formatEntityAsMarkdown(mockEntity, mockAttributes, [], mockNodes, 'customer');

			const lines = result.split('\n');
			const attributesIndex = lines.findIndex(l => l.includes('## Attributes'));
			const headerIndex = attributesIndex + 2; // Account for blank line
			const separatorIndex = headerIndex + 1;

			expect(lines[headerIndex]).toBe('| Name | Type | Description | Origin |');
			expect(lines[separatorIndex]).toBe('|------|------|-------------|--------|');

			// All data rows should start and end with pipe
			for (let i = separatorIndex + 1; i < lines.length; i++) {
				const line = lines[i];
				if (line.startsWith('|') && line.includes('|')) {
					expect(line).toMatch(/^\|.*\|$/);
				}
			}
		});

		it('should have exactly 5 pipes in attributes header', () => {
			const result = formatEntityAsMarkdown(mockEntity, mockAttributes, [], mockNodes, 'customer');

			const headerLine = result.split('\n').find(l => l.includes('Name | Type | Description | Origin'));
			const pipeCount = (headerLine?.match(/\|/g) || []).length;
			expect(pipeCount).toBe(5); // 5 pipes for 4 columns
		});

		it('should have 5 pipes in each attribute data row', () => {
			const attributes = [
				{ name: 'id', type: 'int', description: 'Primary key' },
				{ name: 'name', type: 'text', description: 'Name field' }
			];

			const result = formatEntityAsMarkdown(mockEntity, attributes, [], mockNodes, 'customer');

			const lines = result.split('\n');
			const dataRows = lines.filter(l => l.startsWith('| ') && !l.includes('---|'));

			dataRows.forEach(row => {
				const pipeCount = (row.match(/\|/g) || []).length;
				expect(pipeCount).toBe(5);
			});
		});

		it('should render origin value in 4th column', () => {
			const attributes = [
				{ name: 'campaign_id', type: 'text', description: 'Unique ID', origin: 'DH1: CORE.V_DYN_CAMPAIGN_CUR.CAMPAIGNID' }
			];
			const result = formatEntityAsMarkdown(mockEntity, attributes, [], mockNodes, 'customer');
			expect(result).toContain('| campaign_id | text | Unique ID | DH1: CORE.V_DYN_CAMPAIGN_CUR.CAMPAIGNID |');
		});

		it('should render empty string for undefined origin in 4th column', () => {
			const attributes = [
				{ name: 'field', type: 'text', description: 'A field' }
			];
			const result = formatEntityAsMarkdown(mockEntity, attributes, [], mockNodes, 'customer');
			expect(result).toContain('| field | text | A field |  |');
		});
	});

	describe('formatEntityAsMarkdown - Edge Cases', () => {
		it('should handle very long attribute names', () => {
			const longName = 'a'.repeat(100);
			const attributes = [{ name: longName, type: 'varchar', description: 'Test' }];

			const result = formatEntityAsMarkdown(mockEntity, attributes, [], mockNodes, 'customer');

			expect(result).toContain(longName);
		});

		it('should handle entity with single attribute', () => {
			const attributes = [{ name: 'id', type: 'int' }];

			const result = formatEntityAsMarkdown(mockEntity, attributes, [], mockNodes, 'customer');

			expect(result).toContain('| id | int |');
		});

		it('should handle entity with single relationship', () => {
			const edges = [
				{
					id: 'edge1',
					source: 'customer',
					target: 'order',
					label: 'has',
					data: { type: 'one_to_many' }
				}
			];

			const result = formatEntityAsMarkdown(mockEntity, [], edges, mockNodes, 'customer');

			expect(result).toContain('- **Order**');
		});

		it('should handle domains array with single element', () => {
			const entity: EntityData = {
				label: 'Test',
				domains: ['Sales']
			};

			const result = formatEntityAsMarkdown(entity, [], [], mockNodes, 'test');

			expect(result).toContain('**Domain(s):** Sales');
		});

		it('should return valid markdown string', () => {
			const result = formatEntityAsMarkdown(mockEntity, mockAttributes, mockEdges, mockNodes, 'customer');

			expect(typeof result).toBe('string');
			expect(result.length).toBeGreaterThan(0);
			expect(result).toMatch(/^#\s+/); // Starts with markdown title
		});
	});

	describe('formatEntityAsMarkdown - Entity Type Formatting', () => {
		it('should format fact entity type', () => {
			const entity: EntityData = {
				label: 'Orders',
				entity_type: 'fact'
			};

			const result = formatEntityAsMarkdown(entity, [], [], mockNodes, 'orders');

			expect(result).toContain('**Type:** Fact');
		});

		it('should format unclassified entity type', () => {
			const entity: EntityData = {
				label: 'Test',
				entity_type: 'unclassified'
			};

			const result = formatEntityAsMarkdown(entity, [], [], mockNodes, 'test');

			expect(result).toContain('**Type:** Unclassified');
		});
	});

	describe('formatEntityAsMarkdown - Annotation Type Formatting', () => {
		it('should format 7W annotation types correctly', () => {
			const annotationTypes = ['what', 'when', 'where', 'how', 'why', 'how_many'];

			for (const type of annotationTypes) {
				const entity: EntityData = {
					label: 'Test',
					annotation_type: type as any
				};

				const result = formatEntityAsMarkdown(entity, [], [], mockNodes, 'test');

				expect(result).toContain('**7W Annotation:**');
				expect(result).not.toContain('undefined');
			}
		});
	});
});
