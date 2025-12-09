"""Pytest fixtures for backend tests."""
import os
import sys
import tempfile
import json
import shutil
import pytest
from fastapi.testclient import TestClient


# Create a persistent temp directory for the entire test session
# This is set BEFORE any backend modules are imported
_TEST_TEMP_DIR = tempfile.mkdtemp(prefix="datamodel_test_")
os.environ["DATAMODEL_TEST_DIR"] = _TEST_TEMP_DIR

# Create required directory structure
os.makedirs(os.path.join(_TEST_TEMP_DIR, "models", "3_core"), exist_ok=True)

# Create minimal config.yml
with open(os.path.join(_TEST_TEMP_DIR, "config.yml"), "w") as f:
    f.write("dbt_project_path: .\n")


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
    
    # Clean model yml files (recursively) to avoid cross-test leakage
    models_dir = os.path.join(_TEST_TEMP_DIR, "models", "3_core")
    if os.path.exists(models_dir):
        for root, _, files in os.walk(models_dir):
            for fname in files:
                if fname.endswith((".yml", ".yaml")):
                    os.remove(os.path.join(root, fname))
    
    yield


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


@pytest.fixture
def test_client(mock_manifest):
    """Create a test client. Config is already set via environment variables."""
    from trellis_datamodel.server import app
    return TestClient(app)
