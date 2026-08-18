import json
from pathlib import Path

import pytest


def _write_dbt_snapshot_fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    project_path = tmp_path / "dbt_project"
    models_path = project_path / "models" / "3_core"
    target_path = project_path / "target"
    models_path.mkdir(parents=True)
    target_path.mkdir()

    manifest_path = target_path / "manifest.json"
    catalog_path = target_path / "catalog.json"
    data_model_path = project_path / "data_model.yml"
    manifest = {
        "nodes": {
            "model.project.dim_customer": {
                "unique_id": "model.project.dim_customer",
                "resource_type": "model",
                "name": "dim_customer",
                "schema": "analytics",
                "alias": "dim_customer",
                "original_file_path": "models/3_core/dim_customer.sql",
                "columns": {
                    "id": {
                        "name": "id",
                        "data_type": "integer",
                        "description": "Customer identifier",
                    }
                },
                "depends_on": {"nodes": ["source.project.crm.customers"]},
            },
            "model.project.fct_orders": {
                "unique_id": "model.project.fct_orders",
                "resource_type": "model",
                "name": "fct_orders",
                "schema": "analytics",
                "alias": "fct_orders",
                "original_file_path": "models/3_core/fct_orders.sql",
                "columns": {
                    "customer_id": {
                        "name": "customer_id",
                        "data_type": "integer",
                        "data_tests": [
                            {
                                "relationships": {
                                    "to": "ref('dim_customer')",
                                    "field": "id",
                                }
                            }
                        ],
                    }
                },
                "depends_on": {"nodes": ["model.project.dim_customer"]},
            },
        },
        "sources": {
            "source.project.crm.customers": {
                "unique_id": "source.project.crm.customers",
                "resource_type": "source",
                "name": "customers",
                "source_name": "crm",
                "original_file_path": "models/sources.yml",
            }
        },
    }
    catalog = {
        "nodes": {
            "model.project.dim_customer": {
                "columns": {"id": {"name": "ID", "type": "INTEGER"}}
            },
            "model.project.fct_orders": {
                "columns": {
                    "customer_id": {"name": "CUSTOMER_ID", "type": "INTEGER"}
                }
            },
        }
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
    data_model_path.write_text(
        "entities:\n"
        "  - id: customer\n"
        "    model_ref: model.project.dim_customer\n"
        "  - id: orders\n"
        "    model_ref: model.project.fct_orders\n"
        "relationships: []\n",
        encoding="utf-8",
    )
    (models_path / "dim_customer.yml").write_text(
        "version: 2\n"
        "models:\n"
        "  - name: dim_customer\n"
        "    description: Customers\n"
        "    columns:\n"
        "      - name: id\n"
        "        data_type: integer\n",
        encoding="utf-8",
    )
    (models_path / "fct_orders.yml").write_text(
        "version: 2\n"
        "models:\n"
        "  - name: fct_orders\n"
        "    columns:\n"
        "      - name: customer_id\n"
        "        data_type: integer\n"
        "        data_tests:\n"
        "          - relationships:\n"
        "              to: ref('dim_customer')\n"
        "              field: id\n",
        encoding="utf-8",
    )
    return manifest_path, catalog_path, data_model_path, project_path


def _make_snapshot_adapter(tmp_path: Path):
    from trellis_datamodel.adapters.dbt_core import DbtCoreAdapter

    manifest_path, catalog_path, data_model_path, project_path = (
        _write_dbt_snapshot_fixture(tmp_path)
    )
    return DbtCoreAdapter(
        manifest_path=str(manifest_path),
        catalog_path=str(catalog_path),
        project_path=str(project_path),
        data_model_path=str(data_model_path),
        model_paths=["3_core"],
    )


def _counted_json_loads(monkeypatch):
    calls: list[str] = []
    original_loads = json.loads

    def counted_loads(value, *args, **kwargs):
        calls.append("parse")
        return original_loads(value, *args, **kwargs)

    monkeypatch.setattr(json, "loads", counted_loads)
    return calls


def test_entity_typeddict_uses_generic_model_ref():
    from trellis_datamodel.adapters.base import Entity

    hints = Entity.__annotations__
    assert "model_ref" in hints
    assert "dbt_model" not in hints


def test_get_adapter_raises_value_error_for_unknown_framework(monkeypatch):
    """An unsupported framework must fail loudly, never fall through to dbt behavior.

    The error names the frameworks that are actually supported, so adding one is a
    matter of implementing an adapter rather than teaching this message about it.
    """
    from trellis_datamodel import config as cfg
    from trellis_datamodel.adapters import get_adapter

    monkeypatch.setattr(cfg, "FRAMEWORK", "some-unsupported-framework")

    with pytest.raises(ValueError, match="dbt-core"):
        get_adapter()


def test_get_adapter_still_returns_dbt_core_adapter_for_dbt_core(monkeypatch):
    from trellis_datamodel import config as cfg
    from trellis_datamodel.adapters import DbtCoreAdapter, get_adapter

    monkeypatch.setattr(cfg, "FRAMEWORK", "dbt-core")
    monkeypatch.setattr(cfg, "MANIFEST_PATH", "/tmp/manifest.json")
    monkeypatch.setattr(cfg, "CATALOG_PATH", "/tmp/catalog.json")
    monkeypatch.setattr(cfg, "DBT_PROJECT_PATH", "/tmp/dbt_project")
    monkeypatch.setattr(cfg, "DATA_MODEL_PATH", "/tmp/data_model.yml")
    monkeypatch.setattr(cfg, "DBT_MODEL_PATHS", ["models"])

    adapter = get_adapter()

    assert isinstance(adapter, DbtCoreAdapter)


def test_adapter_instances_share_one_artifact_snapshot(tmp_path, monkeypatch):
    from trellis_datamodel.adapters.artifact_snapshot import clear_snapshots

    clear_snapshots()
    calls = _counted_json_loads(monkeypatch)
    adapter_one = _make_snapshot_adapter(tmp_path)
    adapter_two = type(adapter_one)(
        manifest_path=adapter_one.manifest_path,
        catalog_path=adapter_one.catalog_path,
        project_path=adapter_one.project_path,
        data_model_path=adapter_one.data_model_path,
        model_paths=adapter_one.model_paths,
    )

    assert adapter_one.get_models() == adapter_two.get_models()
    assert adapter_two.get_lineage("model.project.fct_orders") == adapter_one.get_lineage(
        "model.project.fct_orders"
    )

    assert len(calls) == 2


def test_schema_entity_and_relationship_inference_reuse_snapshot_indexes(
    tmp_path, monkeypatch
):
    from trellis_datamodel import config as cfg
    from trellis_datamodel.adapters.artifact_snapshot import clear_snapshots

    clear_snapshots()
    cfg.DIMENSIONAL_MODELING_CONFIG = cfg.DimensionalModelingConfig(
        enabled=True, dimension_prefix=["dim_"], fact_prefix=["fct_"]
    )
    calls = _counted_json_loads(monkeypatch)
    adapter = _make_snapshot_adapter(tmp_path)

    schema = adapter.get_model_schema("dim_customer")
    entity_types = adapter.infer_entity_types()
    relationships = adapter.infer_relationships()

    assert schema["model_name"] == "dim_customer"
    assert entity_types == {"customer": "dimension", "orders": "fact"}
    assert relationships[0]["source"] == "customer"
    assert relationships[0]["target"] == "orders"
    assert len(calls) == 2


def test_adapter_results_match_uncached_fixture_results(tmp_path, monkeypatch):
    from trellis_datamodel.adapters.artifact_snapshot import clear_snapshots

    calls = _counted_json_loads(monkeypatch)
    adapter = _make_snapshot_adapter(tmp_path)

    def read_results():
        return {
            "models": adapter.get_models(),
            "schema": adapter.get_model_schema("dim_customer"),
            "entity_types": adapter.infer_entity_types(),
            "relationships": adapter.infer_relationships(),
            "lineage": adapter.get_lineage("model.project.fct_orders"),
        }

    clear_snapshots()
    uncached_results = read_results()
    clear_snapshots()
    shared_results = read_results()
    repeated_shared_results = read_results()

    assert shared_results == uncached_results
    assert repeated_shared_results == uncached_results
    assert len(calls) == 4
