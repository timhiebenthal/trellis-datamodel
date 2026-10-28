import { readModelRef, readFrameworkTags } from './entity-compat';

/**
 * Normalize any incoming tag shape (string | string[] | undefined) into a
 * clean, deduplicated array of non-empty strings. Prevents single strings
 * from being treated as iterables (which would otherwise explode into
 * characters when spread or flatMapped).
 */
export function normalizeTags(raw: unknown): string[] {
    if (!raw) return [];

    const toStrings = (vals: unknown[]): string[] =>
        vals
            .map((v) => String(v).trim())
            .filter((v) => v.length > 0);

    if (Array.isArray(raw)) {
        return Array.from(new Set(toStrings(raw)));
    }

    if (typeof raw === 'string') {
        // Support comma-separated lists while still accepting single tokens
        const parts = raw.split(',').map((p) => p.trim()).filter(Boolean);
        return Array.from(new Set(parts));
    }

    return [];
}

/**
 * Append a user-typed tag to a list. Returns the new list, or `null` when the
 * trimmed input is empty or already present (callers keep their input text then).
 */
export function addTag(tags: string[], raw: string): string[] | null {
    return addTags(tags, [raw]);
}

/**
 * Append several user-typed tags (e.g. a pasted comma-separated list) in one go:
 * each is trimmed, empty and already-present ones are skipped, duplicates collapse.
 * Returns the new list, or `null` when nothing new would be added.
 */
export function addTags(tags: string[], raws: string[]): string[] | null {
    const added = [...new Set(raws.map((raw) => raw.trim()).filter(Boolean))].filter(
        (tag) => !tags.includes(tag),
    );
    return added.length > 0 ? [...tags, ...added] : null;
}

/** Return `tags` without `tag`. */
export function removeTag(tags: string[], tag: string): string[] {
    return tags.filter((t) => t !== tag);
}

/** Remove `tag` if present, otherwise append it (filter-chip toggle). */
export function toggleTag(tags: string[], tag: string): string[] {
    return tags.includes(tag) ? removeTag(tags, tag) : [...tags, tag];
}

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
