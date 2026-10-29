import { describe, expect, it } from 'vitest';
import { computeResizePatch } from './node-dimensions';

describe('computeResizePatch', () => {
	it('resizes width within 280..600', () => {
		expect(computeResizePatch('width', 320, 50)).toEqual({ width: 370 });
		expect(computeResizePatch('width', 320, -100)).toEqual({ width: 280 });
		expect(computeResizePatch('width', 320, 1000)).toEqual({ width: 600 });
	});

	it('resizes the column panel height within 120..600', () => {
		expect(computeResizePatch('height', 200, 40)).toEqual({ panelHeight: 240 });
		expect(computeResizePatch('height', 200, -500)).toEqual({ panelHeight: 120 });
		expect(computeResizePatch('height', 200, 900)).toEqual({ panelHeight: 600 });
	});
});
