import type { MetricCatalogEntry, MetricEntry, MetricInfluence } from '$lib/types';
import { generateSlug } from '$lib/utils';

/**
 * Graph edits for the metric canvas, as pure functions over `{ metrics, influences }`.
 *
 * The page owns the document and hands each edit the current state; every helper
 * returns a new state and never mutates its argument. Keeping the rules here (and
 * not in the components) is what makes "no duplicate influence" and "delete the
 * entry when its last driver goes" testable without a browser.
 */

export interface MetricGraphState {
    metrics: MetricEntry[];
    influences: MetricInfluence[];
}

export const NEW_METRIC_LABEL = 'New metric';

/** Why a binding was refused. A draft never fails, so this only applies to bindings. */
export type AddBoundRefusal = 'not_bindable' | 'duplicate';

/** Why a drag between two nodes did not become an influence. */
export type ConnectRefusal = 'self' | 'duplicate' | 'unknown';

export interface AddedMetric {
    state: MetricGraphState;
    metric: MetricEntry;
}

export interface AddBoundOutcome {
    state: MetricGraphState;
    /** `null` when the entry was refused; `reason` says why. */
    metric: MetricEntry | null;
    reason?: AddBoundRefusal;
}

export interface ConnectOutcome {
    state: MetricGraphState;
    ok: boolean;
    reason?: ConnectRefusal;
}

function existingIds(state: MetricGraphState): string[] {
    return state.metrics.map((entry) => entry.id);
}

function withMetrics(state: MetricGraphState, metrics: MetricEntry[]): MetricGraphState {
    return { ...state, metrics };
}

function withInfluences(state: MetricGraphState, influences: MetricInfluence[]): MetricGraphState {
    return { ...state, influences };
}

/**
 * Create a hand-authored metric. The id comes from the label through
 * `generateSlug`, which also guarantees it is unique against the canvas.
 */
export function addDraftMetric(
    state: MetricGraphState,
    label: string = NEW_METRIC_LABEL,
): AddedMetric {
    const cleanLabel = label.trim() || NEW_METRIC_LABEL;
    const id = generateSlug(cleanLabel, existingIds(state));

    const metric: MetricEntry = {
        id,
        label: cleanLabel,
        description: '',
        expression: '',
    };

    return { state: withMetrics(state, [...state.metrics, metric]), metric };
}

/** `avg_price` reads as `Avg price` on a node badge; the id keeps the raw name. */
export function metricLabelFromName(name: string): string {
    const words = name.replace(/[_.-]+/g, ' ').trim();

    if (!words) return name;
    return words.charAt(0).toUpperCase() + words.slice(1);
}

/** The metric on the canvas that carries this exact `{dataset, name}` reference. */
export function findBoundMetric(
    metrics: MetricEntry[],
    entry: MetricCatalogEntry,
): MetricEntry | undefined {
    return metrics.find(
        (metric) =>
            metric.binding?.name === entry.name &&
            (!entry.dataset || metric.binding?.dataset === entry.dataset),
    );
}

/** True when the canvas already carries this exact `{dataset, name}` reference. */
export function isCatalogEntryAdded(
    metrics: MetricEntry[],
    entry: MetricCatalogEntry,
): boolean {
    return findBoundMetric(metrics, entry) !== undefined;
}

/**
 * Add a catalog metric as a reference. Bound entries carry `binding` and nothing
 * else: the definition stays in `semantic_model.yml`, so there is no expression or
 * description to copy here.
 */
export function addBoundMetric(
    state: MetricGraphState,
    entry: MetricCatalogEntry,
): AddBoundOutcome {
    const dataset = entry.dataset?.trim();

    if (!entry.bindable || !dataset) {
        return { state, metric: null, reason: 'not_bindable' };
    }

    if (isCatalogEntryAdded(state.metrics, entry)) {
        return { state, metric: null, reason: 'duplicate' };
    }

    const metric: MetricEntry = {
        id: generateSlug(entry.name, existingIds(state)),
        label: metricLabelFromName(entry.name),
        binding: { dataset, name: entry.name },
    };

    return { state: withMetrics(state, [...state.metrics, metric]), metric };
}

