"""Pytest fixtures for backend tests."""

import os
import sys
import tempfile
import json
import shutil
import importlib
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
    _reset_shared_test_state()

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

    # Clean catalog file
    catalog_path = os.path.join(_TEST_TEMP_DIR, "catalog.json")
    if os.path.exists(catalog_path):
        os.remove(catalog_path)

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
    _reset_shared_test_state()


def _reset_shared_test_state():
    """Reset process-wide config and adapter caches between tests."""
    global cfg
    cfg = importlib.import_module("trellis_datamodel.config")

    cfg.CONFIG_PATH = os.path.join(_TEST_TEMP_DIR, "config.yml")
    cfg.FRAMEWORK = "dbt-core"
    cfg.MANIFEST_PATH = os.path.join(_TEST_TEMP_DIR, "manifest.json")
    cfg.CATALOG_PATH = os.path.join(_TEST_TEMP_DIR, "catalog.json")
    cfg.DATA_MODEL_PATH = os.path.join(_TEST_TEMP_DIR, "data_model.yml")
    cfg.CANVAS_LAYOUT_PATH = os.path.join(_TEST_TEMP_DIR, "canvas_layout.yml")
    cfg.CANVAS_LAYOUT_VERSION_CONTROL = True
    cfg.DBT_PROJECT_PATH = _TEST_TEMP_DIR
    cfg.DBT_MODEL_PATHS = ["3_core"]
    cfg.BRUIN_PIPELINE_PATH = ""
    cfg.BRUIN_ASSET_PATHS = []
    cfg.BRUIN_DEFAULT_ASSET_TYPE = "duckdb.sql"
    cfg.FRONTEND_BUILD_DIR = os.path.join(_TEST_TEMP_DIR, "frontend/build")
    cfg.DBT_COMPANY_DUMMY_PATH = os.path.join(_TEST_TEMP_DIR, "dbt_company_dummy")
    cfg.LINEAGE_ENABLED = False
    cfg.LINEAGE_LAYERS = []
    cfg.EXPOSURES_ENABLED = False
    cfg.EXPOSURES_DEFAULT_LAYOUT = "dashboards-as-rows"
    cfg.MODELING_STYLE = "entity_model"
    cfg.Bus_MATRIX_ENABLED = True
    cfg.BUSINESS_EVENTS_ENABLED = False
    cfg.BUSINESS_EVENTS_PATH = ""
    cfg.GUIDANCE_CONFIG = cfg.GuidanceConfig()
    cfg.DIMENSIONAL_MODELING_CONFIG = cfg.DimensionalModelingConfig()
    cfg.ENTITY_MODELING_CONFIG = cfg.EntityModelingConfig()
    cfg.SOURCE_CHIPS_CONFIG = cfg.SourceChipsConfig()

    from trellis_datamodel.adapters.artifact_snapshot import clear_snapshots
    from trellis_datamodel.adapters import entity_type_inference

    clear_snapshots()
    entity_type_inference.reset_cache()


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


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
BRUIN_PIPELINE_FIXTURE = os.path.join(FIXTURES_DIR, "bruin_pipeline")


@pytest.fixture
def bruin_pipeline():
    """Path to the committed read-only Bruin fixture pipeline.

    Use for read paths (get_models, get_lineage, infer_relationships). Anything
    that writes must use `bruin_pipeline_copy` so the fixture stays pristine.
    """
    return BRUIN_PIPELINE_FIXTURE


@pytest.fixture
def bruin_pipeline_copy(tmp_path):
    """A writable per-test copy of the Bruin fixture pipeline."""
    dest = os.path.join(str(tmp_path), "pipeline")
    shutil.copytree(BRUIN_PIPELINE_FIXTURE, dest)
    return dest


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
                    "id": {"name": "id", "data_type": "integer", "description": "Primary key"},
                    "name": {"name": "name", "data_type": "varchar", "description": "Full name"},
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


