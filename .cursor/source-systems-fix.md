# Fix: Source Systems Persistence and Dropdown Suggestions

## Problem
1. **Source systems were not being written to `data_model.yml`** - When users added source systems to unbound entities (entities without a dbt model binding), these sources weren't being persisted to the YAML file.
2. **Dropdown suggestions weren't accumulating** - Since sources weren't persisted, the dropdown in the SourceEditorModal couldn't suggest previously added sources.

## Root Cause
The `buildDataModelFromState` method in `frontend/src/lib/services/auto-save.ts` was not including the `source_system` field when building the DataModel object to send to the backend. This meant even though the frontend stored `source_system` in node data, it was never serialized and sent to the API.

## Solution

### Frontend Change
**File: `frontend/src/lib/services/auto-save.ts` (lines 240-263)**

Added logic to include `source_system` in the entity object sent to the backend:
- Extract `source_system` from node data
- Only persist `source_system` for **unbound entities** (those without a `dbt_model` binding)
- This matches the backend's expectation: bound entities get source systems from lineage, while unbound entities use persisted mock sources

```typescript
const source_system = ((n.data as any)?.source_system) as string[] | undefined;
const entity: any = {
    // ... existing fields ...
};

// Only persist source_system for unbound entities
// Bound entities get source_system from lineage
if (!isBound && source_system && source_system.length > 0) {
    entity.source_system = source_system;
}

return entity;
```

### Backend Validation
**File: `trellis_datamodel/routes/data_model.py`**

The backend already had the correct logic in place:
- Line 240-243: Only persists `source_system` for unbound entities
- Line 243: Debug log to verify persistence: `"DEBUG: Entity {entity_id} is unbound, persisting source_system: ..."`

The API endpoint `GET /source-systems/suggestions` already collects suggestions from both:
1. Mock sources from unbound entities in `data_model.yml` (line 321)
2. Lineage-derived sources from bound entities (line 345+)

## How It Works Now

### Adding a Source to an Unbound Entity
1. User opens "Edit Source Systems" modal
2. User adds a source (e.g., "SAP", "Oracle") via the SourceEditorModal
3. `handleSourcesUpdate` updates node data with `source_system: ["SAP", "Oracle"]`
4. AutoSave debounces and calls `buildDataModelFromState`
5. **NEW**: `source_system` is now included in the entity object
6. API receives the updated entity with `source_system` field
7. Backend persists it to `data_model.yml` only for unbound entities

### Getting Dropdown Suggestions
1. User opens SourceEditorModal for another entity
2. Modal calls `getSourceSystemSuggestions()` API
3. Backend reads `data_model.yml` and finds the sources added to the previous entity
4. Suggestions now include previously added sources

## Key Points
- ✓ Source systems are **only persisted for unbound entities** (entities without `dbt_model`)
- ✓ Bound entities get source systems from lineage (read-only)
- ✓ Suggestions dropdown consolidates:
  - Mock sources from unbound entities
  - Lineage-derived sources from bound entities
- ✓ No schema changes required
- ✓ Backward compatible with existing data models

## Testing
To verify the fix works:
1. Create a new unbound entity (without binding to a dbt model)
2. Add source systems (e.g., "SAP", "Salesforce")
3. Save (AutoSave will persist to YAML)
4. Create another unbound entity
5. Open "Edit Source Systems" modal
6. Verify previously added sources appear in the dropdown suggestions

Check the backend logs for the debug message:
```
DEBUG: Entity {entity_id} is unbound, persisting source_system: ['SAP', 'Salesforce']
```
