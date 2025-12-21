# Spec Requirements: Column-Level Lineage Integration

## Initial Description

I would like to integrate (col-level) lineage as it unlocks a lot of usecases. The "retrieval" of lineage is pretty dbt specific in this case but the handling isn't.

For example, then double-clicking on an entity should lead me to a view where we see all upstream models till the source-tables/raw data of the entity.

To be flexible I thought about leveraging existing work of https://github.com/b-ned/dbt-colibri (MIT license) to not re-invent the wheel.

## Requirements Discussion

### First Round Questions

**Q1:** I assume we'll use dbt-colibri as a Python library dependency (not as a CLI subprocess). We'll call its lineage extraction functions from our FastAPI backend to generate lineage data, then visualize it in the SvelteKit frontend. Is that correct, or should we use it differently?
**Answer:** Correct

**Q2:** I assume double-clicking an entity node opens a new modal/overlay showing the upstream lineage graph. Should this be: a) A full-screen modal overlay? b) A side panel (similar to your existing sidebar)? c) A new route/page that navigates away from the canvas? Or do you prefer a different approach?
**Answer:** Modal overlay for now

**Q3:** When showing upstream lineage for an entity, should we: a) Show only column-level lineage (which columns flow from which upstream columns)? b) Show both column-level and model-level lineage (models connected with column details)? c) Allow toggling between column-level and model-level views?
**Answer:** Let's start with table-level lineage for now. But as we use dbt-colibri there is more possible later on

**Q4:** When double-clicking an entity, should users: a) See lineage for all columns in that entity automatically? b) First select specific columns to trace? c) Have both options (default all columns, with ability to filter)?
**Answer:** Table-level for now

**Q5:** Should double-click also show downstream lineage (where this entity's columns are used), or only upstream? Or should we support both with a toggle?
**Answer:** Upstream only for now

**Q6:** I assume we'll: a) Call dbt-colibri's lineage extraction during backend initialization or on-demand when lineage is requested, b) Store the lineage data in memory or cache it (since dbt artifacts don't change frequently), c) Pass lineage data to frontend via a new API endpoint (e.g., `/api/lineage/{model_id}`). Is that correct, or should we generate lineage data differently?
**Answer:** On-demand I would say? Depends on how much processing it is every time

**Q7:** For identifying "source tables/raw data" in the upstream view, should we: a) Rely on dbt-colibri's detection of sources? b) Use dbt's `sources.yml` definitions to mark source tables? c) Use a heuristic (e.g., models in a `1_raw` or `sources` folder)?
**Answer:** Use dbt-colibri

**Q8:** For large dbt projects (100+ models), should we: a) Generate lineage on-demand (when user double-clicks) with a loading indicator? b) Pre-generate lineage for all models at startup/refresh? c) Cache lineage data and only regenerate when manifest.json changes?
**Answer:** Loading spinner for now. Then let's see how quick it is

### Existing Code to Reference

**Similar Features Identified:**

**Modal Components:**
- `frontend/src/lib/components/DeleteConfirmModal.svelte` - Simple modal with backdrop, escape key handling, and backdrop click to close
- `frontend/src/lib/components/ConfigInfoModal.svelte` - More complex modal with loading states, error handling, header with close button, scrollable content area, and footer actions
- Pattern: Fixed overlay with `z-50`, backdrop blur, centered content, escape key support

**Graph Visualization:**
- `frontend/src/lib/components/Canvas.svelte` - Main canvas using `@xyflow/svelte` with `SvelteFlow` component
- `frontend/src/lib/components/EntityNode.svelte` - Custom node component for entities
- `frontend/src/lib/components/CustomEdge.svelte` - Custom edge component for relationships
- `frontend/src/lib/layout.ts` - Layout utilities using `elkjs` for automatic graph layout
- Pattern: Uses `@xyflow/svelte` for graph rendering, can reuse same library for lineage visualization

**API Patterns:**
- `trellis_datamodel/routes/manifest.py` - FastAPI router pattern with `/api` prefix
- `frontend/src/lib/api.ts` - Frontend API functions using fetch with error handling
- Pattern: Backend routes return JSON, frontend has typed async functions for API calls

**Loading States:**
- `ConfigInfoModal.svelte` shows loading spinner using `lucide:loader-2` icon with `animate-spin` class
- Pattern: Conditional rendering with loading/error/success states

**Components to potentially reuse:**
- Modal structure from `ConfigInfoModal.svelte` (has loading states, error handling, proper accessibility)
- Graph visualization from `Canvas.svelte` using `@xyflow/svelte` (can create separate lineage graph view)
- API call patterns from `api.ts` (typed async functions with error handling)

