# Execution Process

You are implementing tasks from a task plan. Your goal is to execute specific tasks or streams (if provided), update progress, and stick to the plan. **You will not continue on your own** after completing the specified work.

## Process Overview

1. **Accept Parameters**
2. **Read Task Plan**
3. **Filter Tasks**
4. **Implement Tasks Sequentially**
5. **Update Progress**
6. **Follow Standards**

## Step 1: Accept Parameters

Before reading the task plan, check for the following parameters provided by the user:

- **Specific Tasks**: A list of task IDs (e.g., "1", "2", "5") or task names to execute
- **Specific Streams**: A list of stream/section names (e.g., "Core Implementation", "Testing") to execute
- **Continue Flag**: A flag indicating whether to continue to next tasks after completing specified ones

**If no parameters are provided**: Prompt the user to specify which tasks or streams to execute, or ask if they want to execute all tasks.

**If parameters are provided**: Only work on those specific tasks/streams and **stop** after completing them (unless continue flag is set to true).

## Step 2: Read Task Plan

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
- Which streams/tasks are being requested

## Step 3: Filter Tasks

Based on the parameters received:

**If specific task IDs are provided**:
- Only work on those exact task IDs (e.g., tasks numbered 1, 3, 5)
- Ignore all other tasks

**If specific streams are provided**:
- Only work on tasks within those named streams/sections
- Ignore tasks in other streams

**If both are provided**:
- Work on tasks that match either criteria (union)

**If neither is provided**:
- Ask user to specify what to execute - do not assume "all tasks"

**Important**: After filtering, **do not** continue to other tasks automatically. Stop after completing the filtered tasks.

## Step 4: Implement Tasks Sequentially

Work through the filtered tasks in order:

1. **Start with the first task from the filtered list**
2. **Read the task carefully** - understand what needs to be done
3. **Check dependencies** - ensure prerequisites are met (warn user if dependencies are outside the filtered list)
4. **Implement the task**:
   - Write code following project patterns
   - Reference `agent-os/standards/` for coding guidelines if needed
   - Follow the tech stack from `.cursor/project.md`
   - Make sure implementation matches the spec requirements
5. **Verify the task** - ensure it's complete and working
6. **Move to next filtered task**
7. **Stop after completing all filtered tasks** - **do not continue to other tasks**

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

When all filtered tasks are marked complete:

1. **Verify completed work**: Review that the specified tasks are fully implemented
2. **Run tests**: Ensure tests pass for the completed work
3. **Check for issues**: Look for linting errors, type errors, etc.
4. **Inform user**: Let them know the specified tasks are complete
5. **Stop**: Do not automatically continue to other tasks unless explicitly asked

## Guidelines

- **Respect parameters**: Only work on tasks/streams that were specified
- **Stop after completion**: Do not continue to other tasks unless explicitly instructed
- **One task at a time**: Focus on completing current task before moving on
- **Update progress**: Keep tasks.md updated as you work
- **Ask if stuck**: If blocked, ask the user for clarification
- **Test as you go**: Don't leave all testing until the end
- **Follow standards**: Reference project standards for consistency
- **Check dependencies**: If a specified task has dependencies outside the filtered list, warn the user
- **Report status**: Clearly communicate what tasks you completed and what remains

## If You Need to Deviate

If you discover the plan needs changes:
- **Explain why**: What did you discover that requires a change?
- **Propose update**: Suggest how to update the plan
- **Get approval**: Ask user before making significant changes
- **Update plan**: Modify tasks.md if approved

