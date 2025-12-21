# Specification: Table-Level Lineage Integration

## Goal
Enable users to view upstream table-level lineage for any entity by double-clicking on it, showing all upstream models back to source tables using dbt-colibri for lineage extraction.

## User Stories
- As an Analytics Engineer, I want to double-click on an entity to see its upstream lineage so that I can understand where the data comes from and trace back to source tables.
- As a Data Engineer, I want to visualize table-level dependencies in a modal overlay so that I can quickly understand data flow without leaving the main canvas view.

## Specific Requirements

**dbt-colibri Integration**
- Add `dbt-colibri` as a Python dependency in `pyproject.toml` (MIT license compatible)
- Integrate dbt-colibri's lineage extraction functions into the backend
- Use dbt-colibri's source table detection capabilities (do not implement custom detection)
- Call lineage extraction on-demand when user requests lineage (not at startup)
- Pass manifest.json and catalog.json paths to dbt-colibri for processing
- Handle dbt-colibri errors gracefully with appropriate error messages
- Return lineage data in a format suitable for frontend graph visualization
- Support table-level lineage initially (column-level is future enhancement)

**Backend API Endpoint**
- Create new FastAPI route `/api/lineage/{model_id}` following existing router patterns in `routes/manifest.py`
- Use `APIRouter` with `/api` prefix and appropriate tags
- Accept model unique_id (e.g., "model.project.model_name") as path parameter
- Call dbt-colibri to extract upstream lineage for the specified model
- Return JSON response with nodes (models/tables) and edges (dependencies) structure
- Include source table identification from dbt-colibri in response
- Handle missing model errors with 404 status code
- Handle lineage extraction errors with 500 status code and error detail message

**Double-Click Interaction**
- Add `ondblclick` event handler to `EntityNode.svelte` component
- Only trigger lineage modal for entities that are bound to dbt models (have `dbt_model` property)
- Prevent double-click from triggering collapse/expand toggle
- Pass entity's bound model unique_id to lineage modal component
- Show visual feedback (optional: brief highlight) when double-click is registered

**Lineage Modal Component**
- Create new `LineageModal.svelte` component in `frontend/src/lib/components/`
- Follow modal pattern from `ConfigInfoModal.svelte` (backdrop, header, close button, escape key)
- Use fixed overlay with `z-50`, backdrop blur (`bg-black/40 backdrop-blur-sm`)
- Include header with title "Upstream Lineage" and close button (X icon)
- Support closing via backdrop click, escape key, or close button
- Use Svelte 5 runes (`$state`, `$derived`, `$props`) following component standards
- Make modal responsive with max-width constraint and centered positioning
- Include loading state with spinner icon (`lucide:loader-2` with `animate-spin`)

**Lineage Graph Visualization**
- Create new lineage graph view component using `@xyflow/svelte` library (reuse existing dependency)
- Use `SvelteFlow` component similar to `Canvas.svelte` but scoped to modal content area
- Display nodes representing upstream models/tables with model names
- Display edges representing dependencies between models
- Highlight source tables (identified by dbt-colibri) with distinct visual styling
- Use automatic layout algorithm (elkjs) similar to `layout.ts` for node positioning
- Include zoom controls and minimap for navigation within modal
- Fit view to show entire lineage graph when loaded

**Frontend API Integration**
- Add `getLineage(modelId: string)` function to `frontend/src/lib/api.ts`
- Follow existing async fetch patterns with error handling
- Use typed response interface for lineage data structure
- Handle 404 errors gracefully (model not found)
- Handle 500 errors with user-friendly error messages
- Show loading state while fetching lineage data
- Return null on error to allow modal to handle error display

**Loading and Error States**
- Show loading spinner in modal while lineage is being generated
- Display loading message "Generating lineage..." during API call
- Show error message if lineage generation fails with retry option
- Handle timeout scenarios gracefully
- Provide clear error messages for common failure cases (missing manifest, invalid model, etc.)

**Performance Considerations**
- Generate lineage on-demand (when user double-clicks) rather than pre-generating
- Monitor performance during initial implementation to inform future caching strategy
- Use async/await patterns to prevent blocking UI during lineage generation
- Consider future caching if performance testing shows slow generation times

## Visual Design
No visual assets provided.

## Existing Code to Leverage

**ConfigInfoModal.svelte**
- Modal structure with backdrop, header, close button, and escape key handling
- Loading state pattern with spinner icon and conditional rendering
- Error state handling with retry functionality
- Scrollable content area pattern for modal body
- Footer action buttons pattern

**Canvas.svelte and @xyflow/svelte**
- Graph visualization setup using `SvelteFlow` component
- Node and edge type definitions pattern
- Zoom controls and minimap integration
- Graph interaction handlers (connect, delete, drag)
- Background pattern styling

**routes/manifest.py**
- FastAPI router pattern with `/api` prefix
- Error handling with HTTPException for 404 and 500 cases
- Adapter pattern usage (`get_adapter()`)
- JSON response structure
- Route documentation strings

**frontend/src/lib/api.ts**
- Typed async fetch functions with error handling
- API base URL resolution pattern
- Error handling patterns (404 returns empty/null, 500 throws error)
- TypeScript interfaces for request/response types

**adapters/dbt_core.py**
- Manifest.json and catalog.json parsing infrastructure
- Model information extraction patterns
- Adapter interface pattern for framework abstraction
- Error handling for missing files

## Out of Scope
- Column-level lineage visualization (future enhancement, dbt-colibri supports this)
- Downstream lineage (only upstream lineage in this spec)
- Pre-generation or caching of lineage data (on-demand only for now)
- Side panel or separate route for lineage view (modal overlay only)
- Column selection or filtering within lineage view (table-level only)
- Lineage editing or modification capabilities
- Export lineage to external formats (PNG, SVG, etc.)
- Real-time lineage updates when dbt models change
- Integration with other transformation frameworks beyond dbt-core
- Performance optimizations like caching (to be evaluated after initial implementation)
