"""Regression tests for batched source-system lineage extraction."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import replace
import json

from trellis_datamodel.adapters.bruin import BruinAdapter
from trellis_datamodel.adapters.dbt_core import DbtCoreAdapter
from trellis_datamodel.services import lineage as lineage_service


DBT_DIMENSION_ID = "model.project.dim__customer"
DBT_FACT_ID = "model.project.fct__order"


def _write_dbt_fixture(tmp_path):
    project = tmp_path / "dbt_project"
    manifest_path = project / "target" / "manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest = {
        "nodes": {
            DBT_DIMENSION_ID: {
                "unique_id": DBT_DIMENSION_ID,
                "resource_type": "model",
                "name": "dim__customer",
                "depends_on": {"nodes": ["model.project.stg__customer"]},
            },
            "model.project.stg__customer": {
                "unique_id": "model.project.stg__customer",
                "resource_type": "model",
                "name": "stg__customer",
                "depends_on": {"nodes": ["source.project.crm.customers"]},
            },
            DBT_FACT_ID: {
                "unique_id": DBT_FACT_ID,
                "resource_type": "model",
                "name": "fct__order",
                "depends_on": {
                    "nodes": [
                        "model.project.stg__customer",
                        "model.project.stg__order",
                    ]
                },
            },
            "model.project.stg__order": {
                "unique_id": "model.project.stg__order",
                "resource_type": "model",
                "name": "stg__order",
                "depends_on": {"nodes": ["source.project.warehouse.orders"]},
            },
        },
        "sources": {
            "source.project.crm.customers": {
                "unique_id": "source.project.crm.customers",
                "resource_type": "source",
                "name": "customers",
                "source_name": "crm",
            },
            "source.project.warehouse.orders": {
                "unique_id": "source.project.warehouse.orders",
                "resource_type": "source",
                "name": "orders",
                "source_name": "postgres",
            },
        },
    }
    manifest_path.write_text(json.dumps(manifest))
    return DbtCoreAdapter(
        manifest_path=str(manifest_path),
        catalog_path="",
        project_path=str(project),
        data_model_path="",
        model_paths=[],
    )


def test_batch_source_system_index_matches_per_model_results(tmp_path, monkeypatch):
    adapter = _write_dbt_fixture(tmp_path)
    monkeypatch.setattr(lineage_service, "get_adapter", lambda: adapter)
    model_ids = [DBT_DIMENSION_ID, DBT_FACT_ID]

    batch = lineage_service.extract_source_systems_for_models(model_ids)
    individual = {
        model_id: lineage_service.extract_source_systems_for_model(model_id)
        for model_id in model_ids
    }

    assert batch == individual


def test_duplicate_model_ids_share_one_upstream_walk(tmp_path, monkeypatch):
    adapter = _write_dbt_fixture(tmp_path)
    original_get_snapshot = adapter._get_artifact_snapshot
    snapshot = original_get_snapshot()
    dependency_index = snapshot.dependency_index
    dependency_lookups = Counter()

    class CountingDependencyIndex(Mapping):
        def __getitem__(self, model_id):
            dependency_lookups[model_id] += 1
            return dependency_index[model_id]

        def __iter__(self):
            return iter(dependency_index)

        def __len__(self):
            return len(dependency_index)

    snapshot = replace(
        snapshot,
        dependency_index=CountingDependencyIndex(),
    )
    snapshot_calls = 0

    def counted_snapshot():
        nonlocal snapshot_calls
        snapshot_calls += 1
        return snapshot

    monkeypatch.setattr(adapter, "_get_artifact_snapshot", counted_snapshot)
    monkeypatch.setattr(lineage_service, "get_adapter", lambda: adapter)

    result = lineage_service.extract_source_systems_for_models(
        [DBT_DIMENSION_ID, DBT_FACT_ID, DBT_DIMENSION_ID]
    )

    assert result == {
        DBT_DIMENSION_ID: ["crm"],
        DBT_FACT_ID: ["crm", "postgres"],
    }
    assert snapshot_calls == 1
    assert dependency_lookups["model.project.stg__customer"] == 1


def test_primary_and_additional_models_preserve_source_order_and_deduplication(
    tmp_path, monkeypatch
):
    adapter = _write_dbt_fixture(tmp_path)
    monkeypatch.setattr(lineage_service, "get_adapter", lambda: adapter)
    primary_and_additional = [DBT_DIMENSION_ID, DBT_FACT_ID, DBT_DIMENSION_ID]

    source_index = lineage_service.extract_source_systems_for_models(
        primary_and_additional
    )
    ordered_sources = []
    for model_id in primary_and_additional:
        for source_id in source_index[model_id]:
            if source_id not in ordered_sources:
                ordered_sources.append(source_id)

    assert list(source_index) == [DBT_DIMENSION_ID, DBT_FACT_ID]
    assert ordered_sources == ["crm", "postgres"]


def test_bruin_and_dbt_adapters_produce_equivalent_batch_contracts(
    tmp_path, monkeypatch, bruin_pipeline
):
    dbt_adapter = _write_dbt_fixture(tmp_path)
    monkeypatch.setattr(lineage_service, "get_adapter", lambda: dbt_adapter)
    dbt_result = lineage_service.extract_source_systems_for_models(
        [DBT_DIMENSION_ID, DBT_FACT_ID]
    )

    bruin_adapter = BruinAdapter(
        pipeline_path=bruin_pipeline,
        data_model_path="",
        asset_paths=[],
    )
    monkeypatch.setattr(lineage_service, "get_adapter", lambda: bruin_adapter)
    bruin_result = lineage_service.extract_source_systems_for_models(
        ["core.dim__customer", "core.fct__order"]
    )

    assert dbt_result == {
        DBT_DIMENSION_ID: ["crm"],
        DBT_FACT_ID: ["crm", "postgres"],
    }
    assert bruin_result == {
        "core.dim__customer": ["crm_api"],
        "core.fct__order": ["crm_api", "postgres_prod"],
    }
    assert all(isinstance(value, list) for value in dbt_result.values())
    assert all(isinstance(value, list) for value in bruin_result.values())
