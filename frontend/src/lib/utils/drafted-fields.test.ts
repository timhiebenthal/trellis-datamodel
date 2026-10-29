import { describe, expect, it } from 'vitest';
import type { DraftedField } from '$lib/types';
import { appendDraftedField, removeDraftedFieldAt, updateDraftedFieldAt } from './drafted-fields';

const fields: DraftedField[] = [
	{ name: 'id', datatype: 'int' },
	{ name: 'name', datatype: 'text' },
];

describe('drafted-fields', () => {
	it('appends an empty text field', () => {
		expect(appendDraftedField(fields)).toEqual([...fields, { name: '', datatype: 'text' }]);
		expect(fields).toHaveLength(2);
	});

	it('merges updates into the field at the index', () => {
		const result = updateDraftedFieldAt(fields, 1, { description: 'Full name' });
		expect(result[1]).toEqual({ name: 'name', datatype: 'text', description: 'Full name' });
		expect(result[0]).toBe(fields[0]);
	});

	it('removes the field at the index', () => {
		expect(removeDraftedFieldAt(fields, 0)).toEqual([{ name: 'name', datatype: 'text' }]);
	});
});
