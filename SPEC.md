# Apache Ossie Export - Specification

## Overview

Add an exporter that writes one Apache Ossie semantic model document (`0.2.0.dev0`, flat root) from the entities bound in `data_model.yml`, and wire it into the existing "Push to dbt / Push to Bruin" flow.

Ossie (formerly Open Semantic Interchange, Apache Incubator since June 2026) is the vendor-neutral semantic-layer format backed by Snowflake, Databricks, Salesforce, and dbt Labs. Trellis already holds nearly everything an Ossie document needs: physical table bindings, columns with logical types, entity-to-entity foreign keys, and descriptions. Exporting that turns a Trellis project into a portable semantic model that any Ossie-compatible consumer can read, regardless of whether the underlying transformation framework is dbt or Bruin.

The spec is a draft and will change. The exporter is therefore built as a single isolated module with one pinned version constant, so a spec bump is a localized change.

## Requirements

### Functional Requirements

1. **Emit a flat `0.2.0.dev0` document.** One YAML file, root keys `version`, `name`, `datasets`, `relationships`, `metrics`. No `semantic_model:` array wrapper: the `0.2.0.dev0` schema rejects it, and `spec.md` records its removal as an intentional breaking change.

2. **Validate against the official schema.** Output must validate against `apache/ossie`'s `core-spec/ossie-schema.json` for `0.2.0.dev0`.

3. **Config block** in `trellis.yml`, nested like `business_events`:

   ```yaml
   ossie:
     enabled: false
     file: ""            # default: semantic_model.yml beside data_model.yml
     source:
       database: ""      # empty: omit the database segment
       schema: ""        # empty: use the schema the adapter reports
   ```

4. **Trigger through the existing push flow.** When `ossie.enabled` is true, `POST /api/sync-tests` writes the framework schema files and then writes the Ossie file. `SyncTestsResponse.files` includes the Ossie path; a new optional `warnings` field carries skipped-entity and skipped-relationship messages.

5. **Bound entities only.** A dataset is emitted only for an entity whose `model_ref` resolves to a model the active adapter returns. Draft entities are excluded. With zero resolvable bound entities, no file is written and the response says why.

6. **Dataset mapping.** For each resolvable bound entity:

   | Ossie key | Source |
   |---|---|
   | `name` | the bound model's short name (`dim_customer`) |
   | `source` | non-empty parts joined from `ossie.source.database`, `ossie.source.schema`, the model's schema, the model's table |
   | `description` | the entity's description, omitted when empty |
   | `primary_key` | see rule 8 |
   | `unique_keys` | see rule 8 |
   | `fields` | see rule 7 |

7. **Field mapping.** Fields are the bound model's columns in their existing order, then any entity `drafted_fields` whose name is not already present, sorted by name. Each field carries `name`, `expression.dialects: [{dialect: ANSI_SQL, expression: <column name>}]`, `datatype` where a portable equivalent exists, `dimension.is_time` for temporal types, and `description` when non-empty. Blank draft field names are skipped.

   SQL type to Ossie `DataType`:

   | SQL spellings | Ossie `DataType` | `is_time` |
   |---|---|---|
   | `varchar`, `char`, `text`, `string` | `String` | false |
   | `integer`, `int`, `bigint`, `smallint` | `Integer` | false |
   | `decimal`, `numeric`, `number` | `Decimal` | false |
   | `float`, `double`, `real` | `Float` | false |
   | `boolean`, `bool` | `Boolean` | false |
   | `date` | `Date` | true |
   | `time` | `Time` | true |
   | `timestamp`, `datetime`, `timestamp_ntz` | `DateTime` | true |
   | `timestamp_tz`, `timestamptz`, `timestamp_ltz` | `DateTimeTz` | true |
   | anything else, or absent | omitted | false |

8. **Key inference, without inventing composite keys.** Candidates come from framework metadata: Bruin `primary_key: true` columns, and dbt columns carrying both a `unique` and a `not_null` test. A single candidate becomes `primary_key: [<field>]`. Two or more independent candidates become `unique_keys: [[a], [b]]` with no `primary_key`, because a multi-element `primary_key` in Ossie means one composite key. When metadata yields nothing, the `to_columns` field of a relationship pointing at the entity is used as a single candidate. When nothing is available, both keys are omitted.

