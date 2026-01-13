"""Tests for manifest API endpoints."""
import os
import json
from trellis_datamodel import config as cfg
from trellis_datamodel.config import DimensionalModelingConfig, EntityModelingConfig


class TestGetConfigStatus:
    """Tests for GET /api/config-status endpoint."""

    def test_returns_status(self, test_client, mock_manifest):
        response = test_client.get("/api/config-status")
        assert response.status_code == 200
        data = response.json()

        assert data["config_present"] is True
        assert data["manifest_exists"] is True
        assert "dbt_project_path" in data


class TestGetConfigInfo:
    """Tests for GET /api/config-info endpoint."""

    def test_includes_lineage_fields(self, test_client, monkeypatch):
        import sys
        # Patch the actual config module in sys.modules to handle module reloads
        config_module = sys.modules['trellis_datamodel.config']
        monkeypatch.setattr(config_module, "LINEAGE_ENABLED", True)
        monkeypatch.setattr(config_module, "LINEAGE_LAYERS", ["one", "two"])

        response = test_client.get("/api/config-info")

        assert response.status_code == 200
        data = response.json()
        assert data["lineage_enabled"] is True
        assert data["lineage_layers"] == ["one", "two"]

    def test_includes_bus_matrix_field(self, test_client, monkeypatch):
        import sys
        # Patch the actual config module in sys.modules to handle module reloads
        config_module = sys.modules['trellis_datamodel.config']
        monkeypatch.setattr(config_module, "Bus_MATRIX_ENABLED", True)

        response = test_client.get("/api/config-info")

        assert response.status_code == 200
        data = response.json()
        assert data["bus_matrix_enabled"] is True

    def test_label_prefixes_reflect_entity_modeling(self, test_client, monkeypatch):
        import sys
        config_module = sys.modules["trellis_datamodel.config"]
        monkeypatch.setattr(config_module, "MODELING_STYLE", "entity_model")
        entity_config = EntityModelingConfig()
        entity_config.enabled = True
        entity_config.entity_prefix = ["tbl_", "entity_"]
        monkeypatch.setattr(config_module, "ENTITY_MODELING_CONFIG", entity_config)
        monkeypatch.setattr(config_module, "DIMENSIONAL_MODELING_CONFIG", DimensionalModelingConfig())

        response = test_client.get("/api/config-info")

        assert response.status_code == 200
        data = response.json()
        assert data["label_prefixes"] == ["tbl_", "entity_"]

    def test_label_prefixes_reflect_dimensional_modeling(self, test_client, monkeypatch):
        import sys
        config_module = sys.modules["trellis_datamodel.config"]
        monkeypatch.setattr(config_module, "MODELING_STYLE", "dimensional_model")
        dimensional_config = DimensionalModelingConfig()
        dimensional_config.enabled = True
        dimensional_config.dimension_prefix = ["dim_", "d_"]
        dimensional_config.fact_prefix = ["fct_", "fact_"]
        monkeypatch.setattr(config_module, "DIMENSIONAL_MODELING_CONFIG", dimensional_config)
        entity_config = EntityModelingConfig()
        entity_config.enabled = False
        monkeypatch.setattr(config_module, "ENTITY_MODELING_CONFIG", entity_config)

        response = test_client.get("/api/config-info")

        assert response.status_code == 200
        data = response.json()
        assert data["label_prefixes"] == ["dim_", "d_", "fct_", "fact_"]


class TestGetManifest:
    """Tests for GET /api/manifest endpoint."""

    def test_returns_models_from_manifest(self, test_client):
        response = test_client.get("/api/manifest")
        assert response.status_code == 200
        data = response.json()

        assert "models" in data
        models = data["models"]
        assert len(models) == 2

        # Models should be sorted by name
        assert models[0]["name"] == "orders"
        assert models[1]["name"] == "users"

    def test_model_fields(self, test_client):
        response = test_client.get("/api/manifest")
        data = response.json()

        users_model = next(m for m in data["models"] if m["name"] == "users")
        assert users_model["unique_id"] == "model.project.users"
        assert users_model["schema"] == "public"
        assert users_model["description"] == "User table"
        assert users_model["materialization"] == "table"
        assert users_model["tags"] == ["core"]

    def test_filters_by_model_path(self, test_client, temp_dir, mock_manifest):
        # Update manifest to have models in different paths
        with open(mock_manifest, "r") as f:
            manifest = json.load(f)

        manifest["nodes"]["model.project.staging"] = {
            "unique_id": "model.project.staging",
            "resource_type": "model",
            "name": "stg_users",
            "schema": "staging",
            "original_file_path": "models/1_staging/stg_users.sql",
            "columns": {},
            "config": {},
            "tags": [],
        }

        with open(mock_manifest, "w") as f:
            json.dump(manifest, f)

        # DBT_MODEL_PATHS is set to ["3_core"] so staging model should be filtered out
        response = test_client.get("/api/manifest")
        data = response.json()

        model_names = [m["name"] for m in data["models"]]
        assert "stg_users" not in model_names
        assert "users" in model_names
