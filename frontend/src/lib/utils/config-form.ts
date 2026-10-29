import type { ConfigSchema } from '$lib/types';

/**
 * Pure helpers shared by the configuration page and its section components.
 * `config` is the raw trellis.yml-shaped object; paths are dotted keys.
 */

export type ConfigValues = Record<string, any>;

/** Props every section component takes to read and write the config. */
export interface ConfigFormBinding {
    config: ConfigValues;
    schema: ConfigSchema;
    onChange: (field: string, value: any) => void;
    onNestedChange: (path: string, value: any) => void;
}

/** Value at a dotted path, or null when any segment is missing. */
export function getFieldValue(config: ConfigValues, path: string): any {
    let current: any = config;

    for (const part of path.split('.')) {
        if (current && current[part] !== undefined) {
            current = current[part];
        } else {
            return null;
        }
    }

    return current;
}

export function getFieldDescription(schema: ConfigSchema, path: string): string | undefined {
    return schema.fields[path]?.description;
}

export function isBetaField(schema: ConfigSchema, path: string): boolean {
    return schema.beta_flags.includes(path);
}

export function getEnumOptions(schema: ConfigSchema, path: string, fallback: string[]): string[] {
    const options = schema.fields[path]?.enum_values;
    if (options && options.length > 0) return options;
    return fallback;
}
