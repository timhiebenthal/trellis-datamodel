# Task Planning Process

Break down a specification into actionable tasks organized into SPRINTS and STREAMS.

## Process

1. Read spec
2. Break down into tasks
3. Organize into SPRINTS and STREAMS
4. Create tasks.md file

## Step 1: Read Specification

- Path: `specs/[spec-name]/spec.md`
- Understand: requirements, scope, approach, dependencies, success criteria

## Step 2: Break Down into Tasks

Each task should be:
- Specific and actionable
- Clear outcome
- Appropriately sized
- Testable/verifiable
- Include brief implementation detail when useful (e.g., file, function, API)
- **NEVER use placeholder implementations** - all components must be fully functional when marked complete
- **TDD: Test FIRST, code SECOND** - every task includes failing test before implementation

### TDD Enforcement

Each task follows this sequence:

1. **Write failing test** - Show actual test code that fails
2. **Run verify failure** - Expected output shows failure
3. **Write minimal implementation** - Code to make test pass
4. **Run verify pass** - Test passes
5. **Commit** - Atomic change with meaningful message

```markdown
- [ ] **Write failing test**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected  # This will fail
```

- [ ] **Run test to verify failure**

Run: `pytest tests/path/test.py::test_name -v`
Expected: FAIL

- [ ] **Write minimal implementation**

```python
def function(input):
    return expected
```

- [ ] **Run test to verify pass**

Run: `pytest tests/path/test.py::test_name -v`
Expected: PASS

- [ ] **Commit**
```

Task types:
- Setup: Environment, dependencies
- Core implementation: Main feature
- Integration: Connecting systems
- Testing: Unit, integration, E2E
- Documentation: Comments, README
- Polish: Error handling, edge cases, UX

### ⚠️ Anti-Pattern: Placeholder Implementations

**NEVER create placeholder/stub components that say "will be implemented later"**

❌ **BAD - Placeholder modal:**
```svelte
{#if showModal}
    <div class="modal">
        <p>Modal component will be implemented in Stream D.</p>
        <button onclick={close}>Close</button>
    </div>
{/if}
```

✅ **GOOD - Either skip or fully implement:**
- Option 1: Don't create the component until its sprint/stream
- Option 2: Fully implement the component when the task is marked complete

**Why this matters:**
- Placeholders create confusion about what's actually done
- They break the user experience during development
- They require double work (placeholder + real implementation)
- Tasks marked `[x]` should mean "fully functional", not "stub created"

## Step 3: Organize into SPRINTS and STREAMS

### Dependency Awareness

- Before finalizing any stream, inventory the upstream work it relies on (other streams, services, data models, etc.).
- Document hard dependencies with `⚠️ Depends on:` so implementers know they cannot progress until those streams are complete.
- Do not plan a stream whose tasks require functionality that still needs to be built elsewhere unless that dependency is explicitly tracked and slated to finish first.
- When executing filtered tasks, double-check the dependency notes in `tasks.md`—if a dependency is incomplete, pause and request the requisite work instead of proceeding.

### SPRINTS (sequential phases)
- SPRINT 1: Foundation/infrastructure
- SPRINT 2: Core features
- SPRINT 3: Integration, testing, polish
- 2-4 sprints typical

### STREAMS (parallel work within a sprint)
- Run in parallel within each sprint
- Each stream assigned to one agent
- **KEY RULE: 1 file = 1 stream** (or 1 cohesive component)
- Avoid parallel streams editing same files
- A STREAM a SPRINT _MUST NOT_ depend on another SPRINT of the same SPRINT
- STREAM names reset and start with 'A' at each SPRINT

### Task Organization Example

```markdown
## SPRINT 1: Foundation

### Stream A: wizard.py
- [ ] Create module structure in `wizard.py` with `WizardStep` types
- [ ] Implement prompts in `build_prompt()` and wire to CLI args
- [ ] Add error handling for missing config and invalid inputs

### Stream B: cli.py
- [ ] Modify `init` command to accept `--wizard` flag
- [ ] Integrate wizard flow via `run_wizard()` and return exit codes

### Stream C: test_cli.py
- [ ] Add tests mocking error codes `E_CONFIG` and `E_IO` from `run_wizard()`
- [ ] Assert exit codes and user-facing messages per error code
```

### Dependencies

- Use: `⚠️ Depends on: SPRINT 1 - Stream A - Task X`
- Minimize blocking dependencies
- Mark cross-stream dependencies clearly

## Step 4: Create Tasks File

Path: `specs/[spec-name]/tasks.md`

Structure:

```markdown
# [Feature] - Implementation Tasks

## Overview
Brief description (reference spec.md)

## Tasks

[SPRINTS and STREAMS organized here]

## Summary

### Sprint Overview
| Sprint | Name | Tasks | Streams |
|--------|------|--------|---------|
| SPRINT 1 | ... | ... | ... |

### Stream Overview
**SPRINT 1**
- Stream A: [name] - X tasks
- Stream B: [name] - Y tasks

### Parallelization
- Concurrent agents: X
- Critical path: ...
- Independent streams: ...

### Total Effort
- SPRINTS: X
- STREAMS: Y
- Tasks: Z

## Notes
Implementation notes, edge cases, standards

### Implementation Quality Standards
- **No placeholder implementations**: All components fully functional when marked `[x]`
- **Complete integration**: Components properly imported and wired together
- **User-facing quality**: Every marked task should be demonstrable to users
```

## Guidelines

- Reference `.cursor/project.md` for tech stack
- Make tasks concrete and focused
- Prefer 1-2 lines per task if extra technical detail helps
- Include file or symbol when it reduces ambiguity (e.g., `routes/data_model.py`, `load_config()`)
- Include testing tasks
- Order by: dependencies → logical flow → risk
- **Verify no placeholders**: Before marking tasks complete, ensure all components are fully implemented and integrated
- **TDD enforced**: Every task has failing test before code

### Pre-Save Placeholder Scan (Required)

Before saving tasks.md, scan for anti-patterns:

| Anti-Pattern | Example | Fix |
|--------------|---------|-----|
| Placeholder text | "TBD", "TODO", "implement later" | Write actual content |
| Test without code | "Write tests" (no test code) | Show actual test |
| Code step without block | "Implement the function" | Show actual code |
| Vague instruction | "Add appropriate validation" | Specific validation rules |
| Reference to undefined | "Call function from Task 3" | Define function in task |

If ANY found: Fix inline before saving.

### SPRINT Guidelines
- Clear milestones
- Sequential (build on each other)
- High-risk work early

### STREAM Guidelines
- **1 file = 1 stream** (or 1 cohesive component)
- Assignable to one agent
- Minimal cross-dependencies
- Use dependency markers: `⚠️ Depends on: ...`
- **No placeholders**: Components must be fully implemented when tasks are marked complete
- If a component depends on another stream, either:
  - Make it a dependency and implement in correct order
  - Or don't reference it until it's ready

### Parallelization Strategy
- Independent work areas (backend/frontend, API/UI, tests/docs)
- Different files = different streams
- Infrastructure/setup can be its own stream in SPRINT 1
- Testing often separate stream in SPRINT 3

## Output

```
Task plan created!

✅ Tasks: `specs/[spec-name]/tasks.md`

NEXT STEP 👉 Run `/execute` to implement.
```
