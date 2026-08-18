# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.23.0b1] - 2026-08-18

### Added
- **Frontend boot diagnostics**: Capture boot phases, request timing, response sizes,
  server timing data, and deterministic benchmark summaries for troubleshooting large projects.
- **Deterministic boot-performance benchmark**: Add a reproducible 500-entity / 750-relationship
  fixture with cold and warm measurements for Canvas and Entity List startup.

### Changed
- **Faster boot loading**: Parallelize independent startup requests, publish core data earlier,
  defer optional relationship and layout work, and lazy-load editable schemas and heavy Canvas code.
- **Lower backend startup cost**: Cache immutable dbt artifact snapshots, reuse derived indexes,
  batch source-system lineage extraction, and avoid redundant entity-type inference and autosaves.
- **Improved large-graph rendering**: Reuse stable graph indexes, render only visible Svelte Flow
  elements, and defer ELK layout and expensive Canvas content until needed.

### Performance
- The benchmark fixture measured approximately **90–96% lower time to first useful render**,
  with all configured cold and warm startup gates passing.

## [0.22.1] - 2026-08-17

### Fixed
- **Canonical model folder paths**: top-level and nested model directories below `models/`
  are now preserved consistently for grouping and filtering instead of being misclassified
  as `Uncategorized`.

## [0.22.0] - 2026-08-17

### Added
- **Model binding from the UI**: Users can search and select a model from an entity's detail view,
  bind additional models to an existing entity, or drag a model from the Sidebar onto an entity row
  without opening the detail view.
- **URL-addressable entity details**: Entity detail modals can be opened and shared through
  `/entity-list/<entity-id>`, with browser history and related-entity navigation kept in sync.

### Changed
- **Entity detail modal is less scroll-heavy to edit.** Bound dbt models show up with the header
  context instead of below the form, so you see what the entity is tied to before digging into
  attributes. Roles & aliases stay collapsed until you open them, and long domain / tag / source
  lists hide behind a `+N more` control so chip walls no longer crowd the form. Attribute editing
  keeps its full-width table; the rest of the modal is tighter and easier to scan.
- **Bus Matrix usage badges are clearer**: Each badge explains how many related facts or dimensions
  are associated with that row or column, and fact labels retain their normal casing.

### Fixed
- **Bus Matrix tooltips no longer get clipped**: Usage explanations remain readable inside the
  scrollable matrix and size to their content.

## [0.21.1] - 2026-08-05

### Fixed
- **Warehouse-native column types no longer land on `datatype: unknown`**: the reconcile type map only
  knew Postgres-style spellings, so a Snowflake `NUMBER` or a BigQuery `BIGNUMERIC` fell through to
  `unknown` even though the exact type sat right next to it in `physical_datatype`. Parameterized
  types are now split before matching (`VARCHAR(16777216)` → `text`, `TIMESTAMP_NTZ(9)` →
  `timestamp`), and the fixed-point families (`number`, `numeric`, `decimal`, `bignumeric`) are
  scale-aware: an explicit scale of 0 is an `int`, anything else is a `float`. Collection and nested
  types (`ARRAY`, `STRUCT<...>`, `VARIANT`, `int[]`) stay `unknown` on purpose rather than being
  collapsed onto their element type. Existing `unknown` values are backfilled the next time
  reconcile runs, which is on app load.

## [0.21.0] - 2026-08-03

Adds Bruin as a second supported transformation framework, and finishes the adapter boundary the
0.20.0 refactor started. No functional change for dbt-core users, and nothing to migrate: an
existing `trellis.yml` keeps working untouched, since `framework` still defaults to `dbt-core`.

### Added
- **Bruin support**: set `framework: bruin` with `bruin_pipeline_path` in `trellis.yml` and Trellis
  reads your pipeline's assets instead of a dbt project. Asset schemas live inline in each file's
  `@bruin` comment block, so Trellis reads and writes them there. The SQL body is never touched.
  - `bruin_asset_paths` filters which asset subdirectories appear, the same way `dbt_model_paths`
    does. Lineage and relationship resolution deliberately ignore the filter: an upstream asset
    outside the configured paths is still a real dependency.
  - **Lineage** comes from each asset's `depends:`. An `ingestr` asset, or any asset with no
    upstreams, is where data enters the pipeline and is shown as a source (the role a dbt source
    plays). Its source system is the `parameters.source_connection` it pulls from, which is what
    drives the source chips on the canvas.
  - **Relationships** map to Bruin's native `columns[].foreign_key: {table, column}`, so they
    round-trip: pushing writes the foreign key into the asset, pulling reads it back, and deleting a
    relationship in Trellis prunes the foreign key. References written as either `dim__customer` or
    `core.dim__customer` both resolve, and your spelling is left as you wrote it.
  - **Pushing drafted fields** to an entity with no asset yet scaffolds a new `.sql` asset with a
    placeholder body for you to fill in, since Trellis cannot know the query.
    `bruin_default_asset_type` sets the asset type, because it is platform-specific (`duckdb.sql`,
    `bq.sql`, `sf.sql`, and so on). Scaffolding never overwrites an existing file.
- **Framework capabilities in `/api/config-info` and `/api/config-status`**: each adapter declares
  what its framework supports, and the UI hides features that cannot work rather than offering a
  view that would always be empty.
- **Neutral project-status reporting**: both config endpoints now report `project_path`,
  `artifacts_present`, and an `artifacts` map alongside the existing dbt-named keys, so a framework
  with no manifest or catalog can describe its own health.

### Known Bruin limitations
- **No exposures.** Bruin has no exposures concept, so the exposures view is hidden under
  `framework: bruin` even if `exposures.enabled` is set.
- **No column-level lineage.** `depends:` is table-level. Bruin resolves column upstreams itself and
  does not write them into the asset file.
- **No model versioning.** Bruin has no equivalent of dbt's versioned models.

### Changed
- **Lineage, exposures, source-system extraction, and project status now go through the adapter.**
  These were the four subsystems 0.20.0 left reading `manifest.json`/`catalog.json` directly, and
  they were also what made a second framework impossible. `TransformationAdapter` gains
  `get_lineage`, `get_exposures`, `get_source_systems_for_model`, and `get_project_status`, and no
  route or service names a dbt artifact any more. The strict-xfail contract tests that pinned this
  work are now live tests.
- **Sidebar setup warning is framework-aware**: it shows the active adapter's own error and
  remediation hints instead of always advising `dbt compile`.
- **Entity-type inference is shared between adapters**, keyed per framework so two adapters cannot
  clobber each other's cached results.

### Fixed
- **`sync-tests` never merged inferred relationships.** `services/schema.py` called
  `infer_relationships()` before the adapter was constructed. The resulting `NameError` was
  swallowed by a bare `except`, so the merge silently always saw an empty list.