9. **Relationship mapping.** For each relationship in `data_model.yml`:

   - Orientation comes from `services/fk_placement.place_foreign_key`: `from` is the many side holding the foreign key, `to` is the one side holding the referenced key. `from_columns` and `to_columns` each hold one field name, since Trellis relationships are single-field.
   - Skip when either endpoint entity is a draft entity, either endpoint's model does not resolve, or `source_field`/`target_field` is missing.
   - Skip when the referenced field name is absent from the target dataset's fields.
   - Deduplicate identical `(from, to, from_columns, to_columns)` tuples.
   - Name each relationship `<from>_to_<to>`. On a name collision, append `_<from_column>`; if still colliding, append a numeric suffix.

10. **`metrics: []` at the root.** The key ships empty. `apache/ossie`'s schema places no `minItems` on `metrics`, so an empty array validates, and the key is present for the later metric-authoring slice. Datasets omit the `metrics` key entirely.

11. **Root `name` is derived, never configured.** dbt: `manifest.metadata.project_name`. Bruin: `pipeline.yml` `name`. Fallback: the data model file stem.

12. **Deterministic output.** Datasets sorted by name, relationships sorted by `(from, to, from_columns)`, field order as specified in rule 7. Re-running an unchanged model produces a byte-identical file.

13. **Config UI exposure.** `ossie.enabled`, `ossie.file`, `ossie.source.database`, and `ossie.source.schema` are editable on the Config page under the existing beta section.

### Non-Functional Requirements

- **No new runtime dependency.** Validation runs in tests against a vendored copy of the official schema, using `jsonschema` as a dev dependency only.
- **Atomic write.** Temp file plus `os.replace`, reusing the pattern in `utils/yaml_handler.py`.
- **No behaviour change when disabled.** With `ossie.enabled: false`, the push flow is byte-for-byte what it is today.
- **Failures are explicit.** If the framework push succeeds and the Ossie write fails, the error names both outcomes rather than reporting a bare failure.
- **Framework neutrality.** No framework name comparison inside the exporter. Adapter differences arrive through the adapter interface.
- **Existing tests unchanged.** Nothing in the dbt-core or Bruin adapter suites changes except the protocol-surface test noted below.

## Scope

### In Scope

- `trellis_datamodel/services/ossie.py` - the exporter
- `trellis_datamodel/config.py` - `OssieConfig` dataclass, path resolution, `load_config` wiring
- `trellis_datamodel/models/schemas.py` - `OssieConfig` pydantic model on `ConfigSchema`, plus the `warnings` field on `SyncTestsResponse`
- `trellis_datamodel/services/config_service.py` - field definitions and beta flags
- `trellis_datamodel/services/schema.py` - call the exporter from `sync_framework_tests`
- `trellis_datamodel/adapters/base.py` - `project_name` on `ProjectStatus`
- `trellis_datamodel/adapters/dbt_core.py`, `trellis_datamodel/adapters/bruin.py` - populate `project_name`
- `trellis_datamodel/tests/test_ossie_export.py` - mapping, key inference, relationship filtering, golden documents
- `trellis_datamodel/tests/fixtures/ossie/ossie-schema.json` - vendored official schema
- `.cursor/commands`-adjacent docs: `trellis.yml.example` Ossie block with the dev-target caveat
- `CHANGELOG.md` entry under `[Unreleased]`

### Out of Scope

- Metric authoring in Trellis, and populating `metrics`
- `trellis export ossie` CLI command
- Writing Ossie content into dbt or Bruin files, or any `custom_extensions` block
- Tracking Ossie files in `data_model.yml` for cleanup when an entity is deleted
- `additional_models` on an entity: only the primary `model_ref` becomes a dataset
- Conceptual Grain and a user-selectable primary key as first-class Trellis fields
- Composite relationships (Trellis stores single-field relationships only)
- Field-level `origin`, `ai_context.synonyms`, `label`, and `examples` mapping
- Round-tripping: reading an Ossie file back into Trellis
- Version negotiation: `0.2.0.dev0` is pinned

## Approach

### Technical Approach

**Exporter shape.** `services/ossie.py` exposes one entry point:

```python
def export_ossie(entities, relationships, project_name) -> Path
```

It builds a plain dict, then writes it atomically with the existing ruamel YAML handler for consistent formatting. Plain `dict` output rather than ruamel `CommentedMap`, because the file is generated and never hand-edited in place.

**Resolving bound models.** The exporter receives the adapter's model list once and indexes it by `unique_id`. Entity `model_ref` values are dbt `unique_id`s (`model.company_dummy.dim_customer`) or Bruin asset names (`core.dim__customer`), so a single index lookup covers both. An entity whose `model_ref` is absent from that index is skipped with a warning naming the entity and the missing model. Note that `dbt_model_paths` / `bruin_asset_paths` filtering shapes `get_models()`, so it therefore shapes the export; the warning text says so.

