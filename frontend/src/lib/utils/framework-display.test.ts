import { describe, it, expect } from 'vitest';
import {
    DEFAULT_FRAMEWORK_COPY,
    FRAMEWORK_COPY_KEYS,
    FRAMEWORK_DISPLAY_KEYS,
    getFrameworkCopy,
    formatModelHint,
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
            addModelTooltip: 'Drag a dbt model from the sidebar to add it',
            emptyCanvasHint:
                'Drag dbt models from the sidebar or create new entities to begin building your data model.',
            noRelationshipsMessage: 'No relationships in dbt',
            materializedHint: 'Materialized in dbt model {model}',
            unmaterializedHint:
                "Drafted in Trellis — not yet materialized in dbt. Click 'Materialize' to write into {model}'s schema.yml.",
            boundModelsHeading: 'Bound dbt Models',
            materializedColumnsNote: '— dbt columns are read-only',
            managedTagHint: 'Managed by dbt (schema.yml) — cannot be removed here',
            builtHint: 'Built with dbt: {model}',
            unbuiltHint: 'Not yet built with dbt',
            builtLegendHint: 'Entities with this mark are already built with dbt',
            builtLegendShort: '= built with dbt',
            pushWarningDescription:
                'Show a warning for undescribed entities/attributes when you push to dbt.',
            lineageTooltip:
                'Visualize data lineage across your dbt models. Configure layers to organize models by transformation stages (e.g., staging, intermediate, marts).',
            modelColumnLabel: 'dbt Model',
        });
    });

    it('names Bruin instead of dbt and talks about assets, not schema.yml files', () => {
        const copy = getFrameworkCopy('bruin');

        expect(copy.pullLabel).toBe('Pull from Bruin');
        expect(copy.pushLabel).toBe('Push to Bruin');
        expect(copy.emptyBindingHint).toBe('Drag Bruin asset here');
        expect(copy.emptyCanvasHint).toContain('Bruin assets');
        expect(copy.noRelationshipsMessage).toBe('No relationships in Bruin');
        expect(copy.boundModelsHeading).toBe('Bound Bruin Assets');
        expect(copy.materializedHint).toBe('Materialized in Bruin asset {model}');
        expect(copy.modelColumnLabel).toBe('Bruin Asset');

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

    it('returns neutral copy for undefined/null input', () => {
        // The layout coerces a missing framework to 'dbt-core' before it reaches
        // the store, so this only guards the getter's own contract.
        expect(getFrameworkCopy(undefined)).toEqual(DEFAULT_FRAMEWORK_COPY);
        expect(getFrameworkCopy(null)).toEqual(DEFAULT_FRAMEWORK_COPY);
    });

    it('offers copy for exactly the frameworks it offers branding for', () => {
        // Entries may only be added alongside a working adapter, so the two maps
        // cannot drift apart and leave a branded framework with dbt-agnostic copy.
        // Sorted because only set membership matters, not declaration order.
        expect([...FRAMEWORK_COPY_KEYS].sort()).toEqual([...FRAMEWORK_DISPLAY_KEYS].sort());
    });
});

describe('formatModelHint', () => {
    it('substitutes the bound model name into the placeholder', () => {
        expect(formatModelHint('Built with dbt: {model}', 'orders')).toBe('Built with dbt: orders');
    });

    it('leaves a template without the placeholder untouched', () => {
        expect(formatModelHint('Not yet built with dbt', 'orders')).toBe('Not yet built with dbt');
    });
});
