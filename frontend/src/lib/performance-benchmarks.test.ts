/**
 * Performance benchmarks for entity prefix operations.
 * Tests that prefix operations add minimal overhead (<5ms budget).
 */

import { stripEntityPrefixes, formatModelNameForLabel } from './utils';

// Test configuration
const SINGLE_PREFIX = ['tbl_'];
const MULTIPLE_PREFIXES = ['tbl_', 'entity_', 't_'];
const NO_PREFIXES: string[] = [];
const TEST_ITERATIONS = 10000;

/**
 * Benchmark stripEntityPrefixes() performance.
 * Expected: < 1ms per operation (well under 5ms budget)
 */
function benchmarkStripEntityPrefixes() {
    const testCases = [
        { label: 'tbl_customer', prefixes: SINGLE_PREFIX, expected: 'customer' },
        { label: 'TBL_CUSTOMER', prefixes: SINGLE_PREFIX, expected: 'CUSTOMER' }, // case-insensitive
        { label: 'entity_customer', prefixes: MULTIPLE_PREFIXES, expected: 'customer' }, // first match
        { label: 'tbl_customer', prefixes: MULTIPLE_PREFIXES, expected: 'customer' }, // second match
        { label: 'customer', prefixes: MULTIPLE_PREFIXES, expected: 'customer' }, // no match
        { label: 'tbl_', prefixes: SINGLE_PREFIX, expected: '' }, // edge case: label equals prefix
        { label: 'customer', prefixes: NO_PREFIXES, expected: 'customer' }, // no prefixes
    ];

    console.log('=== Benchmarking stripEntityPrefixes() ===');
    
    // Warmup
    for (let i = 0; i < 1000; i++) {
        stripEntityPrefixes('customer', SINGLE_PREFIX);
    }

    // Actual benchmark
    let totalTime = 0;
    testCases.forEach((testCase, index) => {
        const start = performance.now();
        
        let lastResult: string | undefined;
        for (let i = 0; i < TEST_ITERATIONS; i++) {
            lastResult = stripEntityPrefixes(testCase.label, testCase.prefixes);
        }
        
        const end = performance.now();
        const avgTime = (end - start) / TEST_ITERATIONS;
        totalTime += avgTime;
        
        const passed = lastResult === testCase.expected;
        console.log(`  Test ${index + 1}: stripEntityPrefixes('${testCase.label}', [${testCase.prefixes.join(', ')}])`);
        console.log(`    Expected: '${testCase.expected}', Got: '${lastResult}' ${passed ? '✓' : '✗'}`);
        console.log(`    Avg time: ${avgTime.toFixed(4)}ms over ${TEST_ITERATIONS} iterations`);
    });

    const overallAvg = totalTime / testCases.length;
    console.log(`\n=== Results ===`);
    console.log(`Overall average: ${overallAvg.toFixed(4)}ms`);
    console.log(`Performance budget: < 5ms`);
    console.log(`Status: ${overallAvg < 5 ? 'PASS ✓' : 'FAIL ✗'}`);
    
    if (overallAvg >= 5) {
        throw new Error(`Performance budget exceeded: ${overallAvg.toFixed(4)}ms >= 5ms`);
    }
}

/**
 * Benchmark formatModelNameForLabel() performance with prefixes.
 * Expected: minimal overhead from prefix stripping (<5ms budget)
 */
function benchmarkFormatModelNameForLabel() {
    const testCases = [
        { name: 'tbl_customer', prefixes: SINGLE_PREFIX, expected: 'Tbl Customer' },
        { name: 'entity_booking', prefixes: SINGLE_PREFIX, expected: 'Entity Booking' },
        { name: 'customer', prefixes: SINGLE_PREFIX, expected: 'Customer' },
        { name: 'user_id', prefixes: NO_PREFIXES, expected: 'User Id' },
        { name: 'tbl_', prefixes: SINGLE_PREFIX, expected: 'Tbl ' }, // edge case
        { name: 'API_key', prefixes: NO_PREFIXES, expected: 'Api Key' },
    ];

    console.log('=== Benchmarking formatModelNameForLabel() ===');
    
    // Warmup
    for (let i = 0; i < 1000; i++) {
        formatModelNameForLabel('customer', SINGLE_PREFIX);
    }

    // Actual benchmark
    let totalTime = 0;
    testCases.forEach((testCase, index) => {
        const start = performance.now();
        
        let lastResult: string | undefined;
        for (let i = 0; i < TEST_ITERATIONS; i++) {
            lastResult = formatModelNameForLabel(testCase.name, testCase.prefixes);
        }
        
        const end = performance.now();
        const avgTime = (end - start) / TEST_ITERATIONS;
        totalTime += avgTime;
        
        const passed = lastResult === testCase.expected;
        console.log(`  Test ${index + 1}: formatModelNameForLabel('${testCase.name}', [${testCase.prefixes.join(', ')}])`);
        console.log(`    Expected: '${testCase.expected}', Got: '${lastResult}' ${passed ? '✓' : '✗'}`);
        console.log(`    Avg time: ${avgTime.toFixed(4)}ms over ${TEST_ITERATIONS} iterations`);
    });

    const overallAvg = totalTime / testCases.length;
    console.log(`\n=== Results ===`);
    console.log(`Overall average: ${overallAvg.toFixed(4)}ms`);
    console.log(`Performance budget: < 5ms`);
    console.log(`Status: ${overallAvg < 5 ? 'PASS ✓' : 'FAIL ✗'}`);
    
    if (overallAvg >= 5) {
        throw new Error(`Performance budget exceeded: ${overallAvg.toFixed(4)}ms >= 5ms`);
    }
}

// Run benchmarks if executed directly
if (import.meta.url?.includes('performance-benchmarks.test')) {
    try {
        benchmarkStripEntityPrefixes();
        benchmarkFormatModelNameForLabel();
        console.log('\n=== All benchmarks passed ✓ ===');
    } catch (error) {
        console.error('Benchmark failed:', error);
        process.exit(1);
    }
}