## [0.20.0] - 2026-08-03

Structural refactor that decouples Trellis from dbt-specific naming, so a second transformation
framework becomes an adapter you write rather than `if framework == ...` branches threaded through
every service. No functional change for dbt-core users. Validated through the 0.20.0b1/b2
prereleases against a real project: `data_model.yml` migrates cleanly on first save, and push
produces the expected `schema.yml` output.

### ⚠️ Upgrade is one-way

Entity fields are renamed on disk (`dbt_model` → `model_ref`, `dbt_tags` → `framework_tags`,
`dbt_data_type` → `physical_datatype`). Reading the old names is permanent, so **upgrading is
transparent and needs no migration**. Writing is not: the first save after upgrading rewrites your
`data_model.yml` with the new names only.

That means **rolling back to 0.19.x after saving is not supported**. Older versions only look for
`dbt_model`, so every entity would load as unbound — model bindings and framework-mirrored tags would
not appear on the canvas. Commit or back up `data_model.yml` before upgrading if you want a clean way
back.

### Added
- **Framework-neutral endpoint paths**: `/api/reconcile`, `/api/schema`, and `/api/sync-tests` are now the primary API surface, replacing `/api/reconcile-dbt`, `/api/dbt-schema`, and `/api/sync-dbt-tests`.
- **Framework-driven Sidebar icon/label**: the sidebar's model icon and label are driven by the configured `framework` rather than assuming dbt. A framework Trellis has no adapter for falls back to neutral branding instead of silently rendering dbt's.

### Changed
- **`data_model.yml` entity fields generalized**: `dbt_model` → `model_ref`, `dbt_tags` → `framework_tags`, `dbt_data_type` → `physical_datatype`. Old names load transparently and permanently; only the new names are written back. `physical_datatype` pairs with a column's `datatype`: `datatype` is the coarse logical bucket, `physical_datatype` the concrete type the framework's catalog reports, kept so a push doesn't downgrade a precise type.
- **Reconciliation "wins" semantics reworded as framework-neutral**: described as "the active framework's materialized model wins over a drafted concept". The algorithm (one-way, idempotent, absence-is-never-deletion) is unchanged.
- **Adapter protocol closed up**: `save_schema_file`, `infer_entity_types`, `get_model_dirs`, and `reset_inference_cache` are now declared on `TransformationAdapter` instead of being called on `DbtCoreAdapter` without a contract. No module outside `adapters/` imports `DbtCoreAdapter`. A `FakeAdapter` test double proves reconciliation and schema services work against a non-dbt adapter.
- **Internal dbt-named functions renamed**: `reconcile_dbt()` → `reconcile_framework()`, `sync_dbt_tests()` → `sync_framework_tests()`, `_map_dbt_type()` → `_map_column_type()`, `save_dbt_schema()` → `save_model_schema_from_request()`/`save_schema_file()`. Internal only.

### Notes
- Behavior-preserving by design: dbt-core projects see no functional change beyond the transparently read-compatible field renames.
- Some subsystems (`services/lineage.py`, `services/exposures.py`, `services/manifest.py`, and related routes) still read dbt artifacts directly rather than through the adapter protocol. Deferred to the BruinAdapter work and pinned by strict-xfail contract tests so it can't be silently forgotten.
- No second framework ships here. `FrameworkEnum` lists only `dbt-core`, so a framework becomes selectable in `trellis.yml` at the same time as its working adapter, never before.

## [0.20.0b2] - 2026-08-03

> **Prerelease.** Supersedes 0.20.0b1 — same refactor, one field renamed. See b1 below for the full
> set of changes in this release line.

### Changed since b1

- **`native_data_type` renamed to `physical_datatype`.** "Native" left the reader asking native to
  what, and implied an untouched value the field does not hold (catalog spellings are canonicalized
  on the way in). It also read badly beside its sibling: `datatype: text` next to
  `native_data_type: TEXT` differs only by case. `physical_datatype` names the real distinction —
  `datatype` is Trellis's logical bucket (closed set: text/int/float/bool/date/timestamp/unknown),
  `physical_datatype` is the concrete type the framework's catalog reports (varchar, timestamp,
  numeric(38,0)) — and matching `datatype`'s spelling keeps the pair symmetric.

  **If you saved a `data_model.yml` while running b1**, it contains `native_data_type` keys. b2 does
  not read that name (it reads `physical_datatype`, falling back to the legacy `dbt_data_type`), so
  those precise types will read as absent. **Run a reconcile** — it repopulates the field from the
  framework catalog, so nothing is permanently lost. `native_data_type` is deliberately not kept as a
  legacy read key: it existed only in b1 and carrying it forever would mean three spellings of one
  field.

### ⚠️ Upgrade is one-way

Entity fields are renamed on disk (`dbt_model` → `model_ref`, `dbt_tags` → `framework_tags`,
`dbt_data_type` → `physical_datatype`). Reading the old names is permanent, so **upgrading is
transparent and needs no migration**. Writing is not: the first save after upgrading rewrites your
`data_model.yml` with the new names only.

That means **rolling back to 0.19.x after saving is not supported**. Older versions only look for
`dbt_model`, so every entity would load as unbound — model bindings and framework-mirrored tags would
not appear on the canvas. Commit or back up `data_model.yml` before upgrading if you want a clean way
back.

## [0.20.0b1] - 2026-08-03

> **Superseded by 0.20.0b2**, which renames this release's `native_data_type` field to
> `physical_datatype`. Everything below still describes the release line.

### Added
- **Framework-neutral endpoint paths**: `/api/reconcile`, `/api/schema`, and `/api/sync-tests` are now the primary API surface. The legacy `/api/reconcile-dbt`, `/api/dbt-schema`, `/api/sync-dbt-tests` paths have been retired now that the frontend is fully migrated.
- **Framework-driven Sidebar icon/label**: the sidebar's model icon and label are now driven by the configured `framework` rather than assuming dbt. A framework Trellis has no adapter for falls back to neutral branding instead of silently rendering dbt's icon and label.

### Changed
- **`data_model.yml` entity fields generalized**: `dbt_model` → `model_ref`, `dbt_tags` → `framework_tags`, `dbt_data_type` → `native_data_type` (renamed again to `physical_datatype` in b2). Existing files using the old field names continue to load transparently (read-compat is permanent); only the new names are written back on save. No manual migration needed.
- **Reconciliation "wins" semantics reworded as framework-neutral**: `services/reconciliation.py`'s dbt-wins rule is now described as "the active framework's materialized model wins over a drafted concept." The underlying algorithm (one-way, idempotent, absence-is-never-deletion) is unchanged.
- **Adapter protocol closed up**: `save_schema_file`, `infer_entity_types`, `get_model_dirs`, and `reset_inference_cache` are now declared on `TransformationAdapter` instead of being called on `DbtCoreAdapter` without a protocol contract. No module outside `adapters/` imports `DbtCoreAdapter` directly anymore. A new `FakeAdapter` test double proves reconciliation and schema services work against a non-dbt adapter.
- **Internal dbt-named functions renamed**: `reconcile_dbt()` → `reconcile_framework()`, `sync_dbt_tests()` → `sync_framework_tests()`, `_map_dbt_type()` → `_map_column_type()`, `save_dbt_schema()` → `save_model_schema_from_request()`/`save_schema_file()`. Purely internal — no API impact.

