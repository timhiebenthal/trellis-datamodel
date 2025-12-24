# Execution Process

You are implementing tasks from a task plan. Your goal is to execute tasks sequentially, update progress, and stick to the plan.

## Process Overview

1. **Read Task Plan**
2. **Implement Tasks Sequentially**
3. **Update Progress**
4. **Follow Standards**

## Step 1: Read Task Plan

Read the tasks file:
- **Path**: `specs/[spec-name]/tasks.md`
- If multiple specs exist, ask the user which one to execute
- If no tasks.md exists, prompt user to run `/plan-tasks` first

Also read:
- **Spec**: `specs/[spec-name]/spec.md` for context and requirements
- **Project Context**: `.cursor/project.md` for tech stack and mission

Understand:
- What tasks need to be done
- The order of tasks
- Dependencies between tasks

## Step 2: Implement Tasks Sequentially

Work through tasks in order:

1. **Start with the first unchecked task**
2. **Read the task carefully** - understand what needs to be done
3. **Check dependencies** - ensure prerequisites are met
4. **Implement the task**:
   - Write code following project patterns
   - Reference `agent-os/standards/` for coding guidelines if needed
   - Follow the tech stack from `.cursor/project.md`
   - Make sure implementation matches the spec requirements
5. **Verify the task** - ensure it's complete and working
6. **Move to next task**

### Implementation Guidelines

- **Follow existing patterns**: Look at similar code in the codebase
- **Reference standards**: Check `agent-os/standards/` for:
  - Backend: API design, models, queries
  - Frontend: Components, CSS, accessibility
  - Global: Coding style, error handling, testing
- **Write tests**: Include tests for new functionality
- **Handle errors**: Implement proper error handling
- **Document code**: Add comments where helpful

## Step 3: Update Progress

After completing each task (or logical group of tasks):

1. **Mark task as complete** in `tasks.md`:
   - Change `- [ ]` to `- [x]`
2. **Update any subtasks** if applicable
3. **Continue to next task**

Example:
```markdown
## Core Implementation
- [x] Task 1 - Completed
- [x] Task 2 - Completed
- [ ] Task 3 - Next up
```

## Step 4: Follow Standards

When implementing, reference:

- **`.cursor/project.md`**: For tech stack decisions and project mission
- **`agent-os/standards/`**: For coding standards:
  - `backend/` - API, models, migrations, queries
  - `frontend/` - Components, CSS, accessibility, responsive
  - `global/` - Coding style, commenting, error handling, validation
  - `testing/` - Test writing guidelines

## Completion

When all tasks are marked complete:

1. **Final verification**: Review that all requirements from spec.md are met
2. **Run tests**: Ensure all tests pass
3. **Check for issues**: Look for linting errors, type errors, etc.
4. **Inform user**: Let them know implementation is complete

## Guidelines

- **Stick to the plan**: Don't deviate unless there's a good reason
- **One task at a time**: Focus on completing current task before moving on
- **Update progress**: Keep tasks.md updated as you work
- **Ask if stuck**: If blocked, ask the user for clarification
- **Don't skip tasks**: Complete all tasks in the plan
- **Test as you go**: Don't leave all testing until the end
- **Follow standards**: Reference project standards for consistency

## If You Need to Deviate

If you discover the plan needs changes:
- **Explain why**: What did you discover that requires a change?
- **Propose update**: Suggest how to update the plan
- **Get approval**: Ask user before making significant changes
- **Update plan**: Modify tasks.md if approved

