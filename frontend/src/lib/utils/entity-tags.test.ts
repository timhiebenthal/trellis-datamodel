import { describe, it, expect } from 'vitest';
import { mapEntityTagsToNodeData } from './entity-tags';

describe('mapEntityTagsToNodeData', () => {
    it('splits dbt-mirrored tags and trellis_tags for a bound entity without resetting trellis_tags', () => {
        const entity = { dbt_model: 'model.proj.users', tags: ['nightly'], trellis_tags: ['pii'] };
        const result = mapEntityTagsToNodeData(entity);
        expect(result.tags).toEqual(['nightly']);
        expect(result.trellis_tags).toEqual(['pii']);
    });

    it('defaults trellis_tags to [] only when genuinely absent', () => {
        const entity = { dbt_model: 'model.proj.users', tags: ['nightly'] };
        const result = mapEntityTagsToNodeData(entity);
        expect(result.trellis_tags).toEqual([]);
    });

    it('unbound entity treats tags as the single freely-editable field', () => {
        const entity = { tags: ['draft-tag'] };
        const result = mapEntityTagsToNodeData(entity);
        expect(result.tags).toEqual(['draft-tag']);
        expect(result.trellis_tags).toEqual(['draft-tag']);
    });
});
