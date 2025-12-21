# Task Breakdown: Entity Exposures Cross-Table

## Overview
Total Tasks: 2 task groups, 15 sub-tasks

## Task List

### Backend API Layer

#### Task Group 1: Exposures API Endpoint
**Dependencies:** None

- [ ] 1.0 Complete Backend API layer
  - [ ] 1.1 Write 2-8 focused tests for exposures API endpoint
    - Test reading exposures.yml file successfully
    - Test handling missing exposures.yml gracefully (returns empty array)
    - Test parsing YAML structure correctly
    - Test resolving `ref('model_name')` references to full unique_id
    - Test mapping exposures to entities via dbt models
    - Test handling malformed YAML with error response
    - Test handling unresolved model references
    - Limit to 2-8 highly focused tests maximum
  - [ ] 1.2 Create Pydantic response models in `trellis_datamodel/models/schemas.py`
    - `ExposureResponse` model with fields: name, label, type, description, owner (name, email)
    - `ExposuresListResponse` model containing exposures array and entityUsage mapping
    - Follow existing Pydantic model patterns in schemas.py
  - [ ] 1.3 Create new router file `trellis_datamodel/routes/exposures.py`
    - Use `APIRouter(prefix="/api", tags=["exposures"])`
    - Follow FastAPI router pattern from `trellis_datamodel/routes/schema.py`
  - [ ] 1.4 Implement `GET /api/exposures` endpoint
    - Read `exposures.yml` from dbt project directory (check `models/` subdirectory)
    - Use `yaml.safe_load()` to parse YAML file
    - Handle missing file gracefully (return `{ exposures: [], entityUsage: {} }`)
    - Extract exposure metadata (name, label, type, description, owner)
    - Parse `depends_on` array with `ref('model_name')` format references
  - [ ] 1.5 Implement model reference resolution logic
    - Resolve `ref('model_name')` to full dbt model `unique_id` (e.g., `model.project.model_name`)
    - Load manifest.json to get model unique_ids
    - Handle unresolved references (models not in manifest) gracefully
  - [ ] 1.6 Implement entity mapping logic
    - Load data_model.yml to get entities and their `dbt_model` fields
    - Map resolved dbt model unique_ids to entity IDs
    - Handle entities with `additional_models` - if any bound model matches, include entity
    - Build `entityUsage` object mapping entity IDs to arrays of exposure names
  - [ ] 1.7 Add error handling and logging
    - Handle malformed YAML with clear HTTPException (400 status)
    - Log errors server-side for debugging
    - Return user-friendly error messages
    - Follow error handling patterns from `agent-os/standards/backend/api.md`
  - [ ] 1.8 Register router in `trellis_datamodel/server.py`
    - Import exposures router
    - Add router to FastAPI app using `app.include_router()`
    - Follow existing router registration pattern
  - [ ] 1.9 Ensure backend API tests pass
    - Run ONLY the 2-8 tests written in 1.1
    - Verify endpoint returns correct structure
    - Verify error cases handled properly
    - Do NOT run the entire test suite at this stage

**Acceptance Criteria:**
- The 2-8 tests written in 1.1 pass
- API endpoint returns correct JSON structure with exposures and entityUsage
- Missing exposures.yml handled gracefully (no 404 error)
- Model references resolved correctly
- Entity mapping works for entities with single and multiple bound models
- Error cases return appropriate HTTP status codes

### Frontend Components

#### Task Group 2: Exposures Tab and Table UI
**Dependencies:** Task Group 1

