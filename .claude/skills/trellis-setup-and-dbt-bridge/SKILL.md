---
name: trellis-setup-and-dbt-bridge
description: Sets up Trellis for end users working in dbt projects, including trellis.yml paths, manifest/catalog prerequisites, and common startup troubleshooting. Use when users ask to install, initialize, run, or fix Trellis configuration.
---

# Trellis Setup And dbt Bridge

## Use this skill when

- A user needs to install or start Trellis.
- A user asks what to put in `trellis.yml`.
- Trellis cannot find `manifest.json`, `catalog.json`, or the data model file.
- A user wants to understand how Trellis maps to dbt artifacts.

## Core workflow

1. Confirm the user is in the intended dbt project directory.
2. Initialize config if needed: `trellis init`.
3. Validate `trellis.yml` path fields:
   - `dbt_project_path`
   - `dbt_manifest_path`
   - `dbt_catalog_path`
   - `data_model_file`
4. Ensure dbt artifacts are fresh:
   - `dbt compile`
   - `dbt docs generate`
5. Run Trellis:
   - `trellis run`
   - or `trellis serve`
6. If needed, use `--config <path>` and `--no-browser`.

## Explain artifact roles clearly

- `manifest.json` / `catalog.json`: dbt project metadata Trellis reads.
- `data_model.yml`: Trellis-managed conceptual/logical model output.
- `business_events.yml`: optional feature file when business events are enabled.

## Troubleshooting checklist

- No config found: run `trellis init` or pass `--config`.
- Wrong relative paths: resolve paths relative to `dbt_project_path`.
- Missing artifacts: run dbt commands again before starting Trellis.
- Stale artifacts after model refactor: regenerate docs and reload Trellis.

## Response style

- Keep setup guidance action-oriented and short.
- Prefer exact commands over long prose.
- Distinguish clearly between dbt artifacts (inputs) and Trellis files (outputs/state).

## References

- [README.md](../../../README.md)
