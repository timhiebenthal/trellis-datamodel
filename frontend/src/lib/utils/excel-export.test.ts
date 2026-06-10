import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { Node } from '@xyflow/svelte';
import * as XLSX from 'xlsx';
import {
  sanitizeFilename,
  sanitizeSheetName,
  getDateString,
  formatEntityType,
  formatAnnotationType,
  formatRelationshipType,
  formatRelationshipKeys,
  generateOverviewSheet,
  generateAttributesSheet,
  generateRelationshipsSheet,
  generateDataModelOverviewSheet,
  exportDataModelToExcel
} from './excel-export';
import type { EntityData } from '$lib/types';

// Mock XLSX library
vi.mock('xlsx', () => ({
  utils: {
    aoa_to_sheet: vi.fn((data) => ({
      data,
      '!ref': 'A1:D2',
      '!cols': [],
      A1: { s: {} },
      B1: { s: {} },
      C1: { s: {} },
      D1: { s: {} }
    })),
    decode_range: vi.fn(() => ({
      s: { c: 0, r: 0 },
      e: { c: 3, r: 0 }
    })),
    encode_cell: vi.fn(({ r, c }: { r: number; c: number }) => {
      const col = String.fromCharCode(65 + c);
      return `${col}${r + 1}`;
    }),
    book_new: vi.fn(() => ({})),
    book_append_sheet: vi.fn()
  },
  writeFile: vi.fn()
}));

