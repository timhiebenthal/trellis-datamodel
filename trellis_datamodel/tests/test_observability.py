"""Tests for request-scoped backend phase timing."""

import asyncio
import json
from pathlib import Path

import pytest
import yaml

from trellis_datamodel import observability


def test_timed_phase_aggregates_duration_and_call_count(monkeypatch):
    collector = observability.PhaseCollector()
    clock = iter((10.0, 10.125, 11.0, 11.250))
    monkeypatch.setattr(observability, "perf_counter", lambda: next(clock))

    token = observability.set_collector(collector)
    try:
        with observability.timed_phase("artifact_read"):
            pass
        with observability.timed_phase("artifact_read"):
            pass
    finally:
        observability.reset_collector(token)

    record = collector.records["artifact_read"]
    assert record.call_count == 2
    assert record.duration_ms == pytest.approx(375.0)


def test_nested_and_repeated_phases_are_serialized_deterministically(monkeypatch):
    collector = observability.PhaseCollector()
    clock = iter((0.0, 0.001, 0.004, 0.010, 0.020, 0.025))
    monkeypatch.setattr(observability, "perf_counter", lambda: next(clock))

    token = observability.set_collector(collector)
    try:
        with observability.timed_phase("artifact_read"):
            with observability.timed_phase("schema_read"):
                pass
        with observability.timed_phase("artifact_read"):
            pass
    finally:
        observability.reset_collector(token)

    assert observability.serialize_server_timing(collector) == (
        'artifact_read;dur=15.000;desc="artifact read",'
        'schema_read;dur=3.000;desc="schema read"'
    )


def test_collectors_are_isolated_between_concurrent_contexts():
    async def collect(phase_name):
        collector = observability.PhaseCollector()
        token = observability.set_collector(collector)
        try:
            with observability.timed_phase(phase_name):
                await asyncio.sleep(0)
            return collector
        finally:
            observability.reset_collector(token)

    async def run_concurrently():
        return await asyncio.gather(
            collect("artifact_read"),
            collect("relationship_scan"),
        )

    first, second = asyncio.run(run_concurrently())

    assert set(first.records) == {"artifact_read"}
    assert set(second.records) == {"relationship_scan"}


@pytest.mark.parametrize(
    "unsafe_name",
    [
        "model:customer_orders",
        "models/customer_orders.sql",
        "payload={'secret': 'value'}",
    ],
)
def test_phase_description_rejects_or_sanitizes_model_names_paths_and_payloads(
    unsafe_name,
):
    with pytest.raises(ValueError):
        with observability.timed_phase(unsafe_name):
            pass


def test_server_timing_omits_empty_collector():
    assert observability.serialize_server_timing(observability.PhaseCollector()) == ""