class FakeAdapter:
    """In-memory TransformationAdapter test double.

    Backed by plain data structures that tests mutate directly. Proves
    reconciliation and other adapter consumers depend only on the
    TransformationAdapter protocol, not on dbt specifics.

    The lineage/exposure defaults describe a tiny two-model project fed by a
    "crm" source, so the protocol contract tests have something concrete to
    assert against without any framework artifacts on disk.
    """

    DEFAULT_UPSTREAMS = {
        "model.fake.customer": ["model.fake.stg_customer"],
        "model.fake.stg_customer": ["source.fake.crm.customers"],
    }
    DEFAULT_SOURCE_NAMES = {"source.fake.crm.customers": "crm"}
    DEFAULT_EXPOSURES = [
        {
            "name": "fake_dashboard",
            "label": "Fake Dashboard",
            "type": "dashboard",
            "url": None,
            "maturity": None,
            "description": None,
            "owner": {"name": "analytics"},
            "depends_on": ["model.fake.customer"],
        }
    ]

    def __init__(self, models=None):
        self.models = models if models is not None else []
        # unique_id -> list of upstream unique_ids
        self.upstreams = dict(self.DEFAULT_UPSTREAMS)
        # source unique_id -> source system name
        self.source_names = dict(self.DEFAULT_SOURCE_NAMES)
        self.exposures = [dict(e) for e in self.DEFAULT_EXPOSURES]
        self.capabilities = {
            "lineage": True,
            "column_lineage": False,
            "exposures": True,
            "relationships": True,
            "scaffolding": True,
        }

    def get_models(self):
        return self.models

    def get_model_schema(self, model_name, version=None):
        for model in self.models:
            if model.get("name") == model_name and (
                version is None or model.get("version") == version
            ):
                return {
                    "model_name": model_name,
                    "description": model.get("description") or "",
                    "columns": [
                        {
                            "name": col.get("name"),
                            "data_type": col.get("type"),
                            "description": col.get("description"),
                        }
                        for col in model.get("columns", [])
                    ],
                    "tags": model.get("tags") or [],
                    "file_path": model.get("file_path") or "",
                }
        return {"model_name": model_name, "description": "", "columns": [], "tags": []}

    def save_model_schema(self, model_name, columns, description=None, tags=None, version=None):
        from pathlib import Path

        return Path(f"{model_name}.yml")

    def infer_relationships(self, include_unbound=False):
        return []

    def sync_relationships(self, entities, relationships):
        return []

    def save_schema_file(
        self, entity_id, model_name, fields, description=None, tags=None
    ):
        from pathlib import Path

        return Path(f"{model_name}.yml")

    def infer_entity_types(self):
        return {}

    def get_model_dirs(self):
        return []

    def reset_inference_cache(self):
        return None

    def get_lineage(self, model_unique_id):
        from collections import deque

        from trellis_datamodel.exceptions import NotFoundError

        if (
            model_unique_id not in self.upstreams
            and model_unique_id not in self.source_names
        ):
            raise NotFoundError(f"Model '{model_unique_id}' not found")

        node_ids = {model_unique_id}
        edges = []
        queue = deque([model_unique_id])
        visited = {model_unique_id}

        while queue:
            current = queue.popleft()
            for upstream in self.upstreams.get(current, []):
                edges.append({"source": upstream, "target": current})
                node_ids.add(upstream)
                if upstream not in visited:
                    visited.add(upstream)
                    queue.append(upstream)

        return {
            "nodes": [self._lineage_node(nid) for nid in sorted(node_ids)],
            "edges": edges,
        }

    def _lineage_node(self, unique_id):
        is_source = unique_id in self.source_names
        return {
            "unique_id": unique_id,
            "name": unique_id.split(".")[-1],
            "resource_type": "source" if is_source else "model",
            "is_source": is_source,
            "source_name": self.source_names.get(unique_id),
            "folder": None,
        }

    def get_exposures(self):
        return self.exposures

    def get_source_systems_for_model(self, model_unique_id):
        try:
            graph = self.get_lineage(model_unique_id)
        except Exception:
            return []
        return sorted(
            {
                n["source_name"]
                for n in graph["nodes"]
                if n["is_source"] and n["source_name"]
            }
        )

    def get_source_systems_for_models(self, model_unique_ids):
        ordered_model_ids = list(dict.fromkeys(model_unique_ids))
        return {
            model_id: self.get_source_systems_for_model(model_id)
            for model_id in ordered_model_ids
        }

    def get_project_status(self):
        return {
            "framework": "fake",
            "artifacts_present": True,
            "artifacts": {},
            "project_path": "/fake/project",
            "project_path_exists": True,
            "model_paths_configured": [],
            "model_paths_resolved": [],
            "capabilities": dict(self.capabilities),
            "error": None,
        }


@pytest.fixture
def fake_adapter():
    """Construct a fresh FakeAdapter with no models; tests set `.models`."""
    return FakeAdapter()


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
        # Ensure paths are set to the test directory (reset any contamination from test_config.py etc.)
        cfg_module.MANIFEST_PATH = os.path.join(_TEST_TEMP_DIR, "manifest.json")
        cfg_module.DATA_MODEL_PATH = os.path.join(_TEST_TEMP_DIR, "data_model.yml")
        cfg_module.CANVAS_LAYOUT_PATH = os.path.join(_TEST_TEMP_DIR, "canvas_layout.yml")
        cfg_module.DBT_PROJECT_PATH = _TEST_TEMP_DIR

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
