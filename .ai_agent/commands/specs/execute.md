# Execution Process

Execute tasks from plan. Stop after specified work. Do NOT continue on own.

## Process

1. Accept Parameters
2. Read Task Plan
3. Filter Tasks
4. Implement with TDD
5. Verify Before Claiming Complete
6. Update Progress

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

## Step 3b: Parallelization via Subagents

Before executing, check current sprint for parallel streams.

**When to dispatch subagents:**
- Sprint has 2+ independent streams (no cross-stream dependencies in this sprint)
- Streams touch different files (KEY RULE from plan-tasks: 1 file = 1 stream)

**When NOT to dispatch subagents:**
- Only 1 stream in sprint
- Stream has `⚠️ Depends on:` marker pointing to incomplete work in same sprint
- User specified exact task IDs (not streams) — execute sequentially in main agent

**How to dispatch:**

Dispatch one subagent per independent stream. Each subagent receives:

1. Full stream task list (exact checkboxes from tasks.md)
2. Relevant spec section(s) for that stream's scope
3. Tech stack from `.cursor/project.md`
4. TDD iron law: NO production code without failing test first. RED → verify fail → GREEN → verify pass → REFACTOR.
5. Verification iron law: NO completion claims without running command and showing output.
6. Instruction to update tasks.md checkboxes for its stream when done

After all subagents complete:
- Collect results
- Check for conflicts (unexpected file overlaps)
- Run full test suite in main agent — show output
- Proceed to between-sprint review before next sprint

## Step 4: Implement with TDD

### The Iron Law

```
NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST
```

Written code before test? Delete it. Start over from test.

No exceptions:
- Don't keep as "reference"
- Don't "adapt" existing code while writing tests
- Delete means delete

### RED-GREEN-REFACTOR Cycle (Mandatory per task)

**RED — Write Failing Test**

Write one minimal test for behavior this task implements.

Requirements:
- One specific behavior per test
- Clear descriptive name
- Test real code behavior, not mocks (unless unavoidable)

**Verify RED — Run Test, Confirm Failure**

MANDATORY. Never skip.

```bash
uv run pytest path/to/test_file.py::test_name -v
# OR
cd frontend && npm test -- path/to/test.ts
```

Confirm ALL of:
- Test **fails** (not errors due to typos)
- Failure message is what you expect
- Fails because feature is missing, not bug in test

Test passes immediately? Testing existing behavior. Fix test.
Test errors? Fix, re-run until fails correctly.

**GREEN — Write Minimal Implementation**

Write simplest code that makes test pass. Nothing more.

Do NOT:
- Add features not yet tested
- Refactor adjacent code
- "Improve" beyond what test requires

**Verify GREEN — Run Test, Confirm Pass**

MANDATORY.

```bash
uv run pytest path/to/test_file.py::test_name -v
# AND full suite
uv run pytest
```

Confirm ALL of:
- Target test passes
- All other tests still pass
- No new warnings or errors in output

Test fails? Fix code, not test.
Other tests fail? Fix now before proceeding.

**REFACTOR — Clean Up (stay green)**

After green only:
- Remove duplication
- Improve names
- Extract helpers

Keep tests green throughout. Do not add behavior.

**Repeat** for next behavior in task.

### Implementation Guidelines

- Follow existing patterns in codebase
- Reference coding standards
- Handle errors properly
- Document non-obvious intent only

## Step 5: Verify Before Claiming Complete

### The Iron Law

```
NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE
```

If command not run in this message, cannot claim it passes.

### Verification Gate (Required before marking any task done)

1. **Identify** command(s) that prove task is complete
2. **Run** full command fresh — no relying on earlier runs
3. **Read** full output: exit code, pass count, failure count
4. **Check requirements**: re-read task + spec section, confirm each met
5. **Only then** mark complete and report status

### Required Checks

| Claim | Must Run | Evidence Required |
|-------|----------|-------------------|
| Tests pass | `uv run pytest` or `npm test` | "X passed, 0 failed" |
| Frontend clean | `cd frontend && npm run check` | 0 type errors |
| Build works | `make build-package` | exit 0 |
| Bug fixed | Test reproducing bug | RED then GREEN cycle |
| Task complete | All above relevant checks | Shown output |

### Red Flags — STOP

Catch yourself doing any? Stop + verify first:

- Using "should", "probably", "seems to", "looks like"
- Expressing satisfaction before verification ("Done!", "Great!", "Fixed!")
- About to mark `[x]` without having just run test command
- Trusting previous run from earlier in session
- Skipping checks because "it's a small change"

### Common Rationalizations — All Wrong

| Excuse | Reality |
|--------|---------|
| "Should work now" | Run verification |
| "I'm confident" | Confidence ≠ evidence |
| "Just this once" | No exceptions |
| "Tests passed earlier" | Run again now |
| "It's a small change" | Small changes break things |

## Step 6: Update Progress

After task verified complete:

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

## Between Tasks: Code Review Checkpoint

After task (or batch of 2-3 related), pause + review:

1. **Re-read spec section** for what was just implemented
2. **Check git diff**: `git diff HEAD~N` — does it match plan?
3. **Verify no unintended side effects**: changed files outside task scope?
4. **Confirm no placeholders**: no stubs, TODOs, or "will implement later"

If issues found: fix before marking complete and moving on.

## Completion

When all filtered tasks complete:

1. Run full test suite — show output
2. Run `cd frontend && npm run check` if frontend touched
3. Re-read spec success criteria — confirm each met
4. Report status with evidence
5. Update version + changelog (see below)
6. **Stop** — do NOT continue unless asked

## Versioning + Changelog (Required after feature/fix)

### Determine bump type

| Change type | Bump |
|-------------|------|
| Breaking API/behavior change | `major` (X.0.0) |
| New feature, backward-compatible | `minor` (0.X.0) |
| Bug fix | `patch` (0.0.X) |

For bug fixes: after verification passes, ask user:

> "Fix verified. Patch bump to `0.X.Y` directly, or stage as beta (`0.X.Y-beta.1`) for extra verification before release?"

Wait for answer before bumping.

### Update `pyproject.toml`

Bump `version = "X.Y.Z"` under `[project]`.

### Update `CHANGELOG.md`

Prepend new entry above current latest, using Keep a Changelog format:

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- **Feature name**: what it does and why.

### Fixed
- **Bug name**: what broke and how fixed.

### Changed
- **Thing changed**: old behavior → new behavior.
```

Rules:
- Use today's date
- Only include sections with actual changes (`Added` / `Fixed` / `Changed` / `Removed`)
- Bold the subject, plain prose description — match existing entry style
- One entry per logical change, not per file touched

## Guidelines

- Respect parameters
- Stop after completion
- One task at a time
- Update progress in tasks.md
- Ask if stuck
- Follow TDD strictly — no exceptions
- Check dependencies
- Report status with evidence, not claims

## If You Need to Deviate

Plan needs changes:
- **Explain why**: What did you discover?
- **Propose update**: Suggest fix
- **Get approval**: Ask before changing
- **Update plan**: Modify tasks.md if approved