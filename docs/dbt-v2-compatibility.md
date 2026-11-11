# dbt v2 compatibility

Trellis integrates with local dbt projects through `manifest.json`, optional
`catalog.json`, and the project's schema YAML files. It does not run dbt itself.
Use `framework: dbt-core` for both dbt v1 and v2; no extra dbt dependency is needed
in the Trellis environment.

## Generate artifacts

With dbt v2, run these commands in your dbt environment:

```bash
# Model metadata, lineage, tests and YAML-declared columns; no warehouse required
dbt parse

# Optional warehouse column discovery and types; needs warehouse credentials
dbt build --write-catalog
```

Set `dbt_project_path`, `dbt_manifest_path` (usually `target/manifest.json`), and
optionally `dbt_catalog_path` (usually `target/catalog.json`) in `trellis.yml`.
Keep the schema YAML files available locally for editing and relationship inference.
Regenerate the manifest after pushing YAML changes so subsequent reads reflect them.
With dbt v1, continue using `dbt docs generate` for catalog generation.

A manifest alone exposes only declared columns and their declared types. A catalog
adds warehouse column discovery and types. In v2, `dbt docs generate` builds the
documentation site; use `--write-catalog` to explicitly request the JSON catalog.
See the official [docs command reference](https://docs.getdbt.com/reference/commands/cmd-docs?version=2).

## YAML writes and v1 support

Trellis reads the engine version from `metadata.dbt_version`, independently of the
manifest schema version. For v2, Trellis writes column origin under
`columns[].config.meta.origin` and updated model tags under `config.tags`.
Existing user metadata and other column configs are preserved. An updated legacy
metadata block is merged into `config.meta`, with existing config keys taking
precedence over duplicate legacy keys and Trellis's incoming keys applied last.

For v1 (or manifests without an engine version), Trellis keeps legacy metadata
placement for new columns, while respecting an existing `config.meta` block.
Readers accept both nested and legacy metadata, preferring nested origin when
both are present. Relationship tests use `data_tests` with an `arguments` block,
as they did before this change. This does not add support for that syntax to
older v1 releases that do not accept it.

This is a targeted compatibility fix, not an automatic migration of an entire
dbt project. Upgrade your own project and packages using the official
[v2 upgrade guide](https://docs.getdbt.com/docs/dbt-versions/dbt-upgrade/upgrading-to-v2?version=2).
The [deprecation reference](https://docs.getdbt.com/reference/deprecations?version=1.12)
describes metadata moving under config. The shared manifest v12 schema is
[documented here](https://docs.getdbt.com/reference/artifacts/manifest-json?version=1.12);
sharing that schema alone does not establish compatibility.

## Verification and limits

The checked-in fixture contains resource objects produced by the official Linux
dbt **2.0.11** binary from a two-model project. Tests cover model and column reads,
origin, tags, lineage, local relationship inference, optional JSON catalog
merging, and all three schema write paths. They also verify that a v1 engine
version sharing manifest v12 still selects legacy write syntax.

Run the normal regression suite:

```bash
uv run pytest trellis_datamodel/tests/test_dbt_v2.py
```

To additionally parse Trellis-generated YAML with a separately installed v2 binary:

```bash
DBT_V2_BIN=/absolute/path/to/dbt uv run pytest trellis_datamodel/tests/test_dbt_v2.py
```

The parser check uses a placeholder Snowflake profile and `dbt parse
--no-manage-state`; it needs no warehouse credentials. It asserts parsed origin
and relationship round trips. Install the binary using the official
[installation instructions](https://docs.getdbt.com/docs/local/install-dbt).

### dbt OSS

The Apache 2.0 distribution, `dbt-oss`, was checked separately using the official
PyPI package **2.0.11**, installed in a separate temporary environment.
The executable identifies itself as `dbt-oss 2.0.11`.
The official [OSS installation guide](https://docs.getdbt.com/docs/local/install-dbt-v2)
explains how to keep it separate from other dbt installations.

All **20 compatibility tests passed** with:

```bash
DBT_V2_BIN=/absolute/path/to/oss-environment/bin/dbt uv run pytest trellis_datamodel/tests/test_dbt_v2.py
```

This includes parsing the output of all three Trellis schema write paths with
the OSS executable. A fresh manifest was also generated using `dbt-oss parse`
and read through Trellis's adapter: model discovery, declared column types,
origin, tags, local schema reads, relationships, and upstream lineage passed.
No additional implementation changes were needed for OSS. The warehouse catalog
and Parquet limitations below apply to both distributions.

### Remaining verification limits

Generated YAML was also manually parsed successfully with dbt-core **1.11.8**
and its DuckDB adapter. This verifies one v1 runtime, not every historical v1
release.

Warehouse-backed v2 build and catalog hydration have not been verified: no real
warehouse credentials were available. An attempted `parse --write-catalog` with
the placeholder profile emitted an empty catalog with an authentication error.
The populated catalog regression is explicitly synthetic. Other adapters,
packages, and dbt v2 releases have not been independently certified by this check.

Native Parquet Information Schema input is outside this integration. Trellis does
not consume `target/info_schema/v1/` or infer types from those files. Continue
supplying the JSON artifacts described above. See the official
[Information Schema documentation](https://docs.getdbt.com/docs/build/dbt-information-schema?version=2.0).
