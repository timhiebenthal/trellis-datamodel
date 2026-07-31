import { describe, it, expect } from 'vitest';
import { mapEntityTagsToNodeData, computeUiTagsAfterEdit } from './entity-tags';
import { readFrameworkTags } from './entity-compat';

describe('mapEntityTagsToNodeData', () => {
    it('splits dbt_tags and ui_tags for a bound entity, plus the display tags union', () => {
        const entity = { dbt_model: 'model.proj.users', tags: ['nightly', 'pii'], dbt_tags: ['nightly'], ui_tags: ['pii'] };
        const result = mapEntityTagsToNodeData(entity);
        expect(result.tags).toEqual(['nightly', 'pii']);
        expect(result.dbt_tags).toEqual(['nightly']);
        expect(result.ui_tags).toEqual(['pii']);
    });

    it('defaults dbt_tags/ui_tags to [] only when genuinely absent', () => {
        const entity = { dbt_model: 'model.proj.users', tags: ['nightly'] };
        const result = mapEntityTagsToNodeData(entity);
        expect(result.dbt_tags).toEqual([]);
        expect(result.ui_tags).toEqual([]);
    });

    it('unbound entity treats tags as the single freely-editable field, dbt_tags/ui_tags unused', () => {
        const entity = { tags: ['draft-tag'] };
        const result = mapEntityTagsToNodeData(entity);
        expect(result.tags).toEqual(['draft-tag']);
        expect(result.dbt_tags).toEqual([]);
        expect(result.ui_tags).toEqual([]);
    });

    it('returns empty mirrored/ui tags for an unbound entity', () => {
        const entity = { tags: ['draft-tag'] };
        const result = mapEntityTagsToNodeData(entity);
        expect(result.dbt_tags).toEqual(readFrameworkTags({}));
        expect(result.ui_tags).toEqual(readFrameworkTags({}));
    });

    it('returns mirrored+ui split for a bound entity', () => {
        const entity = {
            dbt_model: 'model.proj.users',
            tags: ['nightly', 'pii'],
            dbt_tags: ['nightly'],
            ui_tags: ['pii']
        };
        const result = mapEntityTagsToNodeData(entity);
        expect(result.dbt_tags).toEqual(readFrameworkTags({ dbt_tags: entity.dbt_tags }));
        expect(result.ui_tags).toEqual(readFrameworkTags({ dbt_tags: entity.ui_tags }));
    });
});

describe('computeUiTagsAfterEdit', () => {
    it('appends only the delta not already dbt-mirrored', () => {
        expect(computeUiTagsAfterEdit(['nightly'], ['nightly', 'pii'])).toEqual(['pii']);
    });

    it('removing a dbt-mirrored tag from the widget is a no-op — it is not tracked as a removal', () => {
        expect(computeUiTagsAfterEdit(['nightly'], ['pii'])).toEqual(['pii']);
    });

    it('removing a ui tag is reflected since the diff is keyed off newTags alone', () => {
        expect(computeUiTagsAfterEdit(['nightly'], [])).toEqual([]);
    });
});
