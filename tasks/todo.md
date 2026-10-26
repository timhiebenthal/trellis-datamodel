# Apache Ossie Export - Tasks

Plan: `tasks/plan.md`. Spec: `SPEC.md`.

Rules for every task: no production code without a failing test first; no completion claim without running the verification command and showing its output. Check the box only when the task is fully functional, never when a stub remains.

---

## Task 1: `project_name` on `ProjectStatus`

**Description:** Add `project_name: str` to the `ProjectStatus` TypedDict and populate it in both adapters, so the exporter can name the Ossie document without reading framework artifacts itself. The dbt adapter reads `manifest.metadata.project_name`; the Bruin adapter reads `name` from `pipeline.yml` in the pipeline directory and falls back to the pipeline directory name. `FakeAdapter` returns `"fake"`.

**Acceptance criteria:**
- [x] `ProjectStatus` declares `project_name`, documented as the framework's own project or pipeline identity
- [x] `DbtCoreAdapter.get_project_status()` returns `"company_dummy"` against `dbt_company_dummy/target/manifest.json`
- [x] `DbtCoreAdapter` returns `""` when the manifest is missing, alongside its existing error rather than raising
- [x] `BruinAdapter.get_project_status()` returns `"trellis_test_pipeline"` against `tests/fixtures/bruin_pipeline`
- [x] `BruinAdapter` falls back to the pipeline directory basename when `pipeline.yml` has no `name`
- [x] `FakeAdapter.get_project_status()` returns `"fake"`
- [x] `/api/config-status` and `/api/config-info` response shapes are unchanged: both enumerate keys explicitly and neither gains `project_name`

**Verification:**
- [x] `uv run pytest trellis_datamodel/tests/test_adapter_protocol_surface.py trellis_datamodel/tests/test_dbt_adapter_surface.py trellis_datamodel/tests/test_bruin_adapter.py -q` passes
- [x] `uv run pytest trellis_datamodel/tests/test_manifest.py trellis_datamodel/tests/test_config_api.py -q` passes, proving the two status routes ignore the new field

**Dependencies:** None

**Files likely touched:**
- `trellis_datamodel/adapters/base.py`
- `trellis_datamodel/adapters/dbt_core.py`
- `trellis_datamodel/adapters/bruin.py`
- `trellis_datamodel/tests/conftest.py`
- `trellis_datamodel/tests/test_dbt_adapter_surface.py`
- `trellis_datamodel/tests/test_bruin_adapter.py`

**Estimated scope:** Medium (6 files)

---

## Task 2: `OssieConfig` backend plumbing

**Description:** Add an `OssieConfig` dataclass beside the existing per-block configs in `config.py`, resolve its file path, publish module-level globals, and wire it into `load_config` and the test-mode branch. Default file is `semantic_model.yml` in the directory of the resolved `DATA_MODEL_PATH`; an explicit `ossie.file` resolves with the same base-directory rules as `data_model_file`.

**Acceptance criteria:**
- [x] `OssieConfig` carries `enabled: bool = False`, `file: str = ""`, `database: str = ""`, `schema: str = ""`
- [x] Module globals `OSSIE_CONFIG` (or equivalent) exist in both the `_TEST_DIR` and production branches of `config.py`
- [x] `load_config` populates it, and `reload_config` picks up a changed value without a restart
- [x] With `ossie.file: ""`, the resolved path is `<dirname(DATA_MODEL_PATH)>/semantic_model.yml`
- [x] With `ossie.file: "docs/semantic.yml"`, the path resolves relative to `dbt_project_path` when set, else to the config file directory
- [x] A non-dict `ossie:` value logs a warning and falls back to defaults rather than raising, matching how `lineage` is handled

**Verification:**
- [x] `uv run pytest trellis_datamodel/tests/test_config.py -q` passes
- [x] A new test asserts the three path cases above and the malformed-block fallback

**Dependencies:** None

**Files likely touched:**
- `trellis_datamodel/config.py`
- `trellis_datamodel/tests/test_config.py`

**Estimated scope:** Small (2 files)

---

## Task 3: Ossie config on the API surface

**Description:** Expose the Ossie block through `/api/config` so the Config page can render it: pydantic model on `ConfigSchema`, field metadata entries, beta flags, and a normalization branch so a `PUT` persists the nested `source` block instead of dropping it. Add a commented block to `trellis.yml.example`.

