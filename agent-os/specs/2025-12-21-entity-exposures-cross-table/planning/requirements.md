# Spec Requirements: Entity Exposures Cross-Table

## Initial Description

dbt has the feature to list downstream applications using the transformed models in a @dbt_company_dummy/models/exposures.yml 

I would like to show the usage of entities in a cross-table in a dedicated tab.

## Requirements Discussion

### First Round Questions

**Q1:** I'm assuming you'd like this as a new top-level tab alongside "Conceptual" and "Logical" in the main toolbar. Is that correct, or would you prefer a separate section/panel (like in the sidebar or a modal)?

**Answer:** Top navigation bar first. Maybe we can make the icons a bit narrower to save screenspace for the button.

**Q2:** For the cross-table structure, I'm thinking:
- Rows = entities, Columns = exposures (or vice versa)?
- Cells showing which entities are used by which exposures (checkmarks/X/usage count)?

**Answer:** rows = entities, yes with X's

**Q3:** For exposure data source, I'm assuming we'll:
- Read from `exposures.yml` in the dbt project directory
- Parse the `depends_on` references to map exposures to dbt models
- Then map those models to entities in the data model

Is that correct?

**Answer:** correct

**Q4:** For table interactivity, should users be able to:
- Click cells/rows/columns to navigate to related entities or exposures?
- Filter or sort the table?
- Export the table (CSV, etc.)?

**Answer:** for now maybe nothing first. just viewing

**Q5:** If no `exposures.yml` exists or no exposures reference entities, should we:
- Show an empty state with guidance?
- Hide the tab entirely?

**Answer:** show tab and have a helper box prompting the user to fill out exposure.yml

**Q6:** Should the table include exposure metadata (name, label, type, maturity, URL, owner) as:
- Tooltips on hover?
- Additional columns?
- A detail view on click?

**Answer:** use the Label for the table itself and maybe have the type as a tag/icon and description and owner as tooltip

**Q7:** If an entity has multiple bound dbt models and an exposure references one of them, should the table:
- Show all matching models?
- Just indicate the entity is used?

**Answer:** entity used for now

**Q8:** For scope boundaries, should this focus only on displaying the cross-table, or also include:
- Editing exposures from the UI?
- Creating new exposures?
- Syncing exposure changes back to `exposures.yml`?

**Answer:** no editing, no syncing now. just read only. perhaps we extend it but for now no feature for that

### Existing Code to Reference

No similar existing features identified for reference.

**Similar Features Identified:**
- View mode switcher pattern: `frontend/src/routes/+page.svelte` lines 925-953 (Conceptual/Logical tabs)
- Tab implementation in EntityNode: `frontend/src/lib/components/EntityNode.svelte` lines 995-1023 (model tabs when multiple models bound)
- Icon usage: Uses `@iconify/svelte` with icons like `octicon:workflow-16` and `lucide:database`

### Follow-up Questions

No follow-up questions needed.

## Visual Assets

### Files Provided:
No visual assets provided.

### Visual Insights:
N/A

## Requirements Summary

### Functional Requirements

- **New Tab in Navigation**: Add a third tab alongside "Conceptual" and "Logical" in the top navigation bar
  - Tab should be styled consistently with existing tabs
  - Icons in existing tabs should be made narrower to accommodate new tab
  - Tab should always be visible (not hidden when no exposures exist)

- **Cross-Table Display**: 
  - Rows = entities (from data model)
  - Columns = exposures (from exposures.yml)
  - Cells show X marks indicating entity usage by exposure
  - Table uses exposure `label` for column headers
  - Exposure `type` shown as tag/icon
  - Exposure `description` and `owner` shown as tooltips

- **Data Source & Mapping**:
  - Read `exposures.yml` from dbt project directory
  - Parse `depends_on` references to map exposures to dbt models
  - Map dbt models to entities via entity's `dbt_model` field
  - If entity has multiple bound models, show entity-level usage (not model-level)

- **Empty State**:
  - Show tab even when no exposures.yml exists
  - Display helper box prompting user to fill out exposures.yml
  - Provide guidance on how to create exposures.yml

- **Read-Only View**:
  - No editing capabilities
  - No syncing back to exposures.yml
  - Pure viewing/visualization feature

### Reusability Opportunities

- **View Mode Switcher Pattern**: Reuse the tab button styling and layout from `frontend/src/routes/+page.svelte` (lines 925-953)
- **Icon Component**: Use existing `@iconify/svelte` library for exposure type icons
- **Tooltip Pattern**: Follow existing tooltip patterns in the codebase
- **Empty State Pattern**: Reference existing empty state patterns (e.g., canvas empty state)

### Scope Boundaries

**In Scope:**
- Reading and parsing exposures.yml
- Mapping exposures to entities via dbt models
- Displaying cross-table with X marks
- Showing exposure labels, types (as icons/tags), descriptions and owners (as tooltips)
- Empty state with helper message
- New tab in navigation bar
- Making existing tab icons narrower

**Out of Scope:**
- Editing exposures from UI
- Creating new exposures from UI
- Syncing changes back to exposures.yml
- Filtering or sorting table
- Click interactions to navigate
- Export functionality
- Model-level granularity (only entity-level)

### Technical Considerations

- **Backend**: Need API endpoint to read and parse exposures.yml, map to entities
- **Frontend**: Need new table component (no existing table components found)
- **State Management**: May need new store or extend existing stores for exposure data
- **View Mode**: Need to extend `viewMode` store to include new "exposures" mode, or create separate state
- **File Path**: exposures.yml location relative to dbt project path (likely in models/ directory)
- **dbt Model References**: exposures.yml uses `ref('model_name')` format, need to resolve to full unique_id
- **Icon Selection**: Need appropriate icons for different exposure types (dashboard, notebook, application, etc.)
