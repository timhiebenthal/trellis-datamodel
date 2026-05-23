"""Tests for manifest API endpoints."""
import os
import json
import shutil
import tempfile
from pathlib import Path
from trellis_datamodel import config as cfg
from trellis_datamodel.config import DimensionalModelingConfig, EntityModelingConfig


def _write_sql_asset(assets_dir, filename, name, columns=None, description=None,
                     materialization=None, tags=None):
    """Write a SQL asset with a @bruin block (adapted from test_bruin_adapter)."""
    cols_yaml = ""
    if columns:
        for c in columns:
            cols_yaml += (
                f"  - name: {c['name']}\n"
                f"    type: {c.get('type', 'varchar')}\n"
            )
            if c.get("description"):
                cols_yaml += f'    description: "{c["description"]}"\n'

    mat_yaml = ""
    if materialization:
        mat_yaml = f"materialization:\n  type: {materialization}\n"

    tags_yaml = ""
    if tags:
        tags_yaml = "tags:\n"
        for t in tags:
            tags_yaml += f"  - {t}\n"

    desc_yaml = ""
    if description:
        desc_yaml = f'description: "{description}"\n'

    content = (
        f"/* @bruin\n"
        f"name: {name}\n"
        f"type: pg.sql\n"
        f"{mat_yaml}"
        f"columns:\n{cols_yaml}"
        f"{tags_yaml}"
        f"{desc_yaml}"
        f"@bruin */\n"
        f"SELECT 1;\n"
    )
    assets_dir.mkdir(parents=True, exist_ok=True)
    path = assets_dir / filename
    path.write_text(content)
    return path