beforeEach(() => {
  vi.mocked(XLSX.utils.book_append_sheet).mockClear();
  vi.mocked(XLSX.writeFile).mockClear();
  vi.mocked(XLSX.utils.book_new).mockClear();
});

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

  describe('sanitizeSheetName', () => {
    it('removes forbidden Excel characters from sheet names', () => {
      const used = new Set<string>();
      expect(sanitizeSheetName('A/B:C[D]*?\\', used)).toBe('ABCD');
    });

    it('truncates labels longer than 31 characters', () => {
      const used = new Set<string>();
      const result = sanitizeSheetName('X'.repeat(40), used);
      expect(result.length).toBe(31);
      expect(result).toBe('X'.repeat(31));
    });

    it('uses Entity for blank label after sanitization', () => {
      const used = new Set<string>();
      expect(sanitizeSheetName('   ', used)).toBe('Entity');
      expect(sanitizeSheetName('[]:*?/\\', used)).toBe('Entity_2');
    });

    it('appends _2 and _3 on collision and stays at most 31 chars', () => {
      const used = new Set<string>();
      expect(sanitizeSheetName('Same', used)).toBe('Same');
      expect(sanitizeSheetName('Same', used)).toBe('Same_2');
      expect(sanitizeSheetName('Same', used)).toBe('Same_3');
      expect(used.size).toBe(3);
      const long = 'A'.repeat(50);
      const used2 = new Set<string>();
      const a = sanitizeSheetName(long, used2);
      const b = sanitizeSheetName(long, used2);
      expect(a.length).toBeLessThanOrEqual(31);
      expect(b.length).toBeLessThanOrEqual(31);
      expect(a).not.toBe(b);
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
      expect(sheet.data[0]).toEqual(['Name', 'Type', 'Description', 'Origin']);
    });

    it('should handle empty attributes', () => {
      const sheet = generateAttributesSheet([]);
      expect(sheet).toBeDefined();
      expect(sheet.data[1]).toEqual(['No attributes defined', '', '', '']);
    });

    it('should include origin value when populated', () => {
      const attributes = [
        { name: 'campaign_id', type: 'text', description: 'Unique identifier', origin: 'DH1: CORE.V_DYN_CAMPAIGN_CUR.CAMPAIGNID' }
      ];
      const sheet = generateAttributesSheet(attributes);
      expect(sheet.data[1][3]).toBe('DH1: CORE.V_DYN_CAMPAIGN_CUR.CAMPAIGNID');
    });

    it('should render empty string for undefined origin', () => {
      const attributes = [
        { name: 'name', type: 'text', description: 'Name field' }
      ];
      const sheet = generateAttributesSheet(attributes);
      expect(sheet.data[1][3]).toBe('');
    });
  });

  describe('generateRelationshipsSheet', () => {
    it('should generate relationships with edges', () => {
      const edges = [
        {
          source: 'entity1',
          target: 'entity2',
          data: { label: 'belongs to', type: 'many_to_one' }
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

    it('should use concrete join keys in the relationship cell when available', () => {
      const edges = [
        {
          source: 'entity1',
          target: 'entity2',
          data: {
            label: 'belongs to',
            type: 'many_to_one',
            source_field: 'customer_id',
            target_field: 'id'
          }
        }
      ];
      const nodes = [
        { id: 'entity1', data: { label: 'Order' } },
        { id: 'entity2', data: { label: 'Customer' } }
      ];

      const sheet = generateRelationshipsSheet(edges, 'entity1', nodes);
      expect(sheet.data[1]).toEqual(['Customer', 'customer_id = id', 'N:1', 'Outgoing']);
    });

    it('should handle no relationships', () => {
      const sheet = generateRelationshipsSheet([], 'entity1', []);
      expect(sheet).toBeDefined();
      expect(sheet.data[1]).toEqual(['No relationships defined', '', '', '']);
    });
  });

  describe('formatRelationshipKeys', () => {
    it('returns source = target when both fields present', () => {
      expect(formatRelationshipKeys({ source_field: 'a_id', target_field: 'b_id' })).toBe('a_id = b_id');
    });

    it('returns null when either field is missing', () => {
      expect(formatRelationshipKeys({ source_field: 'a_id' })).toBeNull();
      expect(formatRelationshipKeys({ target_field: 'b_id' })).toBeNull();
      expect(formatRelationshipKeys({})).toBeNull();
      expect(formatRelationshipKeys(undefined)).toBeNull();
    });
  });
});

describe('exportDataModelToExcel', () => {
  it('calls book_append_sheet once per entity node plus one overview sheet, ignores non-entity nodes', () => {
    const nodes = [
      {
        type: 'entity',
        id: 'e1',
        data: { label: 'Alpha', drafted_fields: [{ name: 'id', datatype: 'int' }] }
      },
      { type: 'annotation', id: 'a1', data: {} },
      {
        type: 'entity',
        id: 'e2',
        data: { label: 'Beta', drafted_fields: [] }
      }
    ] as unknown as Node[];

    exportDataModelToExcel(nodes, []);

    // 1 overview + 2 entity sheets = 3
    expect(XLSX.utils.book_append_sheet).toHaveBeenCalledTimes(3);
  });

  it('writes DataModel_export_YYYYMMDD.xlsx', () => {
    const nodes = [
      {
        type: 'entity',
        id: 'e1',
        data: { label: 'Only', drafted_fields: [] }
      }
    ] as unknown as Node[];

    exportDataModelToExcel(nodes, []);

    expect(vi.mocked(XLSX.writeFile)).toHaveBeenCalledWith(
      expect.anything(),
      expect.stringMatching(/^DataModel_export_\d{8}\.xlsx$/)
    );
  });

  it('uses generateAttributesSheet empty state when drafted_fields is missing or empty', () => {
    const nodes = [
      {
        type: 'entity',
        id: 'e1',
        data: { label: 'EmptyFields' }
      }
    ] as unknown as Node[];

    exportDataModelToExcel(nodes, []);

    // calls[0] = overview sheet, calls[1] = first entity sheet
    const sheetArg = vi.mocked(XLSX.utils.book_append_sheet).mock.calls[1][1] as {
      data: string[][];
    };
    expect(sheetArg.data[1]).toEqual(['No attributes defined', '', '', '']);
  });
});

describe('generateDataModelOverviewSheet', () => {
  it('first row contains "About this Data Model Export"', () => {
    const nodes = [
      { type: 'entity', id: 'e1', data: { label: 'Sales', entity_type: 'fact' } }
    ] as unknown as Node[];
    const sheet = generateDataModelOverviewSheet(nodes, []);
    expect(sheet.data[0][0]).toBe('About this Data Model Export');
  });

  it('entity directory section lists all entity names', () => {
    const nodes = [
      { type: 'entity', id: 'e1', data: { label: 'Customer', entity_type: 'dimension', description: 'A customer' } },
      { type: 'entity', id: 'e2', data: { label: 'Order', entity_type: 'fact', description: 'An order' } }
    ] as unknown as Node[];
    const sheet = generateDataModelOverviewSheet(nodes, []);
    const allRows: string[][] = sheet.data;
    const labels = allRows.map((r) => r[0]);
    expect(labels).toContain('Customer');
    expect(labels).toContain('Order');
  });

  it('shows "No relationships defined" when edges is empty', () => {
    const nodes = [
      { type: 'entity', id: 'e1', data: { label: 'Foo', entity_type: 'fact' } }
    ] as unknown as Node[];
    const sheet = generateDataModelOverviewSheet(nodes, []);
    const allRows: string[][] = sheet.data;
    const hasNoRel = allRows.some((r) => r[0] === 'No relationships defined');
    expect(hasNoRel).toBe(true);
  });

  it('lists relationships using entity labels', () => {
    const nodes = [
      { type: 'entity', id: 'e1', data: { label: 'Order', entity_type: 'fact' } },
      { type: 'entity', id: 'e2', data: { label: 'Customer', entity_type: 'dimension' } }
    ] as unknown as Node[];
    const edges = [
      { source: 'e1', target: 'e2', data: { label: 'placed by', type: 'many_to_one' } }
    ];
    const sheet = generateDataModelOverviewSheet(nodes, edges);
    const allRows: string[][] = sheet.data;
    const relRow = allRows.find((r) => r[0] === 'Order' && r[1] === 'Customer');
    expect(relRow).toBeDefined();
    expect(relRow![2]).toBe('placed by');
    expect(relRow![3]).toBe('N:1');
  });
});
