# Implementation Plan: Metric Tree Canvas

## Overview

Add a second canvas at `/metrics-tree` where metrics are drawn as a directed influence graph and persisted to `metric_tree.yml` beside `data_model.yml`. Draft metrics are authored in Trellis with a SQL expression; bound metrics reference a dataset-scoped metric in `semantic_model.yml` instead of copying it. Pushes emit the drafts into the Ossie document without touching metrics Trellis did not author. The feature is off unless `metrics.enabled: true`.

Spec: `SPEC.md` on this branch. Branch `feature/metric-tree`, stacked on `feature/ossie-export` (PR #156).

## Architecture Decisions

1. **A second canvas component, not a second node kind on `Canvas.svelte`.** `Canvas.svelte` is wired to the global `nodes`/`edges` stores, `$frameworkModels`, the group/filter machinery and the star-schema positioner (`Canvas.svelte:7-28, 101-122, 261-351`). None of that is a prop, so reuse means refactoring a 700-line component the entity canvas depends on. `MetricCanvas.svelte` is new and holds its own local state; it renders nodes, edges, and a sidebar, and skips groups, filters, lineage, and the wizard.

2. **No global stores for metric graph state.** `stores.ts` is module singletons with one undo/redo stack over `nodes`/`edges` (`stores.ts:18-19, 134-211`). Metric nodes live in the page component and go straight to the API, so the entity canvas boot effect (`+layout.svelte:689-720`) cannot leak entity nodes into the metric canvas and vice versa.

3. **Separate autosave class.** `AutoSaveService` hardcodes its serializer (`buildDataModelFromState`, `auto-save.ts:249-367`) and its endpoint (`apiSaveDataModel`, `:385`). Making them injectable touches the entity canvas's save path for one new consumer. `metric-tree-save.ts` re-implements the 400 ms debounce and in-flight guard against `/api/metric-tree`. Duplication is accepted; it is ~60 lines and testable in isolation.

4. **Preservation is unconditional, emission is gated.** `export_ossie` currently rebuilds `metrics: []` on every push (`ossie.py:514-520`). The new rule: read whatever the file has, keep every metric whose name Trellis did not author, then add the drafts. This runs even with `metrics.enabled: false`, because a push must never delete a semantic model's metrics just because a feature is off.

5. **Bound metrics are ids plus a reference.** `binding: {dataset, name}` and nothing else. Resolution happens at load: dataset name → entity id via the export mapping (`ossie.py:253, 492`), entity id → `model_ref` → model. Missing definitions stay in the file and surface as unresolved.

6. **Layout in its own file.** `metric_layout.yml`, keyed by metric id. `canvas_layout.yml` is keyed by entity id and would share a namespace; and positions become per-tree once `trees[]` exists while definitions stay global.

7. **Feature gate mirrors existing flags.** `/api/config-info` gains `metrics_enabled` (like `business_events_enabled`, `manifest.py:95-167`); the nav anchor and the page gate read it, the page redirects to `/canvas` when false (`bus-matrix/+page.svelte:18-27` is the pattern). The API answers `404` through `FeatureDisabledError`.

8. **Config normalisation only when the block exists.** Same guard as ossie (`config_service.py:401-423`): saving an unrelated setting must not inject `metrics:` into a tracked `trellis.yml`.

## Dependency Graph

```
T1 MetricsConfig ──▶ T2 metric_tree models + load/save ──▶ T3 API + config-info flag
                                                            │
                              ┌─────────────────────────────┴───────────────────────┐
                              ▼                                                     ▼
                    T4 Ossie emission + preservation                   T6 route/gate/types/api client
                    T5 catalog resolution                                        │
                              │                                                  ▼
                              │                                        T7 MetricCanvas + nodes
                              │                                                  │
                              │                                        T8 sidebar + add metric/edge
                              │                                                  │
                              │                                        T9 detail panel + autosave
                              │                                                  │
                              │                                        T10 layout persistence
                              ▼                                                  ▼
                    T11 config page section  ◀──── independent ────▶  T12 e2e + docs + version
```

T4 and T5 share `services/ossie.py` / `services/schema.py` versus `services/metric_tree.py` and `routes/metric_tree.py` - disjoint files, safe in parallel. T6-T10 all edit the metric canvas components and are strictly sequential. Backend (T4, T5) and frontend (T6) can run in parallel once T3 fixes the API contract.

## Task List

### Phase 1 - Foundation

- [ ] **T1** `MetricsConfig` block: dataclass, path resolution, pydantic model, config-service metadata, test reset
- [ ] **T2** `models/metric.py` + `services/metric_tree.py`: file model, load/save, graph validation, layout split/merge
- [ ] **T3** `/api/metric-tree` GET/POST, `metrics_enabled` on `/api/config-info`, router registration

### Checkpoint: Foundation
- [ ] `uv run pytest` passes
- [ ] `curl localhost:8089/api/metric-tree` returns the empty document with `metrics.enabled: true` and `404` with it false
- [ ] `trellis.yml` without a `metrics:` block is unchanged by `PUT /api/config`

### Phase 2 - Semantic layer

- [ ] **T4** Ossie emission (dataset-scoped vs document-scoped) + preservation of foreign metrics
- [ ] **T5** Catalog resolution: bindable, unmappable dataset, root-level read-only, missing definition

### Checkpoint: Semantic layer
- [ ] Push writes drafted metrics at the right scope and leaves pre-existing metrics byte-identical
- [ ] Second push produces identical bytes
- [ ] With `metrics.enabled: false`, a push leaves `semantic_model.yml` metrics untouched

### Phase 3 - Canvas

- [ ] **T6** `/metrics-tree` route, nav entry, disabled gate, TS types, API client
- [ ] **T7** `MetricCanvas` renders nodes and influence edges with layout positions
- [ ] **T8** Sidebar catalog, add metric, connect influence, delete
- [ ] **T9** Detail panel editing draft fields + debounced autosave
- [ ] **T10** Layout round-trip through `metric_layout.yml`

### Checkpoint: Canvas
- [ ] Add two metrics and one influence, reload, graph survives
- [ ] `npm run check`, `npm run test:smoke` pass
- [ ] Toggling `metrics.enabled` off hides the nav entry and redirects the route

### Phase 4 - Surface and docs

- [ ] **T11** Config page section for `metrics.*` with beta badges
- [ ] **T12** Playwright e2e, `trellis.yml.example`, README, CHANGELOG, version bump

### Checkpoint: Complete
- [ ] Every success criterion in `SPEC.md` is demonstrated by a test or a manual step
- [ ] `uv run pytest`, `npm run check`, `npm run test:smoke`, `npm run test:e2e` pass

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| The layout boot effect builds entity nodes into the global store while `/metrics-tree` is open, and the new page accidentally reads them | High - wrong graph on screen | Metric state is local to the page; no import of `nodes`/`edges` in metric components. Assert in the page's unit test that it never subscribes to those stores |
| `export_ossie` preservation changes output for projects that never enabled metrics | High - PR #156 byte-stability tests fail | Preservation only copies metrics already present; with none present the output is identical. Add an explicit "no metrics in file" regression test before touching the merge |
| pydantic shape for `metrics` fights the ruamel `CommentedMap` loaded from `trellis.yml` | Medium | Validate a plain `dict` from `load_yaml_or_json` and dump with `model_dump(mode="json")`, as `business_events_service` does |
| `_BETA_FIELDS` drifts from `beta=True` markers (it is a hand-maintained duplicate) | Low - missing badge only | Add both edits in T1 and assert `beta_flags` in `test_config_api.py` like the existing ossie test |
| Test-mode defaults leak: `_reset_shared_test_state` does not reset `OSSIE_CONFIG` today | Medium - order-dependent test failures | Add `METRICS_CONFIG` to `_reset_shared_test_state` in T1, before any test depends on it |
| Autosave duplication diverges from the entity canvas (different debounce semantics) | Low | Same 400 ms, same in-flight guard; unit-test the class directly against a fake fetch |
| Bound metric references break when an entity's `model_ref` changes | Medium | Catalog resolution recomputes from `data_model.yml` + models on every GET; unresolved bindings warn and render a badge rather than deleting |

## Parallelisation

- **Sequential, backend**: T1 → T2 → T3 (config, then file model, then routes).
- **Parallel after T3**: stream A = T4 (ossie.py, schema.py), stream B = T5 (metric_tree.py, routes/metric_tree.py), stream C = T6 (frontend types/api/route).
- **Sequential, frontend**: T6 → T7 → T8 → T9 → T10 (same component set).
- **Independent**: T11 (config page) can run any time after T1; it touches only `config/+page.svelte`.
- **Last**: T12 depends on everything.

One file, one worker: T4 owns `services/ossie.py` + `services/schema.py`; T5 owns `services/metric_tree.py` + `routes/metric_tree.py`; frontend stream owns `frontend/src/lib/components/Metric*` and `routes/(app)/metrics-tree/`.

## Open Questions

1. **Version bump.** `0.26.0b1` in T12, assuming #156 ships as `0.25.0b1`. If #156 lands differently, T12 takes whatever comes next.

## Notes

**Stacked PR.** `feature/metric-tree` targets `feature/ossie-export`. T4 edits the module PR #156 introduces, so the two cannot merge out of order; retarget to `main` after #156 lands.

**Not this slice.** `trees[]`, edge metadata (`sign`, `lag`), `unit`, reading MetricFlow/Bruin metric definitions, SQL validation, an MCP endpoint.
