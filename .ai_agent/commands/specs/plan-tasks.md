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

Task types:
- Setup: Environment, dependencies
- Core implementation: Main feature
- Integration: Connecting systems
- Testing: Unit, integration, E2E
- Documentation: Comments, README
- Polish: Error handling, edge cases, UX

## Step 3: Organize into SPRINTS and STREAMS

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
```

## Guidelines

- Reference `.cursor/project.md` for tech stack
- Make tasks concrete and focused
- Prefer 1-2 lines per task if extra technical detail helps
- Include file or symbol when it reduces ambiguity (e.g., `routes/data_model.py`, `load_config()`)
- Include testing tasks
- Order by: dependencies → logical flow → risk

### SPRINT Guidelines
- Clear milestones
- Sequential (build on each other)
- High-risk work early

### STREAM Guidelines
- **1 file = 1 stream** (or 1 cohesive component)
- Assignable to one agent
- Minimal cross-dependencies
- Use dependency markers: `⚠️ Depends on: ...`

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
