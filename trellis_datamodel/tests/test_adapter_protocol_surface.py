"""
Characterization tests for the TransformationAdapter protocol surface.

The protocol is the contract. Anything a service calls on an adapter must be
declared here, or the abstraction is fictional. These tests close the
adapter-boundary loopholes described in Sprint 4B of the
generalize-transformation-adapter spec: methods called on adapter instances
without being declared on the protocol, and modules that reach around
`get_adapter()` to import `DbtCoreAdapter` directly.
"""

from pathlib import Path

import pytest

from trellis_datamodel.adapters.base import TransformationAdapter
from trellis_datamodel.adapters.dbt_core import DbtCoreAdapter
from trellis_datamodel.exceptions import NotFoundError
from trellis_datamodel.tests.conftest import FakeAdapter

REQUIRED_PROTOCOL_METHODS = {
    "get_models",
    "get_model_schema",
    "save_model_schema",
    "infer_relationships",
    "sync_relationships",
    "save_schema_file",
    "infer_entity_types",
    "get_model_dirs",
    "reset_inference_cache",
    "get_lineage",
    "get_exposures",
    "get_source_systems_for_model",
    "get_project_status",
}


def test_protocol_declares_every_method_services_call():
    declared = {n for n in dir(TransformationAdapter) if not n.startswith("_")}
    assert REQUIRED_PROTOCOL_METHODS <= declared


def test_dbt_core_adapter_satisfies_protocol():
    for name in REQUIRED_PROTOCOL_METHODS:
        assert callable(getattr(DbtCoreAdapter, name, None)), name


def test_fake_adapter_satisfies_protocol():
    for name in REQUIRED_PROTOCOL_METHODS:
        assert callable(getattr(FakeAdapter, name, None)), name


class TestLineageContract:
    """get_lineage returns a raw upstream graph; presentation is the caller's job."""

    def test_returns_upstream_nodes_and_edges(self, fake_adapter):
        graph = fake_adapter.get_lineage("model.fake.customer")

        assert {n["unique_id"] for n in graph["nodes"]} == {
            "model.fake.customer",
            "model.fake.stg_customer",
            "source.fake.crm.customers",
        }
        assert {"source": "model.fake.stg_customer", "target": "model.fake.customer"} in (
            graph["edges"]
        )

    def test_nodes_carry_everything_the_service_needs(self, fake_adapter):
        """The service must never need to reach past these fields into artifacts."""
        nodes = {
            n["unique_id"]: n for n in fake_adapter.get_lineage("model.fake.customer")["nodes"]
        }

        source = nodes["source.fake.crm.customers"]
        assert source["is_source"] is True
        assert source["resource_type"] == "source"
        assert source["source_name"] == "crm"

        model = nodes["model.fake.stg_customer"]
        assert model["is_source"] is False
        assert model["resource_type"] == "model"
        assert set(model) >= {"unique_id", "name", "folder"}

    def test_unknown_model_raises_not_found(self, fake_adapter):
        with pytest.raises(NotFoundError):
            fake_adapter.get_lineage("model.fake.nope")


def test_adapter_exposes_exposures(fake_adapter):
    """Exposures arrive with dependencies already resolved to unique_ids."""
    exposures = fake_adapter.get_exposures()

    assert exposures[0]["name"] == "fake_dashboard"
    assert exposures[0]["depends_on"] == ["model.fake.customer"]


def test_adapter_exposes_source_systems_for_model(fake_adapter):
    assert fake_adapter.get_source_systems_for_model("model.fake.customer") == ["crm"]


def test_source_systems_never_raises(fake_adapter):
    """Source chips are optional display: an unknown model yields none, not an error."""
    assert fake_adapter.get_source_systems_for_model("model.fake.nope") == []


def test_adapter_exposes_project_status(fake_adapter):
    status = fake_adapter.get_project_status()

    assert {
        "framework",
        "artifacts_present",
        "artifacts",
        "project_path",
        "project_path_exists",
        "model_paths_configured",
        "model_paths_resolved",
        "capabilities",
        "error",
    } <= status.keys()


def test_project_status_declares_capabilities(fake_adapter):
    """Optional features gate on capabilities, never on the framework name."""
    capabilities = fake_adapter.get_project_status()["capabilities"]

    assert {
        "lineage",
        "column_lineage",
        "exposures",
        "relationships",
        "scaffolding",
    } == capabilities.keys()
    assert all(isinstance(v, bool) for v in capabilities.values())


def test_no_service_or_route_imports_dbt_core_adapter_directly():
    repo_root = Path(__file__).resolve().parents[2]
    hits = [
        p
        for p in repo_root.joinpath("trellis_datamodel").rglob("*.py")
        if "adapters" not in p.parts
        and "tests" not in p.parts
        and "DbtCoreAdapter" in p.read_text()
    ]
    assert hits == []
