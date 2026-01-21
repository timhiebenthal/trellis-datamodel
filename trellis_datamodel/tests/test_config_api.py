"""Tests for config API endpoints."""

import os
import sys
import tempfile
import textwrap
from pathlib import Path
from datetime import datetime
import importlib

import pytest
from httpx import AsyncClient


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory with a config file for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        config_path = Path(tmp_dir) / "trellis.yml"
        config_content = textwrap.dedent(
            """\
            framework: dbt-core
            modeling_style: entity_model
            dbt_project_path: ./dbt_project
            dbt_manifest_path: target/manifest.json
            dbt_catalog_path: target/catalog.json
            data_model_file: data_model.yml
            dbt_model_paths:
              - 3_core
            lineage:
              enabled: true
              layers:
                - 1_clean
                - 2_prep
            entity_creation_guidance:
              enabled: true
              push_warning_enabled: true
              min_description_length: 10
              disabled_guidance: []
            exposures:
              enabled: false
              default_layout: dashboards-as-rows
            dimensional_modeling:
              inference_patterns:
                dimension_prefix: dim_
                fact_prefix: fact_
            entity_modeling:
              inference_patterns:
                prefix: entity_
            """
        )

        config_path.write_text(config_content)

        # Create required directories and files
        (Path(tmp_dir) / "dbt_project").mkdir(exist_ok=True)
        (Path(tmp_dir) / "dbt_project" / "target").mkdir(exist_ok=True)
        (Path(tmp_dir) / "dbt_project" / "target" / "manifest.json").write_text("{}")
        (Path(tmp_dir) / "dbt_project" / "target" / "catalog.json").write_text("{}")

        yield tmp_dir


@pytest.fixture
async def client(temp_config_dir, monkeypatch):
    """Create a test client with config path set."""
    # Monkeypatch to find the temp config BEFORE any imports
    import trellis_datamodel.config as config_module
    import trellis_datamodel.services.config_service as config_service_module

    def patched_find(config_override=None):
        return str(Path(temp_config_dir) / "trellis.yml")

    # Patch both the original module and the service module that imports it
    monkeypatch.setattr(config_module, "find_config_file", patched_find)
    monkeypatch.setattr(config_service_module, "find_config_file", patched_find)

    # Reload the config route to pick up the patched function
    if "trellis_datamodel.routes.config" in sys.modules:
        importlib.reload(sys.modules["trellis_datamodel.routes.config"])
    if "trellis_datamodel.server" in sys.modules:
        importlib.reload(sys.modules["trellis_datamodel.server"])

    from trellis_datamodel.server import app
    from httpx import ASGITransport

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_get_config_success(client: AsyncClient):
    """Test GET /api/config returns config and schema."""
    response = await client.get("/api/config")

    assert response.status_code == 200
    data = response.json()

    assert "config" in data
    assert "schema_metadata" in data
    assert "file_info" in data

    # Check schema has expected fields
    schema = data["schema_metadata"]
    assert "fields" in schema
    assert "beta_flags" in schema

    # Check beta flags
    assert "lineage.enabled" in schema["beta_flags"]
    assert "exposures.enabled" in schema["beta_flags"]


@pytest.mark.asyncio
async def test_get_config_schema_only(client: AsyncClient):
    """Test GET /api/config/schema returns schema only."""
    response = await client.get("/api/config/schema")

    assert response.status_code == 200
    data = response.json()

    assert "fields" in data
    assert "beta_flags" in data


@pytest.mark.asyncio
async def test_put_config_valid_update(client: AsyncClient, temp_config_dir):
    """Test PUT /api/config with valid config."""
    # Get current config first
    get_response = await client.get("/api/config")
    assert get_response.status_code == 200
    initial_config = get_response.json()["config"]
    file_info = get_response.json()["file_info"]

    # Update a field
    updated_config = {**initial_config, "modeling_style": "dimensional_model"}

    put_response = await client.put(
        "/api/config",
        json={
            "config": updated_config,
            "expected_mtime": file_info["mtime"],
            "expected_hash": file_info["hash"],
        },
    )

    assert put_response.status_code == 200
    data = put_response.json()

    assert "config" in data
    assert data["config"]["modeling_style"] == "dimensional_model"
    assert "file_info" in data

    # Check backup was created
    config_dir = Path(temp_config_dir)
    backup_path = config_dir / "trellis.yml.backup"
    assert backup_path.exists()


@pytest.mark.asyncio
async def test_put_config_conflict(client: AsyncClient, temp_config_dir):
    """Test PUT /api/config with conflict detection."""
    import time

    # Get current config first
    get_response = await client.get("/api/config")
    assert get_response.status_code == 200
    initial_config = get_response.json()["config"]
    file_info = get_response.json()["file_info"]

    # Wait a bit to ensure mtime changes
    time.sleep(0.01)

    # Simulate file modification by updating directly
    config_path = Path(temp_config_dir) / "trellis.yml"
    config_content = config_path.read_text()
    config_path.write_text(config_content + "\n# Modified\n")

    # Try to update with old mtime/hash
    updated_config = {**initial_config, "modeling_style": "dimensional_model"}
    put_response = await client.put(
        "/api/config",
        json={
            "config": updated_config,
            "expected_mtime": file_info["mtime"],
            "expected_hash": file_info["hash"],
        },
    )

    assert put_response.status_code == 409
    data = put_response.json()

    assert "error" in data["detail"]
    assert "conflict" in data["detail"]


