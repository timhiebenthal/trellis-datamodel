# Implementation Plan: Apache Ossie Export

## Overview

Write one Apache Ossie `0.2.0.dev0` semantic model document from the entities bound in `data_model.yml`, triggered from the existing Push button when `ossie.enabled` is set. The exporter lives in a single service module with a pinned version constant, so a spec bump stays a localized change. Spec: `SPEC.md`.

## Architecture Decisions

1. **Flat `0.2.0.dev0` root, validated against the official schema.** No `semantic_model:` array wrapper; `apache/ossie`'s `0.2.0.dev0` schema rejects it and `spec.md` records the removal as intentional.

2. **`project_name` joins `ProjectStatus`.** The document's root `name` is framework identity, and `ProjectStatus` is already the framework-neutral identity object. Reading `manifest.json` or `pipeline.yml` inside the exporter would put framework knowledge in a service. Cost: one protocol field plus its surface test and the test fake.

3. **Physical address comes from config, not the manifest.** dbt's `database` and `schema` both reflect the target of the last run, so trusting them writes a developer's dev database into a committed file. `ossie.source.database` and `ossie.source.schema` are overrides; adapter values fill only the gaps, and `database` is omitted by default.

4. **One exporter module, plain dicts, atomic write.** `services/ossie.py` builds a `dict` and hands it to `YamlHandler.save_file` (ruamel for formatting, temp file plus `os.replace` for atomicity). No `CommentedMap`, because the file is generated and never edited in place.

5. **`jsonschema` is a dev dependency.** The official schema is vendored under `tests/fixtures/ossie/`, and tests validate against it in both directions so a stale vendor copy cannot silently pass everything. Runtime gains no dependency.

6. **`ANSI_SQL` for field expressions.** Ossie's `OSSIE_SQL_2026` is the normative dialect, but every column reference is valid in both and `ANSI_SQL` is what Ossie's own examples and fixtures use. One constant in the module makes a later switch a one-line change.

7. **Key inference never invents a composite key.** Multiple independent candidates become `unique_keys: [[a], [b]]`, because a multi-element `primary_key` means one composite key.

8. **Ordered output.** Datasets sorted by name, relationships by `(from, to, from_columns)`, fields in model column order then drafted-only fields sorted by name. Re-pushes produce identical bytes, so review diffs stay meaningful.

## Dependency Graph

```
T1 project_name on ProjectStatus ──────────────┐
                                               ├──▶ T4 exporter core ──▶ T5 key inference ──▶ T6 relationships
T2 OssieConfig backend ──▶ T3 config API surface ┘                                              │
                                                                                                ▼
                                                                          T7 push integration + warnings
                                                                                                │
T3 ──────────────────────────────────────────────────────────▶ T8 config page section           │
                                                                                                ▼
                                                                                        T9 end-to-end + docs
```

T1 and the T2/T3 pair touch disjoint files (adapters vs config) and can run in parallel. T4, T5, and T6 all edit `services/ossie.py`, so they are strictly sequential: one file, one worker.

## Task List

### Phase 1: Foundation

- [x] T1 - `project_name` on `ProjectStatus` (S, 5 files) - deps: none
- [x] T2 - `OssieConfig` backend plumbing (S, 3 files) - deps: none
- [x] T3 - Ossie config on the API surface (M, 5 files) - deps: T2

#### Checkpoint A: Foundation
- [x] `uv run pytest trellis_datamodel/tests/test_adapter_protocol_surface.py trellis_datamodel/tests/test_config.py trellis_datamodel/tests/test_config_api.py -q` passes
- [x] `uv run pytest -q` passes
- [x] `GET /api/config` returns an `ossie` block with four fields and `ossie.enabled` listed in `beta_flags`

### Phase 2: Exporter

- [x] T4 - Datasets and fields from bound entities (M, 3 files) - deps: T1
- [x] T5 - Primary key and unique key inference (S, 2 files) - deps: T4
- [x] T6 - Relationships with orientation, filtering, and naming (S, 2 files) - deps: T4

#### Checkpoint B: Exporter
- [ ] dbt dummy project produces a document that validates against the vendored schema
- [ ] Bruin fixture pipeline produces a document that validates against the vendored schema
- [ ] No draft entity appears in either document
- [ ] `uv run pytest trellis_datamodel/tests/test_ossie_export.py -q` passes

### Phase 3: Wiring

- [x] T7 - Push integration and response warnings (S, 4 files) - deps: T4, T5, T6
- [x] T8 - Ossie section on the Config page (M, 2 files) - deps: T3

#### Checkpoint C: Wiring
- [ ] One push with `ossie.enabled: true` writes both framework files and `semantic_model.yml`
- [ ] `ossie.enabled: false` writes nothing new and leaves the response unchanged apart from the existing fields
- [ ] Config page renders the Ossie group, saves, and survives a reload
- [ ] `cd frontend && npm run check` passes

### Phase 4: Close

- [ ] T9 - End-to-end API test, changelog, config example (S, 4 files) - deps: T7, T8

#### Checkpoint D: Complete
- [ ] `uv run pytest -q` passes
- [ ] `cd frontend && npm run check && npm run test:smoke` passes
- [ ] Every success criterion in the spec has a test or a manual check recorded in the PR body

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Draft spec churn breaks the emitter | Med | Version pinned in one constant, schema vendored, golden files make the diff visible in review |
| Dev-target values leak into committed files | High | Config overrides win; `database` omitted by default; config field hint names the caveat |
| Relationship orientation inverted | High | Orientation delegated to `fk_placement.place_foreign_key`, with a test per relationship type |
| `dbt_model_paths` filtering silently empties the export | Med | Unresolvable `model_ref` produces a named warning in the response |
| Two independent unique columns flattened into one composite key | High | Explicit rule 8 in the spec; dedicated test with two candidate columns |
| `ProjectStatus` change ripples into API responses | Low | `/api/config-status` and `/api/config-info` enumerate keys explicitly, so no response shape changes |

## Open Questions

- **Generated-file header.** A `# Generated by Trellis ... do not edit` comment at the top of the file is cheap and answers discoverability better than a vendor-prefixed filename. Not yet approved; T4 writes without it unless confirmed.
- **ADR.** Three decisions here are hard to reverse and non-obvious: targeting an unreleased draft over stable `0.1.1`, rejecting `semglot` as a runtime dependency, and refusing manifest addresses. Currently captured in the spec's Notes section; awaiting a yes before `docs/adr/` is created.

## Parallelization

| Stream | Tasks | Files |
|---|---|---|
| A | T1 | `adapters/base.py`, `adapters/dbt_core.py`, `adapters/bruin.py`, `tests/conftest.py`, `tests/test_adapter_protocol_surface.py` |
| B | T2, T3 | `config.py`, `models/schemas.py`, `services/config_service.py`, `trellis.yml.example`, `tests/test_config_api.py` |

Streams A and B are disjoint and can run concurrently. Every task from T4 on edits `services/ossie.py` (with T7 adding `services/schema.py`, `routes/schema.py`) and must run sequentially.
