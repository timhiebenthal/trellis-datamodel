# Source Chips on Entities - Implementation Tasks

## Overview
Implement manual, tag-like source chips on entities, with persistence in `data_model.yml`, lineage-based suggestions, and optional per-source colors from `canvas_layout.yml`. See `spec.md` for full context.

## Tasks

## SPRINT 1: Backend & Data Contract Foundation

### Stream A: Data model API and schema (`trellis_datamodel/routes/data_model.py`, `trellis_datamodel/models/schemas.py`)
- [ ] Add `sources: List[str]` to entity model schema (`DataModelUpdate`) with validation (trim/dedupe handled frontend; backend accepts list of strings).
- [ ] Update GET merge to surface `sources` untouched; ensure backward compatibility when missing.
- [ ] Update POST split to write `sources` into `data_model.yml`; ensure layout split ignores it.
- [x] Add pass-through for `source_colors` map from `canvas_layout.yml` (load and round-trip without requiring presence).
- [x] Unit tests: load/save round-trip with/without sources and source_colors (pytest).

## SPRINT 2: Frontend Types and State

### Stream A: Types and helpers (`frontend/src/lib/types.ts`, `frontend/src/lib/utils.ts`)
- [ ] Add `sources?: string[]` to `EntityData` and related response typings.
- [ ] Implement `normalizeSources` helper mirroring tag behavior (trim, dedupe, sort).
- [ ] Export type for `sourceColors` map if needed.

### Stream B: Data plumbing (`frontend/src/routes/+page.svelte`, stores if needed)
- [ ] Map `sources` from API payload into node data; ensure save payload includes updated `sources`.
- [ ] Thread `sourceColors` from backend response into a store or page-local variable for nodes.
- [ ] Backward compatibility: default to empty array/map when missing.

## SPRINT 3: UI/UX and Suggestions

### Stream A: SourceEditor component (`frontend/src/lib/components/SourceEditor.svelte`)
- [ ] Clone TagEditor interaction (add via enter/comma, remove via chip “x”, escape to cancel).
- [ ] Accept props: `sources`, `suggestions`, `canEdit`, `onUpdate`.
- [ ] Style chips with `sourceColors` lookup and deterministic fallback palette.
- [ ] Handle overflow (truncate with tooltip or +N indicator).
- [ ] Unit tests for add/remove/duplicate prevention and suggestions.

### Stream B: Entity integration (`frontend/src/lib/components/EntityNode.svelte`)
- [ ] Render SourceEditor below header; pass entity sources and suggestions.
- [ ] Compose suggestions: all unique manual sources across entities + lineage-derived suggestions for bound model (read-only hints).
- [ ] Ensure manual list overrides lineage suggestions (no auto-merge).
- [ ] Wire updates to node data/save flow.
- [ ] Add UI regression test (Playwright/Vitest component) to verify chips render and persist after reload.

## SPRINT 4: Testing & Polish

### Stream A: Backend tests & docs
- [ ] Finalize pytest coverage for data-model round-trip, including absence/presence cases.
- [ ] Add brief docs/changelog note if required.

### Stream B: Frontend tests & fallback behavior
- [ ] Playwright/Vitest: verify source chips display, add/remove, persist reload, lineage suggestions present but non-destructive.
- [ ] Verify color fallback works without `source_colors`; verify custom colors applied when provided.

## Summary

### Sprint Overview
| Sprint | Name | Tasks | Streams |
|--------|------|-------|---------|
| SPRINT 1 | Backend & Data Contract Foundation | Add sources to model/schema, round-trip source_colors | A |
| SPRINT 2 | Frontend Types and State | Types/helpers and data plumbing | A, B |
| SPRINT 3 | UI/UX and Suggestions | SourceEditor + Entity integration | A, B |
| SPRINT 4 | Testing & Polish | Coverage, docs, UI tests | A, B |

### Stream Overview
**SPRINT 1**
- Stream A: data-model API/schema - 5 tasks

**SPRINT 2**
- Stream A: types/helpers - 3 tasks
- Stream B: data plumbing - 3 tasks

**SPRINT 3**
- Stream A: SourceEditor - 5 tasks
- Stream B: Entity integration - 5 tasks

**SPRINT 4**
- Stream A: backend tests/docs - 2 tasks
- Stream B: frontend tests/fallback - 2 tasks

### Parallelization
- Concurrent agents: up to 2 in SPRINT 2–4 (distinct files/components).
- Critical path: Backend contract (SPRINT 1) → Frontend plumbing (SPRINT 2) → UI (SPRINT 3) → Full tests (SPRINT 4).
- Independent streams: Within each sprint, streams touch disjoint files to avoid merge conflicts.

### Total Effort
- SPRINTS: 4
- STREAMS: 8 (2 per sprint except Sprint 1)
- Tasks: 25

## Notes
- Keep sources high-level (system names). Manual list is source of truth; lineage only feeds suggestions.
- Color config lives in `canvas_layout.yml` as optional `source_colors`; UI must gracefully fall back when absent.
- Maintain backward compatibility for existing models/layouts without sources or source_colors.

## ADDITIONAL TASKS (Post-Implementation)

### Configuration: trellis.yml
- [ ] Add configuration option to `trellis.yml` to disable/activate source chip features
  - Option 1: `sources_enabled: true/false` to enable/disable source chips display
  - Option 2: `source_sources: "manual|lineage|both"` to control which sources are used
    - "manual": Only user-defined sources from entity edits
    - "lineage": Only lineage-derived sources (read-only)
    - "both": Both manual and lineage (manual takes precedence)
  - Default: `sources_enabled: true` and `source_sources: "both"`

### Data Preservation: Prevent canvas_layout.yml Overwrites
- [ ] Ensure frontend load doesn't overwrite existing `source_colors` from `canvas_layout.yml` unless changed
  - When loading data from API, preserve existing `source_colors` if they haven't changed in UI
  - Track which `source_colors` are user-defined vs. loaded from backend
  - Only save `source_colors` that have been explicitly modified by the user
  - Prevent accidental overwrites from cache, multiple tabs, or different users
