import { describe, it, expect, vi } from 'vitest';
import {
  sanitizeFilename,
  getDateString,
  formatEntityType,
  formatAnnotationType,
  formatRelationshipType,
  generateOverviewSheet,
  generateAttributesSheet,
  generateRelationshipsSheet
} from './excel-export';
import type { EntityData } from '$lib/types';

// Mock XLSX library
vi.mock('xlsx', () => ({
  utils: {
    aoa_to_sheet: vi.fn((data) => ({
      data,
      '!cols': [],
      A1: { s: {} },
      B1: { s: {} },
      C1: { s: {} },
      D1: { s: {} }
    })),
    book_new: vi.fn(() => ({})),
    book_append_sheet: vi.fn(),
    writeFile: vi.fn()
  }
}));

describe('excel-export utilities', () => {
  describe('sanitizeFilename', () => {
    it('should remove special characters', () => {
      expect(sanitizeFilename('Customer & Order')).toBe('Customer  Order');
      expect(sanitizeFilename('Test/File\\Name')).toBe('TestFileName');
      expect(sanitizeFilename('Invalid:*?"<>|Chars')).toBe('InvalidChars');
    });

    it('should keep spaces and alphanumeric', () => {
      expect(sanitizeFilename('My Entity 123')).toBe('My Entity 123');
    });

    it('should truncate long names', () => {
      const longName = 'a'.repeat(250);
      expect(sanitizeFilename(longName).length).toBeLessThanOrEqual(200);
    });
  });

  describe('getDateString', () => {
    it('should return YYYYMMDD format', () => {
      const result = getDateString();
      expect(result).toMatch(/^\d{8}$/);
      expect(result.length).toBe(8);
    });
  });

  describe('formatEntityType', () => {
    it('should format dimension', () => {
      expect(formatEntityType('dimension')).toBe('Dimension');
    });

    it('should format fact', () => {
      expect(formatEntityType('fact')).toBe('Fact');
    });

    it('should format unclassified', () => {
      expect(formatEntityType('unclassified')).toBe('Unclassified');
    });

    it('should default to Unclassified', () => {
      expect(formatEntityType(undefined)).toBe('Unclassified');
    });
  });

  describe('formatAnnotationType', () => {
    it('should format all 7W types', () => {
      expect(formatAnnotationType('who')).toBe('Who');
      expect(formatAnnotationType('what')).toBe('What');
      expect(formatAnnotationType('when')).toBe('When');
      expect(formatAnnotationType('where')).toBe('Where');
      expect(formatAnnotationType('how')).toBe('How');
      expect(formatAnnotationType('why')).toBe('Why');
      expect(formatAnnotationType('how_many')).toBe('How Many');
    });

    it('should default to None', () => {
      expect(formatAnnotationType(undefined)).toBe('None');
    });
  });

  describe('formatRelationshipType', () => {
    it('should format one_to_many', () => {
      expect(formatRelationshipType('one_to_many')).toBe('1:N');
    });

    it('should format many_to_one', () => {
      expect(formatRelationshipType('many_to_one')).toBe('N:1');
    });

    it('should format one_to_one', () => {
      expect(formatRelationshipType('one_to_one')).toBe('1:1');
    });

    it('should format many_to_many', () => {
      expect(formatRelationshipType('many_to_many')).toBe('N:N');
    });

    it('should default to Unknown', () => {
      expect(formatRelationshipType('unknown')).toBe('Unknown');
      expect(formatRelationshipType('invalid')).toBe('Unknown');
    });
  });
});

describe('Sheet Generators', () => {
  describe('generateOverviewSheet', () => {
    it('should generate overview with complete entity data', () => {
      const entity: EntityData = {
        label: 'Customer',
        entity_type: 'dimension',
        annotation_type: 'who',
        domains: ['Sales', 'Marketing'],
        tags: ['pii', 'core'],
        source_system: ['CRM', 'ERP'],
        description: 'Customer entity',
        dbt_model: 'model.project.customer',
        additional_models: ['model.project.customer_history']
      };

      const sheet = generateOverviewSheet(entity);
      expect(sheet).toBeDefined();
      expect(sheet.data).toBeDefined();
      expect(sheet.data[0]).toEqual(['Field', 'Value']);
      expect(sheet.data[1][1]).toBe('Customer');
    });

    it('should handle minimal entity data', () => {
      const entity: EntityData = {
        label: 'Test Entity'
      };

      const sheet = generateOverviewSheet(entity);
      expect(sheet).toBeDefined();
    });
  });

  describe('generateAttributesSheet', () => {
    it('should generate attributes with data', () => {
      const attributes = [
        { name: 'customer_id', type: 'int', description: 'Primary key' },
        { name: 'name', type: 'text', description: 'Customer name' }
      ];

      const sheet = generateAttributesSheet(attributes);
      expect(sheet).toBeDefined();
      expect(sheet.data[0]).toEqual(['Name', 'Type', 'Description']);
    });

    it('should handle empty attributes', () => {
      const sheet = generateAttributesSheet([]);
      expect(sheet).toBeDefined();
      expect(sheet.data[1]).toEqual(['No attributes defined', '', '']);
    });
  });

  describe('generateRelationshipsSheet', () => {
    it('should generate relationships with edges', () => {
      const edges = [
        {
          source: 'entity1',
          target: 'entity2',
          label: 'belongs to',
          data: { type: 'many_to_one' }
        }
      ];
      const nodes = [
        { id: 'entity1', data: { label: 'Order' } },
        { id: 'entity2', data: { label: 'Customer' } }
      ];

      const sheet = generateRelationshipsSheet(edges, 'entity1', nodes);
      expect(sheet).toBeDefined();
      expect(sheet.data[0]).toEqual(['Related Entity', 'Relationship Label', 'Relationship Type', 'Direction']);
    });

    it('should handle no relationships', () => {
      const sheet = generateRelationshipsSheet([], 'entity1', []);
      expect(sheet).toBeDefined();
      expect(sheet.data[1]).toEqual(['No relationships defined', '', '', '']);
    });
  });
});
