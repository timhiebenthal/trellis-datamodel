import { describe, expect, it } from 'vitest';
import { uniqueRoleNames } from './entity-roles';

describe('uniqueRoleNames', () => {
	it('prefers role over label and drops empty entries', () => {
		expect(uniqueRoleNames([{ role: 'Buyer', label: 'x' }, { label: 'Seller' }, {}])).toEqual(['Buyer', 'Seller']);
	});

	it('deduplicates case-insensitively keeping the first spelling', () => {
		expect(uniqueRoleNames([{ role: 'Creation Date' }, { role: 'creation date' }])).toEqual(['Creation Date']);
	});

	it('handles missing roles', () => {
		expect(uniqueRoleNames(undefined)).toEqual([]);
	});
});
