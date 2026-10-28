# Task List: Metric Tree Canvas

Spec: `SPEC.md`. Plan: `tasks/plan.md`. Branch: `feature/metric-tree` (stacked on `feature/ossie-export`).

Ordered by dependency. Each task leaves the app runnable. Checkboxes are updated by the worker that completes the task.

---

## Task 1: `MetricsConfig` config block

**Description:** Introduce `metrics.enabled`, `metrics.file`, `metrics.layout_file`, `metrics.expression_dialect` as a first-class config block, mirroring how `ossie` is declared, resolved, validated and normalised. Default paths resolve beside `data_model.yml`; the block is only written back to `trellis.yml` when the file already declares it.

**Acceptance criteria:**
- [x] `cfg.METRICS_CONFIG` is a dataclass with `enabled: bool = False`, `file: str`, `layout_file: str`, `expression_dialect: str = "ANSI_SQL"`, and absolute resolved paths for the two file fields
- [x] Defaults: `<data_model.yml dir>/metric_tree.yml` and `<data_model.yml dir>/metric_layout.yml`; a relative `metrics.file` resolves against the project path
- [x] `Models/schemas.py` exposes a pydantic `MetricsConfig` on `ConfigSchema`, and `ConfigSchema(**config)` accepts both the block and its absence
- [x] `_FIELD_DEFINITIONS` carries the four paths with `beta=True`, `_BETA_FIELDS` lists the same four, and `expression_dialect` is `type="enum"` with at least `ANSI_SQL`
- [x] `_normalize_nested_config` emits the block only when `"metrics" in config`, with a malformed block falling back to defaults instead of raising
- [x] `_reset_shared_test_state` sets `cfg.METRICS_CONFIG` back to the test-mode default, and `config.py` declares that default in both the test-mode and production branches

**Verification:**
- [x] `uv run pytest trellis_datamodel/tests/test_config.py -q` passes with new cases: defaults, override paths, malformed block, block absent from a config save
- [x] `uv run pytest trellis_datamodel/tests/test_config_api.py -q` passes, including a beta-flag assertion naming the four `metrics.*` paths
- [x] Manual: `PUT /api/config` on a `trellis.yml` without a `metrics:` key leaves the file byte-identical

**Dependencies:** None

**Files likely touched:**
- `trellis_datamodel/config.py`
- `trellis_datamodel/models/schemas.py`
- `trellis_datamodel/services/config_service.py`
- `trellis_datamodel/tests/conftest.py`
- `trellis_datamodel/tests/test_config.py`

**Estimated scope:** Medium (5 files)

---

## Task 2: Metric tree models, load/save, validation

**Description:** The `metric_tree.yml` document: pydantic models for a metric entry (draft or bound), the influence list, and the update payload. A service loads the file (empty document when missing), validates the graph, sorts everything deterministically, and splits layout into `metric_layout.yml` the way `_split_model_and_layout` does for the entity canvas.

**Acceptance criteria:**
- [x] `models/metric.py` defines `MetricEntry` (`id`, `label`, optional `description`, `expression`, `dataset_ref`, `binding: {dataset, name}`), `Influence` (`effect`, `drivers`), `MetricTreeFile` (`version`, `metrics`, `influences`), and `MetricTreeUpdate`
- [x] Loading a missing file returns `MetricTreeFile(version=0.1, metrics=[], influences=[])` and writes nothing
- [x] Saving sorts `metrics` by `id`, `influences` by `effect`, and `drivers` alphabetically, so two saves of the same graph are byte-identical
- [x] Saving writes `metric_tree.yml` and `metric_layout.yml` through `YamlHandler.save_file` (atomic, ruamel formatting)
- [x] Validation rejects with `ValidationError`: duplicate metric ids, an influence whose `effect` or any driver is not in `metrics`, and a metric listed as its own driver
- [x] Layout merges back on load by metric id, and layout entries for metrics absent from the payload are dropped, matching the entity canvas behaviour
- [x] Draft and bound shapes are mutually exclusive on save: a bound entry with an `expression`, or a draft entry without one, is rejected with a message naming the metric id

**Verification:**
- [x] `uv run pytest trellis_datamodel/tests/test_metric_tree.py -q` passes: round-trip, missing file, sorting, each validation rejection, layout merge and drop
- [x] A test saves the same graph twice and asserts identical file bytes

**Dependencies:** Task 1

**Files likely touched:**
- `trellis_datamodel/models/metric.py`
- `trellis_datamodel/services/metric_tree.py`
- `trellis_datamodel/tests/test_metric_tree.py`

**Estimated scope:** Medium (3 files)

