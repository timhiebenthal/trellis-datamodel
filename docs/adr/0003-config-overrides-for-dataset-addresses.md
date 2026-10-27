# Take dataset addresses from config, not the dbt manifest

A dbt manifest's `database` and `schema` for each node reflect whichever target last ran, so a local `dbt compile` against a dev target would write `ANALYTICS_DEV.dbt_tsmith_marts` into a committed semantic model. `ossie.source.database` and `ossie.source.schema` are explicit overrides, adapter-reported values fill only the segments the user leaves empty, and no `database` segment is emitted by default. Bruin asset headers carry neither segment, so one rule covers both frameworks.

**Consequences.** The default output is `schema.table`, which is correct but not fully qualified; pointing at production is one config line. Nothing in the generated file records which target populated the schema segment, so the config is the only record of intent.

**Considered options.** Reading `database` straight from the manifest was rejected as a dev-target leak. Emitting bare table names was rejected because it discards information the framework does reliably provide.
