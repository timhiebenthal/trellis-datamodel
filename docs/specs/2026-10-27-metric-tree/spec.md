# Spec: Metric Tree Canvas

## Objective

Give Trellis a second canvas where metrics are laid out as a directed influence graph, persisted as YAML that an agent or an API consumer can read to do root cause analysis.

A user who already has metrics - either drafted in Trellis or defined in the project's Apache Ossie semantic model - draws "revenue is influenced by average price and order count", saves, and gets a `metric_tree.yml` that says exactly that. No arithmetic: an influence is a claim about direction, not a formula.

The existing canvas answers "what is in the warehouse". This one answers "why did this number move", which is what an agent needs when a metric drops and it has to decide what to look at next.

## Requirements

### Functional

1. **New artifact, own file.** `metric_tree.yml` beside `data_model.yml`:

   ```yaml
   version: 0.1
   metrics:
   - id: revenue
     label: Revenue
     description: Booked revenue for the period.
     expression: sum(amount) from fct__order
     dataset_ref: fct__order
   - id: order_count
     label: Order count
     description: Number of orders placed.
     expression: count(*) from fct__order
     dataset_ref: fct__order
   - id: avg_price
     label: Average price
     binding:
       dataset: fct__order
       name: avg_price
   influences:
   - effect: revenue
     drivers:
     - avg_price
     - order_count
   ```

   `metrics[]` holds every metric that is on the canvas, draft and bound alike, so an isolated node survives a save. `influences[]` is flat, one entry per effect, sorted by `effect`, with `drivers` deduplicated and sorted at write time.

