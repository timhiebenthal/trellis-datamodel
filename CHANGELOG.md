# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- **dbt package conflicts**: removed `dbt-core`, `dbt-duckdb`, and `dbt-colibri` from hard dependencies. Trellis only reads dbt artifacts (manifest.json, catalog.json, schema YAMLs) and never imports dbt as a Python package, so requiring a specific dbt version conflicted with users who have their own dbt adapter installed (e.g. dbt-postgres, dbt-snowflake, or the new dbt CLI). Users manage their own dbt installation; `dbt-colibri` is now an optional extra (`pip install trellis-datamodel[colibri]`) and `dbt-duckdb` remains available via the `[dbt-example]` extra for the bundled sample project.

## [0.10.1] - 2026-03-10

Stable release incorporating role-playing dimension fixes and description propagation from 0.10.1b1–b4.

### Fixed
- **Role-playing dimension entity generator**: when an annotation has `dimension_id: dim__employee` but `dim__employee` does not yet exist in `data_model.yml`, the entity generator now creates an entity with `id: dim__employee` (derived from the `dimension_id` value) instead of `id: dim__sales_agent` (derived from the annotation text). The linkage is no longer silently lost on first generation.
- Role context is now stored on the base entity as structured objects `{label, role, source}` in `data_model.yml` rather than being discarded. Roles accumulate across generation runs without duplicating (deduped by `(label, source)`).