### Notes
- This is a behavior-preserving structural refactor: existing dbt-core projects see no functional change beyond internal field renames, which are transparently read-compatible.
- Some subsystems (`services/lineage.py`, `services/exposures.py`, `services/manifest.py`, and related routes) still read dbt artifacts directly instead of going through the adapter protocol. This is deliberately deferred to the upcoming BruinAdapter work and pinned by strict-xfail contract tests so it can't be silently forgotten.
- No second framework ships here. This release is the groundwork that makes adding one an adapter-shaped job; `FrameworkEnum` still lists only `dbt-core`, so a framework becomes selectable in `trellis.yml` at the same time as its working adapter, never before.

## [0.19.1] - 2026-07-31

### Fixed
- **Entity List showed "No entities yet" while still loading**: on projects with lots of entities, the list rendered its empty state for a few seconds during the initial data model fetch, indistinguishable from an actually-empty project. Entity List now shows a loading spinner until the fetch completes, matching the pattern already used on Canvas.
- **Inconsistent loading spinners across views**: Bus Matrix, Exposures, and Business Events each used their own spinner markup (icon-based, different border style/size/color) instead of the shared pattern, and the Bus Matrix/Exposures/Business Events page wrappers showed a blank screen during their initial config-check before rendering. All loading spinners are now visually identical and none of the views have a blank-screen gap.
- **Entity List loading spinner positioned near the top instead of centered**: the wrapper div around the Entity List component had no height set, so the component's own full-height centering never had space to work with. Fixed by propagating height down through the wrapper.

## [0.19.0] - 2026-07-31

