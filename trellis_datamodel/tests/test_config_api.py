"""Tests for config API endpoints."""

import os
import sys
import tempfile
import textwrap
from pathlib import Path
from datetime import datetime
import importlib

import pytest
import yaml
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
async def test_reload_config_clears_artifact_and_entity_inference_caches(
    client: AsyncClient, temp_config_dir, monkeypatch
):
    """A successful reload invalidates every adapter cache namespace."""
    import trellis_datamodel.config as config_module
    import trellis_datamodel.routes.config as config_route
    from trellis_datamodel.adapters import artifact_snapshot, entity_type_inference

    config_path = Path(temp_config_dir) / "trellis.yml"
    original_config = config_path.read_text()
    manifest_path = (
        Path(temp_config_dir) / "dbt_project" / "target" / "manifest.json"
    )
    old_snapshot = artifact_snapshot.get_snapshot(manifest_path)
    entity_type_inference._CACHES.update(
        {
            "dbt-core": ("old-dbt", {"old_dbt": "dimension"}),
            "bruin": ("old-bruin", {"old_bruin": "fact"}),
        }
    )

    # Switch frameworks to prove the reset is not limited to the newly selected
    # adapter, and bypass config.reload_config's lower-level snapshot cleanup.
    config_path.write_text(
        original_config.replace("framework: dbt-core", "framework: bruin")
        + "\nbruin_pipeline_path: .\n"
    )
    monkeypatch.setattr(
        config_route,
        "reload_config",
        lambda: config_module.load_config(str(config_path)),
    )

    try:
        response = await client.post("/api/config/reload")
    finally:
        config_path.write_text(original_config)
        importlib.reload(config_module)

    assert response.status_code == 200
    assert entity_type_inference._CACHES == {}
    assert artifact_snapshot.get_snapshot(manifest_path) is not old_snapshot


@pytest.mark.asyncio
async def test_reload_with_new_artifact_paths_cannot_reuse_previous_snapshot(
    client: AsyncClient, temp_config_dir, monkeypatch
):
    """Reloading a changed manifest path reads the new artifact."""
    import trellis_datamodel.config as config_module
    import trellis_datamodel.routes.config as config_route
    from trellis_datamodel.adapters import artifact_snapshot
    from trellis_datamodel.adapters import get_adapter

    config_path = Path(temp_config_dir) / "trellis.yml"
    original_config = config_path.read_text()
    project_target = Path(temp_config_dir) / "dbt_project" / "target"
    old_manifest_path = project_target / "manifest.json"
    new_manifest_path = project_target / "new_manifest.json"
    old_snapshot = artifact_snapshot.get_snapshot(old_manifest_path)
    new_manifest_path.write_text('{"snapshot_version": 2}')
    config_path.write_text(
        original_config.replace(
            "dbt_manifest_path: target/manifest.json",
            "dbt_manifest_path: target/new_manifest.json",
        )
    )
    monkeypatch.setattr(
        config_route,
        "reload_config",
        lambda: config_module.load_config(str(config_path)),
    )

    try:
        response = await client.post("/api/config/reload")
        new_snapshot = get_adapter()._get_artifact_snapshot()
    finally:
        config_path.write_text(original_config)
        importlib.reload(config_module)

    assert response.status_code == 200
    assert new_snapshot is not old_snapshot
    assert new_snapshot.manifest["snapshot_version"] == 2


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


BRUIN_CONFIG = textwrap.dedent(
    """\
    framework: bruin
    modeling_style: dimensional_model
    bruin_pipeline_path: ./pipeline
    bruin_asset_paths:
      - 02_core
    bruin_default_asset_type: bq.sql
    data_model_file: data_model.yml
    lineage:
      enabled: true
      layers:
        - 01_prep
        - 02_core
    """
)
BRUIN_KEYS = {
    "bruin_pipeline_path": "./pipeline",
    "bruin_asset_paths": ["02_core"],
    "bruin_default_asset_type": "bq.sql",
}


