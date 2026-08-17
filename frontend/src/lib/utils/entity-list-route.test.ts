import { describe, expect, it } from 'vitest';
import {
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
});
