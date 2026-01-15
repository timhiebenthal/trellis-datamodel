# Source Chips on Entities - Specification

## Overview
Add manual, tag-like "source" chips to entities so users can record high-level system origins (e.g., "Salesforce") directly on the canvas. Manual sources override lineage-derived values; lineage suggestions are read-only hints. Sources persist in `data_model.yml` and optionally get per-source colors from `canvas_layout.yml`.

## Requirements

### Functional Requirements
- Users can add/remove multiple source chips on an entity (inline UX mirroring tags).
- Source values are free-text, trimmed, deduped, sorted for stable display; intended to be high-level systems (not table names).
- Manual sources override any lineage-derived sources; lineage suggestions never overwrite user-set chips.
- Existing sources across the model are suggested while typing; for bound entities, lineage-derived sources are also suggested.
- Sources are shown below the entity header (under the title/type row) as chips; overflow is handled (truncate/ellipsis or +N).
- Source chips persist in `data_model.yml`; removing a dbt binding does not delete them.
- Optional per-source colors can be defined in `canvas_layout.yml`; absence falls back to a deterministic default palette.

### Non-Functional Requirements
- UX parity with TagEditor interactions (enter/comma to add, click X to remove, escape to cancel).
- Backend and frontend remain backward compatible with models/layouts lacking sources or source_colors.
- Minimal performance impact when loading suggestions (use memoized, deduped source list).

## Scope

### In Scope
- Backend schema and persistence changes to carry `sources: string[]` on entities.
- Frontend typing, stores, and rendering for source chips.
- Suggestion logic leveraging existing sources and lineage suggestions for bound models.
- Optional color map read/write in `canvas_layout.yml` (pass-through; default palette fallback in UI).

### Out of Scope
- Automatic import of dbt lineage into entities (lineage stays as suggestions only).
- Global color definitions in `trellis.yml` (may be future work).
- Exports or downstream tooling consuming sources beyond display and persistence.

## Approach

### Technical Approach
- Backend (`/api/data-model`):
  - Extend `DataModelUpdate` and entity serialization to include `sources` (list of strings).
  - In `_split_model_and_layout`, persist `sources` to `data_model.yml`; keep `source_colors` (if present) in `canvas_layout.yml` under a top-level `source_colors` map.
  - Ensure GET merges layout data without touching sources; POST remains backward compatible.
- Frontend:
  - Extend `EntityData` with `sources?: string[]`; add `normalizeSources` helper mirroring `normalizeTags` (trim, dedupe, sort).
  - Add `SourceEditor` component (fork TagEditor behavior) with suggestion list composed of:
    - All unique sources across entities.
    - Lineage-derived suggestions for the bound dbt model (read-only hints).
  - Render source chips below the header row in `EntityNode.svelte`; apply color via layout map lookup (`sourceColors[name]`) else deterministic fallback.
  - Persist changes through existing save flow (entities data payload).
  - Handle chip overflow with truncation and tooltip or "+N" indicator.
- Layout color map:
  - Accept/round-trip `canvas_layout.yml` top-level `source_colors` map; expose to frontend via merged layout response.
  - Fallback palette generated client-side when map is missing.

### User Experience
- Inline chips directly under the entity header; add via + button or typing (enter/comma).
- Suggestions drop-down populated from existing + lineage hints; selection adds chip.
- Remove via chip "x"; escape cancels input.
- Colors: use configured color if available; otherwise default/fallback hue.

## Dependencies
- Existing TagEditor pattern and normalize helpers.
- Lineage API to fetch suggestions for bound models (read-only input).
- Canvas layout load/save path for adding optional `source_colors`.

## Success Criteria
- Entities can display and edit multiple source chips inline; state persists after reload.
- Manual sources are retained even if dbt binding is removed.
- Lineage-derived suggestions do not overwrite manual chips.
- Layout color map (when present) influences chip color; absence uses fallback without errors.
- No regressions to existing data-model load/save flows without sources.

## Notes
- Keep sources high-level system identifiers; avoid table-level granularity.
- Color configuration lives in `canvas_layout.yml` to keep it view-specific; consider `trellis.yml` defaults later if needed.
