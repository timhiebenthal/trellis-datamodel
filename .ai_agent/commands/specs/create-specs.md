# Specification Creation Process

You are creating a specification document for a new feature or change. This spec will serve as the foundation for task planning and implementation.

## Process Overview

1. **Gather Requirements**
2. **Create Spec Structure**
3. **Document Requirements, Scope, and Approach**
4. **Save Specification**

## Step 1: Gather Requirements

If you have results from `/spar-idea`, use those as the foundation. Otherwise:

- Ask the user to describe the idea or feature
- Review any existing documentation or related code
- Check for similar features that might inform this spec

## Step 2: Create Spec Structure

Create a new spec directory following this pattern:
- **Path**: `specs/[YYYY-MM-DD]-[descriptive-name]/`
- **Example**: `specs/2025-01-15-user-authentication/`

Create the directory structure:
```
specs/[YYYY-MM-DD]-[name]/
  spec.md
```

## Step 3: Document Specification

Create `spec.md` with the following structure:

```markdown
# [Feature Name] - Specification

## Overview
Brief description of what this feature does and why it's needed.

## Requirements

### Functional Requirements
- [Requirement 1]
- [Requirement 2]
- [Requirement 3]

### Non-Functional Requirements
- Performance considerations
- Security considerations
- Usability considerations

## Scope

### In Scope
- What will be included

### Out of Scope
- What will be explicitly excluded (helps prevent scope creep)

## Approach

### Technical Approach
- High-level technical strategy
- Key design decisions
- Integration points with existing code

### User Experience
- How users will interact with this feature
- UI/UX considerations (if applicable)

## Dependencies
- What needs to be in place first
- External dependencies
- Related features or systems

## Success Criteria
- How we'll know this is complete and successful
- Acceptance criteria

## Notes
- Any additional context, constraints, or considerations
```

Fill in each section based on:
- The validated idea from `/spar-idea` (if available)
- User input and clarification
- Project context from `.cursor/project.md`
- Existing codebase patterns

## Step 4: Save Specification

Save the completed `spec.md` file to `specs/[YYYY-MM-DD]-[name]/spec.md`.

Inform the user:
```
Specification created!

✅ Spec document: `specs/[YYYY-MM-DD]-[name]/spec.md`

NEXT STEP 👉 Run `/plan-tasks` to create an implementation plan.
```

## Guidelines

- Be specific but not overly prescriptive
- Reference `.cursor/project.md` for tech stack and mission alignment
- Consider existing patterns in the codebase
- Keep it focused - avoid scope creep
- Make requirements testable and measurable