/**
 * Record "the effect moves when the driver moves". The drag source is the driver.
 * Self-links, repeats, and ids that are not on the canvas are refused rather than
 * silently written, so the file never holds something the backend would reject.
 */
export function connectInfluence(
    state: MetricGraphState,
    driver: string,
    effect: string,
): ConnectOutcome {
    const known = new Set(existingIds(state));

    if (!known.has(driver) || !known.has(effect)) {
        return { state, ok: false, reason: 'unknown' };
    }

    if (driver === effect) {
        return { state, ok: false, reason: 'self' };
    }

    const target = state.influences.find((influence) => influence.effect === effect);

    if (target?.drivers.includes(driver)) {
        return { state, ok: false, reason: 'duplicate' };
    }

    const influences = target
        ? state.influences.map((influence) =>
              influence.effect === effect
                  ? { ...influence, drivers: [...influence.drivers, driver] }
                  : influence,
          )
        : [...state.influences, { effect, drivers: [driver] }];

    return { state: withInfluences(state, influences), ok: true };
}

/**
 * Remove one arrow. Only that driver leaves the effect's entry; the entry itself
 * goes once its driver list is empty, matching the file format (no empty entries).
 */
export function removeInfluence(
    state: MetricGraphState,
    driver: string,
    effect: string,
): MetricGraphState {
    const influences = state.influences
        .map((influence) =>
            influence.effect === effect
                ? { ...influence, drivers: influence.drivers.filter((id) => id !== driver) }
                : influence,
        )
        .filter((influence) => influence.drivers.length > 0);

    return withInfluences(state, influences);
}

/**
 * Remove a metric and every claim that mentions it: it leaves the canvas, the
 * drivers lists, and any entry it was the effect of.
 */
export function removeMetric(state: MetricGraphState, metricId: string): MetricGraphState {
    const influences = state.influences
        .filter((influence) => influence.effect !== metricId)
        .map((influence) => ({
            ...influence,
            drivers: influence.drivers.filter((id) => id !== metricId),
        }))
        .filter((influence) => influence.drivers.length > 0);

    return {
        metrics: state.metrics.filter((metric) => metric.id !== metricId),
        influences,
    };
}

export interface CatalogGroups {
    /** Bindable, not on the canvas yet: these get an add action. */
    available: MetricCatalogEntry[];
    /** Bindable, already on the canvas: shown as added. */
    added: MetricCatalogEntry[];
    /** Read-only: cross-dataset, or a dataset with no bound entity. */
    unavailable: MetricCatalogEntry[];
}
/** Split the sidebar catalog into what can be added, what is added, and what cannot. */
export function groupCatalog(
    catalog: MetricCatalogEntry[],
    metrics: MetricEntry[],
): CatalogGroups {
    const groups: CatalogGroups = { available: [], added: [], unavailable: [] };

    for (const entry of catalog) {
        if (!entry.bindable) {
            groups.unavailable.push(entry);
            continue;
        }

        (isCatalogEntryAdded(metrics, entry) ? groups.added : groups.available).push(entry);
    }

    return groups;
}

export type CatalogEntityItem =
    | { kind: 'tree'; metric: MetricEntry; status: 'added' | 'draft' }
    | { kind: 'catalog'; entry: MetricCatalogEntry; status: 'available' | 'readonly' };

export interface CatalogEntityGroup {
    key: string;
    label: string;
    /** `entity` is a real entity; the other two hold metrics that have none. */
    kind: 'entity' | 'no-entity' | 'cross-entity';
    onTreeCount: number;
    items: CatalogEntityItem[];
}

export interface CatalogFilter {
    catalog?: (entry: MetricCatalogEntry) => boolean;
    metric?: (metric: MetricEntry) => boolean;
}

const NO_ENTITY_KEY = '__no_entity__';
const CROSS_ENTITY_KEY = '__cross_entity__';
const GROUP_KIND_RANK: Record<CatalogEntityGroup['kind'], number> = {
    entity: 0,
    'no-entity': 1,
    'cross-entity': 2,
};

