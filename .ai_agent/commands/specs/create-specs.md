# Specification Creation Process

Create spec document for new feature. Spec = foundation for task planning + implementation.

## Process

1. Gather Requirements
2. Create Spec Structure  
3. Document Specification
4. Save Specification

## Step 1: Gather Requirements

Input sources:
- `/spar-idea` output (if exists)
- User describes feature
- Review related code/docs
- Check similar features

## Step 2: Create Spec Structure

Directory pattern: `specs/[YYYY-MM-DD]-[name]/`
Example: `specs/2025-01-15-user-authentication/`

Structure:
```
specs/[YYYY-MM-DD]-[name]/
  spec.md
```

## Step 3: Document Specification

`spec.md` structure:

```markdown
# [Feature Name] - Specification

## Overview
What feature does, why needed.

## Requirements

### Functional Requirements
- [requirement]

### Non-Functional Requirements  
- Performance
- Security
- Usability

## Scope

### In Scope
- Included items

### Out of Scope
- Explicitly excluded (prevents scope creep)

## Approach

### Technical Approach
- High-level strategy
- Key design decisions
- Integration points

### User Experience
- How users interact
- UI/UX notes

## Dependencies
- Prerequisites
- External dependencies
- Related systems

## Success Criteria
- How we know it's done
- Acceptance criteria

## Notes
- Context, constraints, considerations
```

Fill using:
- `/spar-idea` output
- User input
- `.cursor/project.md` (tech stack)
- Codebase patterns

## Step 4: Save Specification

Save to `specs/[YYYY-MM-DD]-[name]/spec.md`.

## Spec Self-Review (Required)

Before notifying user, scan and fix:

1. **Placeholder scan**: "TBD", "TODO", vague requirements?
2. **Internal consistency**: Sections contradict?
3. **Scope check**: Focused enough for one plan?
4. **Ambiguity check**: Multiple valid interpretations?

Fix inline. Then proceed.

Output:
```
Specification created!

✅ Spec: `specs/[YYYY-MM-DD]-[name]/spec.md`

NEXT STEP → Run `/plan-tasks`.
```

## Guidelines

- Be specific, not prescriptive
- Reference `.cursor/project.md`
- Follow codebase patterns
- Keep focused — avoid scope creep
- Make requirements testable