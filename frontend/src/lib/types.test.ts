import { describe, it, expectTypeOf } from 'vitest';
import type { OriginEntry, DbtColumn, DraftedField } from './types';

describe('origin types', () => {
	it('OriginEntry is a single-key record', () => {
		expectTypeOf<OriginEntry>().toEqualTypeOf<Record<string, string>>();
	});

	it('DbtColumn accepts structured origin', () => {
		expectTypeOf<DbtColumn['origin']>().toEqualTypeOf<OriginEntry[] | undefined>();
	});

	it('DraftedField origin is a structured list', () => {
		const field: DraftedField = {
			name: 'amount',
			datatype: 'float',
			origin: [{ DH1: 'CORE.A' }],
		};
		expectTypeOf(field.origin).toEqualTypeOf<OriginEntry[] | undefined>();
	});
});
