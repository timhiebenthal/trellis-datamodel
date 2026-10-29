import type { DraftedField } from '$lib/types';

/** Append an empty text field to the drafted fields. */
export function appendDraftedField(fields: DraftedField[]): DraftedField[] {
	const newField: DraftedField = { name: '', datatype: 'text' };
	return [...fields, newField];
}

/** Merge `updates` into the drafted field at `index`. */
export function updateDraftedFieldAt(
	fields: DraftedField[],
	index: number,
	updates: Partial<DraftedField>,
): DraftedField[] {
	return fields.map((field, i) => (i === index ? { ...field, ...updates } : field));
}

/** Remove the drafted field at `index`. */
export function removeDraftedFieldAt(fields: DraftedField[], index: number): DraftedField[] {
	return fields.filter((_, i) => i !== index);
}
