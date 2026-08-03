"""Tests for exposures API."""

import importlib
import sys
import textwrap
from pathlib import Path

import trellis_datamodel.config as cfg
from trellis_datamodel.services.exposures import get_exposures, _find_entities_for_model
from trellis_datamodel.tests._entity_compat import get_model_ref


def _prepare_config(monkeypatch):
    """Reset config globals and disable test-mode short-circuiting."""
    # CLI tests drop trellis_datamodel modules from sys.modules to simulate an
    # installed package. Refresh cfg so it points at the current module instance.
    import importlib

    global cfg
    cfg = importlib.import_module("trellis_datamodel.config")
    monkeypatch.setitem(sys.modules, "trellis_datamodel.config", cfg)

    monkeypatch.setattr(cfg, "_TEST_DIR", "")
    monkeypatch.delenv("DATAMODEL_TEST_DIR", raising=False)
    monkeypatch.setattr(cfg, "CONFIG_PATH", "")
    monkeypatch.setattr(cfg, "DBT_PROJECT_PATH", "")
    monkeypatch.setattr(cfg, "LINEAGE_ENABLED", False)
    monkeypatch.setattr(cfg, "LINEAGE_LAYERS", [])
    # Don't monkeypatch EXPOSURES_ENABLED here - let load_config set it from the config file
    # We'll set it explicitly after load_config if needed


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

    # Verify that EXPOSURES_ENABLED was set correctly
    assert (
        cfg.EXPOSURES_ENABLED is True
    ), f"EXPOSURES_ENABLED should be True but is {cfg.EXPOSURES_ENABLED}"

    # Create a minimal manifest with no exposures (but valid structure)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text('{"nodes": {}, "sources": {}, "exposures": {}}')
    monkeypatch.setattr(cfg, "MANIFEST_PATH", str(manifest_path))

    # Ensure EXPOSURES_ENABLED is set correctly
    cfg.EXPOSURES_ENABLED = True
    monkeypatch.setattr(cfg, "EXPOSURES_ENABLED", True)

    # Reload routes modules to ensure they pick up the updated config value
    # This must be done AFTER setting EXPOSURES_ENABLED so routes see the correct value
    if "trellis_datamodel.routes.exposures" in sys.modules:
        importlib.reload(sys.modules["trellis_datamodel.routes.exposures"])
    if "trellis_datamodel.server" in sys.modules:
        importlib.reload(sys.modules["trellis_datamodel.server"])

    # After reloading, ensure EXPOSURES_ENABLED is still True
    cfg.EXPOSURES_ENABLED = True
    monkeypatch.setattr(cfg, "EXPOSURES_ENABLED", True)

    # Verify the value is set correctly
    assert (
        cfg.EXPOSURES_ENABLED is True
    ), f"EXPOSURES_ENABLED should be True but is {cfg.EXPOSURES_ENABLED}"

    # Get a fresh test client with the reloaded app
    from trellis_datamodel.server import app
    from starlette.testclient import TestClient

    with TestClient(app) as fresh_client:
        response = fresh_client.get("/api/exposures")
    assert response.status_code == 200
    data = response.json()
    assert "exposures" in data
    assert "entityUsage" in data


def test_entity_ids_for_model_matches_primary_binding_and_additional_models():
    """_find_entities_for_model matches entities bound via their primary
    model reference as well as entities that merely list the model under
    additional_models, and does not match unrelated entities."""
    data_model = {
        "entities": [
            {"id": "orders", "dbt_model": "model.project.orders"},
            {
                "id": "sales_summary",
                "dbt_model": "model.project.sales_summary",
                "additional_models": ["model.project.orders"],
            },
            {"id": "customers", "dbt_model": "model.project.customers"},
        ]
    }

    # Sanity check the fixture itself resolves through the compat helper.
    orders_entity = data_model["entities"][0]
    assert get_model_ref(orders_entity) == "model.project.orders"

    entity_ids = _find_entities_for_model("model.project.orders", data_model)

    assert set(entity_ids) == {"orders", "sales_summary"}
    assert "customers" not in entity_ids


def test_entity_ids_for_model_matches_entity_using_generic_model_ref():
    """_find_entities_for_model must resolve the model binding via the
    generic `model_ref` key, not just the legacy `dbt_model` key."""
    data_model = {
        "entities": [
            {"id": "orders", "model_ref": "model.project.orders"},
            {"id": "customers", "model_ref": "model.project.customers"},
        ]
    }

    entity_ids = _find_entities_for_model("model.project.orders", data_model)

    assert set(entity_ids) == {"orders"}
    assert "customers" not in entity_ids
