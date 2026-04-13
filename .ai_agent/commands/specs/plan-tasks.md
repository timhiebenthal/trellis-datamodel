# Task Planning Process

Break down specification into actionable tasks. Organize into SPRINTS and STREAMS.

## Process

1. Read spec
2. Break down into tasks
3. Organize into SPRINTS + STREAMS
4. Create tasks.md

## Step 1: Read Specification

- Path: `specs/[spec-name]/spec.md`
- Understand: requirements, scope, approach, dependencies, success criteria

## Step 2: Break Down into Tasks

Task requirements:
- Specific, actionable
- Clear outcome
- Appropriately sized
- Testable/verifiable
- Include brief implementation detail (file, function, API)
- **NEVER use placeholders** — all components fully functional when marked complete
- **TDD: Test FIRST, code SECOND** — every task has failing test before implementation

### TDD Enforcement

Each task sequence:

1. **Write failing test** — actual test code that fails
2. **Run verify failure** — expected output shows failure
3. **Write minimal implementation** — code to make test pass
4. **Run verify pass** — test passes
5. **Commit** — atomic change with meaningful message

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
- Core: Main feature
- Integration: Connecting systems
- Testing: Unit, integration, E2E
- Documentation: Comments, README
- Polish: Error handling, edge cases, UX

### Anti-Pattern: Placeholders

**NEVER create stubs that say "will be implemented later"**

Reason: placeholders create confusion, break UX, require double work. Tasks marked `[x]` = fully functional, not stub.

## Step 3: Organize into SPRINTS and STREAMS

### Dependency Awareness

- Inventory upstream work before finalizing stream
- Mark hard dependencies: `⚠️ Depends on: SPRINT 1 - Stream A - Task X`
- Don't plan stream requiring unfinished functionality elsewhere

### SPRINTS (sequential)
- SPRINT 1: Foundation/infrastructure
- SPRINT 2: Core features
- SPRINT 3: Integration, testing, polish

### STREAMS (parallel within sprint)
- Run in parallel
- **KEY RULE: 1 file = 1 stream**
- Avoid parallel streams editing same files
- STREAM names reset to 'A' each SPRINT

### Task Example

```markdown
## SPRINT 1: Foundation

### Stream A: wizard.py
- [ ] Create module structure with WizardStep types
- [ ] Implement prompts in build_prompt()

### Stream B: cli.py  
- [ ] Modify init to accept --wizard flag
- [ ] Integrate wizard flow
```

## Step 4: Create Tasks File

Path: `specs/[spec-name]/tasks.md`

Structure:

```markdown
# [Feature] - Implementation Tasks

## Overview
Brief description

## Tasks

[SPRINTS and STREAMS organized here]

## Summary

### Sprint Overview
| Sprint | Name | Tasks | Streams |
|--------|------|--------|---------|
| 1 | Foundation | X | A, B |
...

### Total Effort
- SPRINTS: X
- STREAMS: Y  
- Tasks: Z

## Notes
- Implementation notes, edge cases

### Quality Standards
- No placeholders
- Complete integration
- User-facing quality
```

## Guidelines

- Reference `.cursor/project.md`
- Make tasks concrete
- Include file/symbol when reduces ambiguity
- Include testing tasks
- Order: dependencies → logical flow → risk

### Pre-Save Placeholder Scan (Required)

Before saving, scan for:

| Anti-Pattern | Fix |
|--------------|-----|
| "TBD", "TODO" | Write actual content |
| "Write tests" (no code) | Show actual test |
| "Implement the function" (no code) | Show actual code |
| Vague instruction | Specific rules |
| Reference to undefined | Define in task |

Fix inline before saving.

### SPRINT Guidelines
- Clear milestones
- Sequential (build on each other)
- High-risk early

### STREAM Guidelines
- 1 file = 1 stream
- Minimal cross-dependencies
- Use dependency markers
- No placeholders

## Output

```
Task plan created!

✅ Tasks: `specs/[spec-name]/tasks.md`

NEXT STEP → Run `/execute`.
```