### Added
- **dbt build-status indicator and filter**: entities bound to a dbt model (`dbt_model` truthy) now show a build-status mark in the Entity List (a checkmark matching the sidebar's existing "Bound" filter styling) and in the Bus Matrix (a filled/hollow dot to the left of each dimension and fact label, since a dim-fact pair can have mismatched build status). Both views gained a "Built" filter (Bound/Unbound) alongside their existing filters. The Entity List also shows a small inline legend next to the filter explaining the mark.

## [0.19.0b1] - 2026-07-30

### Added
- **dbt build-status badge and filter**: entities bound to a dbt model (`dbt_model` truthy) now show a dbt icon badge in the Entity List and in the Bus Matrix (both dimensions and facts). Both views gained a "Built" filter (Bound/Unbound) alongside their existing filters, letting you see at a glance — and filter to — what's already built in dbt versus still only modeled in Trellis.

## [0.18.0] - 2026-07-30

### Added
- **`dbt_tags`/`ui_tags` on bound entities**: `dbt_tags` mirrors `schema.yml`/the manifest, refreshed on every reconcile and never hand-edited — the same authority model already applied to `source: dbt` columns. `ui_tags` holds only tags a user explicitly adds via the Trellis tag editor. `tags` itself is no longer a persisted field on a bound entity; it's computed at read time as the union of the two (new `compute_display_tags` helper, wired into `GET /api/data-model` and the Bus Matrix endpoint). Unbound entities are unaffected — `tags` remains their single, persisted, freely-editable field.
- **`YamlHandler.merge_model_tags`/`merge_version_tags`**: additive-union tag writers that read the live `schema.yml` fresh immediately before writing, used everywhere Trellis pushes tags to dbt.

### Fixed
- **Tags added directly to `schema.yml` no longer silently deleted by Trellis pushes**: pushing tags previously did a full replace using a cached, potentially stale list. A tag added outside Trellis (e.g. `nightly`, added directly to `schema.yml` by a dbt developer) was wiped the next time Trellis pushed an unrelated tag change. Push now additively unions `ui_tags` onto the current file content instead.
- **Bound-entity tags silently wiped on any autosave, and on saving from the entity detail modal**: two separate write paths sent an edit without a way for the backend to tell "no change" apart from "clear it," erasing reconciled tags on routine, unrelated saves. Both fixed to only ever write `ui_tags`, never the reconcile-owned `dbt_tags`/`tags`.
- **Migration seed copying dbt's entire tag list into `ui_tags` on a second reconcile**: the one-time legacy-tag migration couldn't tell pre-fix user data apart from tags the manifest had already mirrored in an earlier run. Now only seeds when the existing value genuinely differs from what reconciliation would produce right now.

### Changed
- **Tag removal is additive-only in this release**: removing a tag from `ui_tags` in the Trellis UI does not remove it from `schema.yml` on push. Durable removal tracking would require a second, push-time-only field distinct from the continuously-autosaved `ui_tags` — judged too invasive for this iteration. To remove a Trellis-added tag, edit `schema.yml` directly; dbt then owns it going forward.
- Entities with a pre-existing `tags` value from before this change are seeded into `ui_tags` once on first reconcile (if it represents real legacy data, not tags already mirrored from dbt), so nothing is lost under the new logic; the legacy key is retired afterward.
- Bulk tag add/remove and the "Generate Entities" dialog's save path are updated to the same `dbt_tags`/`ui_tags` split, closing two write paths that would otherwise have hit the same tag-loss bug.

## [0.18.0b4] - 2026-07-30

### Fixed
- **Tag edits from the entity detail modal silently lost for bound entities**: `handleSave` wrote the edited tag list straight to `tags` unconditionally — a fourth write path with the same category of bug as the autosave fix in `0.18.0b2`, since `tags` is no longer persisted for bound entities at all. Reported: adding a tag via the entity detail modal and clicking "Save Changes" never showed up in `data_model.yml`. Fixed to diff the edit against `dbt_tags` and write only `ui_tags` for bound entities, matching every other tag-editing surface.
- **CLA allowlist**: added `tim.hiebenthal@a11.com`.

## [0.18.0b3] - 2026-07-30

### Fixed
- **Migration seed wrongly copying dbt's entire tag list into `trellis_tags`**: the one-time seed fired whenever `trellis_tags` was absent and `tags` was non-empty, with no way to tell legacy pre-fix data apart from tags already mirrored from the manifest by an earlier reconcile run. On a second reconcile, that meant copying dbt's full tag list into `trellis_tags`, wrongly marking it as user-added and defeating the read-only/removable tag-editor split. Now only seeds when the existing value genuinely differs from what reconciliation would produce right now.

### Changed
- **Renamed `tags`/`trellis_tags` to `dbt_tags`/`ui_tags` for clarity, and `tags` is no longer persisted for bound entities at all**: the prior naming — `tags` meaning "dbt-mirrored" for bound entities but "freely editable" for unbound, and `trellis_tags` for user-added tags — caused repeated confusion about which field meant what. `dbt_tags` (dbt-owned, reconcile-refreshed) and `ui_tags` (added via the Trellis UI) are now explicit. `tags` is computed at read time as their union (new `compute_display_tags` helper, wired into `GET /api/data-model` and the Bus Matrix endpoint) and is never written back to `data_model.yml` for a bound entity — a legacy `tags` key is retired on first reconcile after upgrading. Unbound entities are unaffected: `tags` remains their single, persisted, freely-editable field.
- Two additional write paths that duplicated the pre-fix tag-persistence logic (and would have hit the same tag-loss bug) are fixed to match: bulk tag add/remove (`bulk-operations.ts`) and the "Generate Entities" dialog's save path.

## [0.18.0b2] - 2026-07-30

### Fixed
- **Bound-entity `tags` silently wiped on every autosave**: `_split_model_and_layout` built each entity fresh from the incoming save payload with no fallback to the on-disk value for `tags`. Since autosave correctly omits `tags` for bound entities (it's reconcile-owned; only `trellis_tags` is sent), any autosave — not just a tag edit — erased the reconciled tags. Found during real-world validation against a live dbt project. Fixed by extending the existing `roles`-preservation mechanism to `tags`, scoped to bound entities only; an unbound entity's intentional "clear all tags" via omission still works as before.

## [0.18.0b1] - 2026-07-30

### Added
- **`trellis_tags` on bound entities**: tags a user explicitly adds via the Trellis tag editor are now tracked separately from `tags`, which becomes a dbt-mirrored, reconcile-owned field (refreshed from `schema.yml`/the manifest on every reconcile, never hand-edited) — the same authority model already applied to `source: dbt` columns. The tag editor renders dbt-mirrored tags read-only and `trellis_tags` as removable.
- **`YamlHandler.merge_model_tags`/`merge_version_tags`**: additive-union tag writers that read the live file fresh immediately before writing, used everywhere Trellis pushes tags to `schema.yml`.

### Fixed
- **Tags added directly to `schema.yml` no longer silently deleted by Trellis pushes**: `sync_relationships`, `save_model_schema`, and `save_dbt_schema` previously called `update_model_tags`/`update_version_tags` with a cached, potentially stale tag list, doing a full replace on every push. A tag added outside Trellis (e.g. `nightly`, added directly to `schema.yml` by a dbt developer) was wiped the next time Trellis pushed an unrelated tag change. Push now additively unions `trellis_tags` onto the current file content instead.

### Changed
- **Tag removal is additive-only in this release**: removing a tag from `trellis_tags` in the Trellis UI does not remove it from `schema.yml` on push (documented v1 scope decision — durable removal tracking would require a second, push-time-only field written back to `data_model.yml`, judged too invasive for this iteration). To remove a Trellis-added tag, edit `schema.yml` directly; dbt then owns it going forward.
- Entities with a pre-existing `tags` value from before this change are seeded into `trellis_tags` once on first reconcile, so those tags aren't lost under the new merge logic.

## [0.17.1] - 2026-07-27

### Fixed
- **Native dbt column types preserved on push (#111)**: `POST /api/dbt-schema` and `POST /api/sync-dbt-tests` previously wrote the drafted field's coarse UI type bucket (e.g. `text`) to `schema.yml` for dbt-sourced columns, downgrading precise declared types like `varchar(50)` to the generic bucket on every push.
- **Declared `data_type` no longer clobbered by catalog-normalized types (#111)**: warehouses often report a declared type under a different spelling than it was written (e.g. Snowflake's catalog reports a declared `varchar` column as `TEXT`), so trusting the catalog value unconditionally still overwrote a divergent `schema.yml` value, just with a different value. `data_type` is now only backfilled when a column has no existing declared type; an existing value is never touched.
- **Catalog type spellings canonicalized on backfill (#111)**: a dbt-sourced column synced for the first time (no prior `schema.yml` entry) is now backfilled with a canonical spelling (`TEXT` → `varchar`, `TIMESTAMP_NTZ` → `timestamp`) instead of the raw catalog value, so freshly-backfilled columns don't mix spellings with hand-declared ones across `schema.yml` files. Ambiguous types (`NUMBER`, which spans int/decimal/numeric without exposing precision/scale) are left as-is rather than guessed.

## [0.17.0] - 2026-07-24

### Added
- **Structured origin metadata**: Entity attribute `origin` is now a list of `{source_id: path}` objects in `data_model.yml`, written as `meta.origin` in dbt `schema.yml` on materialization, read back from manifest/meta (with `| Origin:` description fallback), and shown read-only in the EntityDetailModal. Legacy pipe-separated strings still load via silent migration.
- **dbt origin icon in EntityDetailModal**: Rows whose origin comes from a materialized dbt model now show a dbt icon in the origin column, distinguishing them from manually entered origin values.

### Changed
- **Origin exports**: Excel and Markdown exports stringify structured origin lists back to the legacy `KEY: VALUE | KEY: VALUE` format.

## [0.16.2] - 2026-06-24
- Add parsing of "Origin" values from the dbt column description

## [0.16.1] - 2026-06-15

### Added

- **Sidebar search now filters the canvas**: Typing in the Explorer search box hides all canvas entities whose label does not match, giving a focused view on crowded canvases with many entities. Clearing the search restores all entities. URL-based business event filters continue to take priority over the sidebar search. The event-filter banner is not shown for search-based filtering.
## [0.16.0] - 2026-06-15

### Added

- **dbt reconciliation — `data_model.yml` as single source of truth**: Trellis now reconciles the compiled dbt manifest into `data_model.yml` on startup. Each bound entity's field list is enriched with its materialized dbt columns tagged `source: dbt`, alongside any unmatched drafted fields (`source: draft`). The file is self-contained and readable offline without a live manifest. Reconciliation is non-destructive: a model absent from the manifest (e.g. after a partial `dbt compile --select`) never removes its existing materialized fields.
- **`POST /api/reconcile-dbt` endpoint**: Triggers manifest→`data_model.yml` reconciliation on demand. Returns `{status, changed, data_model}`. Called automatically by the frontend on app load after the manifest is fetched.
- **Live schema.yml description read**: When opening the entity detail modal for a bound entity, Trellis fetches column descriptions directly from `schema.yml` (via `GET /api/models/{name}/schema`) rather than from the manifest. Lag-free — edited descriptions are visible immediately after save without running `dbt compile`. Priority: user edit > live `schema.yml` value > manifest value.
- **`DraftedField.source` provenance marker**: TypeScript and YAML `drafted_fields` entries gain an optional `source: 'dbt' | 'draft'` field. `source: dbt` fields are dbt-owned and read-only (except description); `source: draft` fields are Trellis-authored. Missing `source` is treated as `draft` for backward compatibility.
- **Collapsible entity sections in undescribed attributes warning**: The multi-entity view in the undescribed attributes modal now shows collapsible sections per entity, making it easier to navigate large lists.

### Fixed

- **`get_models()` now includes column descriptions**: The `/api/manifest` endpoint previously stripped column descriptions silently. Descriptions from the manifest (and `comment` from the catalog) are now included in each column entry.
- **Catalog column names normalized to lowercase**: When a dbt catalog is present (e.g. after `dbt docs generate`), column names were returned in the database's native case (uppercase in Snowflake). This caused a mismatch with the lowercase names in `schema.yml`, breaking description lookup and display. Column names from the catalog are now normalized to lowercase. Descriptions are sourced from the manifest rather than the empty catalog.
- **Column types read from `data_type` key**: dbt manifest columns store their type under `data_type`, not `type`. The manifest fallback only read `type`, returning null for most projects and causing reconciliation to write `datatype: unknown` for every materialized field.
- **Non-destructive push**: `POST /api/dbt-schema` no longer deletes columns from `schema.yml` that are absent from the entity's field list. Columns added directly by developers outside Trellis are preserved.
- **Stale relationship tests cleaned up on push**: `POST /api/dbt-schema` now removes `relationships` tests from columns that were previously FKs but are no longer, matching the behavior of `POST /api/sync-dbt-tests`.

## [0.16.0-beta.3] - 2026-06-15

### Fixed

- **Catalog column names normalized to lowercase**: When a dbt catalog is present (e.g. after `dbt docs generate`), column names were returned in the database's native case (uppercase in Snowflake/DW). This caused a mismatch with the lowercase names in `schema.yml`, breaking description lookup and display. Column names from the catalog are now normalized to lowercase, consistent with the manifest and YAML. Descriptions are now sourced from the manifest (which holds YAML-documented descriptions) rather than the catalog (which holds empty database comments).

## [0.16.0-beta.2] - 2026-06-15

### Fixed

- **Column types no longer overwritten to `unknown` on push**: dbt manifest columns store their type under `data_type`, not `type`. The manifest fallback in `get_models()` only read `type`, returning `None` for most real projects — reconciliation then wrote `datatype: unknown` for every materialized field. Fixed to read `data_type` as fallback, matching the catalog path.

## [0.16.0-beta.1] - 2026-06-15

### Added

- **dbt reconciliation — `data_model.yml` as single source of truth**: Trellis now reconciles the compiled dbt manifest into `data_model.yml` on startup. Each bound entity's field list is enriched with its materialized dbt columns tagged `source: dbt`, alongside any unmatched drafted fields (`source: draft`). The file is self-contained and readable offline without a live manifest. Reconciliation is non-destructive: a model absent from the manifest (e.g. after a partial `dbt compile --select`) never removes its existing materialized fields.
- **`POST /api/reconcile-dbt` endpoint**: Triggers manifest→`data_model.yml` reconciliation on demand. Returns `{status, changed, data_model}`. Called automatically by the frontend on app load after the manifest is fetched.
- **Live schema.yml description read**: When opening the entity detail modal for a bound entity, Trellis now fetches column descriptions directly from `schema.yml` (via `GET /api/models/{name}/schema`) rather than from the manifest. This is lag-free — edited descriptions are visible immediately after save without running `dbt compile`. Priority: user edit > live `schema.yml` value > manifest value.
- **`DraftedField.source` provenance marker**: TypeScript and YAML `drafted_fields` entries gain an optional `source: 'dbt' | 'draft'` field. `source: dbt` fields are dbt-owned and read-only (except description); `source: draft` fields are Trellis-authored. Missing `source` is treated as `draft` for backward compatibility.

### Fixed

- **`get_models()` now includes column descriptions**: The `/api/manifest` endpoint previously stripped column descriptions silently. Descriptions from the manifest (and `comment` from the catalog) are now included in each column entry.
- **Non-destructive push**: `POST /api/dbt-schema` no longer deletes columns from `schema.yml` that are absent from the entity's field list. Columns added directly by developers outside Trellis are preserved.
- **Stale relationship tests cleaned up on push**: `POST /api/dbt-schema` now removes `relationships` tests from columns that were previously FKs but are no longer, matching the behavior of `POST /api/sync-dbt-tests`.

## [0.15.9] - 2026-06-10

### Added

- **Relationships section in the entity detail modal**: The EntityDetailModal now shows the entity's relationships directly on screen, previously they appeared only in the Markdown/Excel export, not the modal UI. Each relationship lists the related entity (a clickable link that navigates the modal to that entity), the direction (incoming/outgoing), the cardinality (e.g. 1:N), and the table-qualified join keys (`source_model.source_field = target_model.target_field`). The list reuses the same `formatRelationshipKeys` / `formatRelationshipType` helpers as the exports, so the modal and exports stay consistent. Navigating to another entity warns first if there are unsaved changes.

## [0.15.8] - 2026-06-10

### Changed

- **Entity exports show concrete join keys for relationships**: The "Relationships" section of the Markdown and Excel exports now renders each relationship with its table-qualified join keys, `via source_model.source_field = target_model.target_field` (e.g. `via invoice_recipient.invoice_recipient_id = dim__lead.customer_number`), matching the canvas lineage view. Table qualifiers come from the edge's model names, falling back to the entity labels when no model is bound. This is more useful than the business label for understanding the join. When join keys are unavailable, the export falls back to the business label, then `-`.

### Fixed

- **Relationship name shows as `-` in entity exports**: Markdown and Excel exports read the relationship name from the top-level `edge.label`, which is always undefined. The name is stored at `edge.data.label` (set in `aggregateRelationshipsIntoEdges`), so every relationship rendered as `via "-"` in exports even though the canvas editor displayed the correct name. All export sites now read `edge.data`. Test fixtures that encoded the wrong edge shape (label at the top level instead of under `data`), which had masked the bug, were corrected.

## [0.15.7] - 2026-05-15

### CI

- **Automated release pipeline**: Merges `release.yml` and `publish.yml` into a single workflow. Version bumps in `pyproject.toml` merged to `main` now automatically create a GitHub Release and trigger a PyPI publish. Manual beta publishing via `workflow_dispatch` with an explicit version input is still supported.

## [0.15.6] - 2026-05-15

### Fixed

- **Entity detail modal — text selection in drafted attribute rows ([#97](https://github.com/timhiebenthal/trellis-datamodel/issues/97))**: Click-drag inside name, description, origin, or type controls no longer starts a row drag. `dragstart` reports the draggable row as `event.target`, not the focused input, so the handler now uses the prior `mousedown` target to cancel the drag when interaction began on `input` / `select` / `textarea`, restoring normal text selection and edge scrolling in those fields.

## [0.15.5] - 2026-05-15

### Packaging

- **PyPI pre-release**: Package version `0.15.5b2` for beta testing elsewhere (`pip install trellis-datamodel==0.15.5b2` after publish).

### Fixed

- **`schema.yml` keeps stale columns after renames/deletes (#98)**: Two code paths were affected. `YamlHandler.update_columns_batch` only added/updated columns and never removed ones missing from the incoming list, so renaming or deleting fields in `data_model.yml` left orphaned entries (and outdated `data_tests`) behind in `schema.yml`. The "push to dbt" flow (`DbtCoreAdapter.sync_relationships`) had the same additive pattern for `drafted_fields`, which is why the first beta still left stale columns on push-to-dbt. Both paths now rebuild the column list from the incoming payload, reusing existing column entries by name so custom `data_tests`/`meta` are preserved while missing names are dropped. `sync_relationships` only prunes when the entity actually carries a `drafted_fields` key, so relationship-only syncs do not wipe existing columns.

## [0.15.4] - 2026-05-08

### Fixed

- **Entity detail modal — attribute name input**: Typing a full attribute name no longer loses focus after each character. Root cause was the Svelte keyed-each using `field.name` as the key, which destroyed and recreated the input on every keystroke; fixed by using a stable `draft-{draftIndex}` key.
- **Entity detail modal — attribute drag-to-reorder**: Drag handles and drop events were wired up in the data model but never attached to the DOM. Rows now have `draggable`, `ondragstart`, `ondragover`, `ondrop`, and `ondragend` handlers, restoring the ability to reorder attributes by dragging.
- **Unbound entity type inference**: Unbound entities (not linked to a dbt model) whose ID matches a configured dimension or fact prefix (e.g. `dim_`, `fct_`) are now automatically classified on load, matching the existing behaviour for bound entities.

## [0.15.3] - 2026-04-29

### Added

- **Markdown export coverage**: Vitest `it.each` with real-world origin strings (`DH1: … | DH2: …`); Entity detail modal tests for Copy as Markdown including origins that contain ` | ` (asserts `&#124;` in the clipboard payload).

## [0.15.2] - 2026-04-29

### Fixed

- **Markdown export origins**: Drafted attributes now copy their saved origin mappings into the Markdown export instead of showing the generic `drafted` label.
- **Markdown attribute tables**: Pipe characters inside attribute cells (especially `DH1: … | DH2: …` origins) are encoded as `&#124;` and newlines are flattened so pipe tables do not gain spurious columns in strict Markdown renderers.

## [0.15.1] - 2026-04-28

### Fixed

- **Filter/sort toolbar consistency**: Aligned the filter and sort controls across Bus Matrix, Entity List, and Business Events — filters on the left, sort always on the right, no all-caps labels. Bus Matrix toolbar is now a single row with compact dropdowns and a subtle divider between the filter and sort sections.

## [0.15.0] - 2026-04-28

### Removed

- **`trellis.yml.backup`**: Trellis no longer creates a `.backup` file alongside `trellis.yml` when saving configuration. Since `trellis.yml` is version-controlled, git history already provides a full audit trail and recovery path — the backup file was redundant noise in tracked repos.

### Added

- **Merged dbt + drafted fields**: Bound entities show a single attribute list combining manifest columns and `drafted_fields`, with origin indicators (materialized vs drafted) in the entity detail modal and on the canvas in logical view.
- **Materialize from modal**: Draft-only rows can be written to the bound model’s `schema.yml` from the entity modal, with a reminder that SQL still needs updating; manifest refresh follows.
- **Manifest column descriptions in modal**: Edits to materialized column descriptions in the modal are persisted to `schema.yml` on Save when there are pending description overrides.
- **Silent auto-promotion**: After each manifest reload, drafted fields whose names match a manifest column are removed from the entity’s `drafted_fields` and the canvas auto-saves when changes occur.
- **Bus Matrix usage counts**: Each dimension label now shows a green badge with the number of currently-visible facts it connects to; each fact column header shows a blue badge with the number of currently-visible dimensions. Counts update as filters change.
- **Bus Matrix sort controls**: Two sort selects let users order dimensions and facts independently by display label (A-Z) or by visible connection count (descending).
- **Bus Matrix full-matrix export**: An "Export full matrix" button downloads `trellis-bus-matrix.xlsx` — a workbook with a `Matrix` sheet (dimensions as rows, facts as columns) and a `Longlist` sheet (every dimension-fact pair with `TRUE`/`FALSE` linked values). Export always uses the complete unfiltered dataset regardless of active UI filters.
- **Entity List type filter**: The Entity List toolbar now has a compact Type filter (Dimension, Fact, Unclassified) with colored chips matching the existing Domain and Tag filter style. Type filters compose with search, domain, and tag filters using AND semantics; multiple selected types use OR logic within the group.
- **Entity List name sort**: A visible A–Z / Z–A sort toggle in the filters toolbar controls entity ordering within every domain group. Clearing filters resets search, domains, tags, and type selection while preserving the chosen sort direction.
- **Entity List group by type**: A "Group by type" checkbox in the filters toolbar adds collapsible Dimensions / Facts / Unclassified sub-headers inside each domain group. Sub-groups are independently collapsible and only appear when the checkbox is enabled.

### Changed

- **Canvas logical view (bound entities)**: The node chip no longer embeds the full schema.yml column editor (“Save to YAML” / per-column CRUD). Use the entity detail modal for materializing new columns and editing column descriptions; the chip lists merged manifest + draft fields with drag-to-link preserved.
- **Bus Matrix strict classification**: The Bus Matrix now includes only entities with `entity_type: dimension` or `entity_type: fact`; `unclassified` entities no longer appear as rows or columns.

### Fixed

- **Schema save from UI**: The client now POSTs to `/api/models/{model}/schema` (matching the API); using PUT returned 405 and broke Materialize / description saves in the browser.
- **Playwright + backend boot**: Test `trellis.yml` and dbt artifacts are prepared when `playwright.config.ts` loads, before `webServer` starts (Playwright starts web servers before `globalSetup`, so the previous order could leave `DATA_MODEL_PATH` unset on first request).
- **Test-mode env overrides**: Under `DATAMODEL_TEST_DIR`, empty-string `DATAMODEL_DATA_MODEL_PATH` / manifest / catalog / canvas env vars are ignored so defaults apply instead of blank paths.
- **Entity detail modal**: Opening the modal no longer re-initializes the whole form on every `currentEntity` reference change (e.g. after manifest refresh), which had cleared the post-materialize SQL-gap banner immediately.

## [0.14.8] - 2026-04-20

### Changed

- **README**: Reworked for end users—benefits and workflows first, optional Kimball and business-events/7W called out last, video walkthroughs linked under `examples/`, configuration summarized with pointers to `trellis.yml.example` and `/config`, development and testing moved to CONTRIBUTING.
- **Branding**: README uses stylized **trellis** (lowercase *t*) for the product name in prose.

### Added

- **CONTRIBUTING**: Expanded with prerequisites, local dev (backend/frontend), `make build-package`, `trellis run` CLI options, and full frontend/backend testing guidance (including Playwright system dependencies on Ubuntu/WSL2).

See commit [`aa8ee6c02d30987a940dba5388bac8f067423858`](https://github.com/timhiebenthal/trellis-datamodel/commit/aa8ee6c02d30987a940dba5388bac8f067423858).

## [0.14.7] - 2026-04-17

### Fixed

- **Config UI: dbt model paths reactivity**: `+ Add Path` and remove (×) now update the `dbt_model_paths` list immediately in the form without requiring a page reload, while preserving saved values after apply.

## [0.14.6] - 2026-04-17

### Fixed

- **Wizard toggle respected**: disabled `entity_creation_guidance.enabled` now properly keeps the Create Entity wizard closed when toggled off. Added regression test confirming the disabled flow works end-to-end.

### Added

- **Config UI: dbt model paths add/remove**: added "+ Add Path" button and remove (×) buttons for `dbt_model_paths` in the config page. Users can now set paths even when the config currently has none.

## [0.14.5] - 2026-04-17

### Fixed

- **Wizard disable toggle coverage**: added an end-to-end canvas regression test that disables `entity_creation_guidance.enabled`, confirms the Create Entity wizard stays closed, and verifies entities are created directly.
- **Guidance deprecation warning copy**: corrected the legacy `guidance` warning so it points users to `entity_creation_guidance.enabled`, matching the config format produced by `trellis init`.

## [0.14.4] - 2026-04-17

### Changed

- **dbt decoupling**: Removed `dbt-duckdb` (and thus `dbt-core`) from optional extras so no Trellis install path pulls in dbt Python packages, avoiding version conflicts with project adapters and `dbt` binary clashes with the dbt Cloud CLI.
- **`[dbt-example]` extra pruned**: The extra name is unchanged, but it no longer pulls in dbt packages; it only includes generator dependencies: `duckdb`, `faker`, `pandas`, `tqdm`.
- **Legacy cleanup**: Dropped unused `marimo` and `nba-api` from that extra.

### Fixed

- **`generate-company-data`**: Removed a misleading error path that suggested installing dbt via the old extra; missing pandas/faker now points at `[dbt-example]`. The generator prints an isolated `uvx`/`dbt-duckdb` build hint (or use a separate venv/pipx).

## [0.14.3] - 2026-04-17

### Added
- **Generate Entities (entity model) — topology in one group**: relationship endpoints from the preview (e.g. Employee, Account) appear under **“From this generation”** together with the derived preview entity, instead of only under “Available in this event”.
- **Create All — stub nodes for relationship endpoints**: when an endpoint is not yet on the canvas, Create All adds a lightweight dimension stub so edges can be created and the filtered canvas shows the full topology.

### Fixed
- **Generate preview dialog**: in-flight preview requests are aborted when the dialog closes; a server timeout avoids an endless spinner; the preview-loading effect no longer retriggered in a tight loop (which could freeze the browser); `loading` resets when the dialog closes.
- **Relationship edge labels**: filler labels that only repeat the target entity’s name or id (as emitted by the generator) are cleared on the canvas; regenerating overwrites stale filler text on existing edges.
## [0.14.2] - 2026-04-15

### Added
- **Create new domain from business events modal**: users can now create new business domains directly from the Create Event modal. Includes a "+" button next to the domain dropdown that reveals an input field for quick add/cancel. Domains are normalized to lowercase on creation.

### Fixed
- **Entity node displays "[object Object]" under Roles**: role-playing dimensions were showing `[object Object]` instead of the actual role name on the canvas. This happened because `Entity.roles` is an array of `EntityRole` objects (`{ role, label, source }`), but the code was treating them as strings.
- **Case-insensitive role deduplication**: duplicate roles with different casing (e.g., "Creation Date", "creation date") are now consolidated into a single role entry, fixing the display of duplicate role badges.

## [0.14.0] - 2026-04-14

### Added
- **Business Events for entity model users**: the `/business-events` route is no longer restricted to `dimensional_model`. Any project with `business_events.enabled: true` can now access the page regardless of modeling style.
- **Entity model generation from business events**: generating entities from an annotated event or process in `entity_model` mode produces a central entity of `entity_type: "entity"`, `drafted_fields` for unlinked annotations, and relationship stubs for annotations linked to an existing entity.
- **Modeling-style-aware UI in Business Events**: entity model users see SVO-focused copy ("Subject Verb Object" framing), no event type selector, no "How Many" section, a `/6` progress badge, and "Link to entity" instead of "Generalize to dimension".
- **`entity` accepted as valid entity type**: saving an entity with `entity_type: "entity"` to `data_model.yml` via the API no longer returns a 400 validation error.
- **Optional event type on create**: `CreateEventRequest.type` is now optional; omitting it defaults to `"discrete"` so existing clients are unaffected.

### Fixed
- **`modelingStyle` store default corrected to `dimensional_model`**: the store was accidentally defaulting to `entity_model`, causing unit tests for `CreateEventModal` and `SevenWsForm` to fail in dimensional mode.

## [0.13.5] - 2026-04-13

### Added
- **`trellis generate-company-data` prompts for output directory**: when no `dbt_company_dummy_path` is set in trellis.yml, the command now prompts for an output directory. If configured, it confirms the path with the user before generating data. Generated CSV files and the dbt project are created in the specified directory.
- **Output directory override**: `generate_data.py` now accepts a positional argument to specify where data goes: `python generate_data.py /path/to/output`. CSV files are written to `<output>/data/`.

### Fixed
- **`trellis generate-company-data` works when installed from PyPI**: the `generate_data.py` script is now bundled in the package, so users don't need the `dbt_company_dummy` project locally. The script is found automatically from the installed package location. Also improved error messages when the script can't be found.
- **Output directory isolation**: running `dbt run` from the generated project now uses `--profiles-dir .` to avoid interfering with the user's dbt configuration. Also added `require-dbt-version: "1.10.0"` to the scaffolded project to warn on version mismatches.
- **CLI dependency documentation**: added `Requires:` note in `--help` output and error message for missing dbt dependency, pointing users to `pip install trellis-datamodel[dbt-example]`.

## [0.13.4] - 2026-04-13

### Fixed
- **Relationship tests not written to dbt schema.yml for unbound entities**: when creating a relationship by dragging one entity's field onto another where at least one entity was not bound to a dbt model, the relationship type always defaulted to `one_to_many`. This caused the backend to write the relationship test to the wrong entity (target instead of source) when the relationship should have been `many_to_one`. The frontend now infers the relationship type from the entity's `entity_type` (fact/dimension) when either entity is unbound — fact → dimension becomes `many_to_one` (FK on source), dimension → fact becomes `one_to_many` (FK on target), matching the dimensional modeling convention.

## [0.13.3] - 2026-04-13

### Fixed
- **Relationship label text visible again**: the label name input in the edge editor was inheriting `color: transparent` from the canvas pane, making typed text invisible (white-on-white). An explicit `text-gray-900` now ensures the text is always readable.
- **Connection handles vs. resize handles disambiguated**: connection handles (top/bottom of entity) now show a teal `mdi:arrow-up` / `mdi:arrow-down` icon on hover with a matching teal background, clearly distinguishing them from the resize handles (right/bottom edge) which keep their existing teal glow. Arrows are invisible at rest and only appear on hover. Left/right connection handles removed — connections are created from the top and bottom edges only. Tooltip updated to "Drag to other entity to create relationship".

## [0.13.2] - 2026-04-13

### Fixed
- **`entity_type` no longer written to `data_model.yml` in entity-modeling mode**: the auto-save service and the Generate Entities dialog save path were unconditionally including `entity_type: "unclassified"` in every entity payload, causing the field to appear in `data_model.yml` even when `modeling_style: entity_model`. Both save paths now only include `entity_type` when `modeling_style` is `dimensional_model`.

## [0.13.1] - 2026-04-08

### Fixed
- **Entity type badge hidden in entity-modeling mode**: the Fact / Dimension / Unclassified badge in `EntityList` rows is no longer shown when the modeling style is `entity_model`. The badge is only visible in `dimensional_model` mode, eliminating the "Unclassified" clutter that appeared next to every entity during entity modeling. Fixes [#72](https://github.com/timhiebenthal/trellis-datamodel/issues/72).

## [0.13.0] - 2026-04-02

### Fixed
- **Entity detail modal — duplicate role rows**: dimensions with multiple `roles` entries sharing the same `role` name (e.g. one per `source` process) now render a single row in the Roles list. Process expansion and counts no longer repeat identical blocks. Edit and delete apply to all entries for that role name so persisted YAML stays consistent.

### Changed
- **Entity detail modal**: dialog title is now `{entity label} Details` instead of a static "Entity Details".
- **Entity detail modal — roles empty state**: replaced the large dashed empty card with a short, low-contrast line of helper text; refined tooltip and add-role placeholder copy for role-playing dimensions.

## [0.12.0] - 2026-04-02

### Added
- **Attribute origin field**: drafted entity attributes now support an optional `origin` field for recording technical source lineage (e.g. `source_system.schema.table.column`) separately from the human-readable description.
  - New `origin?: string` property on `DraftedField`; persisted to and loaded from `data_model.yml` transparently — no backend changes required.
  - Editable `Origin` column added to the attribute table in `EntityDetailModal`; read-only `Origin` column shown for dbt-bound entities.
  - `origin` included as a 4th column in both Excel exports (entity and full data model) and Markdown copy.
  - `dbt_demo/data_model.yml` migrated: all inline `description | DH1: …` / `description | DAX: …` / `description | source: TBD` / `description | MS Dynamics …` patterns split into separate `description` and `origin` fields.
- **Full data model Excel export**: new "Export Data Model" button in the Entity List toolbar downloads a single `.xlsx` workbook covering the entire data model.
  - **Overview sheet** (first tab): export date, entity counts broken down by fact / dimension / unclassified, relationship count, a one-line structural explanation, an entity directory table (Name | Type | Description | Domains | Tags), and a full relationships table (From | To | Label | Type).
  - **Per-entity attribute sheets**: one tab per entity showing its drafted fields (Name | Type | Description | Origin); falls back to "No attributes defined" for entities without fields.
  - Sheet names are sanitised (Excel-forbidden characters removed, truncated to 31 chars) and deduplicated with `_2`, `_3` suffixes on collision.
  - Filename pattern: `DataModel_export_YYYYMMDD.xlsx`.

## [0.11.3] - 2026-04-01

Stable release incorporating dbt relationship test fixes and Generate Entities drafted-field preservation from 0.11.2b2 and 0.11.3b1.

### Fixed
- **Preserve manually drafted fields on entity re-generation**: when re-applying entities from the Generate Entities dialog for a fact that already exists on the canvas, manually added `drafted_fields` are no longer overwritten. Generated fields are merged in (by field name), so only net-new fields from the generator are appended while user-defined columns are retained.
- **dbt relationship tests for non-`one_to_many` relationships**: `save_dbt_schema` (POST `/api/dbt-schema`) now resolves which entity holds the foreign key for `many_to_one`, `one_to_one`, and other relationship types the same way as the full schema sync path. Relationship tests are written on the correct FK column instead of being skipped when the link was not modeled as `one_to_many`.

## [0.11.1] - 2026-04-01

### Fixed
- **dbt package conflicts**: removed `dbt-core`, `dbt-duckdb`, and `dbt-colibri` from hard dependencies. trellis only reads dbt artifacts (manifest.json, catalog.json, schema YAMLs) and never imports dbt as a Python package, so requiring a specific dbt version conflicted with users who have their own dbt adapter installed (e.g. dbt-postgres, dbt-snowflake, or the new dbt CLI). Users manage their own dbt installation; `dbt-colibri` is now an optional extra (`pip install trellis-datamodel[colibri]`) and `dbt-duckdb` remains available via the `[dbt-example]` extra for the bundled sample project.

## [0.10.1] - 2026-03-10

Stable release incorporating role-playing dimension fixes and description propagation from 0.10.1b1–b4.

### Fixed
- **Role-playing dimension entity generator**: when an annotation has `dimension_id: dim__employee` but `dim__employee` does not yet exist in `data_model.yml`, the entity generator now creates an entity with `id: dim__employee` (derived from the `dimension_id` value) instead of `id: dim__sales_agent` (derived from the annotation text). The linkage is no longer silently lost on first generation.
- Role context is now stored on the base entity as structured objects `{label, role, source}` in `data_model.yml` rather than being discarded. Roles accumulate across generation runs without duplicating (deduped by `(label, source)`).
