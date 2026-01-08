# Task Planning Process

You are creating an implementation plan by breaking down a specification into actionable tasks.

## Process Overview

1. **Read Specification**
2. **Break Down into Tasks**
3. **Organize Tasks Logically (with SPRINTS and STREAMS)**
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

## Step 3: Organize Tasks Logically (with SPRINTS and STREAMS)

Organize tasks into **SPRINTS** and **STREAMS** to enable parallelization across AI agents:

### SPRINTS
- Sprints are sequential phases that happen one after another
- Each sprint depends on completion of the previous sprint
- Common sprint breakdown:
  - **SPRINT 1**: Setup, infrastructure, foundational components
  - **SPRINT 2**: Core features, main functionality
  - **SPRINT 3**: Integration, testing, polish, documentation

### STREAMS
- Streams run in **parallel** within a sprint
- Streams should be independent or have minimal cross-dependencies
- Each stream can be assigned to a different AI agent
- Example streams:
  - **Stream A**: Backend API implementation
  - **Stream B**: Frontend UI components
  - **Stream C**: Database schema and migrations
  - **Stream D**: Testing and validation

### Task Organization Template

```markdown
## SPRINT 1: [Sprint Name]

### Stream A: [Stream Name]
- [ ] Task A.1
- [ ] Task A.2

### Stream B: [Stream Name]
- [ ] Task B.1
- [ ] Task B.2

## SPRINT 2: [Sprint Name]

### Stream A: [Stream Name]
- [ ] Task A.3
- [ ] Task A.4

### Stream C: [Stream Name]
- [ ] Task C.1
- [ ] Task C.2

## SPRINT 3: [Sprint Name]

### Stream B: [Stream Name]
- [ ] Task B.3
- [ ] Task B.4
```

### Guidelines for SPRINTS and STREAMS

- **SPRINTS**: Identify clear milestones and dependencies
  - Start with foundation (SPRINT 1)
  - Build core features (SPRINT 2)
  - Integrate and polish (SPRINT 3)
  - Don't create more sprints than needed (2-4 is typical)

- **STREAMS**: Identify independent work areas
  - Group related tasks within a stream
  - Ensure streams have minimal cross-dependencies
  - Balance work across streams
  - Each stream should be assignable to one agent

- **Dependencies**: Clearly mark cross-stream dependencies
  - Use notes like `⚠️ Depends on: SPRINT 1 - Stream A - Task A.2`
  - Minimize blocking dependencies between parallel streams
  - When possible, design tasks to be truly parallel

### Parallelization Benefits

This structure enables you to:
- Assign different streams to multiple AI agents simultaneously
- Track progress at both sprint (milestone) and stream (work area) levels
- Identify bottlenecks where streams block each other
- Scale work up or down based on team capacity
- Quickly see the overall structure and task distribution via the Summary section

### Summary Section

Always include a **Summary** section at the end of the tasks file (before Notes) that provides:
- **Sprint Overview Table**: Quick view of all sprints with task counts and status
- **Stream Overview**: Breakdown of streams within each sprint with task counts
- **Parallelization Strategy**: Max concurrent agents, critical path, independent streams
- **Total Effort**: Overall counts (sprints, streams, tasks)

The summary should be kept up-to-date as tasks are completed or reorganized.

Group related tasks and order them by:
- **Dependencies**: Tasks that must happen first
- **Logical flow**: Natural progression of work
- **Risk**: High-risk items early for early validation

Use markdown task lists with checkboxes, organized by SPRINTS and STREAMS:

```markdown
## SPRINT 1: Foundation & Setup

### Stream A: Infrastructure
- [ ] Task 1
- [ ] Task 2

### Stream B: Configuration
- [ ] Task 3

## SPRINT 2: Core Implementation

### Stream A: Infrastructure
- [ ] Task 4
- [ ] Task 5

### Stream C: Core Features
- [ ] Task 6
- [ ] Task 7
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

[Your SPRINTS and STREAMS organized task list here]

Example structure:

## SPRINT 1: [Sprint Name/Phase]

### Stream A: [Work Area]
- [ ] Task description
- [ ] Another task
  - [ ] Subtask if needed

### Stream B: [Work Area]
- [ ] Task description

## SPRINT 2: [Sprint Name/Phase]

### Stream A: [Work Area]
- [ ] Task description ⚠️ Depends on: SPRINT 1 - Stream A - Task X

### Stream C: [Work Area]
- [ ] Task description

## SPRINT 3: [Sprint Name/Phase]

[... more streams and tasks]

## Summary

Quick overview of all SPRINTS and STREAMS with task counts:

### Sprint Overview
| Sprint | Name | Status | Total Tasks | Streams |
|--------|------|--------|-------------|---------|
| SPRINT 1 | [Name] | ⬜ Not Started | 12 | 3 |
| SPRINT 2 | [Name] | ⬜ Not Started | 15 | 4 |
| SPRINT 3 | [Name] | ⬜ Not Started | 8 | 2 |

### Stream Overview

**SPRINT 1**
- **Stream A**: [Name] - 5 tasks
- **Stream B**: [Name] - 4 tasks
- **Stream C**: [Name] - 3 tasks

**SPRINT 2**
- **Stream A**: [Name] - 4 tasks ⚠️ Depends on: SPRINT 1 - Stream A
- **Stream B**: [Name] - 6 tasks
- **Stream C**: [Name] - 3 tasks ⚠️ Depends on: SPRINT 1 - Stream C
- **Stream D**: [Name] - 2 tasks

**SPRINT 3**
- **Stream A**: [Name] - 5 tasks ⚠️ Depends on: SPRINT 2 - Stream A
- **Stream B**: [Name] - 3 tasks

### Parallelization Strategy
- **Concurrent Agents**: Up to 4 agents can work in parallel within each sprint
- **Critical Path**: Stream A (SPRINT 1 → SPRINT 2 → SPRINT 3)
- **Independent Streams**: Stream B and C can start immediately in SPRINT 2

### Total Effort
- **Total SPRINTS**: 3
- **Total STREAMS**: 7 (across all sprints)
- **Total Tasks**: 35

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

### SPRINT and STREAM Guidelines

**SPRINTS:**
- Define clear sprint objectives/milestones
- Sprints should be sequential and build on each other
- Typical: 2-4 sprints per feature (Setup → Core → Integration → Polish)
- Mark what must be completed before the next sprint begins
- Consider risk: put high-risk validation work early (SPRINT 1 or 2)

**STREAMS:**
- Identify truly parallel work streams within each sprint
- Each stream should be assignable to a single AI agent
- Minimize cross-stream dependencies
- Balance workload across streams
- Use dependency markers: `⚠️ Depends on: SPRINT X - Stream Y - Task Z`

**SUMMARY:**
- Always include a Summary section after all SPRINTS/STREAMS
- Keep it up-to-date as tasks are added/removed/completed
- Use tables for quick scanning of sprint/stream structure
- Highlight dependencies and parallelization opportunities
- Track sprint status (Not Started / In Progress / Completed)

**Parallelization Strategy:**
- Think about which work areas can be done independently
- Backend vs. frontend are classic parallel streams
- Testing can often be its own stream, especially in later sprints
- Documentation and polish make good parallel streams
- Infrastructure/setup can often be a stream in SPRINT 1

**Example SPRINT/STREAM Patterns:**
- **SPRINT 1**: Setup (Stream A: Config, Stream B: Infrastructure)
- **SPRINT 2**: Core (Stream A: Backend API, Stream B: Frontend UI, Stream C: Data Layer)
- **SPRINT 3**: Integration (Stream A: Integration Tests, Stream B: E2E Tests, Stream C: Documentation)