**Backend logic to reference:**
- `trellis_datamodel/adapters/dbt_core.py` - Already parses manifest.json and catalog.json
- `trellis_datamodel/routes/manifest.py` - API endpoint pattern for returning data
- Pattern: Use adapter pattern, add lineage extraction logic to dbt_core adapter or create separate service

### Follow-up Questions

**Follow-up 1:** Should the modal show only upstream lineage, or also support downstream (where this entity's columns are used)? If both, should there be a toggle or tabs?
**Answer:** Upstream only for now

**Follow-up 2:** For identifying "source tables/raw data" in the upstream view, should we: a) Use dbt's `sources.yml` definitions to mark source tables? b) Use a folder-based heuristic (e.g., models in `1_raw` or `sources` folder)? c) Rely on dbt-colibri's detection?
**Answer:** Use dbt-colibri

**Follow-up 3:** For on-demand generation, should we: a) Show a loading spinner while generating lineage? b) Cache results per model after first generation (so subsequent views are instant)? c) Or regenerate every time (if processing is fast enough)?
**Answer:** Loading spinner for now. Then let's see how quick it is

**Follow-up 4:** Are there similar features in your codebase we should reference? For example: Modal components in the frontend, Graph visualization patterns, API endpoints that fetch and return graph data
**Answer:** Have a look pls

## Visual Assets

### Files Provided:
No visual assets provided.

### Visual Insights:
N/A

## Requirements Summary

### Functional Requirements

**Core Functionality:**
- Integrate dbt-colibri as Python library dependency for lineage extraction
- Add double-click handler to entity nodes in the canvas
- Open modal overlay when entity is double-clicked
- Display upstream table-level lineage graph in modal
- Show all upstream models back to source tables/raw data
- Use dbt-colibri for source table detection
- Generate lineage on-demand when user double-clicks (not pre-generated)
- Show loading spinner during lineage generation

**User Actions:**
- Double-click entity node → Opens lineage modal
- View upstream lineage graph in modal
- Close modal via backdrop click, escape key, or close button

**Data to be Managed:**
- Lineage data from dbt-colibri (table-level dependencies)
- Model relationships and source table identification
- Caching strategy TBD based on performance testing

### Reusability Opportunities

**Frontend Components:**
- Reuse modal pattern from `ConfigInfoModal.svelte` (loading states, error handling, accessibility)
- Reuse `@xyflow/svelte` graph visualization library (already used in `Canvas.svelte`)
- Create new `LineageModal.svelte` component following existing modal patterns
- Create new lineage graph view component using `@xyflow/svelte` (similar to `Canvas.svelte`)

**Backend Patterns:**
- Add new API endpoint `/api/lineage/{model_id}` following pattern in `routes/manifest.py`
- Integrate dbt-colibri lineage extraction into `adapters/dbt_core.py` or create separate service
- Use existing manifest.json/catalog.json parsing infrastructure

**API Patterns:**
- Add new function to `frontend/src/lib/api.ts` following existing async fetch patterns
- Use typed responses with error handling like existing API functions

### Scope Boundaries

**In Scope:**
- Table-level upstream lineage visualization
- Modal overlay UI for lineage view
- Double-click interaction on entity nodes
- Integration with dbt-colibri for lineage extraction
- On-demand lineage generation with loading states
- Source table detection via dbt-colibri

**Out of Scope:**
- Column-level lineage (future enhancement)
- Downstream lineage (future enhancement)
- Pre-generation or caching strategy (to be evaluated after performance testing)
- Side panel or separate route navigation (using modal for now)
- Column selection/filtering (table-level only for now)

### Technical Considerations

**Integration Points:**
- dbt-colibri as Python dependency (MIT license compatible)
- FastAPI backend for lineage API endpoint
- SvelteKit frontend for modal and graph visualization
- Existing `@xyflow/svelte` library for graph rendering

**Existing System Constraints:**
- Must work with existing dbt manifest.json and catalog.json parsing
- Must integrate with existing adapter pattern (`adapters/dbt_core.py`)
- Must follow existing API patterns (`/api` prefix, JSON responses)
- Must follow existing frontend component patterns (Svelte 5 runes, TypeScript)

**Technology Preferences:**
- Use dbt-colibri for lineage extraction (not custom implementation)
- Use existing `@xyflow/svelte` for graph visualization (already in use)
- Follow existing modal component patterns
- On-demand generation initially, performance testing will inform caching strategy

**Similar Code Patterns to Follow:**
- Modal: `frontend/src/lib/components/ConfigInfoModal.svelte`
- Graph visualization: `frontend/src/lib/components/Canvas.svelte`
- API endpoint: `trellis_datamodel/routes/manifest.py`
- Frontend API: `frontend/src/lib/api.ts`
- Backend adapter: `trellis_datamodel/adapters/dbt_core.py`
