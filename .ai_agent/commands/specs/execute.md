# Execution Process

Execute tasks from plan. Stop after specified work. Do NOT continue on own.

## Process

1. Accept Parameters
2. Read Task Plan
3. Filter Tasks
4. Implement Sequentially
5. Update Progress

## Step 1: Accept Parameters

Check for:
- **Specific Tasks**: Task IDs (e.g., "1", "2", "5")
- **Specific Streams**: Stream names (e.g., "Core Implementation")
- **Continue Flag**: Continue to next tasks after completing?

If no parameters: Ask user what to execute. Do NOT assume "all tasks".

## Step 2: Read Task Plan

- Path: `specs/[spec-name]/tasks.md`
- If multiple specs, ask which to execute
- If no tasks.md, prompt to run `/plan-tasks` first

Also read:
- Spec: `specs/[spec-name]/spec.md` (context)
- Project: `.cursor/project.md` (tech stack)

Understand: tasks, order, dependencies, requested streams.

## Step 3: Filter Tasks

Based on parameters:
- **Task IDs**: Only those exact tasks
- **Streams only**: Tasks within those streams
- **Both**: Match either (union)
- **Neither**: Ask user to specify

After filtering: do NOT continue automatically. Stop after filtered tasks.

## Step 4: Implement Sequentially

Work through filtered tasks:

1. Start with first task
2. Read carefully — understand requirement
3. Check dependencies — warn if outside filtered list
4. Implement:
   - Follow project patterns
   - Reference `agent-os/standards/`
   - Match spec requirements
5. Verify — complete and working
6. Move to next task
7. **Stop** after completing filtered tasks

### Implementation Guidelines

- Follow existing patterns
- Reference coding standards
- Write tests for new functionality
- Handle errors properly
- Document code where helpful

## Step 5: Update Progress

After completing task:

1. Mark complete in tasks.md: `- [ ]` → `- [x]`
2. Update subtasks if applicable
3. Continue to next task

Example:
```markdown
## Core Implementation
- [x] Task 1 - Completed
- [x] Task 2 - Completed  
- [ ] Task 3 - Next up
```

## Completion

When all filtered tasks complete:

1. Verify fully implemented
2. Run tests — ensure pass
3. Check lint/type errors
4. Inform user complete
5. **Stop** — do NOT continue unless asked

## Guidelines

- Respect parameters
- Stop after completion
- One task at a time
- Update progress in tasks.md
- Ask if stuck
- Test as you go
- Follow standards
- Check dependencies
- Report status clearly

## If You Need to Deviate

Plan needs changes:
- **Explain why**: What discovered?
- **Propose update**: Suggest fix
- **Get approval**: Ask before changing
- **Update plan**: Modify tasks.md if approved