/**
 * Group the sidebar by entity: one list per entity, holding its drafts, its
 * metrics already on the tree, and its semantic-model metrics still to add.
 *
 * A binding names the Ossie dataset (the model's name), not the entity that owns
 * it, so the owner is looked up through the catalog. That lookup uses the whole
 * catalog even when `filter` hides entries, or a search would split an entity in two.
 */
export function groupCatalogByEntity(
    catalog: MetricCatalogEntry[],
    metrics: MetricEntry[],
    filter: CatalogFilter = {},
): CatalogEntityGroup[] {
    const entityByDataset = new Map<string, string>();
    for (const entry of catalog) {
        if (entry.dataset && entry.entity_id) entityByDataset.set(entry.dataset, entry.entity_id);
    }

    const groups = new Map<string, CatalogEntityGroup>();
    const groupFor = (key: string, label: string, kind: CatalogEntityGroup['kind']) => {
        let group = groups.get(key);
        if (!group) {
            group = { key, label, kind, onTreeCount: 0, items: [] };
            groups.set(key, group);
        }
        return group;
    };
    const entityGroup = (entityId: string) => groupFor(entityId, entityId, 'entity');

    const placed = new Set<MetricEntry>();
    const placeOnTree = (metric: MetricEntry) => {
        const { binding } = metric;
        const entityId = binding
            ? (entityByDataset.get(binding.dataset) ?? binding.dataset)
            : (metric.dataset_ref ?? '').trim();
        const group = entityId
            ? entityGroup(entityId)
            : groupFor(NO_ENTITY_KEY, 'No entity', 'no-entity');

        group.onTreeCount += 1;
        group.items.push({ kind: 'tree', metric, status: binding ? 'added' : 'draft' });
        placed.add(metric);
    };

    for (const metric of metrics) {
        if (filter.metric?.(metric) ?? true) placeOnTree(metric);
    }

    for (const entry of catalog) {
        if (!(filter.catalog?.(entry) ?? true)) continue;

        // A match on the entry alone still shows the metric it is bound to.
        const bound = entry.bindable ? findBoundMetric(metrics, entry) : undefined;
        if (bound) {
            if (!placed.has(bound)) placeOnTree(bound);
            continue;
        }

        const entityId = (entry.entity_id ?? entry.dataset ?? '').trim();
        const group = entityId
            ? entityGroup(entityId)
            : groupFor(CROSS_ENTITY_KEY, 'Cross-entity', 'cross-entity');
        group.items.push({
            kind: 'catalog',
            entry,
            status: entry.bindable ? 'available' : 'readonly',
        });
    }

    // On-tree entries lead each group; the sort is stable, so order is otherwise kept.
    for (const group of groups.values()) {
        group.items.sort((a, b) => Number(b.kind === 'tree') - Number(a.kind === 'tree'));
    }

    return [...groups.values()].sort(
        (a, b) => GROUP_KIND_RANK[a.kind] - GROUP_KIND_RANK[b.kind] || a.label.localeCompare(b.label),
    );
}

/**
 * Edit one metric's fields. The id is never patched - influences reference it -
 * and a bound entry can never acquire an expression or description, because that
 * would turn a reference into a copy (and the backend rejects the file).
 */
export function updateMetric(
    state: MetricGraphState,
    metricId: string,
    patch: Partial<MetricEntry>,
): MetricGraphState {
    const metrics = state.metrics.map((metric) => {
        if (metric.id !== metricId) return metric;

        const next: MetricEntry = { ...metric, ...patch, id: metric.id };

        if (next.binding) {
            delete next.expression;
            delete next.description;
            delete next.dataset_ref;
        }

        return next;
    });

    return withMetrics(state, metrics);
}

/** Turn a bound entry back into a draft by dropping the reference, keeping the label. */
export function unlinkMetric(state: MetricGraphState, metricId: string): MetricGraphState {
    return updateMetric(state, metricId, { binding: undefined });
}

/**
 * Drafts a save would reject: the backend answers 422 when a metric has no
 * expression. Autosave is gated on this list being empty.
 */
export function incompleteDraftIds(metrics: MetricEntry[]): string[] {
    return metrics
        .filter((metric) => !metric.binding && !(metric.expression ?? '').trim())
        .map((metric) => metric.id);
}
