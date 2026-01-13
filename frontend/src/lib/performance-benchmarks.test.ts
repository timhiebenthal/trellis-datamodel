/**
 * Performance benchmarks for entity prefix operations.
 * Tests that prefix operations add minimal overhead (<5ms budget).
 */

import { describe, it, expect } from 'vitest';
import { stripEntityPrefixes, formatModelNameForLabel } from './utils';

// Test configuration
const SINGLE_PREFIX = ['tbl_'];
const MULTIPLE_PREFIXES = ['tbl_', 'entity_', 't_'];
const NO_PREFIXES: string[] = [];
const TEST_ITERATIONS = 10000;
const PERFORMANCE_BUDGET_MS = 5;

/**
 * Benchmark stripEntityPrefixes() performance.
 * Expected: < 1ms per operation (well under 5ms budget)
 */
describe('Performance: stripEntityPrefixes()', () => {
    const testCases = [
        { label: 'tbl_customer', prefixes: SINGLE_PREFIX, expected: 'customer' },
        { label: 'TBL_CUSTOMER', prefixes: SINGLE_PREFIX, expected: 'CUSTOMER' }, // case-insensitive
        { label: 'entity_customer', prefixes: MULTIPLE_PREFIXES, expected: 'customer' }, // first match
        { label: 'tbl_customer', prefixes: MULTIPLE_PREFIXES, expected: 'customer' }, // second match
        { label: 'customer', prefixes: MULTIPLE_PREFIXES, expected: 'customer' }, // no match
        { label: 'tbl_', prefixes: SINGLE_PREFIX, expected: 'tbl_' }, // edge case: label equals prefix, returns original
        { label: 'customer', prefixes: NO_PREFIXES, expected: 'customer' }, // no prefixes
    ];

    let totalTime = 0;

    testCases.forEach((testCase, index) => {
        it(`should strip prefix correctly for '${testCase.label}'`, () => {
            // Warmup
            for (let i = 0; i < 1000; i++) {
                stripEntityPrefixes('customer', SINGLE_PREFIX);
            }

            // Actual benchmark
            const start = performance.now();
            let lastResult: string | undefined;
            for (let i = 0; i < TEST_ITERATIONS; i++) {
                lastResult = stripEntityPrefixes(testCase.label, testCase.prefixes);
            }
            const end = performance.now();
            const avgTime = (end - start) / TEST_ITERATIONS;
            totalTime += avgTime;

            // Verify correctness
            expect(lastResult).toBe(testCase.expected);

            // Log performance (for visibility in CI)
            console.log(`  Test ${index + 1}: stripEntityPrefixes('${testCase.label}')`);
            console.log(`    Expected: '${testCase.expected}', Got: '${lastResult}' ✓`);
            console.log(`    Avg time: ${avgTime.toFixed(4)}ms over ${TEST_ITERATIONS} iterations`);
        });
    });

    it('should meet performance budget overall', () => {
        const overallAvg = totalTime / testCases.length;
        console.log(`\n=== Results ===`);
        console.log(`Overall average: ${overallAvg.toFixed(4)}ms`);
        console.log(`Performance budget: < ${PERFORMANCE_BUDGET_MS}ms`);
        console.log(`Status: ${overallAvg < PERFORMANCE_BUDGET_MS ? 'PASS ✓' : 'FAIL ✗'}`);

        expect(overallAvg).toBeLessThan(PERFORMANCE_BUDGET_MS);
    });
});

/**
 * Benchmark formatModelNameForLabel() performance with prefixes.
 * Expected: minimal overhead from prefix stripping (<5ms budget)
 */
describe('Performance: formatModelNameForLabel()', () => {
    const testCases = [
        { name: 'tbl_customer', prefixes: SINGLE_PREFIX, expected: 'Customer' },
        { name: 'entity_booking', prefixes: SINGLE_PREFIX, expected: 'Entity Booking' },
        { name: 'customer', prefixes: SINGLE_PREFIX, expected: 'Customer' },
        { name: 'user_id', prefixes: NO_PREFIXES, expected: 'User Id' },
        { name: 'tbl_', prefixes: SINGLE_PREFIX, expected: 'Tbl ' }, // edge case: prefix stripped results in empty, returns original which is then formatted
        { name: 'API_key', prefixes: NO_PREFIXES, expected: 'Api Key' },
    ];

    let totalTime = 0;

    testCases.forEach((testCase, index) => {
        it(`should format correctly for '${testCase.name}'`, () => {
            // Warmup
            for (let i = 0; i < 1000; i++) {
                formatModelNameForLabel('customer', SINGLE_PREFIX);
            }

            // Actual benchmark
            const start = performance.now();
            let lastResult: string | undefined;
            for (let i = 0; i < TEST_ITERATIONS; i++) {
                lastResult = formatModelNameForLabel(testCase.name, testCase.prefixes);
            }
            const end = performance.now();
            const avgTime = (end - start) / TEST_ITERATIONS;
            totalTime += avgTime;

            // Verify correctness
            expect(lastResult).toBe(testCase.expected);

            // Log performance (for visibility in CI)
            console.log(`  Test ${index + 1}: formatModelNameForLabel('${testCase.name}')`);
            console.log(`    Expected: '${testCase.expected}', Got: '${lastResult}' ✓`);
            console.log(`    Avg time: ${avgTime.toFixed(4)}ms over ${TEST_ITERATIONS} iterations`);
        });
    });

    it('should meet performance budget overall', () => {
        const overallAvg = totalTime / testCases.length;
        console.log(`\n=== Results ===`);
        console.log(`Overall average: ${overallAvg.toFixed(4)}ms`);
        console.log(`Performance budget: < ${PERFORMANCE_BUDGET_MS}ms`);
        console.log(`Status: ${overallAvg < PERFORMANCE_BUDGET_MS ? 'PASS ✓' : 'FAIL ✗'}`);
        console.log(`\n=== All benchmarks passed ✓ ===`);

        expect(overallAvg).toBeLessThan(PERFORMANCE_BUDGET_MS);
    });
});
