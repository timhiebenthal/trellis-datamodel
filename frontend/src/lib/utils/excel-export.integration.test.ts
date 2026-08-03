import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  generateOverviewSheet,
  generateAttributesSheet,
  generateRelationshipsSheet,
  exportEntityToExcel
} from './excel-export';
import type { EntityData } from '$lib/types';
import type { Node } from '@xyflow/svelte';
import * as XLSX from 'xlsx';

vi.mock('xlsx', async () => {
  const actual = await vi.importActual<typeof import('xlsx')>('xlsx');
  return {
    ...actual,
    writeFile: vi.fn()
  };
});

describe('excel-export integration tests', () => {
  describe('generateOverviewSheet', () => {
    it('should generate complete overview sheet with all entity data', () => {
      const entity: EntityData = {
        id: 'entity-1',
        label: 'Customer',
        entity_type: 'dimension',
        annotation_type: 'who',
        domains: ['Sales', 'Marketing'],
        tags: ['core', 'master-data'],
        source_system: ['SAP', 'Salesforce'],
        description: 'Customer master data from various sources',
        model_ref: 'dim_customer',
        additional_models: ['stg_customer', 'int_customer']
      };

      const ws = generateOverviewSheet(entity);

      // Verify worksheet structure exists
      expect(ws).toBeDefined();
      expect(ws['!cols']).toBeDefined();
      expect(ws['!cols']).toHaveLength(2);

      // Check headers are bold
      expect(ws['A1']?.s?.font?.bold).toBe(true);
      expect(ws['B1']?.s?.font?.bold).toBe(true);

      // Verify column widths
      expect(ws['!cols'][0].wch).toBe(20);
      expect(ws['!cols'][1].wch).toBe(60);
    });

    it('should handle entity with minimal data', () => {
      const entity: EntityData = {
        id: 'entity-2',
        label: 'Minimal Entity'
      };

      const ws = generateOverviewSheet(entity);

      expect(ws).toBeDefined();
      expect(ws['!cols']).toBeDefined();
    });

    it('should format entity type correctly', () => {
      const factEntity: EntityData = {
        id: 'fact-1',
        label: 'Sales',
        entity_type: 'fact'
      };

      const ws = generateOverviewSheet(factEntity);
      expect(ws).toBeDefined();
    });

    it('should handle array domains and single domain', () => {
      const entityWithArrayDomains: EntityData = {
        id: 'entity-3',
        label: 'Entity With Domains',
        domains: ['Domain A', 'Domain B', 'Domain C']
      };

      const entityWithSingleDomain: EntityData = {
        id: 'entity-4',
        label: 'Entity Single Domain',
        domain: 'Single Domain'
      };

      const ws1 = generateOverviewSheet(entityWithArrayDomains);
      const ws2 = generateOverviewSheet(entityWithSingleDomain);

      expect(ws1).toBeDefined();
      expect(ws2).toBeDefined();
    });
  });

  describe('generateAttributesSheet', () => {
    it('should generate attributes sheet with data', () => {
      const attributes = [
        { name: 'customer_id', type: 'integer', description: 'Unique identifier' },
        { name: 'customer_name', type: 'string', description: 'Full name' },
        { name: 'email', type: 'string', description: 'Email address' },
        { name: 'created_at', type: 'timestamp' }
      ];

      const ws = generateAttributesSheet(attributes);

      expect(ws).toBeDefined();
      expect(ws['!cols']).toBeDefined();
      expect(ws['!cols']).toHaveLength(4);

      // Verify headers are bold
      expect(ws['A1']?.s?.font?.bold).toBe(true);
      expect(ws['B1']?.s?.font?.bold).toBe(true);
      expect(ws['C1']?.s?.font?.bold).toBe(true);

      // Verify column widths
      expect(ws['!cols'][0].wch).toBe(25);
      expect(ws['!cols'][1].wch).toBe(15);
      expect(ws['!cols'][2].wch).toBe(40);
      expect(ws['!cols'][3].wch).toBe(35);
    });

    it('should handle empty attributes array', () => {
      const ws = generateAttributesSheet([]);

      expect(ws).toBeDefined();
      expect(ws['!cols']).toBeDefined();
    });

    it('should handle attributes without descriptions', () => {
      const attributes = [
        { name: 'field1', type: 'string' },
        { name: 'field2', type: 'integer' }
      ];

      const ws = generateAttributesSheet(attributes);
      expect(ws).toBeDefined();
    });
  });

  describe('generateRelationshipsSheet', () => {
    const allNodes: Node[] = [
      {
        id: 'entity-1',
        data: { label: 'Customer' },
        position: { x: 0, y: 0 },
        type: 'custom'
      },
      {
        id: 'entity-2',
        data: { label: 'Order' },
        position: { x: 100, y: 100 },
        type: 'custom'
      },
      {
        id: 'entity-3',
        data: { label: 'Product' },
        position: { x: 200, y: 200 },
        type: 'custom'
      }
    ];

    it('should generate relationships sheet with outgoing edges', () => {
      const edges = [
        {
          id: 'edge-1',
          source: 'entity-1',
          target: 'entity-2',
          label: 'places',
          data: { type: 'one_to_many' }
        },
        {
          id: 'edge-2',
          source: 'entity-1',
          target: 'entity-3',
          label: 'views',
          data: { type: 'many_to_many' }
        }
      ];

      const ws = generateRelationshipsSheet(edges, 'entity-1', allNodes);

      expect(ws).toBeDefined();
      expect(ws['!cols']).toBeDefined();
      expect(ws['!cols']).toHaveLength(4);

      // Verify headers are bold
      expect(ws['A1']?.s?.font?.bold).toBe(true);
      expect(ws['B1']?.s?.font?.bold).toBe(true);
      expect(ws['C1']?.s?.font?.bold).toBe(true);
      expect(ws['D1']?.s?.font?.bold).toBe(true);

      // Verify column widths
      expect(ws['!cols'][0].wch).toBe(25);
      expect(ws['!cols'][1].wch).toBe(30);
      expect(ws['!cols'][2].wch).toBe(20);
      expect(ws['!cols'][3].wch).toBe(15);
    });

    it('should generate relationships sheet with incoming edges', () => {
      const edges = [
        {
          id: 'edge-1',
          source: 'entity-2',
          target: 'entity-1',
          label: 'belongs_to',
          data: { type: 'many_to_one' }
        }
      ];

      const ws = generateRelationshipsSheet(edges, 'entity-1', allNodes);
      expect(ws).toBeDefined();
    });

    it('should handle mixed incoming and outgoing edges', () => {
      const edges = [
        {
          id: 'edge-1',
          source: 'entity-1',
          target: 'entity-2',
          label: 'has',
          data: { type: 'one_to_many' }
        },
        {
          id: 'edge-2',
          source: 'entity-3',
          target: 'entity-1',
          label: 'references',
          data: { type: 'many_to_one' }
        }
      ];

      const ws = generateRelationshipsSheet(edges, 'entity-1', allNodes);
      expect(ws).toBeDefined();
    });

    it('should handle entity with no relationships', () => {
      const ws = generateRelationshipsSheet([], 'entity-1', allNodes);
      expect(ws).toBeDefined();
    });

    it('should handle edges without labels', () => {
      const edges = [
        {
          id: 'edge-1',
          source: 'entity-1',
          target: 'entity-2',
          data: { type: 'one_to_one' }
        }
      ];

      const ws = generateRelationshipsSheet(edges, 'entity-1', allNodes);
      expect(ws).toBeDefined();
    });

    it('should handle edges with unknown relationship types', () => {
      const edges = [
        {
          id: 'edge-1',
          source: 'entity-1',
          target: 'entity-2',
          label: 'mystery',
          data: { type: 'unknown' }
        }
      ];

      const ws = generateRelationshipsSheet(edges, 'entity-1', allNodes);
      expect(ws).toBeDefined();
    });
  });

  describe('exportEntityToExcel', () => {
    beforeEach(() => {
      vi.mocked(XLSX.writeFile).mockReset();
      vi.mocked(XLSX.writeFile).mockImplementation(() => {});
    });

    it('should create complete workbook with all three sheets', () => {
      const entity: EntityData = {
        id: 'entity-1',
        label: 'Customer',
        entity_type: 'dimension',
        annotation_type: 'who',
        description: 'Customer data'
      };

      const attributes = [
        { name: 'id', type: 'integer', description: 'Primary key' },
        { name: 'name', type: 'string', description: 'Customer name' }
      ];

      const edges = [
        {
          id: 'edge-1',
          source: 'entity-1',
          target: 'entity-2',
          label: 'places',
          data: { type: 'one_to_many' }
        }
      ];

      const allNodes: Node[] = [
        {
          id: 'entity-1',
          data: { label: 'Customer' },
          position: { x: 0, y: 0 },
          type: 'custom'
        },
        {
          id: 'entity-2',
          data: { label: 'Order' },
          position: { x: 100, y: 100 },
          type: 'custom'
        }
      ];

      exportEntityToExcel(entity, attributes, edges, allNodes, 'entity-1');

      // Verify writeFile was called
      expect(XLSX.writeFile).toHaveBeenCalledTimes(1);

      // Verify filename format
      const callArgs = (XLSX.writeFile as any).mock.calls[0];
      const filename = callArgs[1];
      expect(filename).toMatch(/^Customer_export_\d{8}\.xlsx$/);
    });

    it('should sanitize filename with special characters', () => {
      const entity: EntityData = {
        id: 'entity-1',
        label: 'Customer & Order/Report',
        entity_type: 'dimension'
      };

      exportEntityToExcel(entity, [], [], [], 'entity-1');

      const callArgs = (XLSX.writeFile as any).mock.calls[0];
      const filename = callArgs[1];
      expect(filename).not.toContain('&');
      expect(filename).not.toContain('/');
    });

    it('should handle export with empty data', () => {
      const entity: EntityData = {
        id: 'entity-1',
        label: 'Empty Entity'
      };

      exportEntityToExcel(entity, [], [], [], 'entity-1');
      expect(XLSX.writeFile).toHaveBeenCalled();
    });

    it('should handle errors gracefully', () => {
      // Mock writeFile to throw error
      vi.mocked(XLSX.writeFile).mockImplementation(() => {
        throw new Error('Write failed');
      });

      const entity: EntityData = {
        id: 'entity-1',
        label: 'Test'
      };

      expect(() => {
        exportEntityToExcel(entity, [], [], [], 'entity-1');
      }).toThrow('Failed to export entity to Excel');
    });
  });
});
