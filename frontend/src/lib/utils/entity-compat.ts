/**
 * Migration-compat helpers for reading entity fields that are being renamed
 * from their legacy dbt-specific names to framework-agnostic ones:
 *   - `dbt_model` -> `model_ref`
 *   - `dbt_tags` -> `framework_tags`
 *
 * These helpers prefer the new key when present and fall back to the legacy
 * key otherwise, so callers can be migrated incrementally without any change
 * in observed behavior. Once all data is migrated and all call sites read
 * through these helpers, the legacy keys can be dropped in one place.
 */

interface EntityWithModelRef {
    model_ref?: string;
    dbt_model?: string;
}

interface EntityWithFrameworkTags {
    framework_tags?: string[];
    dbt_tags?: string[];
}

/**
 * Returns the entity's model reference, preferring the new `model_ref` key
 * and falling back to the legacy `dbt_model` key.
 */
export function readModelRef(e: EntityWithModelRef): string | undefined {
    return e.model_ref ?? e.dbt_model;
}

/**
 * Returns the entity's framework tags, preferring the new `framework_tags`
 * key and falling back to the legacy `dbt_tags` key. Returns an empty array
 * when neither is present.
 */
export function readFrameworkTags(e: EntityWithFrameworkTags): string[] {
    return e.framework_tags ?? e.dbt_tags ?? [];
}
