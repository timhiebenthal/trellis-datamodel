/**
 * Framework-driven branding for the model sidebar.
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
