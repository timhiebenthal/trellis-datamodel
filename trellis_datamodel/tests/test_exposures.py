"""Tests for exposures API."""

import textwrap
from pathlib import Path

import trellis_datamodel.config as cfg
from trellis_datamodel.routes.exposures import _load_manifest, _load_data_model


def _prepare_config(monkeypatch):
    """Reset config globals and disable test-mode short-circuiting."""
    monkeypatch.setattr(cfg, "_TEST_DIR", "")
    monkeypatch.delenv("DATAMODEL_TEST_DIR", raising=False)
    monkeypatch.setattr(cfg, "CONFIG_PATH", "")
    monkeypatch.setattr(cfg, "DBT_PROJECT_PATH", "")
    monkeypatch.setattr(cfg, "LINEAGE_ENABLED", False)
    monkeypatch.setattr(cfg, "LINEAGE_LAYERS", [])


def _write_config(tmp_path: Path, contents: str) -> Path:
    path = tmp_path / "trellis.yml"
    path.write_text(textwrap.dedent(contents))
    return path


def test_exposures_api_returns_403_when_disabled(monkeypatch, tmp_path, test_client):
    _prepare_config(monkeypatch)
    config_path = _write_config(
        tmp_path,
        """
        framework: dbt-core
        dbt_project_path: .
        exposures:
          enabled: false
        """,
    )

    cfg.load_config(str(config_path))

    response = test_client.get("/api/exposures")
    assert response.status_code == 403
    assert "disabled" in response.json()["detail"].lower()


def test_exposures_api_returns_200_when_enabled(monkeypatch, tmp_path, test_client):
    _prepare_config(monkeypatch)
    config_path = _write_config(
        tmp_path,
        """
        framework: dbt-core
        dbt_project_path: .
        exposures:
          enabled: true
        """,
    )

    cfg.load_config(str(config_path))

    # Create a minimal manifest with no exposures (but valid structure)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text('{"nodes": {}, "sources": {}, "exposures": {}}')
    monkeypatch.setattr(cfg, "MANIFEST_PATH", str(manifest_path))

    response = test_client.get("/api/exposures")
    assert response.status_code == 200
    data = response.json()
    assert "exposures" in data
    assert "entityUsage" in data