class TestGetConfigStatus:
    """Tests for GET /api/config-status endpoint."""

    def test_returns_status(self, test_client, mock_manifest):
        response = test_client.get("/api/config-status")
        assert response.status_code == 200
        data = response.json()

        assert data["config_present"] is True
        assert data["manifest_exists"] is True
        assert "dbt_project_path" in data

    def test_config_status_bruin_framework(self, test_client, monkeypatch):
        """When framework is bruin, config-status returns bruin-specific fields."""
        import sys
        config_module = sys.modules['trellis_datamodel.config']
        monkeypatch.setattr(config_module, "FRAMEWORK", "bruin")

        # Create a temp pipeline path for bruin
        bruin_pipeline = Path(tempfile.mkdtemp(prefix="bruin_pipeline_"))
        try:
            monkeypatch.setattr(config_module, "BRUIN_PIPELINE_PATH", str(bruin_pipeline))
            monkeypatch.setattr(config_module, "BRUIN_ASSET_PATHS", ["assets"])

            response = test_client.get("/api/config-status")
            assert response.status_code == 200
            data = response.json()

            assert data["framework"] == "bruin"
            assert data["pipeline_path_exists"] is True
            assert "bruin_pipeline_path" in data
            assert data["bruin_pipeline_path"] == str(bruin_pipeline)
            assert data["error"] is None
            # Should NOT have dbt-specific fields
            assert "manifest_exists" not in data
            assert "dbt_project_path" not in data
        finally:
            shutil.rmtree(str(bruin_pipeline), ignore_errors=True)

    def test_config_status_bruin_missing_pipeline(self, test_client, monkeypatch):
        """When bruin pipeline path is not set, config-status shows error."""
        import sys
        config_module = sys.modules['trellis_datamodel.config']
        monkeypatch.setattr(config_module, "FRAMEWORK", "bruin")
        monkeypatch.setattr(config_module, "BRUIN_PIPELINE_PATH", "")

        response = test_client.get("/api/config-status")
        assert response.status_code == 200
        data = response.json()

        assert data["framework"] == "bruin"
        assert data["pipeline_path_exists"] is False
        assert "bruin_pipeline_path" in data
        assert data["error"] == "bruin_pipeline_path not set in config."


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

    def test_config_info_bruin_framework(self, test_client, monkeypatch):
        """When framework is bruin, config-info includes bruin-specific fields."""
        import sys
        config_module = sys.modules['trellis_datamodel.config']
        monkeypatch.setattr(config_module, "FRAMEWORK", "bruin")

        bruin_pipeline = Path(tempfile.mkdtemp(prefix="bruin_pipeline_"))
        try:
            monkeypatch.setattr(config_module, "BRUIN_PIPELINE_PATH", str(bruin_pipeline))
            monkeypatch.setattr(config_module, "BRUIN_ASSET_PATHS", ["assets", "extra"])

            response = test_client.get("/api/config-info")
            assert response.status_code == 200
            data = response.json()

            assert data["framework"] == "bruin"
            assert "bruin_pipeline_path" in data
            assert data["bruin_pipeline_path"] == str(bruin_pipeline)
            assert "bruin_asset_paths" in data
            assert data["bruin_asset_paths"] == ["assets", "extra"]
            assert "pipeline_path_exists" in data
            assert data["pipeline_path_exists"] is True
        finally:
            shutil.rmtree(str(bruin_pipeline), ignore_errors=True)


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

    def test_manifest_bruin_endpoint(self, test_client, monkeypatch):
        """With bruin framework, GET /api/manifest returns bruin pipeline assets."""
        import sys
        config_module = sys.modules['trellis_datamodel.config']
        monkeypatch.setattr(config_module, "FRAMEWORK", "bruin")

        bruin_pipeline = Path(tempfile.mkdtemp(prefix="bruin_pipeline_"))
        try:
            monkeypatch.setattr(config_module, "BRUIN_PIPELINE_PATH", str(bruin_pipeline))
            monkeypatch.setattr(config_module, "BRUIN_ASSET_PATHS", [])

            # Create bruin pipeline assets
            assets_dir = bruin_pipeline / "assets" / "01_clean"
            _write_sql_asset(
                assets_dir,
                "dim__game.sql",
                name="core.dim__game",
                columns=[
                    {"name": "game_id", "type": "varchar", "description": "Game ID"},
                    {"name": "game_name", "type": "varchar", "description": "Game name"},
                ],
                description="Dimension for games",
                materialization="table",
                tags=["dimension"],
            )

            response = test_client.get("/api/manifest")
            assert response.status_code == 200
            data = response.json()

            assert "models" in data
            assert len(data["models"]) == 1
            model = data["models"][0]
            assert model["name"] == "dim__game"
            assert model["unique_id"] == "core.dim__game"
            assert model["schema"] == "core"
            assert model["description"] == "Dimension for games"
            assert model["materialization"] == "table"
            assert model["tags"] == ["dimension"]
            assert len(model["columns"]) == 2
        finally:
            shutil.rmtree(str(bruin_pipeline), ignore_errors=True)


class TestBruinManifestService:
    """Tests for manifest service with Bruin framework."""

    def test_get_models_uses_pipeline_path_in_bruin(self, monkeypatch, temp_dir):
        """When framework is bruin, get_models calls validate_pipeline_path instead of validate_manifest_path."""
        import sys
        config_module = sys.modules["trellis_datamodel.config"]
        monkeypatch.setattr(config_module, "FRAMEWORK", "bruin")
        monkeypatch.setattr(config_module, "BRUIN_PIPELINE_PATH", temp_dir)
        monkeypatch.setattr(config_module, "BRUIN_ASSET_PATHS", [])

        # Monkeypatch validate_manifest_path to raise — it should NOT be called for Bruin
        monkeypatch.setattr(
            "trellis_datamodel.services.manifest.validate_manifest_path",
            lambda: (_ for _ in ()).throw(
                ConfigurationError("should not be called")
            ),
        )

        from trellis_datamodel.services.manifest import get_models

        # Should NOT raise ConfigurationError from validate_manifest_path
        result = get_models()
        assert result == []
