import { getContext, setContext } from 'svelte';
import type { ConfigFieldMetadata } from '$lib/api';

/** Page-level helpers the shared config field components read and write through. */
export interface ConfigFormContext {
    getFieldValue: (path: string) => any;
    handleNestedFieldChange: (path: string, value: any) => void;
    getFieldMetadata: (path: string) => ConfigFieldMetadata | null;
    isBetaField: (path: string) => boolean;
}

const KEY = Symbol('config-form');

export function setConfigFormContext(ctx: ConfigFormContext) {
    setContext(KEY, ctx);
}

export function getConfigFormContext(): ConfigFormContext {
    return getContext<ConfigFormContext>(KEY);
}
