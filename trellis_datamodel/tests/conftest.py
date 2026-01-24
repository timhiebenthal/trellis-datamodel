"""Pytest fixtures for backend tests."""

import os
import sys
import tempfile
import json
import shutil
import pytest
import httpx
from starlette.testclient import TestClient


# Create a persistent temp directory for the entire test session
# This is set BEFORE any backend modules are imported
_TEST_TEMP_DIR = tempfile.mkdtemp(prefix="datamodel_test_")
os.environ["DATAMODEL_TEST_DIR"] = _TEST_TEMP_DIR

# Create required directory structure
os.makedirs(os.path.join(_TEST_TEMP_DIR, "models", "3_core"), exist_ok=True)

# Create minimal config.yml
with open(os.path.join(_TEST_TEMP_DIR, "config.yml"), "w") as f:
    f.write("dbt_project_path: .\n")

# Import config after DATAMODEL_TEST_DIR is set so test-mode defaults apply
from trellis_datamodel import config as cfg  # noqa: E402


def pytest_sessionfinish(session, exitstatus):
    """Clean up temp directory after all tests complete."""
    if os.path.exists(_TEST_TEMP_DIR):
        shutil.rmtree(_TEST_TEMP_DIR, ignore_errors=True)


@pytest.fixture(autouse=True)
def clean_test_files():
    """Clean up test files before each test to ensure isolation."""
    # Clean data model file before each test
    data_model_path = os.path.join(_TEST_TEMP_DIR, "data_model.yml")
    if os.path.exists(data_model_path):
        os.remove(data_model_path)

    # Clean canvas layout file before each test
    canvas_layout_path = os.path.join(_TEST_TEMP_DIR, "canvas_layout.yml")
    if os.path.exists(canvas_layout_path):
        os.remove(canvas_layout_path)

    # Clean manifest file
    manifest_path = os.path.join(_TEST_TEMP_DIR, "manifest.json")
    if os.path.exists(manifest_path):
        os.remove(manifest_path)

    # Clean business_events.yml file
    business_events_path = os.path.join(_TEST_TEMP_DIR, "business_events.yml")
    if os.path.exists(business_events_path):
        os.remove(business_events_path)

    # Clean model yml files (recursively) to avoid cross-test leakage
    models_dir = os.path.join(_TEST_TEMP_DIR, "models", "3_core")
    if os.path.exists(models_dir):
        for root, _, files in os.walk(models_dir):
            for fname in files:
                if fname.endswith((".yml", ".yaml")):
                    os.remove(os.path.join(root, fname))
    yield
    # After each test, ensure config is reset to test mode values
    # This is needed because some tests (like CLI tests) may reload modules
    cfg.LINEAGE_ENABLED = False
    cfg.LINEAGE_LAYERS = []
    cfg.EXPOSURES_ENABLED = False
    cfg.EXPOSURES_DEFAULT_LAYOUT = "dashboards-as-rows"
    cfg.Bus_MATRIX_ENABLED = True  # Default to enabled
    cfg.MANIFEST_PATH = os.path.join(_TEST_TEMP_DIR, "manifest.json")


@pytest.fixture
def temp_dir():
    """Return the shared test temp directory."""
    return _TEST_TEMP_DIR


@pytest.fixture
def temp_data_model_path():
    """Return path for the data model file (in session temp dir)."""
    return os.path.join(_TEST_TEMP_DIR, "data_model.yml")


@pytest.fixture
def temp_canvas_layout_path():
    """Return path for the canvas layout file (in session temp dir)."""
    return os.path.join(_TEST_TEMP_DIR, "canvas_layout.yml")


@pytest.fixture
def temp_dbt_project():
    """Return the test dbt project directory."""
    return _TEST_TEMP_DIR


@pytest.fixture
def mock_manifest_data():
    """Return mock manifest data."""
    return {
        "nodes": {
            "model.project.users": {
                "unique_id": "model.project.users",
                "resource_type": "model",
                "name": "users",
                "schema": "public",
                "alias": "users",
                "original_file_path": "models/3_core/users.sql",
                "columns": {
                    "id": {"name": "id", "type": "integer"},
                    "name": {"name": "name", "type": "text"},
                },
                "description": "User table",
                "config": {"materialized": "table"},
                "tags": ["core"],
            },
            "model.project.orders": {
                "unique_id": "model.project.orders",
                "resource_type": "model",
                "name": "orders",
                "schema": "public",
                "alias": "orders",
                "original_file_path": "models/3_core/orders.sql",
                "columns": {},
                "description": "Orders table",
                "config": {"materialized": "view"},
                "tags": [],
            },
        }
    }


@pytest.fixture
def mock_manifest(mock_manifest_data):
    """Create a mock manifest.json file."""
    manifest_path = os.path.join(_TEST_TEMP_DIR, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(mock_manifest_data, f)
    return manifest_path


class _PatchedASGITransport(httpx.ASGITransport):
    """ASGITransport with sync context manager support for httpx.Client/TestClient."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False


@pytest.fixture
def test_client(mock_manifest):
    """Create a synchronous test client against the ASGI app.

    Tests can override config values using monkeypatch.
    Default test mode values: LINEAGE_ENABLED=True, LINEAGE_LAYERS=[]
    """
    # Import fresh to handle module reloads from CLI tests
    import importlib
    import sys

    # Ensure we're using the current config module
    if "trellis_datamodel.config" in sys.modules:
        cfg_module = sys.modules["trellis_datamodel.config"]

        # Reset to test defaults in case of module reload
        cfg_module.LINEAGE_ENABLED = False
        cfg_module.LINEAGE_LAYERS = []
        cfg_module.EXPOSURES_ENABLED = False
        cfg_module.EXPOSURES_DEFAULT_LAYOUT = "dashboards-as-rows"
        cfg_module.Bus_MATRIX_ENABLED = True
        # Ensure MANIFEST_PATH is set to the test directory manifest (mock_manifest creates it)
        cfg_module.MANIFEST_PATH = os.path.join(_TEST_TEMP_DIR, "manifest.json")

        # Reload routes modules to ensure they use the updated config
        routes_modules = [
            "trellis_datamodel.routes.exposures",
            "trellis_datamodel.routes.lineage",
            "trellis_datamodel.routes.manifest",
        ]
        for mod_name in routes_modules:
            if mod_name in sys.modules:
                importlib.reload(sys.modules[mod_name])
        # Reload server module last to ensure it picks up reloaded routes
        if "trellis_datamodel.server" in sys.modules:
            importlib.reload(sys.modules["trellis_datamodel.server"])

    from trellis_datamodel.server import app

    with TestClient(app) as client:
        yield client
