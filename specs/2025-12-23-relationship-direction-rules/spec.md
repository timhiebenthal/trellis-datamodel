# Relationship Direction Rules - Specification

## Overview

Currently, relationship labels in the conceptual data model don't always follow expected direction based on either semantic meaning (parent/child) or visual screen position. This creates confusion, especially in the conceptual modeling stage where visual clarity is critical.

This feature establishes consistent rules for relationship direction, ensuring labels always read naturally from the "1" side to the "*" side (parent → child), while providing flexibility for greenfield projects where semantic information isn't yet available.

## Requirements

### Functional Requirements

1. **Consistent Direction Rule**
   - Relationships must always be named from the "1" side to the "*" side (parent → child)
   - This applies to `one_to_many` relationships: source = parent (1), target = child (*)
   - This applies to `many_to_one` relationships: source = child (*), target = parent (1)
   - For `one_to_one` relationships: source = FK holder, target = referenced table (matches dbt semantics)

2. **Auto-Detection from dbt**
   - When inferring relationships from dbt relationship tests:
     - Parent = model referenced in `to` field (already correct)
     - Child = model where test is defined (has FK column)
     - Direction should be parent → child (1 → *)
   - Current implementation already follows this correctly

3. **User Drag Behavior**
   - When user drags a field to create a relationship:
     - **If dbt models are bound**: Detect FK/PK semantics to determine parent/child
       - If source field is FK and target field is PK → flip to target → source
       - If source field is PK and target field is FK → keep source → target
       - If both are PKs or both are FKs → use drag direction as fallback
     - **If no dbt models (greenfield)**: Use drag direction (source → target)
       - User can manually swap if needed

4. **Swap Direction Control**
   - Provide a "swap direction" button/control in the relationship editor
   - Swaps `source` ↔ `target`, `source_field` ↔ `target_field`
   - Updates relationship type accordingly:
     - `one_to_many` ↔ `many_to_one`
     - `one_to_one` remains `one_to_one` (just swaps direction)
     - `many_to_many` remains `many_to_many` (just swaps direction)
   - Available for manual override in all cases

5. **Label Display**
   - Relationship label reads as: `${sourceName} ${verb} ${targetName}`
   - Example: "department employs employee" (department = 1, employee = *)
   - Label should align with visual arrow direction when possible

### Non-Functional Requirements

- **Backward Compatibility**: Existing relationships in saved data models should continue to work
- **Performance**: Direction detection should not significantly slow down relationship creation
- **Usability**: Rules should be intuitive - users shouldn't need to understand implementation details
- **Consistency**: Same relationship should always have same direction regardless of how it was created

## Scope

### In Scope

- Updating user drag logic to detect FK/PK semantics when dbt models are available
- Adding swap direction functionality to relationship editor
- Ensuring dbt inference maintains correct direction (already correct, verify)
- Updating relationship type logic to match direction rules
- Handling one-to-one relationships with FK-based direction

### Out of Scope

- Changing how relationships are stored in YAML (structure stays the same)
- Automatic layout adjustment based on relationship direction
- Inferring FK/PK from field names (e.g., `*_id` pattern matching)
- Changing existing relationship direction in saved data models (preserve user intent)

## Approach

### Technical Approach

1. **FK/PK Detection Logic**
   - When creating relationship from drag:
     - Check if both entities have bound dbt models
     - Query dbt manifest/catalog for column information
     - Check if source field is FK (references another table) or PK (primary key)
     - Check if target field is FK or PK
     - Determine parent/child based on FK/PK semantics
     - Flip direction if needed to maintain 1 → * rule

2. **Swap Direction Implementation**
   - Add swap button to `CustomEdge.svelte` relationship editor
   - Create function to swap relationship direction:
     ```typescript
     function swapDirection() {
       // Swap source/target
       // Swap source_field/target_field
       // Update type: one_to_many ↔ many_to_one
       // Update edge data
     }
     ```

3. **Relationship Type Updates**
   - When direction is determined or swapped:
     - `one_to_many`: source = 1 (parent), target = * (child)
     - `many_to_one`: source = * (child), target = 1 (parent)
     - `one_to_one`: source = FK holder, target = referenced table
     - `many_to_many`: direction is arbitrary, preserve user choice

4. **Integration Points**
   - `frontend/src/lib/components/EntityNode.svelte`: Update `onFieldDrop` function
   - `frontend/src/lib/components/CustomEdge.svelte`: Add swap button and logic
   - `frontend/src/lib/utils.ts`: Add helper functions for FK/PK detection
   - `trellis_datamodel/adapters/dbt_core.py`: Verify inference logic (already correct)

### User Experience

1. **Creating Relationships**
   - User drags field A → field B
   - If dbt models available: System auto-detects direction, may flip if needed
   - If greenfield: Uses drag direction, user can swap if needed
   - Relationship appears with correct direction and type

2. **Editing Relationships**
   - User clicks relationship label to edit
   - Swap button visible next to cardinality button
   - Clicking swap immediately flips direction and updates display
   - Changes persist when relationship is saved

3. **Visual Feedback**
   - Relationship arrow direction matches label reading direction
   - Cardinality indicator (1 → *) matches semantic direction
   - No confusion about which side is parent/child

## Dependencies

- Access to dbt manifest/catalog for FK/PK detection
- Existing relationship type system (`one_to_many`, `many_to_one`, etc.)
- Relationship editor UI in `CustomEdge.svelte`
- Field drag functionality in `EntityNode.svelte`

## Success Criteria

1. **Functional**
   - All relationships created from dbt inference maintain parent → child direction
   - User drag relationships auto-detect direction when dbt models are available
   - Swap button successfully flips relationship direction
   - Relationship types correctly reflect direction (1 → *)

2. **User Experience**
   - Users can create relationships without confusion about direction
   - Labels read naturally from parent to child
   - Visual direction matches semantic direction
   - Greenfield users can easily set and correct direction

3. **Technical**
   - No breaking changes to existing data model YAML structure
   - Existing relationships continue to work correctly
   - Performance impact is negligible

## Notes

### Current Behavior Analysis

**dbt Inference** (`trellis_datamodel/adapters/dbt_core.py` lines 708-721):
- ✅ Already correct: `source` = parent (referenced model), `target` = child (model with FK)
- ✅ Direction: parent → child (1 → *)
- ✅ Field mapping: `source_field` = PK, `target_field` = FK

**User Drag** (`frontend/src/lib/components/EntityNode.svelte` lines 864-875):
- ⚠️ Currently: `source` = drag start, `target` = drag end
- ⚠️ Always sets `type: "one_to_many"` regardless of actual semantics
- ⚠️ No FK/PK detection

### Implementation Considerations

- FK/PK detection may require querying dbt manifest - ensure this is fast
- For greenfield projects, we can't infer FK/PK, so drag direction is best default
- Swap button should be prominent but not intrusive in the UI
- Consider adding visual indicator (icon) showing which side is parent/child

### Edge Cases

- **Both entities unbound**: Use drag direction, allow manual swap
- **One entity bound, one unbound**: Use drag direction, allow manual swap
- **Both fields are PKs**: Likely many-to-many or one-to-one, use drag direction
- **Both fields are FKs**: Unusual case, use drag direction
- **No field information**: Use drag direction