**Acceptance criteria:**
- [x] `ConfigSchema` gains `ossie: OssieConfig` with `enabled`, `file`, `database`, `schema` nested under `source`
- [x] `_FIELD_DEFINITIONS` describes `ossie.enabled`, `ossie.file`, `ossie.source.database`, `ossie.source.schema`, each `beta=True`
- [x] The `ossie.source.database` description states that adapter-derived values reflect the target that last ran dbt, so the field exists to override them
- [x] `_BETA_FIELDS` lists all four paths, and `GET /api/config` reports them in `beta_flags`
- [x] `_normalize_nested_config` has an `ossie` branch preserving `enabled`, `file`, and the nested `source.database` / `source.schema` strings
- [x] A `PUT` followed by a `GET` round-trips the nested block without losing `source`
- [x] `trellis.yml.example` documents the block, including the default filename and the dev-target caveat

**Verification:**
- [x] `uv run pytest trellis_datamodel/tests/test_config_api.py -q` passes
- [x] New tests cover the round-trip and the beta listing
- [ ] `curl -s localhost:8089/api/config | python3 -m json.tool` shows the block (manual, after `make backend`)

**Dependencies:** Task 2

**Files likely touched:**
- `trellis_datamodel/models/schemas.py`
- `trellis_datamodel/services/config_service.py`
- `trellis.yml.example`
- `trellis_datamodel/tests/test_config_api.py`

**Estimated scope:** Medium (4 files)

---

## Checkpoint A: Foundation

- [x] `uv run pytest trellis_datamodel/tests/test_adapter_protocol_surface.py trellis_datamodel/tests/test_config.py trellis_datamodel/tests/test_config_api.py -q` passes
- [x] `uv run pytest -q` passes
- [x] `GET /api/config` returns the `ossie` block and lists `ossie.enabled` in `beta_flags`

---

## Task 4: Datasets and fields from bound entities

**Description:** Create `services/ossie.py` with the pinned version constant, the type map, and the dataset/field builders, and wire the atomic write through `YamlHandler.save_file`. Resolve bound models through the adapter's model list indexed by `unique_id`. Return a small `OssieExport` dataclass carrying `path` and `warnings`, because the push integration needs to surface skipped entities. Vendor the official schema into the test fixtures and validate against it in both directions.

**Acceptance criteria:**
- [x] `export_ossie(entities, relationships, project_name, models) -> OssieExport` writes one file and returns its path plus accumulated warnings
- [x] The document has `version: 0.2.0.dev0`, the passed `name`, `datasets`, `relationships`, and `metrics: []`
- [x] No dataset carries a `metrics` key
- [x] Only entities with a resolvable `model_ref` become datasets; a draft entity or an unresolvable ref is skipped and produces a warning naming the entity and the missing model
- [x] `source` joins non-empty parts from `ossie.source.database`, `ossie.source.schema`, the model's schema, and the model's table; with no database configured the result is `main.dim_customer`
- [x] Fields are the model's columns in order, then drafted-only fields sorted by name, deduplicated by name with the model winning; blank draft names skipped
- [x] `datatype` follows the spec's type table; an unmappable type omits the key rather than emitting `Opaque`
- [x] `dimension.is_time` is `true` exactly for `Date`, `Time`, `DateTime`, `DateTimeTz`
- [x] Each field's `expression.dialects` holds one `ANSI_SQL` entry whose expression is the column name
- [x] Empty descriptions are omitted rather than emitted as `""`
- [x] Datasets and fields come out in the deterministic order the plan specifies, and a second run over the same input is byte-identical
- [x] The write is atomic: no partial file survives a simulated dump failure
- [x] `tests/fixtures/ossie/ossie-schema.json` is the vendored `0.2.0.dev0` schema, and a negative test proves the validator rejects a deliberately broken document

**Verification:**
- [x] `uv run pytest trellis_datamodel/tests/test_ossie_export.py -q` passes
- [x] The dbt-shaped golden document validates, and so does the Bruin fixture document
- [x] `uv run pytest -q` passes

**Note:** the dbt case is a hand-built dbt-shaped model list, not a run against `dbt_company_dummy/target/manifest.json`: that artifact is gitignored (`dbt_company_dummy/.gitignore`), so a test depending on it would vanish in CI. The Bruin case does drive the real committed fixture pipeline through `BruinAdapter.get_models()`.

**Dependencies:** Task 1

