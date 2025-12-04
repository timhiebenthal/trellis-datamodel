"""Tests for manifest API endpoints."""
import os
import json
import pytest


class TestGetConfigStatus:
    """Tests for GET /api/config-status endpoint."""

    def test_returns_status(self, test_client, mock_manifest):
        response = test_client.get("/api/config-status")
        assert response.status_code == 200
        data = response.json()

        assert data["config_present"] is True
        assert data["manifest_exists"] is True
        assert "dbt_project_path" in data


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
