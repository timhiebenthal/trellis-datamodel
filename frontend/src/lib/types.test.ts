import { describe, it, expect, expectTypeOf } from 'vitest';
import type { OriginEntry, DbtColumn, DraftedField, Entity } from './types';
import { readModelRef, readFrameworkTags } from './utils/entity-compat';

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

describe('Entity model_ref/framework_tags round-trip', () => {
	it('reads model_ref and framework_tags via the compat helpers', () => {
		const entity: Entity = {
			id: 'entity_booking',
			label: 'Booking',
			position: { x: 0, y: 0 },
			model_ref: 'model.elmo.entity_booking',
			framework_tags: ['pii', 'core'],
		};

		expect(readModelRef(entity)).toBe('model.elmo.entity_booking');
		expect(readFrameworkTags(entity)).toEqual(['pii', 'core']);
	});
});
