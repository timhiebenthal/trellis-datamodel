import { describe, it, expect } from 'vitest';
import { generateSlug, generateEntityId } from './slug';

describe('generateSlug', () => {
    it('converts label to lowercase slug', () => {
        expect(generateSlug('My Entity', [])).toBe('my_entity');
    });

    it('replaces special characters with underscores', () => {
        expect(generateSlug('Hello@World!', [])).toBe('hello_world');
    });

    it('trims leading and trailing underscores', () => {
        expect(generateSlug('  Test  ', [])).toBe('test');
        expect(generateSlug('___test___', [])).toBe('test');
    });

    it('returns "entity" for empty or special-char-only input', () => {
        expect(generateSlug('', [])).toBe('entity');
        expect(generateSlug('@#$%', [])).toBe('entity');
        expect(generateSlug('   ', [])).toBe('entity');
    });

    it('ensures uniqueness by appending counter', () => {
        const existingIds = ['users', 'orders'];
        expect(generateSlug('Users', existingIds)).toBe('users_1');
        expect(generateSlug('Orders', existingIds)).toBe('orders_1');
    });

    it('increments counter until unique', () => {
        const existingIds = ['test', 'test_1', 'test_2'];
        expect(generateSlug('Test', existingIds)).toBe('test_3');
    });

    it('excludes currentId when checking uniqueness (for renaming)', () => {
        const existingIds = ['users', 'orders'];
        // When renaming 'users' to 'Users', slug should stay 'users'
        expect(generateSlug('Users', existingIds, 'users')).toBe('users');
    });

    it('handles complex labels correctly', () => {
        expect(generateSlug('User Profile (v2)', [])).toBe('user_profile_v2');
        expect(generateSlug('Data-Model_123', [])).toBe('data_model_123');
    });
});

describe('generateEntityId', () => {
    it('preserves underscore runs such as configured prefixes', () => {
        expect(generateEntityId('dim__Customer', [])).toBe('dim__customer');
    });

    it('collapses other special characters and trims underscores', () => {
        expect(generateEntityId('  Order Line!  ', [])).toBe('order_line');
    });

    it('falls back to "entity" and suffixes duplicates, ignoring currentId', () => {
        expect(generateEntityId('!!!', [])).toBe('entity');
        expect(generateEntityId('customer', ['customer', 'customer_1'])).toBe('customer_2');
        expect(generateEntityId('customer', ['customer'], 'customer')).toBe('customer');
    });
});

describe('generateSlug vs generateEntityId', () => {
    it('differ only in how underscore runs are treated', () => {
        expect(generateSlug('dim__customer', [])).toBe('dim_customer');
        expect(generateEntityId('dim__customer', [])).toBe('dim__customer');
    });
});
