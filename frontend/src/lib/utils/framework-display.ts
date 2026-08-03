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
