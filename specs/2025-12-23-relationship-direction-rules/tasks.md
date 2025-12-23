# Relationship Direction Rules - Implementation Tasks

## Overview

Implement consistent relationship direction rules ensuring labels always read from "1" side to "*" side (parent → child). Add FK/PK detection for auto-orientation when dbt models are available, and provide swap direction control for manual override.

Reference: `spec.md` for full requirements and approach.

## Tasks

### Setup & Analysis

- [x] Verify dbt inference direction is correct (already implemented correctly)
  - [x] Review `trellis_datamodel/adapters/dbt_core.py` lines 708-721
  - [x] Confirm source = parent, target = child, direction = 1 → *
  - [x] Document current behavior as baseline

- [x] Create utility function to detect FK/PK from model schemas
  - [x] Add function in `frontend/src/lib/utils.ts`
  - [x] Function signature: `detectFieldSemantics(modelName: string, fieldName: string, otherModelName: string, modelSchemas: Map<string, ModelSchema>): 'fk' | 'pk' | 'unknown'`
  - [x] FK detection: Check if field has `relationships` test in schema
  - [x] PK detection: Check if field is referenced by other model's relationship tests
  - [x] Handle edge cases (no schema, no tests, etc.)

- [x] Add API endpoint or enhance existing endpoint to get model schema with relationship tests
  - [x] Check if `/api/models/{model_name}/schema` already returns relationship test info
  - [x] Verified: Endpoint already returns relationship test info via `yaml_handler.get_columns()` which extracts `data_tests`
  - [x] Frontend can access this information via `getModelSchema()` API function

### Core Implementation - FK/PK Detection

- [x] Update `onFieldDrop` in `EntityNode.svelte` to detect FK/PK semantics
  - [x] Check if both source and target entities have bound dbt models
  - [x] Query model schemas for both entities (use existing API)
  - [x] Detect FK/PK for source field and target field
  - [x] Determine if direction needs to be flipped:
    - [x] If source = FK and target = PK → flip direction
    - [x] If source = PK and target = FK → keep direction
    - [x] Otherwise → use drag direction (fallback)
  - [x] Update relationship creation to use detected direction

- [x] Update relationship type determination logic
  - [x] When FK/PK detected: Set type based on semantics
    - [x] FK → PK = flip to PK → FK = `one_to_many` (parent → child)
    - [x] PK → FK = keep direction = `one_to_many` (parent → child)
  - [x] When no FK/PK info: Default to `one_to_many` (current behavior)
  - [x] For `one_to_one`: User can manually set via toggle button (FK holder → referenced table rule applies)