---

## Task 3: `/api/metric-tree` endpoints and feature flag

**Description:** Expose the document over HTTP with the same shape the canvas consumes, gate it on `metrics.enabled`, and publish the flag on `/api/config-info` so the frontend can hide the nav entry.

**Acceptance criteria:**
- [x] `GET /api/metric-tree` returns `{version, metrics, influences, catalog}` with layout merged into each metric; `catalog` is an empty list until Task 5
- [x] `POST /api/metric-tree` accepts `{version, metrics, influences}`, returns `{status: "success", warnings: []}`, and writes both YAML files
- [x] Both endpoints answer `404` with a message naming `metrics.enabled` when `cfg.METRICS_CONFIG.enabled` is false, raised through `FeatureDisabledError`
- [x] `ValidationError` from the service maps to `422` with the offending id in `detail`, following `routes/business_events.py:271-281`
- [x] `metrics_enabled` appears in `GET /api/config-info`, and the router is registered in `routes/__init__.py` and `server.py:_register_routers`

**Verification:**
- [x] `uv run pytest trellis_datamodel/tests/test_metric_tree_api.py -q` passes: disabled 404, empty GET, POST round-trip, invalid payload 422, config-info flag true and false
- [x] Manual: `curl -s localhost:8089/api/metric-tree | jq` returns the empty document with the flag on

**Dependencies:** Task 2

**Files likely touched:**
- `trellis_datamodel/routes/metric_tree.py`
- `trellis_datamodel/routes/__init__.py`
- `trellis_datamodel/server.py`
- `trellis_datamodel/routes/manifest.py`
- `trellis_datamodel/tests/test_metric_tree_api.py`

**Estimated scope:** Medium (5 files)

---

## Checkpoint: Foundation

- [x] `uv run pytest -q` passes
- [x] `GET /api/metric-tree` returns the empty document when enabled and `404` when not
- [x] A `trellis.yml` without `metrics:` survives `PUT /api/config` unchanged
- [x] `uv run python -c "import trellis_datamodel.server"` imports cleanly

---

## Task 4: Ossie metric emission and preservation

**Description:** Replace the hardcoded `metrics: []` with real emission. Drafted metrics with a `dataset_ref` land under that dataset's `metrics`; drafts without one land at the document root. Every metric already in the file that Trellis did not author is preserved at both levels, including `custom_extensions` and `ai_context`.

**Acceptance criteria:**
- [x] `export_ossie` accepts the metric tree (new parameter, default `None`) and emits drafted metrics only when `cfg.METRICS_CONFIG.enabled` is true
- [x] A draft with `dataset_ref` resolving to an emitted dataset appears under that dataset's `metrics`; one without appears at the document root sorted by name
- [x] Every discovered metric expression is written as `dialects: [{dialect: <metrics.expression_dialect>, expression: <sql>}]` and `datatype` is omitted
- [x] Pre-existing dataset-scoped and root-level metrics are preserved with all their keys intact, including ones Trellis cannot interpret
- [x] A draft whose `dataset_ref` does not resolve to an emitted dataset becomes a warning and is emitted at the document root rather than dropped
- [x] With `metrics.enabled: false`, no metric is emitted but existing metrics are still preserved
- [x] A dataset with no drafted metrics carries no `metrics` key, and the document's key order stays `version, name, datasets, relationships, metrics`

**Verification:**
- [x] `uv run pytest trellis_datamodel/tests/test_ossie_export.py -q` passes with new cases: scope mapping, preservation at both levels, disabled feature, unresolvable `dataset_ref`, byte-identical re-push, and a no-metrics-file regression asserting the output equals the pre-change golden
- [x] `uv run pytest trellis_datamodel/tests/test_ossie_e2e.py -q` passes

**Dependencies:** Task 2

**Files likely touched:**
- `trellis_datamodel/services/ossie.py`
- `trellis_datamodel/services/schema.py`
- `trellis_datamodel/tests/test_ossie_export.py`
- `trellis_datamodel/tests/test_ossie_e2e.py`

**Estimated scope:** Medium (4 files)

---

## Task 5: Bound metric catalog resolution

**Description:** Read `semantic_model.yml` and classify every metric in it: bindable when it is dataset-scoped and its dataset maps to a bound entity, read-only when it is document-scoped or its dataset does not map. Expose that through the `catalog` field of the GET response.

