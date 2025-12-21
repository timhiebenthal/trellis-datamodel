# Specification: Entity Exposures Cross-Table

## Goal
Display a read-only cross-table showing which entities are used by which downstream exposures (from dbt exposures.yml) in a dedicated tab, enabling users to visualize entity usage across their data applications.

## User Stories
- As an Analytics Engineer, I want to see which entities are consumed by downstream applications so that I can understand the impact of changes to my data models.
- As a Data Engineer, I want to visualize entity usage across exposures so that I can identify critical entities and plan migrations effectively.

## Specific Requirements

**New Exposures Tab in Navigation**
- Add third tab button alongside "Conceptual" and "Logical" in the top navigation bar (`frontend/src/routes/+page.svelte` lines 925-953)
- Style consistently with existing tabs using same button classes and layout pattern
- Reduce icon width in existing tabs from `w-4 h-4` to `w-3.5 h-3.5` to save screen space
- Tab always visible regardless of exposures.yml existence
- Extend `viewMode` store type to include `'exposures'` option (`frontend/src/lib/stores.ts`)

**Exposures Data Loading**
- Create new API endpoint `GET /api/exposures` in `trellis_datamodel/routes/` directory
- Read and parse `exposures.yml` file from dbt project directory (typically in `models/` subdirectory)
- Handle missing file gracefully (return empty array, not error)
- Parse YAML structure with `exposures` array containing exposure objects
- Return structured data with exposure name, label, type, description, owner, and resolved model dependencies

**Model Reference Resolution**
- Parse `depends_on` array from each exposure which contains `ref('model_name')` format references
- Resolve `ref('model_name')` to full dbt model `unique_id` (e.g., `model.project.model_name`)
- Map resolved dbt model `unique_id` values to entities via entity's `dbt_model` field
- Handle entities with multiple bound models (`additional_models`) - if any bound model matches, mark entity as used
- Return mapping data showing which exposures reference which entities

**Cross-Table Display Component**
- Create new Svelte component `ExposuresTable.svelte` in `frontend/src/lib/components/`
- Table structure: rows = entities, columns = exposures
- Display entity labels in first column (leftmost)
- Display exposure labels as column headers
- Show X mark (✓ or × character) in cells where entity is used by exposure
- Use Tailwind CSS for styling, following existing component patterns
- Make table scrollable horizontally if many exposures exist

**Exposure Metadata Display**
- Show exposure `label` as column header text
- Display exposure `type` (dashboard, notebook, application, etc.) as small tag/badge or icon next to label
- Use appropriate icons from `@iconify/svelte` library for different exposure types
- Show exposure `description` and `owner.name` as tooltip on column header hover
- Follow existing tooltip patterns in codebase

**Empty State Handling**
- Display helper box when no exposures.yml exists or file is empty
- Use similar styling to existing empty states (e.g., `Canvas.svelte` lines 318-348)
- Include icon, heading, and descriptive text prompting user to create exposures.yml
- Provide guidance text explaining how to structure exposures.yml file
- Reference dbt documentation or show example structure

**View Mode Integration**
- When exposures tab is active, hide canvas view and show table component
- Update main page layout to conditionally render table vs canvas based on `viewMode`
- Ensure sidebar remains visible when in exposures view
- Maintain existing Conceptual/Logical view functionality unchanged

**API Response Structure**
- Return JSON with structure: `{ exposures: [...], entityUsage: {...} }`
- `exposures` array contains exposure metadata (name, label, type, description, owner)
- `entityUsage` object maps entity IDs to arrays of exposure names that use them
- Use Pydantic models in `trellis_datamodel/models/schemas.py` for response validation
- Follow RESTful API conventions from `agent-os/standards/backend/api.md`

**Error Handling**
- Handle missing exposures.yml file gracefully (return empty data, not 404 error)
- Handle malformed YAML with clear error messages
- Handle unresolved model references (exposures referencing models not in manifest)
- Display user-friendly error messages in UI following existing error patterns
- Log errors server-side for debugging

**Component Architecture**
- Create reusable `ExposuresTable.svelte` component following Svelte 5 runes (`$state`, `$derived`)
- Use TypeScript interfaces for exposure and entity usage types
- Fetch data via API call on component mount or when tab becomes active
- Store exposure data in component state, not global store (read-only, no need for shared state)
- Follow component best practices from `agent-os/standards/frontend/components.md`

## Visual Design
No visual assets provided.

## Existing Code to Leverage

**View Mode Switcher Pattern (`frontend/src/routes/+page.svelte` lines 925-953)**
- Reuse exact button styling classes and layout structure for new exposures tab
- Follow same conditional class application pattern (`class:bg-white={$viewMode === "exposures"}`)
- Use same icon + text layout with `@iconify/svelte` Icon component
- Maintain consistent spacing and visual hierarchy

**Empty State Pattern (`frontend/src/lib/components/Canvas.svelte` lines 318-348)**
- Reuse empty state component structure with icon, heading, description, and action button
- Apply same styling classes (`bg-white/90 backdrop-blur-sm`, `rounded-xl border`, etc.)
- Use similar icon treatment with circular background and centered layout
- Follow same text hierarchy and spacing patterns

**API Endpoint Pattern (`trellis_datamodel/routes/schema.py` and `data_model.py`)**
- Follow FastAPI router pattern with `APIRouter(prefix="/api", tags=["exposures"])`
- Use same error handling approach with HTTPException for client errors
- Follow YAML file reading pattern using `yaml.safe_load()` for exposures.yml
- Use config module (`trellis_datamodel.config`) to resolve file paths relative to dbt project

**Store Pattern (`frontend/src/lib/stores.ts`)**
- Extend `viewMode` writable store type from `'conceptual' | 'logical'` to include `'exposures'`
- Follow same store structure and initialization patterns
- Maintain type safety with TypeScript union types

**Helper Box Pattern (`frontend/src/lib/components/Sidebar.svelte` lines 421-468)**
- Reuse amber/yellow warning box styling for exposures.yml helper message
- Follow same structure with icon, strong text, and code formatting
- Use similar border and background color scheme (`bg-amber-50 border-amber-200`)

## Out of Scope
- Editing exposures from the UI (no create/edit/delete functionality)
- Syncing changes back to exposures.yml file
- Filtering or sorting the cross-table
- Click interactions to navigate to entities or exposures
- Export functionality (CSV, PDF, etc.)
- Model-level granularity (only showing entity-level usage, not individual model usage)
- Real-time updates when exposures.yml changes (requires file watching)
- Exposure detail modal or expanded view
- Search functionality within the table
- Pagination for large numbers of entities or exposures