2. **Two kinds of metric, one file.**

   - **Draft metric**: authored in Trellis. Carries `label`, `description`, `expression`, optional `dataset_ref`. `dataset_ref` is the name of a dataset a push writes to `semantic_model.yml` (the bound model's short name, version-suffixed for a versioned model) - not a data-model entity id.
   - **Bound metric**: a reference, never a copy. Carries `binding: {dataset, name}` and no `expression`, `description` or `dataset_ref`. Its definition is read from `semantic_model.yml` at load.

   A bound metric whose definition disappears from `semantic_model.yml` stays in the file, renders on the canvas as unresolved, and produces a warning; nothing is deleted.

3. **What is bindable.** Only **dataset-scoped** metrics - entries under `datasets[].metrics[]` in `semantic_model.yml`. They resolve to an entity through the mapping the exporter already computes: entity `model_ref` → model short name → dataset name (`services/ossie.py:253, 492`). Root-level `metrics[]` describes cross-dataset metrics, resolves to no entity, and is listed in the sidebar as read-only with no add action.

   A dataset-scoped metric whose dataset maps to no bound entity is likewise read-only, with the reason shown.

4. **Sidebar is the catalog.** The sidebar lists every metric found in `semantic_model.yml` (bindable or read-only), plus the metrics already on the canvas. Adding a catalog metric creates a bound entry; removing it from the canvas deletes only the reference, never the definition in the semantic model.

5. **Layout lives separately.** `metric_layout.yml` keyed by metric id (`{position: {x, y}, width, panel_height, collapsed}`), mirroring the existing `data_model.yml` / `canvas_layout.yml` split. Separate because `canvas_layout.yml` is keyed by entity id and metric ids would share that namespace; and because metric positions become per-tree once `trees[]` exists, while metric definitions stay global.

6. **Export on push.** `export_ossie` stops writing `metrics: []` and instead:

   - emits drafted metrics with a `dataset_ref` under that dataset's `metrics[]`, in the dataset-scoped form (unqualified field references);
   - emits drafted metrics without a `dataset_ref` under the document-level `metrics[]`, sorted by name;
   - preserves every metric it did not author, at both levels, including `custom_extensions` and `ai_context` on those entries;
   - leaves bound metrics where the file already has them. Since bound metrics are references, a push that only reads them writes nothing on their behalf.

   All emitted metric expressions use `metrics.expression_dialect`.

7. **Config block** in `trellis.yml`:

   ```yaml
   metrics:
     enabled: false            # off by default, like ossie
     file: ""                  # default: metric_tree.yml beside data_model.yml
     layout_file: ""           # default: metric_layout.yml beside data_model.yml
     expression_dialect: ANSI_SQL
   ```

   The block is normalised only when the file declares it, matching how `ossie` behaves. `expression_dialect` is a label, not a parser: it goes into `expression.dialects[0].dialect` and nothing validates the SQL against it.

   **Off means off.** With `metrics.enabled: false`: no nav entry, `/metrics-tree` and `/api/metric-tree` answer `404` with a message naming the config key, no file is read or written, and `export_ossie` emits no metrics. An existing `metric_tree.yml` is left untouched and comes back into view when the toggle is flipped. Preservation of metrics Trellis did not author stays unconditional even while disabled - a disabled feature must never damage a file that a push happens to rewrite.

8. **API.** `GET /api/metric-tree` returns `{version, metrics, influences, catalog, datasets}` with layout merged into each metric, `catalog` carrying the bindable plus read-only entries with `bindable`, `dataset`, `entity_id` and, when unbindable, `reason`, and `datasets` listing the names a push writes (what a draft's `dataset_ref` can name). `POST /api/metric-tree` accepts `{version, metrics, influences}`, where each metric may carry an optional `position`; the backend splits positions into `metric_layout.yml`, exactly as `POST /api/data-model` splits layout today. The response is `{status, warnings}`.

9. **Save validation.** Duplicate metric ids, an influence referencing an unknown id, or an influence whose effect also appears as its own driver are rejected with `422` and a message naming the offender. An unresolvable `dataset_ref`, or a binding to a metric absent from `semantic_model.yml`, is a warning - the entry is kept and the canvas badges it. Trellis does not parse SQL, so a dataset-scoped expression that really spans two datasets is the author's error, not a rejected save.

10. **Frontend.** A `/metrics-tree` route with its own nav entry, one canvas, metric nodes and influence edges, sidebar catalog, and a detail panel for draft fields. Autosave reuses the existing debounced pattern from `services/auto-save.ts`, posting to `/api/metric-tree`.

### Non-Functional

- **Atomic writes.** Reuse `utils/yaml_handler.YamlHandler.save_file` (temp file plus `os.replace`).
- **Byte-stable output.** Saving an unchanged graph twice produces identical bytes: metrics sorted by id, influences sorted by effect, drivers sorted, layout keys emitted in metric order.
- **No new runtime dependency.** No SQL parser, no graph library.
- **No behaviour change while disabled.** With `metrics.enabled: false` (the default) the app is what it is today: no nav entry, no route, no file IO, and `export_ossie` emits no metrics instead of the hardcoded empty list.
- **Framework neutral.** The metric canvas reads `semantic_model.yml` and `data_model.yml` only; it never calls an adapter except through the existing model list when resolving dataset names.
- **Agent-readable.** A reader who has only `metric_tree.yml` can tell direction without documentation: `effect` is what moves, `drivers` are what move it.

## Scope

### In Scope

- `trellis_datamodel/services/metric_tree.py` - load, validate, save, catalog resolution, Ossie scoping
- `trellis_datamodel/routes/metric_tree.py` - GET/POST `/api/metric-tree`
- `trellis_datamodel/models/metric.py` - pydantic models for the file and the API payload
- `trellis_datamodel/config.py` - `MetricsConfig` dataclass, path resolution, `load_config` wiring
- `trellis_datamodel/models/schemas.py` - `MetricsConfig` on `ConfigSchema`
- `trellis_datamodel/services/config_service.py` - field metadata and the metrics block
- `trellis_datamodel/services/ossie.py` - metric emission and preservation
- `frontend/src/routes/(app)/metrics-tree/+page.svelte` and its components
- `frontend/src/lib/types.ts`, `stores.ts`, `api.ts`, `services/auto-save.ts` - metric node and edge kinds
- `frontend/src/routes/(app)/+layout.svelte` - route mapping and nav entry
- Tests: `test_metric_tree.py`, `test_metric_tree_api.py`, additions to `test_ossie_export.py`, frontend unit tests for the save payload
- `trellis.yml.example`, `README.md`, `CHANGELOG.md`, `GLOSSARY.md`

### Out of Scope

- Multiple trees, tree groups, or non-MECE overlap (`trees[]`); the flat shape admits it later without a migration
- Arithmetic on influences: no sign, weight, lag, formula or decomposition kind
- `unit` on a metric
- Reading metric definitions from dbt MetricFlow or Bruin assets; `semantic_model.yml` is the only source of bound metrics
- Writing metrics into dbt or Bruin files
- SQL validation, execution, preview, or result caching
- An MCP server or an agent-facing query endpoint; the YAML file is the agent interface
- Deleting or editing a bound metric's definition from the canvas
- Entity/dataset nodes on the metric canvas
- Search, filtering and graph layout algorithms beyond fitting nodes on screen

## Commands

```
Backend tests:  uv run pytest
Single test:    uv run pytest trellis_datamodel/tests/test_metric_tree.py -q
Frontend check: cd frontend && npm run check
Frontend unit:  cd frontend && npm run test:unit
Smoke:          cd frontend && npm run test:smoke
Dev:            make backend        # FastAPI :8089
                make frontend       # Vite :5173
```

## Project Structure

```
trellis_datamodel/services/metric_tree.py   load/validate/save, catalog, Ossie scoping
trellis_datamodel/routes/metric_tree.py     GET/POST /api/metric-tree
trellis_datamodel/models/metric.py          pydantic file and API models
trellis_datamodel/tests/                    pytest alongside the feature
frontend/src/routes/(app)/metrics-tree/      the second canvas route
frontend/src/lib/components/                MetricNode, influence edge, sidebar, detail panel
```

## Code Style

Backend follows the existing service shape: module-level functions, typed dicts or pydantic at the boundary, no classes unless state is carried. Frontend uses PascalCase components, typed props, and the existing Tailwind conventions:

```python
def load_metric_tree(path: Path) -> MetricTreeFile:
    if not path.exists():
        return MetricTreeFile(version=0.1, metrics=[], influences=[])
    return MetricTreeFile.model_validate(load_yaml_or_json(path))
```

```svelte
<script lang="ts">
  let { data }: { data: MetricNodeData } = $props();
</script>
```

## Testing Strategy

- `uv run pytest` for backend: file round-trip, validation rejections, catalog resolution (bindable, unmappable dataset, root-level readonly, missing definition), Ossie emission scope, preservation of foreign metrics, byte-stability.
- `frontend npm run test:unit` for the payload builder and catalog filtering.
- `npm run test:smoke` for route rendering.
- One Playwright e2e: add two metrics and an influence, reload, assert the graph survives and both files exist.
- Frontend save payload added to `trellis_datamodel/tests/fixtures/frontend_save_payloads/` so the save contract test covers the new shape.

## Boundaries

- **Always**: run `uv run pytest` and `npm run check` before a commit; keep writes atomic; sort every list before writing.
- **Ask first**: adding a runtime dependency; changing `export_ossie`'s dataset or relationship behaviour; renaming the files or config keys once implemented.
- **Never**: edit `semantic_model.yml` metrics Trellis did not author; delete user data on a validation warning; commit a fixture that depends on this machine's dbt artifacts.

## Success Criteria

1. On a project with no `metric_tree.yml`, `/metrics-tree` renders an empty canvas, the sidebar shows only what `semantic_model.yml` contains, and no file is written until the first save.
2. With `metrics.enabled: false` (the default), there is no nav entry, `/metrics-tree` and `/api/metric-tree` return `404`, no file appears, and a push leaves the metrics already present in `semantic_model.yml` untouched.
3. Adding two draft metrics and one influence writes the file shape in Requirement 1; reloading the page renders the same graph; positions round-trip through `metric_layout.yml`.
4. With `ossie.enabled: true` and a dataset-scoped metric in `semantic_model.yml`, the sidebar lists it as bindable, adding it produces an entry with `binding` and no `expression`, and the canvas node shows the definition read from the file.
5. A root-level Ossie metric appears read-only, with no add action.
6. Pushing with two drafted metrics writes one under `datasets[].metrics` and one at the document root, preserves every pre-existing metric untouched, and a second push produces identical bytes.
7. A `dataset_ref` naming a dataset that is no longer exported saves with a warning and renders a badge.
8. `uv run pytest`, `npm run check`, `npm run test:smoke` and the new e2e pass.

## Open Questions

1. **Version.** `0.26.0b1` if #156 ships as `0.25.0b1` first; otherwise this rides the same beta.
2. **Hard failures versus warnings.** Duplicate ids, an influence pointing at an unknown id, and a self-driving metric are specced as `422`. Unresolvable references to the outside (`dataset_ref`, a vanished binding) are warnings. Say if the graph-integrity half should warn too.

## Notes

**Stacked on #156.** The branch is `feature/metric-tree`, cut from `feature/ossie-export`. This feature reads `semantic_model.yml` and edits `export_ossie`, so it cannot merge before #156 does; the PR targets `feature/ossie-export`, and retargeting it to `main` is a one-click change once #156 lands.

**Decisions worth remembering.**

- **Influence, not decomposition.** `revenue = price × orders` is a formula; an influence edge only says "revenue moves when price moves". Skipping the arithmetic keeps the canvas a two-click action and keeps the file readable by an agent that cannot evaluate SQL. The cost is that Trellis can never check a tree for consistency or split a variance deterministically - a later derived-metric slice would have to add a second edge kind.
- **Bind, never copy.** A bound metric stores `{dataset, name}` and nothing else, the way a bound entity stores `model_ref` instead of columns. Copying would make Trellis' file authoritative and drift from the semantic model, and it would make the push a write-back problem rather than a merge.
- **One tree now, `trees[]` later.** Metric ids are global and `influences` is flat, so adding named trees later is a grouping that references ids, not a nesting of definitions. Chosen because a metric legitimately belongs to several root-cause paths and non-MECE trees were named as the eventual shape.

**Known gaps.** Trellis cannot tell whether a dataset-scoped expression really stays inside its dataset; it only checks that `dataset_ref` names an exported dataset. Ossie's `Metric` has no unit, owner or target-direction field, so an agent gets name, description and expression and infers the rest.

**Dependency on #156.** The preservation fix in `export_ossie` is the only change that touches PR #156's module. If #156 changes the dataset naming rule, the entity ↔ dataset resolution in this feature changes with it, and both are covered by the same tests.
