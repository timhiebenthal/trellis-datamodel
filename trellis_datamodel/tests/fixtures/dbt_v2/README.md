# dbt 2.0.11 fixture

Generated on 2026-11-11 with the official Linux x86_64 dbt 2.0.11 binary:

```bash
dbt parse --project-dir PROJECT --profiles-dir PROJECT --no-manage-state
```

`dbt_project.yml` and `models/` are the input project. Use the placeholder
Snowflake profile written by `test_dbt_v2.py` to reproduce without credentials.
`manifest.json` retains actual emitted resource objects, parent/child maps and
schema metadata. Only the built-in macro library and volatile metadata
(generation time, invocation identifiers, user identifier) were removed.

No populated warehouse catalog was obtained. Catalog enrichment in the test is
synthetic and labeled accordingly. See `docs/dbt-v2-compatibility.md` for scope
and the opt-in real parser check.
