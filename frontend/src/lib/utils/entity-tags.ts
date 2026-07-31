import { normalizeTags } from '$lib/utils';
import { readModelRef, readFrameworkTags } from './entity-compat';

/**
 * Split an entity's tag fields into node data. `tags` is the backend-computed
 * display union (framework_tags + ui_tags) for bound entities — read-only, never
 * hand-edited. `framework_tags`/`ui_tags` are only meaningful for bound entities;
 * unbound entities have no schema.yml to mirror and use plain `tags` as their
 * single, freely-editable field instead.
 */
export function mapEntityTagsToNodeData(entity: { model_ref?: string; dbt_model?: string; tags?: unknown; framework_tags?: string[]; dbt_tags?: string[]; ui_tags?: unknown }): {
    tags: string[];
    framework_tags: string[];
    ui_tags: string[];
} {
    const tags = normalizeTags(entity.tags);
    if (!readModelRef(entity)) {
        return { tags, framework_tags: [], ui_tags: [] };
    }
    return { tags, framework_tags: normalizeTags(readFrameworkTags(entity)), ui_tags: normalizeTags(entity.ui_tags) };
}

/**
 * Given a bound entity's framework-mirrored tags and the full tag list a user's edit
 * in the tag-editor widget implies (`newTags` — the widget's post-edit state),
 * compute the resulting `ui_tags`.
 *
 * Only tags not already framework-mirrored are Trellis's to track: a framework-mirrored
 * tag is never removable via this path (the framework's model wins), so its absence from
 * `newTags` — e.g. a user trying to drop a read-only chip — is not treated as a removal.
 * Anything the user actually removed from `ui_tags` (tags absent from `newTags` that
 * aren't framework-mirrored either) is dropped, since the diff is keyed off `newTags` alone.
 */
export function computeUiTagsAfterEdit(frameworkTags: unknown, newTags: unknown): string[] {
    const frameworkMirrored = new Set(normalizeTags(frameworkTags));
    return normalizeTags(newTags).filter((t) => !frameworkMirrored.has(t));
}
