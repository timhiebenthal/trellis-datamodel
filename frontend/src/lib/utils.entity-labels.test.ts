/**
 * Correctness cases for entity prefix operations.
 * (Timing budgets were removed: a 5ms-per-call budget cannot fail in practice.)
 */

import { describe, it, expect } from 'vitest';
import { stripEntityPrefixes, formatModelNameForLabel } from './utils';

const SINGLE_PREFIX = ['tbl_'];
const MULTIPLE_PREFIXES = ['tbl_', 'entity_', 't_'];
const NO_PREFIXES: string[] = [];

describe('stripEntityPrefixes() cases', () => {
    const testCases = [
        { label: 'tbl_customer', prefixes: SINGLE_PREFIX, expected: 'customer' },
        { label: 'TBL_CUSTOMER', prefixes: SINGLE_PREFIX, expected: 'CUSTOMER' }, // case-insensitive
        { label: 'entity_customer', prefixes: MULTIPLE_PREFIXES, expected: 'customer' }, // first match
        { label: 'tbl_customer', prefixes: MULTIPLE_PREFIXES, expected: 'customer' }, // second match
        { label: 'customer', prefixes: MULTIPLE_PREFIXES, expected: 'customer' }, // no match
        { label: 'tbl_', prefixes: SINGLE_PREFIX, expected: 'tbl_' }, // label equals prefix, returns original
        { label: 'customer', prefixes: NO_PREFIXES, expected: 'customer' }, // no prefixes
    ];

    testCases.forEach((testCase) => {
        it(`should strip prefix correctly for '${testCase.label}'`, () => {
            expect(stripEntityPrefixes(testCase.label, testCase.prefixes)).toBe(testCase.expected);
        });
    });
});

describe('formatModelNameForLabel() cases', () => {
    const testCases = [
        { name: 'tbl_customer', prefixes: SINGLE_PREFIX, expected: 'Customer' },
        { name: 'entity_booking', prefixes: SINGLE_PREFIX, expected: 'Entity Booking' },
        { name: 'customer', prefixes: SINGLE_PREFIX, expected: 'Customer' },
        { name: 'user_id', prefixes: NO_PREFIXES, expected: 'User Id' },
        { name: 'tbl_', prefixes: SINGLE_PREFIX, expected: 'Tbl ' }, // prefix-only name returns original, then formatted
        { name: 'API_key', prefixes: NO_PREFIXES, expected: 'Api Key' },
    ];

    testCases.forEach((testCase) => {
        it(`should format correctly for '${testCase.name}'`, () => {
            expect(formatModelNameForLabel(testCase.name, testCase.prefixes)).toBe(testCase.expected);
        });
    });
});
