/**
 * Framework-driven branding and copy for the UI.
 *
 * Trellis is framework-agnostic by design: the transformation framework is a
 * config value, not an assumption baked into the UI. This map holds branding
 * only for frameworks Trellis actually implements an adapter for. Anything else
 * gets neutral branding rather than silently inheriting dbt's, which would make
 * the header lie about what the models came from.
 *
 * Add an entry here when its adapter lands, not before.
 */

import type { FrameworkCapabilities } from "$lib/types";

export interface FrameworkDisplay {
    icon: string;
    label: string;
    alt: string;
}

const FRAMEWORK_DISPLAY: Record<string, FrameworkDisplay> = {
    "dbt-core": {
        icon: "https://www.getdbt.com/favicon.ico",
        label: "dbt Models",
        alt: "dbt icon",
    },
    bruin: {
        // The vendor's own favicon, same approach as dbt above, rather than a
        // hand-drawn stand-in that would misrepresent the brand.
        icon: "https://getbruin.com/favicon.ico",
        label: "Bruin Assets",
        alt: "Bruin icon",
    },
};

/** Neutral branding for a configured framework Trellis has no adapter for yet. */
export const DEFAULT_FRAMEWORK_DISPLAY: FrameworkDisplay = {
    icon: "/icons/framework.svg",
    label: "Models",
    alt: "framework icon",
};

/** Frameworks with dedicated branding. Exported so tests can assert it stays honest. */
export const FRAMEWORK_DISPLAY_KEYS = Object.keys(FRAMEWORK_DISPLAY);

export function getFrameworkDisplay(framework: string | undefined | null): FrameworkDisplay {
    if (!framework) return DEFAULT_FRAMEWORK_DISPLAY;
    return FRAMEWORK_DISPLAY[framework] ?? DEFAULT_FRAMEWORK_DISPLAY;
}

/**
 * Wording for the controls that move relationship metadata in and out of the
 * project. These sit next to the icon/label branding because they answer the
 * same question the header does: what is the configured framework called?
 *
 * The dbt strings are byte-for-byte what the toolbar shipped before this map
 * existed, so a dbt project renders identically. Only the entries Trellis has
 * an adapter for may name a framework; everything else gets neutral wording
 * rather than claiming dbt.
 */
export interface FrameworkCopy {
    /** Label for the button that imports relationships from the project. */
    pullLabel: string;
    /** Tooltip for the pull button. */
    pullTooltip: string;
    /** Label for the button that writes relationships back to the project. */
    pushLabel: string;
    /** Tooltip for the push button while it has unsynced changes. */
    pushDirtyTooltip: string;
    /** Tooltip for the push button when everything is in sync. */
    pushCleanTooltip: string;
    /** Placeholder shown on an entity that is not bound to a model yet. */
    emptyBindingHint: string;
    /** Tooltip on the draft badge of an entity that is not bound to a model. */
    unboundHint: string;
}

const FRAMEWORK_COPY: Record<string, FrameworkCopy> = {
    "dbt-core": {
        pullLabel: "Pull from dbt",
        pullTooltip: "Import relationship tests from dbt yml files",
        pushLabel: "Push to dbt",
        pushDirtyTooltip: "⚠️ Changes in data model need to be pushed to dbt schema files",
        pushCleanTooltip:
            "Sync entity & field-definitions and relationship-tests to dbt schema.yml files",
        emptyBindingHint: "Drag dbt model here",
        unboundHint: "Draft mode (not bound to dbt model)",
    },
    bruin: {
        // Bruin keeps metadata inline in @bruin blocks, not in schema.yml files.
        pullLabel: "Pull from Bruin",
        pullTooltip: "Import relationship tests from Bruin asset files",
        pushLabel: "Push to Bruin",
        pushDirtyTooltip: "⚠️ Changes in data model need to be pushed to Bruin asset files",
        pushCleanTooltip:
            "Sync entity & field-definitions and relationship-tests to Bruin asset definitions",
        emptyBindingHint: "Drag Bruin asset here",
        unboundHint: "Draft mode (not bound to Bruin asset)",
    },
};

/** Frameworks with dedicated copy. Exported so tests can assert it stays in step with the branding. */
export const FRAMEWORK_COPY_KEYS = Object.keys(FRAMEWORK_COPY);

/**
 * Neutral wording for a configured framework Trellis has no adapter for yet.
 *
 * Deliberately avoids naming any framework: it is better to say less than to
 * tell a Bruin user their assets are dbt models.
 */
export const DEFAULT_FRAMEWORK_COPY: FrameworkCopy = {
    pullLabel: "Pull relationships",
    pullTooltip: "Import relationship tests from the configured framework",
    pushLabel: "Push schema",
    pushDirtyTooltip: "⚠️ Changes in data model need to be pushed to the configured framework",
    pushCleanTooltip:
        "Sync entity & field-definitions and relationship-tests to the configured framework",
    emptyBindingHint: "Drag a model here",
    unboundHint: "Draft mode (not bound to a model)",
};

export function getFrameworkCopy(framework: string | undefined | null): FrameworkCopy {
    if (!framework) return DEFAULT_FRAMEWORK_COPY;
    return FRAMEWORK_COPY[framework] ?? DEFAULT_FRAMEWORK_COPY;
}

/**
 * Whether an optional feature should be offered at all.
 *
 * A feature needs both the user's opt-in and the framework's support: enabling
 * exposures on a framework that has no exposure concept would put a permanently
 * empty view in the nav. Absent capabilities default to supported, so an older
 * backend keeps behaving as before.
 */
export function isFeatureAvailable(
    enabledInConfig: boolean | undefined,
    capabilities: Partial<FrameworkCapabilities> | undefined,
    capability: keyof FrameworkCapabilities,
): boolean {
    return (enabledInConfig ?? false) && (capabilities?.[capability] ?? true);
}

/**
 * Remediation hints for whichever of the framework's artifacts are missing.
 *
 * Each adapter words its own hints, because only it knows what its framework
 * needs — "run dbt compile" versus "a Bruin pipeline needs pipeline.yml and
 * assets/". Hardcoding dbt's advice here is exactly what made the setup warning
 * wrong for a second framework.
 */
export function missingArtifactHints(status: {
    artifacts?: Record<string, { exists: boolean; hint: string }>;
}): string[] {
    return Object.values(status.artifacts ?? {})
        .filter((artifact) => !artifact.exists && artifact.hint)
        .map((artifact) => artifact.hint);
}