**Acceptance criteria:**
- [x] `resolve_catalog()` returns one entry per metric in `semantic_model.yml` with `name`, `dataset`, `entity_id`, `bindable`, and `reason` when not bindable
- [x] Dataset-scoped metric whose dataset matches a bound entity's model name is `bindable: true` with the entity id resolved from `data_model.yml`
- [x] Document-level metrics are `bindable: false` with reason naming cross-dataset scope
- [x] Dataset-scoped metric whose dataset maps to no bound entity is `bindable: false` with a reason naming the unmatched dataset
- [x] Missing `semantic_model.yml` yields an empty catalog and no error; a file with no `metrics` anywhere also yields an empty catalog
- [x] Adding a catalog entry on save produces `binding: {dataset, name}` with no `expression`, and a binding whose definition is missing from `semantic_model.yml` produces a warning while keeping the entry

**Verification:**
- [x] `uv run pytest trellis_datamodel/tests/test_metric_tree_catalog.py -q` passes with a fixture `semantic_model.yml` covering all four cases
- [x] `GET /api/metric-tree` on the same fixture returns the expected `bindable` flags

**Dependencies:** Task 3

**Files likely touched:**
- `trellis_datamodel/services/metric_tree.py`
- `trellis_datamodel/routes/metric_tree.py`
- `trellis_datamodel/tests/test_metric_tree_catalog.py`
- `trellis_datamodel/tests/fixtures/metric_tree/semantic_model.yml`

**Estimated scope:** Medium (4 files)

---

## Checkpoint: Semantic layer

- [x] `uv run pytest -q` passes
- [x] A push with two drafts writes one dataset-scoped and one document-scoped metric, and a second push produces identical bytes
- [x] Pre-existing Ossie metrics survive a push with the feature disabled
- [x] Catalog flags are correct for bindable, document-level and unmapped metrics

---

## Task 6: Route, gate, nav entry, types, API client

**Description:** The `/metrics-tree` page shell: TypeScript types for the document and catalog, client functions for GET/POST, a nav anchor gated on `metrics_enabled`, and the page's own guard that redirects to `/canvas` when the feature is off.

**Acceptance criteria:**
- [x] `types.ts` declares `MetricEntry`, `MetricInfluence`, `MetricTreeFile`, `MetricCatalogEntry`, `MetricTreeNode`, `MetricTreeEdge`, and adds `metrics_enabled?: boolean` to `ConfigInfo`
- [x] `api.ts` exposes `getMetricTree()` and `saveMetricTree(payload)` against `/api/metric-tree`, returning typed data and throwing with the response body on failure
- [x] `routes/(app)/metrics-tree/+page.svelte` fetches config-info, redirects to `/canvas` when `metrics_enabled` is false, renders a spinner while loading, and a "not available" notice otherwise, following `bus-matrix/+page.svelte`
- [x] The nav anchor appears only when `metricsEnabled` is true and carries the active style when the path is `/metrics-tree`, placed after `/business-events` in `+layout.svelte`
- [x] `metricsEnabled` is derived from `getConfigInfo()` in the same boot block as `busMatrixEnabled`

**Verification:**
- [x] `cd frontend && npm run check` passes with no new errors
- [x] `cd frontend && npm run test:smoke` passes
- [x] Manual: with `metrics.enabled: false` the nav entry is absent and visiting `/metrics-tree` lands on `/canvas`

**Dependencies:** Task 3

**Files likely touched:**
- `frontend/src/lib/types.ts`
- `frontend/src/lib/api.ts`
- `frontend/src/routes/(app)/metrics-tree/+page.svelte`
- `frontend/src/routes/(app)/+layout.svelte`

**Estimated scope:** Medium (4 files)

---

## Task 7: `MetricCanvas` renders the graph

**Description:** A Svelte Flow canvas for metrics only: nodes for metrics, directed edges for influences, positions from the payload, fit-on-load. No groups, filters, lineage, star-schema positioning or entity wizard.

**Acceptance criteria:**
- [x] `MetricCanvas.svelte` takes `metrics`, `influences` and `layout` as props and imports neither `nodes` nor `edges` from `stores.ts`
- [x] `MetricNode.svelte` shows label, a dataset or "unbound" badge, a "bound" badge for bound entries, and an unresolved badge when `unresolved` is true
- [x] Influences render as directed edges from each driver to the effect, with an arrow marker and no label
- [x] Nodes without a stored position are placed in a deterministic grid rather than at `{0,0}`
- [x] The page passes the fetched document into the canvas and renders an empty state with a call to action when there are no metrics

**Verification:**
- [x] `cd frontend && npm run check` passes
- [x] `cd frontend && npm run test:unit` passes, including a component test asserting one node per metric and one edge per driver
- [x] Manual: two metrics with one influence render as two boxes and one arrow

**Dependencies:** Task 6

