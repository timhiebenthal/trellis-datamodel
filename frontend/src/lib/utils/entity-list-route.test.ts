import { describe, expect, it } from 'vitest';
import {
	getCanvasFilterPath,
	getEntityDetailPath,
	getEntityIdFromPath,
	isEntityDetailPath,
} from './entity-list-route';

describe('entity-list routes', () => {
	it('builds a detail path from an entity ID', () => {
		expect(getEntityDetailPath('dim-customer')).toBe('/entity-list/dim-customer');
	});

	it('encodes and decodes entity IDs containing reserved URL characters', () => {
		const path = getEntityDetailPath('customer/profile');

		expect(path).toBe('/entity-list/customer%2Fprofile');
		expect(getEntityIdFromPath(path)).toBe('customer/profile');
	});

	it('only recognizes entity-list detail paths', () => {
		expect(getEntityIdFromPath('/entity-list/dim-customer')).toBe('dim-customer');
		expect(getEntityIdFromPath('/entity-list')).toBeNull();
		expect(getEntityIdFromPath('/canvas/dim-customer')).toBeNull();
		expect(isEntityDetailPath('/entity-list/dim-customer')).toBe(true);
		expect(isEntityDetailPath('/entity-list')).toBe(false);
	});

	it('builds one encoded entities query parameter for Canvas', () => {
		expect(getCanvasFilterPath(['customer profile', 'orders/line-items', 'facts?&='])).toBe(
			'/canvas?entities=customer%20profile%2Corders%2Fline-items%2Cfacts%3F%26%3D',
		);
	});

	it('preserves entity ID order in the Canvas route', () => {
		expect(getCanvasFilterPath(['third', 'first', 'second'])).toBe(
			'/canvas?entities=third%2Cfirst%2Csecond',
		);
	});

	it('returns the unfiltered Canvas path when no IDs are supplied', () => {
		expect(getCanvasFilterPath([])).toBe('/canvas');
	});
});