**Files likely touched:**
- `trellis_datamodel/services/ossie.py`
- `trellis_datamodel/tests/fixtures/ossie/ossie-schema.json`
- `trellis_datamodel/tests/test_ossie_export.py`
- `pyproject.toml` (`uv add --dev jsonschema`)

**Estimated scope:** Medium (4 files)

---

## Task 5: Primary key and unique key inference

**Description:** Fill `primary_key` and `unique_keys` on each dataset from framework metadata, without ever producing an accidental composite key.

**Acceptance criteria:**
- [x] Candidates come from Bruin columns with `primary_key: true` and from dbt columns carrying both a `unique` and a `not_null` test
- [x] Exactly one candidate yields `primary_key: [<field>]` and no `unique_keys`
- [x] Two or more candidates yield `unique_keys: [[a], [b]]` and no `primary_key`
- [x] With no metadata candidate, the `to_columns` field of a relationship pointing at the dataset is used as a single candidate
- [x] With nothing available, both keys are omitted
- [x] A candidate naming a field that is not in the dataset's fields is dropped rather than emitted
- [x] The Bruin fixture's `dim__customer` gets `primary_key: ["customer_id"]` from its asset header

**Verification:**
- [x] `uv run pytest trellis_datamodel/tests/test_ossie_export.py -q -k key` passes
- [x] The golden documents still validate

**Note:** key metadata is not on `ModelInfo.columns`, so `export_ossie` gained an optional `model_schemas` argument keyed by `unique_id`. Task 7 supplies it from `adapter.get_model_schema`, keeping adapter I/O out of the exporter. The dbt-dummy acceptance line was exercised through a dbt-shaped schema fixture plus the real Bruin fixture, because the dummy manifest is gitignored.

**Dependencies:** Task 4

**Files likely touched:**
- `trellis_datamodel/services/ossie.py`
- `trellis_datamodel/tests/test_ossie_export.py`

**Estimated scope:** Small (2 files)

---

## Task 6: Relationships with orientation, filtering, and naming

**Description:** Emit `relationships[]` with `from` on the many side, orienting each entry through `services/fk_placement.place_foreign_key` so the rule stays in one place, and filter out everything Ossie would reject.

**Acceptance criteria:**
- [ ] Orientation delegates to `place_foreign_key`, with a test per relationship type in `_FK_ON_SOURCE` and `_FK_ON_TARGET`
- [ ] `from_columns` and `to_columns` each hold exactly one field name
- [ ] A relationship is skipped when either endpoint is a draft entity, either `model_ref` fails to resolve, either `source_field`/`target_field` is missing, or the referenced field is absent from the target dataset's fields
- [ ] Each skip produces a warning naming the entities and the reason
- [ ] Identical `(from, to, from_columns, to_columns)` tuples collapse to one entry
- [ ] Names are `<from>_to_<to>`; a collision appends `_<from_column>`, and a surviving collision appends a numeric suffix
- [ ] Entries are sorted by `(from, to, from_columns)` for stable output
- [ ] The dbt dummy's duplicated `product -> sale` pair yields one relationship, and its `procurement` links yield none

**Verification:**
- [ ] `uv run pytest trellis_datamodel/tests/test_ossie_export.py -q -k relationship` passes
- [ ] The golden documents still validate

**Dependencies:** Task 4

**Files likely touched:**
- `trellis_datamodel/services/ossie.py`
- `trellis_datamodel/tests/test_ossie_export.py`

**Estimated scope:** Small (2 files)

---

## Checkpoint B: Exporter

- [ ] `uv run pytest trellis_datamodel/tests/test_ossie_export.py -q` passes
- [ ] dbt dummy output validates against the vendored schema; Bruin fixture output validates too
- [ ] Neither output contains a draft entity, and neither contains a relationship to one
- [ ] Re-running the exporter on unchanged input produces identical bytes (`cmp` on two runs)

---

## Task 7: Push integration and response warnings

**Description:** Call the exporter from `sync_framework_tests` when `ossie.enabled` is set, after framework files are written and pushed tags are persisted, and surface the result through `/api/sync-tests`.

**Acceptance criteria:**
- [ ] With `ossie.enabled: true`, one `POST /api/sync-tests` writes the framework schema files and `semantic_model.yml`
- [ ] With `ossie.enabled: false`, no file is created and the previous file is left untouched
- [ ] With zero resolvable bound entities, no file is written and `message` says why
- [ ] `SyncTestsResponse` gains `warnings: List[str] = []`, populated from the exporter
- [ ] `files` includes the Ossie path, and `message` names the written file
- [ ] If the framework push succeeds and the Ossie write fails, the raised error states that the framework files were updated and the Ossie file was not
- [ ] Framework-file writing and tag persistence are unchanged when Ossie is disabled, proven by the existing `test_dbt_schema.py` and `test_bruin_push.py` suites passing untouched

