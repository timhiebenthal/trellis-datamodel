# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- **dbt package conflicts**: removed `dbt-core`, `dbt-duckdb`, and `dbt-colibri` from hard dependencies. Trellis only reads dbt artifacts (manifest.json, catalog.json, schema YAMLs) and never imports dbt as a Python package, so requiring a specific dbt version conflicted with users who have their own dbt adapter installed (e.g. dbt-postgres, dbt-snowflake, or the new dbt CLI). Users manage their own dbt installation; `dbt-colibri` is now an optional extra (`pip install trellis-datamodel[colibri]`) and `dbt-duckdb` remains available via the `[dbt-example]` extra for the bundled sample project.

## [0.10.1] - 2026-03-10

Stable release incorporating role-playing dimension fixes and description propagation from 0.10.1b1–b4.

### Fixed
- **Role-playing dimension entity generator**: when an annotation has `dimension_id: dim__employee` but `dim__employee` does not yet exist in `data_model.yml`, the entity generator now creates an entity with `id: dim__employee` (derived from the `dimension_id` value) instead of `id: dim__sales_agent` (derived from the annotation text). The linkage is no longer silently lost on first generation.
- Role context is now stored on the base entity as structured objects `{label, role, source}` in `data_model.yml` rather than being discarded. Roles accumulate across generation runs without duplicating (deduped by `(label, source)`).
