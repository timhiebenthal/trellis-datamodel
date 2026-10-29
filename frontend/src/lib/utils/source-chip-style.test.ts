import { describe, expect, it } from 'vitest';
import { getSourceChipStyle } from './source-chip-style';

describe('getSourceChipStyle', () => {
	it('uses the configured colour as a solid chip', () => {
		expect(getSourceChipStyle('SAP', { SAP: '#123456' })).toBe(
			'background-color: #123456; color: white; border: 1px solid #123456;',
		);
	});

	it('falls back to a deterministic tinted colour', () => {
		const style = getSourceChipStyle('Salesforce', {});
		expect(style).toBe(getSourceChipStyle('Salesforce', {}));
		expect(style).toMatch(/^background-color: #[0-9A-F]{6}20; color: #[0-9A-F]{6}; border: 1px solid #[0-9A-F]{6}40;$/);
	});

	it('hashes the empty name to the first fallback colour', () => {
		expect(getSourceChipStyle('', {})).toBe(
			'background-color: #3B82F620; color: #3B82F6; border: 1px solid #3B82F640;',
		);
	});
});
