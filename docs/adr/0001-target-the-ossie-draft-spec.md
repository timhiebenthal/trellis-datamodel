# Target the Apache Ossie 0.2.0.dev0 draft rather than the released 0.1.1

Ossie shipped 0.1.1 in December 2025 with models wrapped in a `semantic_model:` array; the in-development 0.2.0.dev0 flattens the document to one model at the root and moves relationship and metric name resolution onto dataset fields. We emit 0.2.0.dev0 because building the exporter against a shape Apache has already declared it is replacing would mean writing it twice, and the vendor tooling that matters (Snowflake, Databricks, dbt Labs) is following the draft.

**Consequences.** The version is pinned in `OSSIE_VERSION`, the official schema is vendored under `tests/fixtures/ossie/`, and golden documents make a spec change visible in review. Consumers built against 0.1.1 - `semglot` among them - will not read the file until they move. Revisit when 0.2.0 ships: diff the vendored schema, bump the constant, adjust the type and name mapping.

**Considered options.** Emitting both shapes behind a config switch was rejected: it doubles the mapping surface to serve a format nobody has committed to deploying.
