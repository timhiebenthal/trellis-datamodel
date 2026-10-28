/**
 * Lowercase `label`, replace each run of `disallowed` characters with `_`, trim
 * leading/trailing underscores (falling back to `entity` when nothing is left),
 * then suffix `_1`, `_2`, ... until the result is not taken by another ID in
 * `existingIds` (`currentId` itself does not count as taken).
 */
function uniqueSlug(label: string, disallowed: RegExp, existingIds: string[], currentId?: string): string {
    const base = label.toLowerCase().replace(disallowed, '_').replace(/^_+|_+$/g, '') || 'entity';

    let candidate = base;
    let counter = 1;
    while (existingIds.some((id) => id === candidate && id !== currentId)) {
        candidate = `${base}_${counter}`;
        counter++;
    }

    return candidate;
}

/**
 * Generate a URL-safe slug from a label, ensuring uniqueness against existing IDs.
 * Underscore runs collapse to a single `_` (`"a__b"` -> `"a_b"`).
 */
export function generateSlug(label: string, existingIds: string[], currentId?: string): string {
    return uniqueSlug(label, /[^a-z0-9]+/g, existingIds, currentId);
}

/**
 * Generate an entity ID while preserving existing underscores.
 *
 * This is used for dimensional model entity IDs where configured prefixes like
 * `dim__` and `fact__` must survive round-tripping through the UI.
 */
export function generateEntityId(label: string, existingIds: string[], currentId?: string): string {
    return uniqueSlug(label, /[^a-z0-9_]+/g, existingIds, currentId);
}