**Project name.** `ProjectStatus` gains a `project_name: str` field. The dbt adapter reads `manifest.metadata.project_name`; the Bruin adapter reads `name` from `pipeline.yml`, falling back to the pipeline directory name. `ProjectStatus` is already the framework-neutral identity object, and reading framework artifacts inside the exporter would leak framework knowledge into a service. `tests/test_adapter_protocol_surface.py` and the API contract snapshot need updating for the new field.

**Config plumbing.** `OssieConfig` dataclass (`enabled`, `file`, `database`, `schema`) follows the existing per-block pattern: a `_resolve_ossie_file_path` helper resolving `ossie.file` with the same base-directory rules as `data_model_file`, defaulting to `semantic_model.yml` beside the resolved `DATA_MODEL_PATH`. The pydantic equivalent goes on `ConfigSchema`, and four entries plus four beta flags go into `_FIELD_DEFINITIONS`.

**Push integration.** `sync_framework_tests` writes framework files first, persists pushed tags, then calls the exporter when `cfg.OSSIE_ENABLED` is set. Warnings are collected and returned. Wrapping order matters for the failure message: an Ossie failure after a successful framework push reports that the framework files were updated.

**Validation.** Tests load the vendored `ossie-schema.json` with `jsonschema.Draft202012Validator` and assert the emitted document passes, plus a negative test asserting a deliberately broken document fails, so a stale vendored schema cannot silently pass everything.

**Test coverage.** Unit tests for the type map, key inference (single candidate, multiple candidates, relationship fallback, nothing), relationship orientation across all `place_foreign_key` types, filtering of draft endpoints and missing fields, and deduplication. Golden-file tests for the dbt dummy project and for the Bruin fixture pipeline. An end-to-end API test asserting `ossie.enabled: false` leaves the response and filesystem untouched.

### User Experience

No new button. With `ossie.enabled: true`, the existing Push button does both jobs and its status message reports how many files changed. The Config page gains an Ossie group under beta features, with the `database` and `schema` fields carrying a hint that adapter-derived values reflect the target that last ran dbt.

## Dependencies

- `apache/ossie` `core-spec/ossie-schema.json` at `0.2.0.dev0`, vendored under tests
- `jsonschema` as a dev dependency
- Existing: `ruamel.yaml`, FastAPI, pydantic
- Existing structures: `services/fk_placement.place_foreign_key`, `TransformationAdapter.get_models`, `ProjectStatus`, `utils/yaml_handler.YamlHandler`

## Success Criteria

1. With `ossie.enabled: true` and the dbt dummy project, one push writes `semantic_model.yml` that validates against the vendored `0.2.0.dev0` schema.
2. Every dataset corresponds to a bound entity, and no draft entity appears in the file.
3. Every relationship has `from` on the many side; no relationship references an unbound dataset or a field absent from the target dataset.
4. `metrics: []` is present; no dataset carries a `metrics` key.
5. Setting `ossie.source.database` changes every `source` to three-part form without touching anything else.
6. Running the same push twice produces an identical file.
7. With `ossie.enabled: false`, no file appears and the existing test suite passes unchanged.
8. The Bruin fixture pipeline exports with `schema.table` sources and the pipeline name at the root.
9. `uv run pytest` and `npm run check` pass.

## Notes

**Decisions worth remembering.** Three choices here are hard to reverse and non-obvious without this context:

- **Targeting an unreleased draft instead of stable `0.1.1`.** `0.2.0.dev0` is the direction `apache/ossie` is moving, and it dropped the `semantic_model:` array in favour of a flat root. Building against `0.1.1` would mean a rewrite at the next release. The cost is churn while the draft settles, contained by pinning the version in one constant and vendoring the schema.
- **No `semglot` runtime dependency.** `benchouse/semglot` transpiles semantic layers through a neutral IR and reads Ossie as a source dialect, but it is a Go binary. Trellis ships as a Python wheel, so the emitter is written natively and `semglot` stays a downstream consumer of the output rather than a dependency.
- **`manifest.json` is not authoritative for physical addresses.** Both `database` and `schema` in a dbt manifest reflect the target of the last run, so a developer's dev database and per-user schema would land in a committed file. They are therefore config overrides with adapter values only as fallback, and no `database` segment is emitted by default.

**Known gaps.** Ossie's `datatype` vocabulary is logical while dbt reports warehouse types, so unusual types fall through to "omitted" rather than being guessed. Trellis has no composite relationship concept, so `from_columns` and `to_columns` are always single-element in this version.

**Spec churn.** The vendored schema carries the upstream draft warning. When `0.2.0` ships, diff the vendored file, adjust the mapping table, and bump the version constant. The golden files make that diff visible in review.