- [x] Handle edge cases in FK/PK detection
  - [x] Both entities unbound: Use drag direction (implemented - checks for sourceActiveModel && targetActiveModel)
  - [x] One entity bound, one unbound: Use drag direction (implemented - same check)
  - [x] Both fields are PKs: Use drag direction (implemented - falls back when semantics don't match FK→PK or PK→FK)
  - [x] Both fields are FKs: Use drag direction (implemented - same fallback)
  - [x] No field information available: Use drag direction (implemented - try/catch handles errors)

### Swap Direction Control

- [x] Add swap direction function to `CustomEdge.svelte`
  - [x] Create `swapDirection()` function
  - [x] Swap `source` ↔ `target` in edge data
  - [x] Swap `source_field` ↔ `target_field` in edge data
  - [x] Update relationship type:
    - [x] `one_to_many` ↔ `many_to_one`
    - [x] `one_to_one` → remains `one_to_one` (just swaps direction)
    - [x] `many_to_many` → remains `many_to_many` (just swaps direction)
  - [x] Update all models array entries if multiple models exist
  - [x] Update edge ID to match new source/target
  - [x] Persist changes to edge store

- [x] Add swap button UI to relationship editor
  - [x] Add button next to cardinality toggle button in expanded view
  - [x] Use appropriate icon (lucide:arrow-left-right)
  - [x] Style consistently with existing UI (teal theme)
  - [x] Add tooltip: "Swap relationship direction"
  - [x] Ensure button is accessible (keyboard navigation, ARIA labels)

- [x] Update edge update logic to handle direction swaps
  - [x] Ensure `updateEdge` function properly updates all edge properties (swapDirection updates all properties)
  - [x] Relationship aggregation logic already handles direction changes (mergeRelationshipIntoEdges works with any direction)
  - [ ] Test that swaps persist when saving data model (manual testing needed)

### Relationship Type Logic

- [x] Ensure relationship types match direction rules
  - [x] `one_to_many`: source = 1 (parent), target = * (child) - verified in implementation
  - [x] `many_to_one`: source = * (child), target = 1 (parent) - handled in swap function
  - [x] `one_to_one`: source = FK holder, target = referenced table - user can set via toggle
  - [x] `many_to_many`: direction is arbitrary, preserve user choice - handled in swap function

- [x] Update relationship type display logic
  - [x] Cardinality indicator (1 → *) matches semantic direction - already implemented in CustomEdge
  - [x] `CustomEdge.svelte` displays correct cardinality based on type and direction - already working

### Testing

- [x] Unit tests for FK/PK detection utility
  - [x] Test FK detection (field with relationship test)
  - [x] Test PK detection (field referenced by relationship tests)
  - [x] Test unknown case (no tests, no references)
  - [x] Test edge cases (missing schema, missing fields)

- [ ] Integration tests for relationship creation
  - [ ] Test drag from FK to PK (should flip direction)
  - [ ] Test drag from PK to FK (should keep direction)
  - [ ] Test drag with no dbt models (should use drag direction)
  - [ ] Test drag with one bound entity (should use drag direction)

- [ ] UI tests for swap direction
  - [ ] Test swap button appears in relationship editor
  - [ ] Test swap button functionality (flips direction, updates type)
  - [ ] Test swap persists after save
  - [ ] Test swap with multiple models (all models updated)

- [ ] End-to-end tests
  - [ ] Create relationship from dbt inference (verify direction)
  - [ ] Create relationship from drag with dbt models (verify auto-detection)
  - [ ] Create relationship from drag without dbt models (verify drag direction)
  - [ ] Swap relationship direction (verify all properties update)

### Documentation & Polish

- [x] Add code comments explaining FK/PK detection logic
  - [x] Document detection algorithm
  - [x] Explain fallback behavior
  - [x] Note edge cases

- [x] Update inline documentation for relationship direction rules
  - [x] Document "always name from 1 → *" rule
  - [x] Explain when auto-detection works vs. manual override needed

- [x] Verify backward compatibility
  - [x] YAML structure unchanged - relationships still use same fields (source, target, type, source_field, target_field, etc.)
  - [x] No breaking changes - implementation only affects how relationships are created, not how they're stored
  - [x] Existing relationships continue to work - they load and display correctly

- [ ] Performance optimization
  - [ ] Cache model schema lookups if needed
  - [ ] Ensure FK/PK detection doesn't slow down relationship creation
  - [ ] Profile relationship creation with dbt models vs. without

## Notes

### Implementation Considerations

- **FK/PK Detection**: The simplest approach is to check if a field has a `relationships` test (FK) or is referenced by one (PK). This requires access to model schemas, which may need to be fetched from the backend API.

- **API Access**: Check if `/api/models/{model_name}/schema` endpoint already provides relationship test information. If not, we may need to enhance it or create a new utility function that queries schema files directly.

- **Performance**: FK/PK detection requires scanning schema files or querying APIs. Consider caching results or making detection async/non-blocking.

- **Swap Button Placement**: Place next to cardinality toggle button in the expanded relationship editor view. Should be visually distinct but not intrusive.

- **Edge Cases**: Many edge cases where we can't detect FK/PK (greenfield, unbound entities, etc.). Always fall back to drag direction in these cases.

### Reference Files

- `frontend/src/lib/components/EntityNode.svelte` - Field drag handler (lines 770-881)
- `frontend/src/lib/components/CustomEdge.svelte` - Relationship editor UI
- `frontend/src/lib/utils.ts` - Utility functions
- `trellis_datamodel/adapters/dbt_core.py` - dbt inference logic (lines 708-721)
- `trellis_datamodel/routes/schema.py` - Schema API endpoints

### Standards Reference

- Follow existing code patterns in frontend components
- Use TypeScript types from `frontend/src/lib/types.ts`
- Maintain consistency with existing UI styling (Tailwind CSS, teal theme)
- Reference `agent-os/standards/` for coding guidelines if needed

