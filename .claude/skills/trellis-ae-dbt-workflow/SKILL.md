---
name: trellis-ae-dbt-workflow
description: Supports analytics engineers using Trellis inside dbt projects, focusing on dbt artifact refresh cadence, source-of-truth decisions, Git collaboration, and naming/layer alignment. Use when users ask about day-to-day Trellis plus dbt workflow practices.
---

# Trellis AE dbt Workflow

## Use this skill when

- A user asks how Trellis should fit daily dbt work.
- A user hits drift between Trellis state and dbt artifacts.
- A user asks how to handle merge conflicts in Trellis-managed YAML files.

## Analytics engineer workflow

1. Refresh dbt artifacts before Trellis sessions after model changes:
   - `dbt compile`
   - `dbt docs generate`
2. Open Trellis and verify model representation after renames/moves.
3. Decide source-of-truth direction per change:
   - dbt-first physical refactor, then reconcile Trellis.
   - Trellis-first conceptual adjustment, then write updates to dbt YAML/tests.
4. Commit Trellis artifacts as code:
   - `data_model.yml`
   - optional `business_events.yml`
   - optional canvas layout file
5. Re-open Trellis after conflict resolution to validate model integrity.

## Collaboration rules

- Treat Trellis YAML files like code review artifacts in PRs.
- Watch for risky cases:
  - renamed or deleted models
  - manual `schema.yml` edits that overlap with Trellis-generated changes
- Keep naming conventions (`dim_`, `fct_`, entity prefixes, layer folders) aligned with `trellis.yml` inference settings.

## Scope boundary

- This skill covers Trellis-to-dbt handoff and collaboration hygiene.
- It does not replace deep dbt SQL/Jinja authoring guidance.

## References

- [README.md](../../../README.md)
- [trellis-setup-and-dbt-bridge](../trellis-setup-and-dbt-bridge/SKILL.md)
- [trellis-using-the-app](../trellis-using-the-app/SKILL.md)
