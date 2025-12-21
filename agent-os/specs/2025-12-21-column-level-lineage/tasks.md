# Task Breakdown: Table-Level Lineage Integration

## Overview
Total Tasks: 4 groups, ~25 sub-tasks

## Task List

### Backend Layer

#### Task Group 1: dbt-colibri Integration and Backend API
**Dependencies:** None

- [ ] 1.0 Complete backend lineage extraction layer
  - [ ] 1.1 Write 2-8 focused tests for lineage API endpoint
    - Test successful lineage extraction for valid model_id
    - Test 404 error for non-existent model_id
    - Test 500 error handling for dbt-colibri failures
    - Test response structure (nodes and edges format)
    - Test source table identification in response
    - Limit to 2-8 highly focused tests maximum
  - [ ] 1.2 Add dbt-colibri dependency to pyproject.toml
    - Add `dbt-colibri` package with appropriate version constraint
    - Verify MIT license compatibility
    - Update uv.lock after adding dependency
  - [ ] 1.3 Create lineage extraction service/function
    - Integrate dbt-colibri's lineage extraction functions
    - Accept model unique_id, manifest.json path, and catalog.json path
    - Extract upstream table-level lineage using dbt-colibri
    - Use dbt-colibri's source table detection
    - Transform dbt-colibri output to nodes/edges format for frontend
    - Handle dbt-colibri errors gracefully with clear error messages
    - Place in `trellis_datamodel/adapters/dbt_core.py` or separate service module
  - [ ] 1.4 Create FastAPI route `/api/lineage/{model_id}`
    - Follow pattern from `routes/manifest.py`
    - Use `APIRouter` with `/api` prefix and appropriate tags
    - Accept model unique_id as path parameter
    - Call lineage extraction service
    - Return JSON with nodes (models/tables) and edges (dependencies) structure
    - Include source table identification in response
    - Handle 404 for missing models (HTTPException)
    - Handle 500 for extraction errors (HTTPException with detail)
    - Add route documentation string
  - [ ] 1.5 Ensure backend API tests pass
    - Run ONLY the 2-8 tests written in 1.1
    - Verify endpoint returns correct lineage structure
    - Verify error handling works correctly
    - Do NOT run the entire test suite at this stage

**Acceptance Criteria:**
- The 2-8 tests written in 1.1 pass
- dbt-colibri dependency added and installable
- Lineage extraction service successfully extracts upstream lineage
- API endpoint returns correct JSON structure with nodes and edges
- Error handling returns appropriate HTTP status codes
- Source tables are correctly identified in response

### Frontend Layer

#### Task Group 2: Double-Click Interaction and Modal Component
**Dependencies:** Task Group 1 (API endpoint should exist, but can develop in parallel)

- [ ] 2.0 Complete modal component and interaction
  - [ ] 2.1 Write 2-8 focused tests for modal component
    - Test modal opens on double-click of bound entity
    - Test modal closes via backdrop click, escape key, and close button
    - Test loading state displays during API call
    - Test error state displays on API failure
    - Limit to 2-8 highly focused tests maximum
  - [ ] 2.2 Add double-click handler to EntityNode.svelte
    - Add `ondblclick` event handler to entity node
    - Only trigger for entities bound to dbt models (check `dbt_model` property)
    - Prevent double-click from triggering collapse/expand toggle
    - Extract bound model unique_id from entity data
    - Pass model unique_id to lineage modal component
    - Optional: Add brief visual feedback on double-click
  - [ ] 2.3 Create LineageModal.svelte component
    - Follow modal pattern from `ConfigInfoModal.svelte`
    - Use fixed overlay with `z-50`, backdrop blur (`bg-black/40 backdrop-blur-sm`)
    - Include header with title "Upstream Lineage" and close button (X icon using lucide)
    - Support closing via backdrop click, escape key, or close button
    - Use Svelte 5 runes (`$state`, `$derived`, `$props`) following component standards
    - Make modal responsive with max-width constraint and centered positioning
    - Include loading state with spinner icon (`lucide:loader-2` with `animate-spin`)
    - Include error state with retry option
    - Place in `frontend/src/lib/components/LineageModal.svelte`
  - [ ] 2.4 Integrate modal into main page
    - Import LineageModal component in `+page.svelte`
    - Add state to track which model's lineage to show
    - Pass model_id prop to modal when opened
    - Handle modal open/close state
  - [ ] 2.5 Ensure modal component tests pass
    - Run ONLY the 2-8 tests written in 2.1
    - Verify modal opens and closes correctly
    - Verify loading and error states display properly
    - Do NOT run the entire test suite at this stage

**Acceptance Criteria:**
- The 2-8 tests written in 2.1 pass
- Double-click on bound entity opens lineage modal
- Modal displays loading state during API call
- Modal closes via all three methods (backdrop, escape, close button)
- Error states display with retry option

#### Task Group 3: Lineage Graph Visualization and API Integration
**Dependencies:** Task Group 1 (API endpoint), Task Group 2 (Modal component)