def _write_bruin_project(config_dir: str) -> Path:
    """Replace the fixture's dbt trellis.yml with a Bruin one and its pipeline."""
    (Path(config_dir) / "pipeline" / "assets" / "02_core").mkdir(parents=True)
    (Path(config_dir) / "pipeline" / "pipeline.yml").write_text("name: shop\n")
    config_path = Path(config_dir) / "trellis.yml"
    config_path.write_text(BRUIN_CONFIG)
    return config_path


async def _load_then_save(client: AsyncClient) -> dict:
    """What the config page does on Save: GET the config, PUT it back unchanged."""
    loaded = (await client.get("/api/config")).json()
    response = await client.put(
        "/api/config",
        json={
            "config": loaded["config"],
            "expected_mtime": loaded["file_info"]["mtime"],
            "expected_hash": loaded["file_info"]["hash"],
        },
    )
    assert response.status_code == 200, response.text
    return loaded["config"]


@pytest.mark.asyncio
async def test_bruin_settings_survive_load_then_save(client: AsyncClient, temp_config_dir):
    config_path = _write_bruin_project(temp_config_dir)

    loaded = await _load_then_save(client)

    assert {k: loaded.get(k) for k in BRUIN_KEYS} == BRUIN_KEYS
    saved = yaml.safe_load(config_path.read_text())
    assert saved["framework"] == "bruin"
    assert {k: saved.get(k) for k in BRUIN_KEYS} == BRUIN_KEYS


@pytest.mark.asyncio
async def test_dbt_config_save_adds_no_bruin_keys(client: AsyncClient, temp_config_dir):
    await _load_then_save(client)

    saved = yaml.safe_load((Path(temp_config_dir) / "trellis.yml").read_text())
    assert saved["dbt_project_path"] == "./dbt_project"
    assert not [k for k in saved if k.startswith("bruin_")]


@pytest.mark.asyncio
async def test_config_schema_describes_bruin_fields(client: AsyncClient):
    fields = (await client.get("/api/config/schema")).json()["fields"]

    assert "bruin" in fields["framework"]["enum_values"]
    for key in BRUIN_KEYS:
        assert fields[key]["description"], key
    assert fields["bruin_asset_paths"]["type"] == "list"
    assert fields["bruin_default_asset_type"]["default"] == "duckdb.sql"


def test_validate_paths_accepts_an_existing_bruin_pipeline(temp_config_dir):
    from trellis_datamodel.services.config_service import _validate_paths

    config_path = _write_bruin_project(temp_config_dir)

    assert _validate_paths(yaml.safe_load(BRUIN_CONFIG), str(config_path)) == []


def test_validate_paths_flags_a_missing_bruin_pipeline(temp_config_dir):
    from trellis_datamodel.services.config_service import _validate_paths

    config_path = Path(temp_config_dir) / "trellis.yml"
    config = {"framework": "bruin", "bruin_pipeline_path": "./no_such_pipeline"}

    messages = _validate_paths(config, str(config_path))

    expected = os.path.abspath(os.path.join(temp_config_dir, "no_such_pipeline"))
    assert messages == [f"bruin_pipeline_path does not exist: {expected}"]


def test_validate_paths_warns_about_a_missing_bruin_asset_path(temp_config_dir):
    from trellis_datamodel.services.config_service import _validate_paths

    config_path = _write_bruin_project(temp_config_dir)
    config = {**yaml.safe_load(BRUIN_CONFIG), "bruin_asset_paths": ["02_core", "99_gone"]}

    messages = _validate_paths(config, str(config_path))

    expected = os.path.join(temp_config_dir, "pipeline", "assets", "99_gone")
    assert messages == [f"Warning: bruin_asset_paths entry does not exist: {expected}"]


def test_validate_paths_ignores_bruin_for_a_dbt_config(temp_config_dir):
    from trellis_datamodel.services.config_service import _validate_paths

    config = {"framework": "dbt-core", "dbt_project_path": "./dbt_project"}

    assert _validate_paths(config, str(Path(temp_config_dir) / "trellis.yml")) == []
