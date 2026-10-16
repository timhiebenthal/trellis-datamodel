import { describe, it, expect } from 'vitest';
import {
    DEFAULT_FRAMEWORK_COPY,
    FRAMEWORK_COPY_KEYS,
    FRAMEWORK_DISPLAY_KEYS,
    getFrameworkCopy,
} from './framework-display';

describe('getFrameworkCopy', () => {
    it('keeps dbt wording byte-for-byte what the toolbar shipped before', () => {
        // A dbt project must render exactly as it did before this map existed;
        // these are the literal strings the buttons and placeholder carried.
        expect(getFrameworkCopy('dbt-core')).toEqual({
            pullLabel: 'Pull from dbt',
            pullTooltip: 'Import relationship tests from dbt yml files',
            pushLabel: 'Push to dbt',
            pushDirtyTooltip: '⚠️ Changes in data model need to be pushed to dbt schema files',
            pushCleanTooltip:
                'Sync entity & field-definitions and relationship-tests to dbt schema.yml files',
            emptyBindingHint: 'Drag dbt model here',
            unboundHint: 'Draft mode (not bound to dbt model)',
        });
    });

    it('names Bruin instead of dbt and talks about assets, not schema.yml files', () => {
        const copy = getFrameworkCopy('bruin');

        expect(copy.pullLabel).toBe('Pull from Bruin');
        expect(copy.pushLabel).toBe('Push to Bruin');
        expect(copy.emptyBindingHint).toBe('Drag Bruin asset here');

        for (const text of Object.values(copy)) {
            expect(text.toLowerCase()).not.toContain('dbt');
        }
    });

    it('never inherits dbt wording for a framework with no adapter of its own', () => {
        // The same promise the sidebar header makes: an unrecognised framework
        // must not silently claim its models came from dbt.
        for (const framework of ['some-other-framework', 'sqlmesh', '']) {
            const copy = getFrameworkCopy(framework);
            expect(copy).toEqual(DEFAULT_FRAMEWORK_COPY);

            for (const text of Object.values(copy)) {
                expect(text.toLowerCase()).not.toContain('dbt');
            }
        }
    });

    it('falls back to neutral copy when no framework is configured yet', () => {
        expect(getFrameworkCopy(undefined)).toEqual(DEFAULT_FRAMEWORK_COPY);
        expect(getFrameworkCopy(null)).toEqual(DEFAULT_FRAMEWORK_COPY);
    });

    it('offers copy for exactly the frameworks it offers branding for', () => {
        // Entries may only be added alongside a working adapter, so the two maps
        // cannot drift apart and leave a branded framework with dbt-agnostic copy.
        expect(FRAMEWORK_COPY_KEYS).toEqual(FRAMEWORK_DISPLAY_KEYS);
    });
});
