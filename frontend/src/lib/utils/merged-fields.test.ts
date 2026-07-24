import { describe, it, expect } from 'vitest';
import { mergeFields } from './merged-fields';
import type { DbtColumn, DraftedField } from '$lib/types';

describe('mergeFields', () => {
	it('returns empty array when both args are undefined', () => {
		expect(mergeFields(undefined, undefined)).toEqual([]);
	});

	it('maps dbt columns to origin:dbt rows with datatype from type field', () => {
		const dbtCols: DbtColumn[] = [{ name: 'id', type: 'int' }];
		const result = mergeFields(dbtCols, undefined);
		expect(result).toHaveLength(1);
		expect(result[0]).toMatchObject({ origin: 'dbt', name: 'id', datatype: 'int' });
	});

	it('maps drafted fields to origin:draft rows with draftIndex', () => {
		const drafted: DraftedField[] = [{ name: 'x', datatype: 'text' }];
		const result = mergeFields(undefined, drafted);
		expect(result).toHaveLength(1);
		expect(result[0]).toMatchObject({ origin: 'draft', name: 'x', datatype: 'text', draftIndex: 0 });
	});

	it('orders dbt columns first then drafts', () => {
		const dbtCols: DbtColumn[] = [{ name: 'id', type: 'int' }];
		const drafted: DraftedField[] = [{ name: 'extra', datatype: 'text' }];
		const result = mergeFields(dbtCols, drafted);
		expect(result).toHaveLength(2);
		expect(result[0].origin).toBe('dbt');
		expect(result[1].origin).toBe('draft');
	});

	it('omits a draft when its name exactly matches a dbt column name (collision)', () => {
		const dbtCols: DbtColumn[] = [{ name: 'id', type: 'int' }];
		const drafted: DraftedField[] = [{ name: 'id', datatype: 'bigint' }];
		const result = mergeFields(dbtCols, drafted);
		expect(result).toHaveLength(1);
		expect(result[0].origin).toBe('dbt');
	});

	it('omits a draft when its name differs from a dbt column only by case', () => {
		const dbtCols: DbtColumn[] = [{ name: 'id', type: 'int' }];
		const drafted: DraftedField[] = [{ name: 'ID', datatype: 'bigint' }];
		const result = mergeFields(dbtCols, drafted);
		expect(result).toHaveLength(1);
		expect(result[0]).toMatchObject({ origin: 'dbt', name: 'id' });
	});

	it('draftIndex reflects original index in drafted array after a collision at index 0', () => {
		const dbtCols: DbtColumn[] = [{ name: 'id', type: 'int' }];
		const drafted: DraftedField[] = [
			{ name: 'id', datatype: 'bigint' }, // index 0 — collides, omitted
			{ name: 'created_at', datatype: 'timestamp' }, // index 1 — survives
		];
		const result = mergeFields(dbtCols, drafted);
		expect(result).toHaveLength(2);
		const draftRow = result.find((r) => r.origin === 'draft');
		expect(draftRow).toBeDefined();
		if (draftRow?.origin === 'draft') {
			expect(draftRow.draftIndex).toBe(1);
		}
	});

	it('preserves dbt manifest order', () => {
		const dbtCols: DbtColumn[] = [
			{ name: 'c', type: 'text' },
			{ name: 'a', type: 'text' },
			{ name: 'b', type: 'text' },
		];
		const result = mergeFields(dbtCols, undefined);
		expect(result.map((r) => r.name)).toEqual(['c', 'a', 'b']);
	});

	it('preserves draft stored order for surviving drafts', () => {
		const drafted: DraftedField[] = [
			{ name: 'z', datatype: 'text' },
			{ name: 'a', datatype: 'text' },
			{ name: 'm', datatype: 'text' },
		];
		const result = mergeFields(undefined, drafted);
		expect(result.map((r) => r.name)).toEqual(['z', 'a', 'm']);
	});

	it('passes through description from dbt columns', () => {
		const dbtCols: DbtColumn[] = [{ name: 'id', type: 'int', description: 'primary key' }];
		const result = mergeFields(dbtCols, undefined);
		expect(result[0]).toMatchObject({ description: 'primary key' });
	});

	it('passes through description from drafted fields', () => {
		const drafted: DraftedField[] = [{ name: 'x', datatype: 'text', description: 'some field' }];
		const result = mergeFields(undefined, drafted);
		expect(result[0]).toMatchObject({ description: 'some field' });
	});

	it('passes originRefs from dbt columns with origin discriminant dbt', () => {
		const dbtCols: DbtColumn[] = [
			{ name: 'amount', type: 'numeric', origin: [{ DH1: 'CORE.A' }] },
		];
		const result = mergeFields(dbtCols, undefined);
		expect(result[0]).toMatchObject({
			origin: 'dbt',
			originRefs: [{ DH1: 'CORE.A' }],
		});
	});

	it('passes originRefs from drafted fields with origin discriminant draft', () => {
		const drafted: DraftedField[] = [
			{ name: 'amount', datatype: 'float', origin: [{ DH2: 'CBUS.B' }] },
		];
		const result = mergeFields(undefined, drafted);
		expect(result[0]).toMatchObject({
			origin: 'draft',
			originRefs: [{ DH2: 'CBUS.B' }],
		});
	});

	it('leaves originRefs undefined when no origin is present', () => {
		const dbtCols: DbtColumn[] = [{ name: 'id', type: 'int' }];
		const drafted: DraftedField[] = [{ name: 'extra', datatype: 'text' }];
		const result = mergeFields(dbtCols, drafted);
		expect(result[0].originRefs).toBeUndefined();
		expect(result[1].originRefs).toBeUndefined();
	});
});
