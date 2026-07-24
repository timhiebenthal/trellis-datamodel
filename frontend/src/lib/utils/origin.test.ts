import { describe, it, expect } from 'vitest';
import { stringifyOrigin } from './origin';

describe('stringifyOrigin', () => {
	it('joins keyed entries with pipe separator', () => {
		expect(stringifyOrigin([{ DH1: 'CORE.A' }, { DH2: 'CBUS.B' }])).toBe(
			'DH1: CORE.A | DH2: CBUS.B'
		);
	});

	it('renders empty key as value only', () => {
		expect(stringifyOrigin([{ '': 'SAP.X' }])).toBe('SAP.X');
	});

	it('returns empty string for empty or undefined input', () => {
		expect(stringifyOrigin([])).toBe('');
		expect(stringifyOrigin(undefined)).toBe('');
	});
});
