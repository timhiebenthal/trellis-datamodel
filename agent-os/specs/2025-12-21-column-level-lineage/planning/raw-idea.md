# Raw Idea: Column-Level Lineage Integration

## User Description

I would like to integrate (col-level) lineage as it unlocks a lot of usecases. The "retrieval" of lineage is pretty dbt specific in this case but the handling isn't.

For example, then double-clicking on an entity should lead me to a view where we see all upstream models till the source-tables/raw data of the entity.

To be flexible I thought about leveraging existing work of https://github.com/b-ned/dbt-colibri (MIT license) to not re-invent the wheel.

## Key Points

- Column-level lineage unlocks many use cases
- Retrieval is dbt-specific, but handling/visualization is framework-agnostic
- User interaction: Double-clicking on an entity should show upstream lineage view
- Upstream view should show all models back to source tables/raw data
- Leverage dbt-colibri (MIT license) to avoid reinventing the wheel

## Reference

- dbt-colibri: https://github.com/b-ned/dbt-colibri
- License: MIT (compatible)
- Purpose: Extract and analyze column lineage for dbt projects
