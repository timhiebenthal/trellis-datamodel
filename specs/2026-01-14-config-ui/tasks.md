# Config UI Page - Implementation Tasks

## Overview
Implements the `/config` page with backend-validated apply flow, backups, conflict detection, and Danger Zone gating per `spec.md`.

## Tasks

## SPRINT 1: Backend foundation

### Stream A: Config schema & API (backend)
- [x] Define Pydantic schema for user-facing fields (enums, paths, lists) and defaults.
- [x] Implement loader that reads `trellis.yml`, normalizes via YAML parser, and returns current values plus schema metadata.
- [x] Add validation for paths (project/manifest/catalog existence) and type/enum checks; reject unknown fields.
- [x] Implement conflict detection (mtime/hash) surfaced in responses for optimistic concurrency.
- [x] Implement backup + atomic write (temp file + move) with timestamped `.bak` before overwrite; normalized formatting acceptable.
- [x] Add FastAPI endpoints (GET/PUT `/api/config`) with structured errors and beta flag metadata.
- [x] Error handling for missing/unreadable config with clear messages; no crash of other routes.

## SPRINT 2: Frontend config UI

### Stream A: Config page route (frontend)
- [x] Add `/config` route under `(app)` layout; fetch config + schema on load.
- [x] Build form sections for paths, modeling style, entity guidance, dimensional/entity patterns, exposures/lineage, etc.
- [x] Implement Danger Zone gating (ack checkbox) before enabling beta toggles.
- [x] Add Apply flow: submit to PUT, surface validation errors inline, show success toast, reload saved state.
- [x] Handle conflict warning if mtime/hash differs; offer reload or confirm overwrite.
- [x] Handle missing/unreadable config state with recovery UI.
- [x] Add navigation/link entry to reach `/config`.

## SPRINT 3: Tests & polish

### Stream A: Backend tests
- [x] pytest coverage for GET/PUT: valid save, validation errors, conflict detection, backup creation, normalized write.
- [x] Fixtures for temp config files and path validation cases.

### Stream B: Frontend tests
- [ ] Vitest/component tests for form rendering, validation display, ack gating, success/error states.
- [ ] (Optional) Playwright smoke for load + apply happy path against mock/dev backend.

### Stream C: Documentation
- [x] Update `specs/2026-01-14-config-ui/spec.md` notes if schema/options change.
- [x] Add brief README/usage note pointing to `/config` page and backup behavior.

## Summary

### Sprint Overview
| Sprint | Name | Tasks | Streams |
|--------|------|-------|---------|
| SPRINT 1 | Backend foundation | 7 | 1 |
| SPRINT 2 | Frontend config UI | 7 | 1 |
| SPRINT 3 | Tests & polish | 7 | 3 |

### Stream Overview
**SPRINT 1**
- Stream A: Config schema & API (backend) - 7 tasks

**SPRINT 2**
- Stream A: Config page route (frontend) - 7 tasks

**SPRINT 3**
- Stream A: Backend tests - 2 tasks
- Stream B: Frontend tests - 2 tasks
- Stream C: Documentation - 2 tasks

### Parallelization
- Concurrent agents: up to 3 (Sprint 3 streams touch different areas/files).
- Critical path: Backend foundation → Frontend UI → Tests/Docs.
- Independent streams: Sprint 3 streams can run in parallel.

### Total Effort
- SPRINTS: 3
- STREAMS: 5
- Tasks: 21

## Notes
- Normalize YAML on save; comments may be lost.
- Keep beta flags gated; default to disabled unless existing config enables them.
- Ensure path validation is non-destructive (warn vs hard-fail on missing catalog if intentional).***
