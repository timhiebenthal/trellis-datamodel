import { normalizeTags } from '$lib/utils';

export function mapEntityTagsToNodeData(entity: { dbt_model?: string; tags?: unknown; trellis_tags?: unknown }): {
    tags: string[];
    trellis_tags: string[];
} {
    const tags = normalizeTags(entity.tags);
    if (!entity.dbt_model) {
        return { tags, trellis_tags: tags };
    }
    return { tags, trellis_tags: normalizeTags(entity.trellis_tags) };
}

/**
 * Given the tags currently mirrored from dbt (schema.yml) and the full tag list a
 * user's edit in the tag-editor widget implies (`newTags` — the widget's post-edit
 * state), compute the resulting `trellis_tags`.
 *
 * Only tags not already dbt-mirrored are Trellis's to track: a dbt-mirrored tag is
 * never removable via this path (dbt wins), so its absence from `newTags` — e.g. a
 * user trying to drop a read-only chip — is not treated as a removal. Anything the
 * user actually removed from `trellis_tags` (tags absent from `newTags` that aren't
 * dbt-mirrored either) is dropped, since the diff is keyed off `newTags` alone.
 */
export function computeTrellisTagsAfterEdit(dbtMirroredTags: unknown, newTags: unknown): string[] {
    const dbtMirrored = new Set(normalizeTags(dbtMirroredTags));
    return normalizeTags(newTags).filter((t) => !dbtMirrored.has(t));
}
