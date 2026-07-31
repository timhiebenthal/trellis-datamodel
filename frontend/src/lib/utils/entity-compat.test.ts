import { describe, it, expect } from 'vitest';
import { readModelRef, readFrameworkTags } from './entity-compat';

describe('readModelRef', () => {
    it('reads the new model_ref key', () => {
        expect(readModelRef({ model_ref: 'model.proj.users' })).toBe('model.proj.users');
    });

    it('falls back to the legacy dbt_model key', () => {
        expect(readModelRef({ dbt_model: 'model.proj.legacy_users' })).toBe('model.proj.legacy_users');
    });

    it('prefers model_ref when both are present', () => {
        expect(readModelRef({ model_ref: 'model.proj.new_users', dbt_model: 'model.proj.legacy_users' })).toBe(
            'model.proj.new_users'
        );
    });

    it('returns undefined when neither key is present', () => {
        expect(readModelRef({})).toBeUndefined();
    });
});

describe('readFrameworkTags', () => {
    it('reads the new framework_tags key', () => {
        expect(readFrameworkTags({ framework_tags: ['nightly'] })).toEqual(['nightly']);
    });

    it('falls back to the legacy dbt_tags key', () => {
        expect(readFrameworkTags({ dbt_tags: ['nightly'] })).toEqual(['nightly']);
    });

    it('prefers framework_tags when both are present', () => {
        expect(readFrameworkTags({ framework_tags: ['pii'], dbt_tags: ['nightly'] })).toEqual(['pii']);
    });

    it('returns [] when neither key is present', () => {
        expect(readFrameworkTags({})).toEqual([]);
    });
});
