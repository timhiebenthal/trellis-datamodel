# Config UI Page - Specification

## Overview
Add a `/config` page that lets users view and edit user-facing `trellis.yml` settings through a validated UI. Changes use a backend-backed schema, validate before apply, and write normalized YAML (no comment preservation). Risky/experimental toggles (e.g., lineage/exposures) are clearly marked as beta.

## Requirements

### Functional Requirements
- Provide a routed page at `/config` (within the app layout) that loads the current `trellis.yml` values and renders form controls for user-facing keys only.
- Display validation feedback from the backend; prevent saving invalid values (paths, enums, booleans, lists).
- Apply flow: user edits → clicks `Apply` → backend validates → creates a backup → writes normalized `trellis.yml` → returns updated config; UI reflects saved state.
- Show a “Danger Zone / Beta” section for experimental features; require an acknowledgment before enabling those toggles.
- Detect on-disk changes (mtime/hash) between load and apply; warn and require user confirmation before overwriting if the file changed.
- If `trellis.yml` is missing or unreadable, show a clear error with retry guidance (do not crash other routes).

### Non-Functional Requirements
- Local-only behavior; no telemetry or external calls.
- Writes are atomic as feasible (temp file + move) and create a timestamped backup of the previous file before overwrite.
- Normalized YAML output is acceptable; comments/formatting may be lost.
- Validation is authoritative on the backend (Pydantic schema); the frontend mirrors constraints for UX but does not bypass backend checks.

## Scope

### In Scope
- New `/config` route/page in the Svelte app.
- Backend config schema + GET/PUT endpoints (or equivalent) to read/validate/write `trellis.yml` with backup.
- UI controls for the enumerated user-facing keys below.

### Out of Scope
- Editing non-user-facing/internal config fields.
- Persisting comments/formatting beyond normalized YAML.
- Auto-save/instant write (can be future work behind a separate toggle).

## Approach

### Technical Approach
- Define a backend Pydantic schema for `trellis.yml` user-facing fields, including enum options and defaults; reject unknown fields.
- Add endpoints (e.g., `GET /api/config`, `PUT /api/config`): GET returns current config plus schema metadata for options; PUT validates, checks mtime/hash for conflicts, creates a timestamped backup (e.g., `trellis.yml.bak.20260114-123000`), writes via temp file + move, and returns the saved config.
- YAML handling can normalize formatting (no comment preservation). Validation covers path existence for critical fields (dbt project/manifest/catalog), value enums, and basic type checks.
- Frontend: Svelte route at `/config` (under `(app)` layout) fetches config + schema, renders forms, handles conflict warnings, and shows apply success/errors.
- Danger Zone: wrap beta toggles behind an acknowledgment checkbox; disabled until checked.

### User Experience
- Sections with clear labels and helper text; dropdowns for enums, toggles for booleans, text inputs for paths.
- “Apply” button triggers validation/save; show inline errors and a global toast/banner on success/failure.
- Conflict warning if file changed since load; allow reload or force overwrite after confirmation.
- Empty/missing file shows a recovery message with a “Reload” action.

## User-Facing Keys & Expected Options
- `framework`: enum `dbt-core` (others not yet supported; display but lock if future?).
- `modeling_style`: enum `dimensional_model`, `entity_model`.
- `dbt_project_path`: path string (relative/absolute); validate exists.
- `dbt_manifest_path`: path string (relative to project or absolute); validate exists.
- `dbt_catalog_path`: path string (relative to project or absolute); validate exists or warn if missing.
- `data_model_file`: path string (relative/absolute).
- `dbt_model_paths`: list of strings (patterns); allow empty = all.
- `dbt_company_dummy_path`: optional path string.
- `lineage.enabled` (beta): boolean.
- `lineage.layers` (beta): ordered list of strings.
- `entity_creation_guidance.enabled`: boolean.
- `entity_creation_guidance.push_warning_enabled`: boolean.
- `entity_creation_guidance.min_description_length`: integer >= 0.
- `entity_creation_guidance.disabled_guidance`: list of strings.
- `exposures.enabled` (beta): boolean.
- `exposures.default_layout` (beta): enum `dashboards-as-rows`, `entities-as-rows`.
- `dimensional_modeling.inference_patterns.dimension_prefix`: string or list of strings.
- `dimensional_modeling.inference_patterns.fact_prefix`: string or list of strings.
- `entity_modeling.inference_patterns.prefix`: string or list of strings.

## Dependencies
- Existing Svelte app layout and upcoming routed views (`/canvas`, `/exposures`, `/bus-matrix`).
- Backend ability to read/write local files; ruamel/pyyaml for YAML.
- Auth assumptions unchanged (local-only).

## Success Criteria
- Visiting `/config` loads without console/backend errors and shows current config values.
- Invalid inputs are blocked with clear errors; valid apply rewrites `trellis.yml` and produces a backup.
- Danger Zone toggles require explicit acknowledgment and do not auto-enable on load.
- Reloading `/config` reflects the saved state; other app routes remain unaffected.

## Notes
- If we later add auto-save, keep it opt-in and reuse the same validation + backup path.
- Ensure error messages avoid leaking sensitive paths in logs; UI can still show local paths for clarity.

## Implementation Notes
- Backend implementation completed: Pydantic schemas, config service, and FastAPI endpoints
- Frontend implementation completed: Svelte config page with form sections, validation, and conflict handling
- All user-facing keys from specification are supported
- Beta features (lineage, exposures) are gated behind Danger Zone acknowledgment
- Backups are created with timestamp format: `trellis.yml.bak.YYYYMMDD-HHMMSS`
- Conflict detection uses mtime and hash for optimistic concurrency
- Normalized YAML output (comments not preserved)