- [ ] 2.0 Complete Frontend UI components
  - [ ] 2.1 Write 2-8 focused tests for ExposuresTable component
    - Test component renders table with correct structure (rows=entities, columns=exposures)
    - Test displays X marks in correct cells
    - Test shows exposure labels as column headers
    - Test displays exposure type icons/tags
    - Test shows tooltips with description and owner on hover
    - Test displays empty state when no exposures exist
    - Limit to 2-8 highly focused tests maximum
  - [ ] 2.2 Extend `viewMode` store type in `frontend/src/lib/stores.ts`
    - Update type from `'conceptual' | 'logical'` to `'conceptual' | 'logical' | 'exposures'`
    - Maintain type safety with TypeScript union types
    - Follow existing store structure patterns
  - [ ] 2.3 Add exposures tab button to navigation in `frontend/src/routes/+page.svelte`
    - Add third button alongside Conceptual/Logical tabs (lines 925-953)
    - Use same button styling classes and layout pattern
    - Reduce icon width in existing tabs from `w-4 h-4` to `w-3.5 h-3.5`
    - Add icon for exposures tab (use appropriate icon from @iconify/svelte, e.g., `lucide:external-link` or `lucide:layers`)
    - Set `onclick` handler to update `viewMode` store to `'exposures'`
    - Apply conditional classes: `class:bg-white={$viewMode === "exposures"}`
  - [ ] 2.4 Create TypeScript interfaces in `frontend/src/lib/types.ts`
    - `Exposure` interface: name, label, type, description, owner (name, email)
    - `ExposuresResponse` interface: exposures array and entityUsage mapping
    - Follow existing type definition patterns
  - [ ] 2.5 Add API function in `frontend/src/lib/api.ts`
    - Create `getExposures()` async function
    - Call `GET /api/exposures` endpoint
    - Return typed `ExposuresResponse` object
    - Handle errors gracefully (return empty data structure)
    - Follow existing API function patterns
  - [ ] 2.6 Create `ExposuresTable.svelte` component in `frontend/src/lib/components/`
    - Use Svelte 5 runes (`$state`, `$derived`) for reactivity
    - Fetch exposures data on component mount using `getExposures()` API call
    - Store data in component state (not global store - read-only)
    - Create table structure: rows = entities, columns = exposures
    - Display entity labels in first column (leftmost)
    - Display exposure labels as column headers
    - Show X mark (× character) in cells where entity is used by exposure
    - Use Tailwind CSS for styling, following existing component patterns
    - Make table horizontally scrollable if many exposures exist
  - [ ] 2.7 Implement exposure metadata display in ExposuresTable
    - Show exposure `label` as column header text
    - Display exposure `type` as small tag/badge or icon next to label
    - Use appropriate icons from `@iconify/svelte` for different types (dashboard, notebook, application, etc.)
    - Show exposure `description` and `owner.name` as tooltip on column header hover
    - Follow existing tooltip patterns in codebase
  - [ ] 2.8 Implement empty state in ExposuresTable component
    - Display helper box when no exposures.yml exists or file is empty
    - Use similar styling to `Canvas.svelte` empty state (lines 318-348)
    - Include icon, heading ("No Exposures Found"), and descriptive text
    - Provide guidance text explaining how to create exposures.yml
    - Use amber/yellow warning box styling similar to Sidebar helper boxes (`bg-amber-50 border-amber-200`)
    - Reference dbt documentation or show example structure
  - [ ] 2.9 Integrate ExposuresTable into main page layout
    - Update `frontend/src/routes/+page.svelte` to conditionally render table vs canvas
    - When `viewMode === 'exposures'`, show ExposuresTable component instead of Canvas
    - Ensure sidebar remains visible when in exposures view
    - Maintain existing Conceptual/Logical view functionality unchanged
    - Import ExposuresTable component
  - [ ] 2.10 Ensure frontend component tests pass
    - Run ONLY the 2-8 tests written in 2.1
    - Verify table renders correctly with data
    - Verify empty state displays correctly
    - Do NOT run the entire test suite at this stage

**Acceptance Criteria:**
- The 2-8 tests written in 2.1 pass
- Exposures tab appears in navigation bar with correct styling
- Tab icons are narrower (w-3.5 h-3.5) to save screen space
- ExposuresTable component renders cross-table correctly
- Table shows X marks in correct cells indicating entity usage
- Exposure metadata (label, type, description, owner) displays correctly
- Empty state shows helpful guidance when no exposures exist
- View mode switching works correctly (Conceptual/Logical/Exposures)
- Sidebar remains visible in exposures view

### Testing

#### Task Group 3: Test Review & Gap Analysis
**Dependencies:** Task Groups 1-2

- [ ] 3.0 Review existing tests and fill critical gaps only
  - [ ] 3.1 Review tests from Task Groups 1-2
    - Review the 2-8 tests written by backend-engineer (Task 1.1)
    - Review the 2-8 tests written by frontend-engineer (Task 2.1)
    - Total existing tests: approximately 4-16 tests
  - [ ] 3.2 Analyze test coverage gaps for THIS feature only
    - Identify critical user workflows that lack test coverage
    - Focus ONLY on gaps related to this spec's feature requirements
    - Do NOT assess entire application test coverage
    - Prioritize end-to-end workflows over unit test gaps
    - Consider: API endpoint integration, full table rendering with real data, view mode switching
  - [ ] 3.3 Write up to 10 additional strategic tests maximum
    - Add maximum of 10 new tests to fill identified critical gaps
    - Focus on integration points and end-to-end workflows
    - Do NOT write comprehensive coverage for all scenarios
    - Skip edge cases, performance tests, and accessibility tests unless business-critical
    - Potential areas: E2E test for switching to exposures tab, integration test for API + frontend, test for entity mapping with multiple bound models
  - [ ] 3.4 Run feature-specific tests only
    - Run ONLY tests related to this spec's feature (tests from 1.1, 2.1, and 3.3)
    - Expected total: approximately 14-26 tests maximum
    - Do NOT run the entire application test suite
    - Verify critical workflows pass

**Acceptance Criteria:**
- All feature-specific tests pass (approximately 14-26 tests total)
- Critical user workflows for this feature are covered
- No more than 10 additional tests added when filling in testing gaps
- Testing focused exclusively on this spec's feature requirements

## Execution Order

Recommended implementation sequence:
1. Backend API Layer (Task Group 1) - Must complete before frontend can work
2. Frontend Components (Task Group 2) - Depends on API endpoint from Task Group 1
3. Test Review & Gap Analysis (Task Group 3) - Depends on both Task Groups 1-2
