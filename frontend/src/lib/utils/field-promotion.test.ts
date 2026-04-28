import { describe, it, expect } from 'vitest';
import { promoteDraftsAgainstModel } from './field-promotion';
import type { DbtModel, DraftedField } from '$lib/types';

const makeModel = (columnNames: string[]): DbtModel => ({
	unique_id: 'model.test.foo',
	name: 'foo',
	schema: 'public',
	table: 'foo',
	columns: columnNames.map((n) => ({ name: n, type: 'text' })),
});

describe('promoteDraftsAgainstModel', () => {
	it('returns undefined when drafted is undefined', () => {
		expect(promoteDraftsAgainstModel(undefined, makeModel(['x']))).toBeUndefined();
	});

	it('returns empty array when drafted is empty', () => {
		const result = promoteDraftsAgainstModel([], makeModel(['x']));
		expect(result).toEqual([]);
	});

	it('returns all drafts unchanged when model is undefined (unbound)', () => {
		const drafts: DraftedField[] = [{ name: 'x', datatype: 'text' }];
		const result = promoteDraftsAgainstModel(drafts, undefined);
		expect(result).toEqual([{ name: 'x', datatype: 'text' }]);
	});

	it('drops drafted fields whose name matches a dbt column', () => {
		const drafts: DraftedField[] = [
			{ name: 'x', datatype: 'text' },
			{ name: 'y', datatype: 'int' },
		];
		const model = makeModel(['y']);
		const result = promoteDraftsAgainstModel(drafts, model);
		expect(result).toEqual([{ name: 'x', datatype: 'text' }]);
	});

	it('returns a new array (not the original) when items are dropped', () => {
		const drafts: DraftedField[] = [
			{ name: 'x', datatype: 'text' },
			{ name: 'y', datatype: 'int' },
		];
		const model = makeModel(['y']);
		const result = promoteDraftsAgainstModel(drafts, model);
		expect(result).not.toBe(drafts);
	});

	it('returns the exact same array reference when nothing changed', () => {
		const drafts: DraftedField[] = [{ name: 'x', datatype: 'text' }];
		const model = makeModel(['z']); // 'x' not in model columns
		const result = promoteDraftsAgainstModel(drafts, model);
		expect(result).toBe(drafts);
	});

	it('is case-sensitive: does not drop drafts whose name differs in case from dbt column', () => {
		const drafts: DraftedField[] = [{ name: 'X', datatype: 'text' }];
		const model = makeModel(['x']); // lowercase 'x', draft has uppercase 'X'
		const result = promoteDraftsAgainstModel(drafts, model);
		expect(result).toEqual([{ name: 'X', datatype: 'text' }]);
	});
});