**Files likely touched:**
- `frontend/src/lib/components/MetricCanvas.svelte`
- `frontend/src/lib/components/MetricNode.svelte`
- `frontend/src/lib/components/MetricInfluenceEdge.svelte`
- `frontend/src/routes/(app)/metrics-tree/+page.svelte`

**Estimated scope:** Medium (4 files)

---

## Task 8: Sidebar catalog, create and connect

**Description:** A sidebar listing bindable catalog metrics and the metrics already on the canvas, plus the canvas interactions: add a metric, connect two metrics, delete an edge or a metric.

**Acceptance criteria:**
- [x] The sidebar lists catalog entries with `bindable: true` as addable, and non-bindable entries greyed out with their `reason` as a tooltip
- [x] "Add metric" creates a draft with a unique id derived from the label (`generateSlug`), empty description, empty expression, and starts the detail panel focused on the label
- [x] Adding a catalog entry creates an entry with `binding` only, and the node immediately shows the definition read from the catalog
- [x] Dragging from one node handle to another creates an influence with the drag source as driver and the target as effect; duplicates and self-links are refused
- [x] Deleting an influence removes only that driver from the effect's entry, deleting the entry when its driver list empties
- [x] Deleting a metric removes it from `metrics` and from every `drivers` list

**Verification:**
- [x] `cd frontend && npm run test:unit` passes with tests for add, dedupe, self-link refusal and cascade delete on the pure helpers
- [x] `cd frontend && npm run check` passes
- [x] Manual: add two catalog metrics, connect them, delete one, confirm the other remains with no edge

**Dependencies:** Task 7

**Files likely touched:**
- `frontend/src/lib/components/MetricSidebar.svelte`
- `frontend/src/lib/components/MetricCanvas.svelte`
- `frontend/src/routes/(app)/metrics-tree/+page.svelte`

**Estimated scope:** Medium (3 files)

---

## Task 9: Detail panel and autosave

**Description:** Edit a draft metric's label, description, expression and `dataset_ref`; a bound metric shows its definition read-only with an unlink action. Every change is debounced and posted to `/api/metric-tree`, with warnings surfaced.

**Acceptance criteria:**
- [x] The panel edits `label`, `description`, `expression`, and `dataset_ref` (the datasets a push writes, picked from the datasets GET `/api/metric-tree` returns) for drafts, and shows label, dataset, expression and "unlink" for bound entries
- [x] `services/metric-tree-save.ts` debounces 400 ms, coalesces in-flight saves, exposes `isSaving`, `hasUnsavedChanges`, `saveNow()` and `flushSync()`, and calls `saveMetricTree`
- [x] Server `warnings` render in the panel, one line per warning, and clear on the next successful save
- [x] A failed save keeps the edited state on screen and shows the error, rather than silently discarding it
- [x] Saving does not remount the canvas or reset node positions

**Verification:**
- [x] `cd frontend && npm run test:unit` passes with tests for debounce coalescing, `flushSync` on unload, and the error path on a rejected fetch
- [x] `cd frontend && npm run check` passes
- [x] Manual: type in the expression field, wait, reload - the value persists

**Dependencies:** Task 8

**Files likely touched:**
- `frontend/src/lib/components/MetricDetailPanel.svelte`
- `frontend/src/lib/services/metric-tree-save.ts`
- `frontend/src/lib/services/metric-tree-save.test.ts`
- `frontend/src/routes/(app)/metrics-tree/+page.svelte`

**Estimated scope:** Medium (4 files)

---

## Task 10: Layout round-trip

**Description:** Persist node positions into `metric_layout.yml` through the same save call, so the graph comes back where it was drawn.

**Acceptance criteria:**
- [x] Dragging a node updates local layout state and is included in the next save
- [x] `POST /api/metric-tree` accepts a `position` on each metric and writes `metric_layout.yml`, splitting it out of the payload; a layout entry for a metric not in `metrics` is dropped
- [x] Reloading returns nodes at their saved positions, and a metric with no saved position falls back to the grid
- [x] Layout writes are atomic and do not rewrite `metric_tree.yml` content when only positions changed

**Verification:**
- [x] `uv run pytest trellis_datamodel/tests/test_metric_tree.py -q` passes with a layout round-trip case
- [x] `cd frontend && npm run test:unit` passes with a position-persistence case
- [x] Manual: drag a node, reload, position holds

**Dependencies:** Task 9

**Files likely touched:**
- `frontend/src/lib/services/metric-tree-save.ts`
- `frontend/src/lib/components/MetricCanvas.svelte`
- `trellis_datamodel/services/metric_tree.py`
- `trellis_datamodel/routes/metric_tree.py`