def _write_boot_fixture(tmp_path: Path) -> None:
    """Create the smallest compiled dbt project that exercises boot services."""
    models_dir = tmp_path / "models" / "3_core"
    models_dir.mkdir(parents=True)

    manifest_nodes = {
        "model.project.dim_custom": {
            "unique_id": "model.project.dim_custom",
            "resource_type": "model",
            "name": "dim_custom",
            "schema": "public",
            "alias": "dim_custom",
            "original_file_path": "models/3_core/dim_custom.sql",
            "columns": {
                "id": {
                    "name": "id",
                    "data_type": "integer",
                    "description": "Dimension key",
                }
            },
            "depends_on": {"nodes": ["source.project.raw.customers"]},
            "config": {"materialized": "table"},
        },
        "model.project.fct_sales": {
            "unique_id": "model.project.fct_sales",
            "resource_type": "model",
            "name": "fct_sales",
            "schema": "public",
            "alias": "fct_sales",
            "original_file_path": "models/3_core/fct_sales.sql",
            "columns": {
                "dim_id": {
                    "name": "dim_id",
                    "data_type": "integer",
                    "description": "Dimension reference",
                }
            },
            "depends_on": {"nodes": ["model.project.dim_custom"]},
            "config": {"materialized": "table"},
        },
    }
    manifest = {
        "nodes": manifest_nodes,
        "sources": {
            "source.project.raw.customers": {
                "unique_id": "source.project.raw.customers",
                "resource_type": "source",
                "name": "customers",
                "source_name": "warehouse",
            }
        },
    }
    catalog = {
        "nodes": {
            unique_id: {
                "columns": {
                    column_name: {
                        "name": column_name.upper(),
                        "type": column_data["data_type"],
                    }
                    for column_name, column_data in node["columns"].items()
                }
            }
            for unique_id, node in manifest_nodes.items()
        }
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    (tmp_path / "catalog.json").write_text(json.dumps(catalog))
    (models_dir / "dim_custom.yml").write_text(
        yaml.safe_dump({"version": 2, "models": [{"name": "dim_custom"}]})
    )
    (models_dir / "fct_sales.yml").write_text(
        yaml.safe_dump(
            {
                "version": 2,
                "models": [
                    {
                        "name": "fct_sales",
                        "columns": [
                            {
                                "name": "dim_id",
                                "tests": [
                                    {
                                        "relationships": {
                                            "to": "ref('dim_custom')",
                                            "field": "id",
                                        }
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        )
    )
    (tmp_path / "data_model.yml").write_text(
        yaml.safe_dump(
            {
                "version": 0.1,
                "entities": [
                    {
                        "id": "dim_custom",
                        "label": "Custom dimension",
                        "model_ref": "model.project.dim_custom",
                        "drafted_fields": [],
                    }
                ],
                "relationships": [],
            }
        )
    )
    (tmp_path / "canvas_layout.yml").write_text(
        yaml.safe_dump(
            {
                "version": 0.1,
                "entities": {"dim_custom": {"position": {"x": 1, "y": 2}}},
                "relationships": {},
            }
        )
    )


@pytest.fixture
def real_boot_fixture(tmp_path, monkeypatch):
    """Configure services against a temporary real dbt artifact fixture."""
    _write_boot_fixture(tmp_path)

    from trellis_datamodel import config as cfg

    monkeypatch.setattr(cfg, "FRAMEWORK", "dbt-core")
    monkeypatch.setattr(cfg, "DBT_PROJECT_PATH", str(tmp_path))
    monkeypatch.setattr(cfg, "DBT_MODEL_PATHS", ["3_core"])
    monkeypatch.setattr(cfg, "MANIFEST_PATH", str(tmp_path / "manifest.json"))
    monkeypatch.setattr(cfg, "CATALOG_PATH", str(tmp_path / "catalog.json"))
    monkeypatch.setattr(cfg, "DATA_MODEL_PATH", str(tmp_path / "data_model.yml"))
    monkeypatch.setattr(cfg, "CANVAS_LAYOUT_PATH", str(tmp_path / "canvas_layout.yml"))
    monkeypatch.setattr(cfg, "DIMENSIONAL_MODELING_CONFIG", cfg.DimensionalModelingConfig(
        enabled=True,
        dimension_prefix=["dim_"],
        fact_prefix=["fct_"],
    ))
    return tmp_path


def _phase_counts(collector: observability.PhaseCollector) -> dict[str, int]:
    return {name: record.call_count for name, record in collector.records.items()}


def _current_observability():
    """Use the live module after CLI tests intentionally reload package modules."""
    import importlib

    return importlib.import_module("trellis_datamodel.observability")


def test_real_adapter_artifact_reads_and_parses_are_timed(real_boot_fixture):
    """A real model service call emits one read/parse pair per artifact."""
    current_observability = _current_observability()
    from trellis_datamodel.services.manifest import get_models

    with current_observability.collector_scope() as collector:
        models = get_models()

    assert {model["name"] for model in models} == {"dim_custom", "fct_sales"}
    assert _phase_counts(collector)["artifact_read"] == 2
    assert _phase_counts(collector)["artifact_parse"] == 2


def test_real_boot_services_emit_fixed_phase_keys_and_call_counts(real_boot_fixture):
    """Real route/service calls cover every backend boot phase exactly."""
    current_observability = _current_observability()
    from trellis_datamodel.routes.data_model import get_data_model
    from trellis_datamodel.services.lineage import extract_source_systems_for_model
    from trellis_datamodel.services.reconciliation import reconcile_framework
    from trellis_datamodel.services.schema import get_model_schema, infer_relationships

    with current_observability.collector_scope() as reconciliation_collector:
        reconciled, changed = reconcile_framework()
    assert reconciled["entities"]
    assert changed is True
    assert _phase_counts(reconciliation_collector)["reconciliation"] == 1

    with current_observability.collector_scope() as data_model_collector:
        data_model = asyncio.run(get_data_model())
    assert data_model["entities"][0]["source_system"] == ["warehouse"]
    data_model_counts = _phase_counts(data_model_collector)
    assert data_model_counts["data_model_read"] == 1
    assert data_model_counts["layout_read"] == 1
    assert data_model_counts["entity_inference"] == 1
    assert data_model_counts["source_lineage"] == 1

    with current_observability.collector_scope() as lineage_collector:
        assert extract_source_systems_for_model("model.project.dim_custom") == [
            "warehouse"
        ]
    assert _phase_counts(lineage_collector)["source_lineage"] == 1

    with current_observability.collector_scope() as schema_collector:
        schema = get_model_schema("dim_custom")
    assert schema["model_name"] == "dim_custom"
    assert _phase_counts(schema_collector)["schema_read"] == 1

    with current_observability.collector_scope() as relationship_collector:
        relationships = infer_relationships(include_unbound=True)
    assert relationships[0]["source_model_name"] == "dim_custom"
    assert _phase_counts(relationship_collector)["relationship_scan"] == 1

    expected_phase_names = set(current_observability.PHASE_NAMES)
    for collector in (
        reconciliation_collector,
        data_model_collector,
        lineage_collector,
        schema_collector,
        relationship_collector,
    ):
        assert set(collector.records) <= expected_phase_names