@pytest.mark.asyncio
async def test_put_config_validation_error(client: AsyncClient, temp_config_dir):
    """Test PUT /api/config with validation error."""
    # Get current config first
    get_response = await client.get("/api/config")
    assert get_response.status_code == 200
    initial_config = get_response.json()["config"]

    # Try to set invalid enum value
    updated_config = {
        **initial_config,
        "framework": "invalid_framework",  # Invalid enum
    }

    put_response = await client.put(
        "/api/config",
        json={"config": updated_config},
    )

    assert put_response.status_code == 422
    data = put_response.json()

    assert "error" in data["detail"]
    assert "validation_error" in data["detail"]["error"]


@pytest.mark.asyncio
async def test_put_config_invalid_path(client: AsyncClient, temp_config_dir):
    """Test PUT /api/config accepts non-existent paths (they might be created later)."""
    config_path = Path(temp_config_dir) / "trellis.yml"

    # Set non-existent path - this should be allowed
    get_response = await client.get("/api/config")
    initial_config = get_response.json()["config"]

    updated_config = {
        **initial_config,
        "dbt_project_path": "/nonexistent/path",
    }

    put_response = await client.put(
        "/api/config",
        json={"config": updated_config},
    )

    # Should succeed - paths don't need to exist at config time
    assert put_response.status_code == 200
    data = put_response.json()

    assert "config" in data
    assert data["config"]["dbt_project_path"] == "/nonexistent/path"


@pytest.mark.asyncio
async def test_validate_config_endpoint(client: AsyncClient):
    """Test POST /api/config/validate validates config."""
    valid_config = {
        "framework": "dbt-core",
        "modeling_style": "entity_model",
        "dbt_project_path": "./dbt_project",
    }

    response = await client.post("/api/config/validate", json=valid_config)

    assert response.status_code == 200
    data = response.json()

    assert data["valid"] is True
    assert data.get("error") is None


@pytest.mark.asyncio
async def test_validate_config_invalid(client: AsyncClient):
    """Test POST /api/config/validate with invalid config."""
    invalid_config = {
        "framework": "invalid_enum",
        "modeling_style": "invalid_style",
    }

    response = await client.post("/api/config/validate", json=invalid_config)

    assert response.status_code == 200
    data = response.json()

    assert data["valid"] is False
    assert "error" in data
    assert data["error"] is not None


@pytest.mark.asyncio
async def test_config_file_info_includes_mtime_and_hash(client: AsyncClient):
    """Test that GET /api/config returns file info with mtime and hash."""
    response = await client.get("/api/config")

    assert response.status_code == 200
    data = response.json()

    assert "file_info" in data
    file_info = data["file_info"]

    assert "path" in file_info
    assert "mtime" in file_info
    assert "hash" in file_info

    # Check mtime is a number
    assert isinstance(file_info["mtime"], (int, float))

    # Check hash is a string
    assert isinstance(file_info["hash"], str)
    assert len(file_info["hash"]) > 0


@pytest.mark.asyncio
async def test_config_beta_flags_list(client: AsyncClient):
    """Test that schema metadata includes correct beta flags."""
    response = await client.get("/api/config/schema")

    assert response.status_code == 200
    data = response.json()

    assert "beta_flags" in data
    beta_flags = data["beta_flags"]

    # Check expected beta flags
    assert "lineage.enabled" in beta_flags
    assert "lineage.layers" in beta_flags
    assert "exposures.enabled" in beta_flags
    assert "exposures.default_layout" in beta_flags


@pytest.mark.asyncio
async def test_config_schema_field_descriptions(client: AsyncClient):
    """Test that schema fields have descriptions."""
    response = await client.get("/api/config/schema")

    assert response.status_code == 200
    data = response.json()

    assert "fields" in data
    fields = data["fields"]

    # Check some important fields have descriptions
    assert "framework" in fields
    assert "modeling_style" in fields
    assert "dbt_project_path" in fields

    # Check field metadata structure
    for field_name, field_metadata in list(fields.items())[:3]:
        assert "type" in field_metadata
        assert "required" in field_metadata
        assert "description" in field_metadata
        assert "beta" in field_metadata


@pytest.mark.asyncio
async def test_reload_config_success(client: AsyncClient, temp_config_dir):
    """Test POST /api/config/reload successfully reloads config."""
    # First, update config to change a value
    get_response = await client.get("/api/config")
    assert get_response.status_code == 200
    initial_config = get_response.json()["config"]
    file_info = get_response.json()["file_info"]

    # Update a field
    updated_config = {**initial_config, "modeling_style": "dimensional_model"}
    put_response = await client.put(
        "/api/config",
        json={
            "config": updated_config,
            "expected_mtime": file_info["mtime"],
            "expected_hash": file_info["hash"],
        },
    )
    assert put_response.status_code == 200

    # Now reload config
    reload_response = await client.post("/api/config/reload")

    assert reload_response.status_code == 200
    data = reload_response.json()

    assert "status" in data
    assert data["status"] == "success"
    assert "message" in data
    assert "reloaded" in data["message"].lower()


@pytest.mark.asyncio
async def test_reload_config_missing_file(client: AsyncClient, temp_config_dir, monkeypatch):
    """Test POST /api/config/reload fails gracefully when config file is missing."""
    import trellis_datamodel.config as config_module

    def patched_find(config_override=None):
        return None  # Simulate missing config file

    monkeypatch.setattr(config_module, "find_config_file", patched_find)

    # Reload should fail with 400 (configuration error)
    reload_response = await client.post("/api/config/reload")

    assert reload_response.status_code == 400
    data = reload_response.json()

    assert "error" in data["detail"]
    assert "configuration_error" in data["detail"]["error"]
