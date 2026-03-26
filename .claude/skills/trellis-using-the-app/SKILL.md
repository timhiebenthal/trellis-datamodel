---
name: trellis-using-the-app
description: Guides end users through Trellis product workflows in dbt projects, including conceptual vs logical views, canvas modeling, classification, and sync outputs. Use when users ask how to model, document, or operate Trellis features.
---

# Trellis Using The App

## Use this skill when

- A user asks how to model in Trellis.
- A user asks about conceptual vs logical view.
- A user asks how Trellis outputs sync back to dbt YAML/tests.
- A user asks about lineage, exposures, business events, or bus matrix usage.

## Workflow framing

- **Greenfield:** draft entities/relationships in Trellis, then generate or update dbt-facing YAML/tests.
- **Brownfield:** load existing dbt models, document and classify them, then refine relationships and metadata.

## Core product guidance

1. Pick the right view:
   - Conceptual: names, descriptions, business meaning.
   - Logical: fields, data types, implementation-oriented detail.
2. Model on canvas:
   - Create entities and relationships.
   - Classify entities as fact, dimension, or unclassified.
   - Use naming inference from `trellis.yml` when configured.
3. Sync and review outputs:
   - Schema metadata updates.
   - Relationship test generation.
   - Descriptions/tags written back to dbt project files.
4. Confirm persisted files:
   - `data_model.yml`
   - optional `business_events.yml`
   - optional canvas layout file when configured.

## Optional feature guidance

- **Lineage:** use configured layers to explain flow from raw/clean/prep/core models.
- **Exposures:** document dashboard/report consumers where enabled.
- **Business events/processes:** capture 7W style event semantics and process groupings.
- **Bus matrix:** inspect fact/dimension intersections for Kimball-style communication.

## Guardrails

- Do not explain backend route internals to end users unless explicitly requested.
- Prefer product behavior and file outcomes over implementation details.
- For visual type styling, align with `trellis-visual-guidance`.

## References

- [README.md](../../../README.md)
- [trellis-visual-guidance](../trellis-visual-guidance/SKILL.md)
