---
name: trellis-ae-dbt-workflow
description: Supports analytics engineers using Trellis inside dbt projects, including when humans or AI agents edit dbt models and YAML. Covers artifact refresh, Trellis YAML reconciliation, ownership boundaries, and risky overlaps. Use when users ask about Trellis plus dbt workflow, AI-generated dbt changes, or keeping both tools consistent.
---

# Trellis AE dbt Workflow

## Use this skill when

- A user asks how Trellis should fit daily dbt work.
- A user hits drift between Trellis state and dbt artifacts.
- A user asks how to handle merge conflicts in Trellis-managed YAML files.
- A user wants a habit or checklist so Trellis is not skipped after dbt-only work.
- dbt SQL or `schema.yml` is being written or refactored by an **AI agent** (same coordination rules as human edits).

## What does not happen automatically

- Trellis does **not** watch `manifest.json` / `catalog.json` on disk. After `dbt compile` / `dbt docs generate`, **reload the Trellis UI** (browser refresh) or **restart** `trellis run` so reads pick up new artifacts.
- Changing **`trellis.yml`** is separate: use the Config UI (reload flow) or restart the server; that reloads config, not a substitute for refreshing after new dbt artifacts.

## Which Trellis YAML to change when dbt models change (e.g. rename)

- **`trellis.yml`:** Usually **unchanged** for a model rename. Paths to the dbt project, manifest, catalog, and `data_model_file` stay the same.
- **`data_model.yml`:** Often **must be reconciled**. Bound entities store `dbt_model` (and optional `additional_models`) as dbt **unique ids**. Renaming a model in dbt yields a **new** unique id in the manifest; Trellis does **not** rewrite those fields automatically. Re-bind in the app or update YAML, then regenerate dbt artifacts and refresh Trellis.
- **`business_events.yml`:** Update **only if** events or derived links still point at old model or entity identifiers.
- **Canvas layout file:** Often **unchanged** on rename if entity **ids** stayed the same; if the user recreated entities with new ids, layout may need a quick check.

## Extra interplay: dbt and Trellis (including AI-edited dbt)

Use this mental model: **dbt owns executable models and project structure**; **Trellis owns `data_model.yml` (and optional events/layout)** as the visual/semantic layer. Neither tool auto-merges the other’s files.

- **`schema.yml` / relationship tests / descriptions:** Trellis can generate or update these from the canvas. If an **AI agent** (or human) edits the same files, treat it like any multi-writer problem: diff carefully, avoid blind overwrites, and run `dbt compile` / `dbt docs generate` before reconciling Trellis.
- **`trellis.yml` `dbt_model_paths`:** If set, models **outside** those paths may be **invisible or filtered** in Trellis. AI-added models in new folders may need **path config updates** plus refresh.
- **New models from AI:** They appear in the manifest after compile; they are **not** automatically bound in `data_model.yml`. Open Trellis after artifact refresh if the team expects canvas coverage or bindings.
- **Deleted or merged models:** Expect **stale `dbt_model` references** in `data_model.yml`; clean up in Trellis or YAML after the manifest no longer lists the old unique id.
- **Moves between layers / folders:** dbt still works; **lineage layer** grouping (if enabled) and **inference** from names/paths may shift—refresh Trellis and re-check classification.
- **Packages, versions, `ref` refactors:** Any change that alters **model unique ids** in the manifest triggers the same **re-bind** concern as renames.
- **Same PR, two authors:** A commit that only touches dbt without updating **`data_model.yml`** can be valid, but PR review should ask: “Did any bound model identity change?” If yes, reconcile Trellis in the same PR or a fast follow.
- **Agents that batch-commit:** Prefer a fixed order when both tools matter: **dbt succeeds locally → regenerate artifacts → refresh Trellis → adjust `data_model.yml` if needed → commit dbt + Trellis artifacts together** when changes are coupled.

## Analytics engineer workflow

1. After meaningful dbt changes, regenerate artifacts, then refresh Trellis:
   - `dbt compile`
   - `dbt docs generate` (so `catalog.json` exists/updates where your project writes it)
   - Reload the Trellis tab or restart the Trellis process before trusting the canvas.
2. Verify model representation after renames/moves (orphaned bindings, missing nodes).
3. Decide source-of-truth direction per change:
   - dbt-first physical refactor, then reconcile Trellis.
   - Trellis-first conceptual adjustment, then write updates to dbt YAML/tests.
4. Commit Trellis artifacts as code:
   - `data_model.yml`
   - optional `business_events.yml`
   - optional canvas layout file
5. Re-open Trellis after conflict resolution to validate model integrity.

## Do not forget Trellis (team habits)

- **PR / checklist:** Add a line for model refactors: “Regenerated dbt docs and reconciled Trellis / `data_model.yml` if applicable.”
- **Wrapper script or Make target:** One command that runs `dbt compile` + `dbt docs generate` then prints “Open Trellis” (optional `trellis run`) so dbt and Trellis stay paired.
- **Branch workflow:** When merging main into a modeling branch, rerun dbt artifacts, refresh Trellis, then resolve any `data_model.yml` conflicts with the UI open.

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
