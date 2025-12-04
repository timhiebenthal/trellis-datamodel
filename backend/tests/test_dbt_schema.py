"""Tests for dbt schema API endpoints."""
import os
import yaml
import json
import pytest


class TestSaveDbtSchema:
    """Tests for POST /api/dbt-schema endpoint."""

    def test_creates_schema_file(self, test_client, temp_dir):
        request_data = {
            "entity_id": "users",
            "model_name": "users",
            "fields": [
                {"name": "id", "datatype": "int"},
                {"name": "email", "datatype": "text", "description": "User email"},
            ],
            "description": "User entity",
        }
        response = test_client.post("/api/dbt-schema", json=request_data)
        assert response.status_code == 200

        result = response.json()
        assert result["status"] == "success"
        assert "file_path" in result

        # Verify file content
        with open(result["file_path"], "r") as f:
            schema = yaml.safe_load(f)

        assert schema["version"] == 2
        assert len(schema["models"]) == 1
        model = schema["models"][0]
        assert model["name"] == "users"
        assert model["description"] == "User entity"
        assert len(model["columns"]) == 2


class TestSyncDbtTests:
    """Tests for POST /api/sync-dbt-tests endpoint."""

    def test_syncs_relationship_tests(self, test_client, temp_dir, temp_data_model_path):
        # Create data model with entities and relationships
        data_model = {
            "version": 0.1,
            "entities": [
                {"id": "users", "label": "Users", "position": {"x": 0, "y": 0}},
                {
                    "id": "orders",
                    "label": "Orders",
                    "position": {"x": 100, "y": 0},
                    "drafted_fields": [{"name": "user_id", "datatype": "int"}],
                },
            ],
            "relationships": [
                {
                    "source": "users",
                    "target": "orders",
                    "type": "one_to_many",
                    "source_field": "id",
                    "target_field": "user_id",
                }
            ],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data_model, f)

        response = test_client.post("/api/sync-dbt-tests")
        assert response.status_code == 200

        result = response.json()
        assert result["status"] == "success"
        assert len(result["files"]) == 2  # One for each entity


class TestGetModelSchema:
    """Tests for GET /api/models/{model_name}/schema endpoint."""

    def test_returns_empty_for_missing_yml(self, test_client, temp_dir, mock_manifest):
        # Create SQL file path structure (manifest points to this)
        sql_dir = os.path.join(temp_dir, "models", "3_core")
        os.makedirs(sql_dir, exist_ok=True)
        with open(os.path.join(sql_dir, "users.sql"), "w") as f:
            f.write("SELECT 1")

        response = test_client.get("/api/models/users/schema")
        assert response.status_code == 200

        data = response.json()
        assert data["model_name"] == "users"
        assert data["columns"] == []

    def test_returns_404_for_unknown_model(self, test_client):
        response = test_client.get("/api/models/nonexistent/schema")
        assert response.status_code == 404


class TestUpdateModelSchema:
    """Tests for POST /api/models/{model_name}/schema endpoint."""

    def test_updates_schema(self, test_client, temp_dir, mock_manifest):
        # Create the SQL file that manifest points to
        sql_dir = os.path.join(temp_dir, "models", "3_core")
        os.makedirs(sql_dir, exist_ok=True)
        with open(os.path.join(sql_dir, "users.sql"), "w") as f:
            f.write("SELECT 1")

        request_data = {
            "columns": [
                {"name": "id", "data_type": "int", "description": "Primary key"},
            ],
            "description": "Updated description",
        }
        response = test_client.post("/api/models/users/schema", json=request_data)
        assert response.status_code == 200

        result = response.json()
        assert result["status"] == "success"

        # Verify the YML file was created
        yml_path = os.path.join(sql_dir, "users.yml")
        assert os.path.exists(yml_path)


class TestInferRelationships:
    """Tests for GET /api/infer-relationships endpoint."""

    def test_returns_empty_for_no_yml_files(self, test_client, temp_dir):
        response = test_client.get("/api/infer-relationships")
        assert response.status_code == 200
        assert response.json()["relationships"] == []

    def test_infers_relationships_from_tests(self, test_client, temp_dir):
        # Create a YML file with relationship tests
        models_dir = os.path.join(temp_dir, "models", "3_core")
        os.makedirs(models_dir, exist_ok=True)

        schema = {
            "version": 2,
            "models": [
                {
                    "name": "orders",
                    "columns": [
                        {
                            "name": "user_id",
                            "data_type": "int",
                            "data_tests": [
                                {"relationships": {"to": "ref('users')", "field": "id"}}
                            ],
                        }
                    ],
                }
            ],
        }
        with open(os.path.join(models_dir, "orders.yml"), "w") as f:
            yaml.dump(schema, f)

        response = test_client.get("/api/infer-relationships")
        assert response.status_code == 200

        rels = response.json()["relationships"]
        assert len(rels) == 1
        assert rels[0]["source"] == "users"
        assert rels[0]["target"] == "orders"
        assert rels[0]["source_field"] == "id"
        assert rels[0]["target_field"] == "user_id"

    def test_infers_relationships_from_nested_directories(self, test_client, temp_dir):
        # Ensure nested model directories are also scanned
        nested_dir = os.path.join(temp_dir, "models", "3_core", "all")
        os.makedirs(nested_dir, exist_ok=True)

        schema = {
            "version": 2,
            "models": [
                {
                    "name": "game",
                    "columns": [
                        {
                            "name": "home_team_id",
                            "data_type": "text",
                            "data_tests": [
                                {
                                    "relationships": {
                                        "to": "ref('team')",
                                        "field": "team_id",
                                    }
                                }
                            ],
                        },
                        {
                            "name": "away_team_id",
                            "data_type": "text",
                            "data_tests": [
                                {
                                    "relationships": {
                                        "to": "ref('team')",
                                        "field": "team_id",
                                    }
                                }
                            ],
                        },
                    ],
                }
            ],
        }

        with open(os.path.join(nested_dir, "game.yml"), "w") as f:
            yaml.dump(schema, f)

        response = test_client.get("/api/infer-relationships")
        assert response.status_code == 200

        rels = response.json()["relationships"]
        assert len(rels) == 2
        assert {"source": "team", "target": "game", "source_field": "team_id", "target_field": "home_team_id"} in [
            {
                "source": r["source"],
                "target": r["target"],
                "source_field": r["source_field"],
                "target_field": r["target_field"],
            }
            for r in rels
        ]
        assert {"source": "team", "target": "game", "source_field": "team_id", "target_field": "away_team_id"} in [
            {
                "source": r["source"],
                "target": r["target"],
                "source_field": r["source_field"],
                "target_field": r["target_field"],
            }
            for r in rels
        ]
