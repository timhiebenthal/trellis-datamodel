"""
Strict-xfail contract tests pinning the adapter surface deferred to the
BruinAdapter spec.

These tests are meant to FAIL (as xfail), not pass. They document the
subsystems that still bypass TransformationAdapter and read dbt files
(manifest.json / catalog.json / schema.yml) directly: services/lineage.py,
services/exposures.py, routes/manifest.py, and the source-system extraction
in routes/data_model.py. Because they are marked `strict=True`, an
unexpected pass (XPASS) becomes a hard failure, so this deferred-work list
cannot be silently forgotten or half-implemented.
"""

import re
from pathlib import Path

import pytest

FUTURE_REASON = (
    "Deferred to the BruinAdapter spec: this subsystem still reads dbt files "
    "directly instead of going through TransformationAdapter. "
    "When implemented, remove the xfail mark — strict=True makes an "
    "unexpected pass a hard failure so this cannot be silently skipped."
)


@pytest.mark.xfail(strict=True, reason=FUTURE_REASON)
def test_adapter_exposes_get_lineage(fake_adapter):
    """services/lineage.py parses manifest.json/catalog.json directly."""
    upstream = fake_adapter.get_lineage("model.fake.customer")
    assert [n["unique_id"] for n in upstream] == ["model.fake.stg_customer"]


@pytest.mark.xfail(strict=True, reason=FUTURE_REASON)
def test_adapter_exposes_get_exposures(fake_adapter):
    """services/exposures.py reads manifest.json + probes DBT_PROJECT_PATH for exposures.yml."""
    assert fake_adapter.get_exposures()[0]["name"] == "fake_dashboard"


@pytest.mark.xfail(strict=True, reason=FUTURE_REASON)
def test_adapter_exposes_get_source_systems_for_model(fake_adapter):
    """routes/data_model.py:266-290,514-548 reads manifest/catalog for source-system extraction."""
    assert fake_adapter.get_source_systems_for_model("model.fake.customer") == ["crm"]


@pytest.mark.xfail(strict=True, reason=FUTURE_REASON)
def test_adapter_exposes_get_project_status(fake_adapter):
    """routes/manifest.py:50-110 reports dbt manifest/catalog/project paths directly."""
    status = fake_adapter.get_project_status()
    assert {"artifacts_present", "project_path", "model_paths_configured"} <= status.keys()


@pytest.mark.xfail(strict=True, reason=FUTURE_REASON)
def test_no_service_reads_framework_artifacts_directly():
    """The end state: only adapters/ may name manifest.json / catalog.json / schema.yml."""
    repo_root = Path(__file__).resolve().parents[2]
    offenders = [
        str(p)
        for p in repo_root.joinpath("trellis_datamodel").rglob("*.py")
        if "adapters" not in p.parts
        and "tests" not in p.parts
        and re.search(r"manifest\.json|catalog\.json|MANIFEST_PATH|CATALOG_PATH", p.read_text())
    ]
    assert offenders == []