**Verification:**
- [ ] `uv run pytest trellis_datamodel/tests/test_ossie_export.py -q -k push` passes
- [ ] `uv run pytest trellis_datamodel/tests/test_dbt_schema.py trellis_datamodel/tests/test_bruin_push.py -q` passes
- [ ] Manual: `make preview PROJECT=dbt_company_dummy` then press Push; the file appears beside `data_model.yml`

**Dependencies:** Tasks 4, 5, 6

**Files likely touched:**
- `trellis_datamodel/services/schema.py`
- `trellis_datamodel/models/schemas.py`
- `trellis_datamodel/routes/schema.py`
- `trellis_datamodel/tests/test_ossie_export.py`

**Estimated scope:** Medium (4 files)

---

## Task 8: Ossie section on the Config page

**Description:** Add an Ossie group to the Config page under beta features, following the `business_events` block markup: an enable toggle, a file path input, and the two address overrides. The existing `handleNestedFieldChange` and `getFieldValue` helpers already split on `.`, so the three-part path `ossie.source.database` needs no helper change.

**Acceptance criteria:**
- [ ] A beta-flagged Ossie section renders `enabled` as a toggle and `file`, `source.database`, `source.schema` as text inputs with their schema descriptions
- [ ] The `file` input shows the placeholder `semantic_model.yml (defaults to same directory as data_model.yml)`
- [ ] The `source.database` hint states that leaving it empty omits the database segment and that adapter values reflect the last dbt run's target
- [ ] Editing any field marks the form dirty, saves through `PUT /api/config`, and survives a reload with the values intact
- [ ] Disabling the toggle leaves the rest of the section visible but does not clear saved values
- [ ] No TypeScript errors and no unused imports

**Verification:**
- [ ] `cd frontend && npm run check` passes
- [ ] `cd frontend && npm run test:smoke` passes
- [ ] Manual: `make dev`, open Config, set `database: ANALYTICS`, save, reload, confirm it persisted and that a following Push writes three-part sources

**Dependencies:** Task 3

**Files likely touched:**
- `frontend/src/routes/(app)/config/+page.svelte`
- `frontend/src/lib/types.ts` (only if the config type needs the `ossie` block declared)

**Estimated scope:** Medium (2 files)

---

## Checkpoint C: Wiring

- [ ] `uv run pytest -q` passes
- [ ] `cd frontend && npm run check && npm run test:smoke` passes
- [ ] One push with Ossie enabled writes both framework files and the semantic model; one push with it disabled writes only framework files
- [ ] The Config page round-trips the Ossie block

---

## Task 9: End-to-end test, changelog, and docs

**Description:** Close the loop with a test that exercises the real HTTP path against the dbt dummy project, and record the feature where users will look for it.

**Acceptance criteria:**
- [ ] `tests/test_ossie_e2e.py` drives `POST /api/sync-tests` through `test_client` with `ossie.enabled: true`, then asserts the written file validates against the vendored schema and contains the expected dataset and relationship counts
- [ ] The same test asserts that toggling `ossie.enabled: false` and pushing again leaves the file untouched (mtime unchanged)
- [ ] `CHANGELOG.md` has an `[Unreleased]` entry naming the feature, the config block, and the fact that only bound entities are exported
- [ ] `README.md` documents the toggle and the default output filename
- [ ] The spec's `Success Criteria` list is checked against the test suite, with any criterion that only has a manual check noted in the PR body

**Verification:**
- [ ] `uv run pytest trellis_datamodel/tests/test_ossie_e2e.py -q` passes
- [ ] `uv run pytest -q` passes
- [ ] `cd frontend && npm run test:smoke` passes

**Dependencies:** Tasks 7, 8

**Files likely touched:**
- `trellis_datamodel/tests/test_ossie_e2e.py`
- `CHANGELOG.md`
- `README.md`

**Estimated scope:** Small (3 files)

---

## Checkpoint D: Complete

- [ ] `uv run pytest -q` passes
- [ ] `cd frontend && npm run check && npm run test:smoke` passes
- [ ] Every task box above is checked, with no stubs or deferred detail
- [ ] Every spec success criterion is either covered by a test or recorded as a manual check
