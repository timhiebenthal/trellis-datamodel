import { describe, it, expect } from 'vitest';
import { mapEntityTagsToNodeData, computeUiTagsAfterEdit, normalizeTags, addTag, removeTag, toggleTag } from './entity-tags';
import { readFrameworkTags } from './entity-compat';

describe('mapEntityTagsToNodeData', () => {
    it('splits framework_tags and ui_tags for a bound entity, plus the display tags union', () => {
        const entity = { model_ref: 'model.proj.users', tags: ['nightly', 'pii'], framework_tags: ['nightly'], ui_tags: ['pii'] };
        const result = mapEntityTagsToNodeData(entity);
        expect(result.tags).toEqual(['nightly', 'pii']);
        expect(result.framework_tags).toEqual(['nightly']);
        expect(result.ui_tags).toEqual(['pii']);
    });

    it('defaults framework_tags/ui_tags to [] only when genuinely absent', () => {
        const entity = { model_ref: 'model.proj.users', tags: ['nightly'] };
        const result = mapEntityTagsToNodeData(entity);
        expect(result.framework_tags).toEqual([]);
        expect(result.ui_tags).toEqual([]);
    });

    it('unbound entity treats tags as the single freely-editable field, framework_tags/ui_tags unused', () => {
        const entity = { tags: ['draft-tag'] };
        const result = mapEntityTagsToNodeData(entity);
        expect(result.tags).toEqual(['draft-tag']);
        expect(result.framework_tags).toEqual([]);
        expect(result.ui_tags).toEqual([]);
    });

    it('returns empty mirrored/ui tags for an unbound entity', () => {
        const entity = { tags: ['draft-tag'] };
        const result = mapEntityTagsToNodeData(entity);
        expect(result.framework_tags).toEqual(readFrameworkTags({}));
        expect(result.ui_tags).toEqual(readFrameworkTags({}));
    });

    it('returns mirrored+ui split for a bound entity', () => {
        const entity = {
            model_ref: 'model.proj.users',
            tags: ['nightly', 'pii'],
            framework_tags: ['nightly'],
            ui_tags: ['pii']
        };
        const result = mapEntityTagsToNodeData(entity);
        expect(result.framework_tags).toEqual(readFrameworkTags({ framework_tags: entity.framework_tags }));
        expect(result.ui_tags).toEqual(readFrameworkTags({ framework_tags: entity.ui_tags }));
    });
});

describe('computeUiTagsAfterEdit', () => {
    it('appends only the delta not already framework-mirrored', () => {
        expect(computeUiTagsAfterEdit(['nightly'], ['nightly', 'pii'])).toEqual(['pii']);
    });

    it('removing a framework-mirrored tag from the widget is a no-op — it is not tracked as a removal', () => {
        expect(computeUiTagsAfterEdit(['nightly'], ['pii'])).toEqual(['pii']);
    });

    it('removing a ui tag is reflected since the diff is keyed off newTags alone', () => {
        expect(computeUiTagsAfterEdit(['nightly'], [])).toEqual([]);
    });
});

describe('normalizeTags', () => {
    it('returns [] for empty or non-tag input', () => {
        expect(normalizeTags(undefined)).toEqual([]);
        expect(normalizeTags('')).toEqual([]);
        expect(normalizeTags(42)).toEqual([]);
    });

    it('trims, drops empties and dedupes arrays', () => {
        expect(normalizeTags([' a ', '', 'b', 'a'])).toEqual(['a', 'b']);
    });

    it('splits a comma-separated string instead of iterating characters', () => {
        expect(normalizeTags('pii, nightly ,pii')).toEqual(['pii', 'nightly']);
    });
});

describe('addTag', () => {
    it('appends the trimmed tag', () => {
        expect(addTag(['a'], '  b ')).toEqual(['a', 'b']);
    });

    it('returns null for blank input or an existing tag', () => {
        expect(addTag(['a'], '   ')).toBeNull();
        expect(addTag(['a'], ' a ')).toBeNull();
    });

    it('does not mutate the input list', () => {
        const tags = ['a'];
        addTag(tags, 'b');
        expect(tags).toEqual(['a']);
    });
});

describe('removeTag', () => {
    it('removes every occurrence of the tag', () => {
        expect(removeTag(['a', 'b', 'a'], 'a')).toEqual(['b']);
    });

    it('leaves the list unchanged when the tag is absent', () => {
        expect(removeTag(['a'], 'z')).toEqual(['a']);
    });
});

describe('toggleTag', () => {
    it('adds a missing tag at the end', () => {
        expect(toggleTag(['a'], 'b')).toEqual(['a', 'b']);
    });

    it('removes a present tag', () => {
        expect(toggleTag(['a', 'b'], 'a')).toEqual(['b']);
    });
});
