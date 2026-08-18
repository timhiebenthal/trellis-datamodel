"""Tests for Canvas navigation and project default filter configuration."""

import importlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from trellis_datamodel import config as cfg
from trellis_datamodel.services.config_service import validate_config


def test_validate_config_accepts_canvas_start_page():
    valid, error = validate_config({"start_page": "canvas"})

    assert valid is True
    assert error is None


def test_validate_config_accepts_entity_list_start_page():
    valid, error = validate_config({"start_page": "entity-list"})

    assert valid is True
    assert error is None


def test_validate_config_rejects_unknown_start_page():
    valid, error = validate_config({"start_page": "unknown"})

    assert valid is False
    assert error is not None


def test_validate_config_accepts_canvas_default_domains_and_tags():
    valid, error = validate_config(
        {
            "canvas": {
                "default_filters": {
                    "domains": ["sales"],
                    "tags": ["important"],
                }
            }
        }
    )

    assert valid is True
    assert error is None


def test_validate_config_rejects_non_list_canvas_default_filters():
    valid, error = validate_config(
        {"canvas": {"default_filters": {"domains": "sales", "tags": []}}}
    )

    assert valid is False
    assert error is not None


def test_load_config_normalizes_missing_canvas_defaults_to_empty_lists(
    monkeypatch, tmp_path
):
    config_path = tmp_path / "trellis.yml"
    config_path.write_text("dbt_project_path: .\n")
    monkeypatch.setattr(cfg, "_TEST_DIR", "")

    cfg.load_config(str(config_path))

    assert cfg.START_PAGE == "canvas"
    assert cfg.CANVAS_DEFAULT_FILTERS == {"domains": [], "tags": []}


@pytest.fixture
def canvas_config_client(monkeypatch, tmp_path):
    """Client backed by a config containing the new Canvas settings."""
    config_path = Path(tmp_path) / "trellis.yml"
    config_path.write_text(
        "dbt_project_path: .\n"
        "start_page: entity-list\n"
        "canvas:\n"
        "  default_filters:\n"
        "    domains: [sales]\n"
        "    tags: [important]\n"
    )

    cfg.load_config(str(config_path))

    import trellis_datamodel.config as config_module
    import trellis_datamodel.services.config_service as config_service_module
    import trellis_datamodel.routes.config as config_route_module
    import trellis_datamodel.server as server_module

    monkeypatch.setattr(
        config_module, "find_config_file", lambda config_override=None: str(config_path)
    )
    monkeypatch.setattr(
        config_service_module,
        "find_config_file",
        lambda config_override=None: str(config_path),
    )
    importlib.reload(config_route_module)
    importlib.reload(server_module)

    with TestClient(server_module.app) as client:
        yield client


def test_config_api_preserves_canvas_navigation_fields(canvas_config_client):
    response = canvas_config_client.get("/api/config")

    assert response.status_code == 200
    config = response.json()["config"]
    assert config["start_page"] == "entity-list"
    assert config["canvas"]["default_filters"] == {
        "domains": ["sales"],
        "tags": ["important"],
    }


def test_config_info_exposes_normalized_canvas_navigation_fields(
    canvas_config_client,
):
    response = canvas_config_client.get("/api/config-info")

    assert response.status_code == 200
    data = response.json()
    assert data["start_page"] == "entity-list"
    assert data["canvas_default_filters"] == {
        "domains": ["sales"],
        "tags": ["important"],
    }
