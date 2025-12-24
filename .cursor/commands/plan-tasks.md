# Task Planning Process

You are creating an implementation plan by breaking down a specification into actionable tasks.

## Process Overview

1. **Read Specification**
2. **Break Down into Tasks**
3. **Organize Tasks Logically**
4. **Create Tasks File**

## Step 1: Read Specification

Read the spec document:
- **Path**: `specs/[spec-name]/spec.md`
- If multiple specs exist, ask the user which one to use
- If no spec exists, prompt user to run `/create-specs` first

Understand:
- Requirements (functional and non-functional)
- Scope (in and out of scope)
- Technical approach
- Dependencies
- Success criteria

## Step 2: Break Down into Tasks

Break down the specification into actionable tasks. Each task should:
- Be specific and actionable
- Have a clear outcome
- Be appropriately sized (not too large, not too small)
- Be testable/verifiable

Consider:
- **Setup tasks**: Environment, dependencies, configuration
- **Core implementation**: Main feature development
- **Integration**: Connecting with existing systems
- **Testing**: Unit tests, integration tests
- **Documentation**: Code comments, README updates
- **Polish**: Error handling, edge cases, UX improvements

## Step 3: Organize Tasks Logically

Group related tasks and order them by:
- **Dependencies**: Tasks that must happen first
- **Logical flow**: Natural progression of work
- **Risk**: High-risk items early for early validation

Use markdown task lists with checkboxes:
```markdown
- [ ] Task description
- [ ] Another task
  - [ ] Subtask if needed
```

Group tasks under clear headings:
```markdown
## Setup & Configuration
- [ ] Task 1
- [ ] Task 2

## Core Implementation
- [ ] Task 3
- [ ] Task 4

## Testing
- [ ] Task 5
```

## Step 4: Create Tasks File

Create `tasks.md` in the spec directory:
- **Path**: `specs/[spec-name]/tasks.md`

Structure the file:

```markdown
# [Feature Name] - Implementation Tasks

## Overview
Brief reminder of what we're building (reference to spec.md)

## Tasks

[Your organized task list here]

## Notes
- Any implementation notes or reminders
- Reference to standards: `agent-os/standards/` if needed
```

Inform the user:
```
Task plan created!

✅ Tasks list: `specs/[spec-name]/tasks.md`

NEXT STEP 👉 Run `/execute` to start implementation.
```

## Guidelines

- Reference `.cursor/project.md` for tech stack context
- Consider referencing `agent-os/standards/` for coding guidelines
- Make tasks concrete - avoid vague descriptions
- Order tasks to minimize rework
- Include testing tasks - don't skip them
- Keep tasks focused - one task, one outcome

