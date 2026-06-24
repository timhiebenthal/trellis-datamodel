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

    def test_column_descriptions_included(self, test_client):
        response = test_client.get("/api/manifest")
        assert response.status_code == 200
        models = response.json()["models"]
        users = next(m for m in models if m["name"] == "users")
        col = next(c for c in users["columns"] if c["name"] == "id")
        assert col.get("description") == "Primary key"

    def test_catalog_columns_normalized_to_lowercase_with_manifest_descriptions(
        self, test_client, temp_dir, mock_manifest_data, monkeypatch
    ):
        """When a catalog is present, column names are lowercased (Snowflake returns
        uppercase names) and descriptions come from the manifest, not the empty catalog."""
        import json, os
        from trellis_datamodel import config as cfg

        # Write a catalog with UPPERCASE column names and no descriptions
        catalog_data = {
            "nodes": {
                "model.project.users": {
                    "unique_id": "model.project.users",
                    "columns": {
                        "ID": {"name": "ID", "type": "NUMBER", "comment": None},
                        "NAME": {"name": "NAME", "type": "TEXT", "comment": None},
                    },
                }
            }
        }
        catalog_path = os.path.join(temp_dir, "catalog.json")
        with open(catalog_path, "w") as f:
            json.dump(catalog_data, f)
        monkeypatch.setattr(cfg, "CATALOG_PATH", catalog_path)

        response = test_client.get("/api/manifest")
        assert response.status_code == 200
        users = next(m for m in response.json()["models"] if m["name"] == "users")

        cols = {c["name"]: c for c in users["columns"]}
        # Names must be lowercase even though catalog had uppercase
        assert "id" in cols, f"Expected lowercase 'id', got: {list(cols.keys())}"
        assert "name" in cols
        # Descriptions come from the manifest, not the empty catalog
        assert cols["id"]["description"] == "Primary key"
        assert cols["name"]["description"] == "Full name"

    def test_column_type_from_data_type_key(self, test_client):
        """Manifest columns using data_type (not type) must have their type passed through.
        Real dbt manifests use data_type; type is often absent or null."""
        response = test_client.get("/api/manifest")
        models = response.json()["models"]
        users = next(m for m in models if m["name"] == "users")
        col = next(c for c in users["columns"] if c["name"] == "id")
        assert col.get("type") == "integer", (
            f"Expected 'integer' from data_type key, got: {col.get('type')}"
        )

    def test_get_models_reads_meta_origin(
        self, test_client, temp_dir, mock_manifest_data, monkeypatch
    ):
        """Columns with meta.origin return structured origin on manifest read-back."""
        from trellis_datamodel import config as cfg

        mock_manifest_data["nodes"]["model.project.users"]["columns"]["revenue"] = {
            "name": "revenue",
            "data_type": "numeric",
            "description": "Net sales",
            "meta": {"origin": [{"DH1": "CORE.A"}]},
        }
        manifest_path = os.path.join(temp_dir, "manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(mock_manifest_data, f)
        monkeypatch.setattr(cfg, "MANIFEST_PATH", manifest_path)
        monkeypatch.setattr(cfg, "CATALOG_PATH", "")

        response = test_client.get("/api/manifest")
        users = next(m for m in response.json()["models"] if m["name"] == "users")
        col = next(c for c in users["columns"] if c["name"] == "revenue")
        assert col["origin"] == [{"DH1": "CORE.A"}]
        assert col["description"] == "Net sales"

    def test_get_models_origin_description_fallback(
        self, test_client, temp_dir, mock_manifest_data, monkeypatch
    ):
        """Legacy | Origin: description suffix is parsed into structured origin."""
        from trellis_datamodel import config as cfg

        mock_manifest_data["nodes"]["model.project.users"]["columns"]["revenue"] = {
            "name": "revenue",
            "data_type": "numeric",
            "description": "Net sales | Origin: DH1: CORE.A",
        }
        mock_manifest_data["nodes"]["model.project.users"]["columns"]["cost"] = {
            "name": "cost",
            "data_type": "numeric",
            "description": "Operating cost",
        }
        manifest_path = os.path.join(temp_dir, "manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(mock_manifest_data, f)
        monkeypatch.setattr(cfg, "MANIFEST_PATH", manifest_path)
        monkeypatch.setattr(cfg, "CATALOG_PATH", "")

        response = test_client.get("/api/manifest")
        users = next(m for m in response.json()["models"] if m["name"] == "users")
        revenue = next(c for c in users["columns"] if c["name"] == "revenue")
        cost = next(c for c in users["columns"] if c["name"] == "cost")

        assert revenue["origin"] == [{"DH1": "CORE.A"}]
        assert revenue["description"] == "Net sales"
        assert cost["origin"] == []
        assert cost["description"] == "Operating cost"

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