**Estimated scope:** Medium (4 files)

---

## Checkpoint: Canvas

- [x] `uv run pytest -q` passes
- [x] `cd frontend && npm run check && npm run test:unit && npm run test:smoke` pass
- [x] Add two metrics plus an influence, reload, graph and positions survive
- [x] Deleting a metric removes its edges from the file, not just from the screen
- [x] Feature toggle off hides the nav entry and redirects the route

---

## Task 11: Config page section

**Description:** A `metrics` group on the Config page with the enable toggle, the two file paths and the dialect select, matching the Ossie section's visual language and beta badges.

**Acceptance criteria:**
- [x] The section renders below the Ossie group, wrapped in the same amber beta styling, with a toggle bound to `metrics.enabled`
- [x] `metrics.file`, `metrics.layout_file` and `metrics.expression_dialect` are editable, and the dialect is a select limited to `ANSI_SQL` and `OSSIE_SQL_2026`
- [x] Every control is disabled while the danger zone is unacknowledged, like its neighbours
- [x] Descriptions come from `_FIELD_DEFINITIONS`, with a fallback sentence when metadata is absent
- [x] Saving the page and reloading shows the persisted values

**Verification:**
- [x] `cd frontend && npm run check` passes
- [x] Manual: enable the toggle, save, reload - the nav entry appears without a rebuild

**Dependencies:** Task 1

**Files likely touched:**
- `frontend/src/routes/(app)/config/+page.svelte`

**Estimated scope:** Small (1 file)

---

## Task 12: End-to-end test, docs, version

**Description:** One Playwright spec covering the whole path, plus the example config, README section, changelog entry and version bump.

**Acceptance criteria:**
- [x] `frontend/tests/metric-tree.spec.ts` enables the feature, adds two metrics, connects them, reloads, and asserts both nodes and the edge survive; it skips cleanly when `metrics_enabled` is false in the test config
- [x] `trellis.yml.example` documents the `metrics` block with all four keys
- [x] `README.md` gains a short section on the metric tree, the two files it writes, and that pushes emit the drafts into the Ossie document
- [x] `CHANGELOG.md` carries an `[Unreleased]` entry naming the feature, the files and the config block
- [x] `pyproject.toml` version is `0.26.0b1` and `uv.lock` is refreshed
- [x] `GLOSSARY.md` already carries `Metric`, `Draft Metric`, `Bound Metric`, `Influence`, `Metric Tree` - no duplicates added

**Verification:**
- [x] `cd frontend && npm run test:e2e -- metric-tree` passes
- [x] `uv run pytest -q` passes
- [x] `cd frontend && npm run check && npm run test:smoke` pass

**Dependencies:** Tasks 4, 5, 10, 11

**Files likely touched:**
- `frontend/tests/metric-tree.spec.ts`
- `trellis.yml.example`
- `README.md`
- `CHANGELOG.md`
- `pyproject.toml`

**Estimated scope:** Medium (5 files)

---

## Checkpoint: Complete

- [x] Every success criterion in `SPEC.md` maps to a passing test or a stated manual step
- [x] `uv run pytest -q` passes
- [x] `cd frontend && npm run check && npm run test:unit && npm run test:smoke` pass
- [x] `cd frontend && npm run test:e2e` passes
- [x] No task was marked complete without its verification command showing passing output

---

## Verification notes

- Backend: `uv run pytest -q` → 1063 passed, 1 skipped.
- Frontend: `npm run check` → 0 errors, 40 pref-existing warnings; `npm run test:unit` → 1054 passed; `npm run test:smoke` → 1 passed; `npm run test:e2e -- metric-tree` → 1 passed (enabled path, not skipped).
- Covered by tests instead of by hand: the disabled `404` on both endpoints (`test_metric_tree_api.py`), the `/metrics-tree` → `/canvas` redirect (`page.test.ts`), and `trellis.yml` without a `metrics:` key surviving a config save (`test_config.py` normalisation cases).
- Stated manual step: flip `metrics.enabled: false` in a real `trellis.yml` and reload - the sidebar nav entry disappears and the route redirects. Nav visibility is a one-line `{#if metricsEnabled}` in `+layout.svelte` and has no browser-level assertion.
- Known limitation: `metric_tree.yml` carries no provenance, so deleting a draft does not remove the copy a previous push emitted into `semantic_model.yml`; that entry is indistinguishable from one the user authored and is preserved.
- Known limitation: preservation moves a metric whose dataset is no longer exported to the document root with a warning rather than dropping it.
