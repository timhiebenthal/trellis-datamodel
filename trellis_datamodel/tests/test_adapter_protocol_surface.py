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

from trellis_datamodel.adapters.base import TransformationAdapter
from trellis_datamodel.adapters.dbt_core import DbtCoreAdapter
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