- [ ] 3.0 Complete graph visualization and API integration
  - [ ] 3.1 Write 2-8 focused tests for graph visualization
    - Test graph renders nodes and edges from API response
    - Test source tables are highlighted with distinct styling
    - Test graph fits view to show entire lineage
    - Test zoom controls and minimap functionality
    - Limit to 2-8 highly focused tests maximum
  - [ ] 3.2 Add getLineage API function to frontend/src/lib/api.ts
    - Follow existing async fetch patterns from `api.ts`
    - Create typed response interface for lineage data (nodes, edges structure)
    - Handle 404 errors gracefully (return null)
    - Handle 500 errors with user-friendly error messages
    - Use API_BASE from existing getApiBase() function
    - Return null on error to allow modal to handle error display
  - [ ] 3.3 Create LineageGraph.svelte component
    - Use `@xyflow/svelte` library (reuse existing dependency)
    - Use `SvelteFlow` component similar to `Canvas.svelte`
    - Scope graph to modal content area (not full screen)
    - Display nodes representing upstream models/tables with model names
    - Display edges representing dependencies between models
    - Highlight source tables (from API response) with distinct visual styling
    - Use automatic layout algorithm (elkjs) similar to `layout.ts` for node positioning
    - Include zoom controls (`Controls` component from @xyflow/svelte)
    - Include minimap (`MiniMap` component from @xyflow/svelte)
    - Fit view to show entire lineage graph when loaded
    - Place in `frontend/src/lib/components/LineageGraph.svelte`
  - [ ] 3.4 Integrate graph into LineageModal
    - Call getLineage API function when modal opens with model_id
    - Pass lineage data to LineageGraph component
    - Handle loading state (show spinner while fetching)
    - Handle error state (show error message with retry)
    - Handle success state (display graph)
  - [ ] 3.5 Add TypeScript types for lineage data
    - Create interface for LineageNode (id, label, isSource, etc.)
    - Create interface for LineageEdge (source, target, etc.)
    - Create interface for LineageResponse (nodes, edges)
    - Add to `frontend/src/lib/types.ts` or separate types file
  - [ ] 3.6 Ensure graph visualization tests pass
    - Run ONLY the 2-8 tests written in 3.1
    - Verify graph renders correctly with sample data
    - Verify source tables are highlighted
    - Do NOT run the entire test suite at this stage

**Acceptance Criteria:**
- The 2-8 tests written in 3.1 pass
- API function successfully fetches lineage data
- Graph component renders nodes and edges correctly
- Source tables are visually distinct from regular models
- Graph fits view and includes zoom/minimap controls
- Loading and error states work correctly

### Testing

#### Task Group 4: Test Review & Gap Analysis
**Dependencies:** Task Groups 1-3

- [ ] 4.0 Review existing tests and fill critical gaps only
  - [ ] 4.1 Review tests from Task Groups 1-3
    - Review the 2-8 tests written by backend-engineer (Task 1.1)
    - Review the 2-8 tests written by frontend-engineer (Task 2.1)
    - Review the 2-8 tests written by frontend-engineer (Task 3.1)
    - Total existing tests: approximately 6-24 tests
  - [ ] 4.2 Analyze test coverage gaps for THIS feature only
    - Identify critical user workflows that lack test coverage
    - Focus ONLY on gaps related to lineage feature requirements
    - Do NOT assess entire application test coverage
    - Prioritize end-to-end workflows (double-click → API call → graph display)
    - Check integration between EntityNode → Modal → API → Graph
  - [ ] 4.3 Write up to 10 additional strategic tests maximum
    - Add maximum of 10 new tests to fill identified critical gaps
    - Focus on integration points: double-click → modal → API → graph rendering
    - Test end-to-end flow: user double-clicks entity → sees lineage graph
    - Test error propagation: API error → modal error state
    - Do NOT write comprehensive coverage for all scenarios
    - Skip edge cases, performance tests, and accessibility tests unless business-critical
  - [ ] 4.4 Run feature-specific tests only
    - Run ONLY tests related to lineage feature (tests from 1.1, 2.1, 3.1, and 4.3)
    - Expected total: approximately 16-34 tests maximum
    - Do NOT run the entire application test suite
    - Verify critical workflows pass (double-click → lineage display)

**Acceptance Criteria:**
- All feature-specific tests pass (approximately 16-34 tests total)
- Critical user workflows for lineage feature are covered
- End-to-end flow works: double-click entity → see upstream lineage graph
- No more than 10 additional tests added when filling in testing gaps
- Testing focused exclusively on lineage feature requirements

## Execution Order

Recommended implementation sequence:
1. Backend Layer (Task Group 1) - Can start immediately, no dependencies
2. Frontend Layer - Modal Component (Task Group 2) - Can develop in parallel with Task Group 1
3. Frontend Layer - Graph Visualization (Task Group 3) - Requires Task Group 1 API endpoint
4. Test Review & Gap Analysis (Task Group 4) - Requires all previous groups

**Note:** Task Groups 1 and 2 can be developed in parallel since the modal UI doesn't require the API to be complete (can use mock data initially).
