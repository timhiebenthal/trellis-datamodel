"""Tests for dbt schema API endpoints."""

import os
import shutil
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

    def test_preserves_versioned_models_and_versions(
        self, test_client, temp_dir, temp_data_model_path
    ):
        # Overwrite manifest with versioned model pointing to player_v2.sql
        manifest_path = os.path.join(temp_dir, "manifest.json")
        manifest_data = {
            "nodes": {
                "model.project.player.v1": {
                    "unique_id": "model.project.player.v1",
                    "resource_type": "model",
                    "name": "player",
                    "version": 1,
                    "schema": "public",
                    "alias": "player",
                    "original_file_path": "models/3_core/all/player_v1.sql",
                    "columns": {},
                    "description": "Player v1",
                    "config": {"materialized": "table"},
                    "tags": [],
                },
                "model.project.player.v2": {
                    "unique_id": "model.project.player.v2",
                    "resource_type": "model",
                    "name": "player",
                    "version": 2,
                    "schema": "public",
                    "alias": "player",
                    "original_file_path": "models/3_core/all/player_v2.sql",
                    "columns": {},
                    "description": "Player v2",
                    "config": {"materialized": "table"},
                    "tags": [],
                },
            }
        }
        with open(manifest_path, "w") as f:
            json.dump(manifest_data, f)

        # Existing schema with v1 definition (stored in player.yml)
        models_dir = os.path.join(temp_dir, "models", "3_core", "all")
        os.makedirs(models_dir, exist_ok=True)
        yml_path = os.path.join(models_dir, "player.yml")
        existing_schema = {
            "version": 2,
            "models": [
                {
                    "name": "player",
                    "latest_version": 1,
                    "versions": [
                        {
                            "v": 1,
                            "description": "v1 description",
                            "columns": [{"name": "player_id", "data_type": "text"}],
                        }
                    ],
                }
            ],
        }
        with open(yml_path, "w") as f:
            yaml.dump(existing_schema, f)

        # Data model binds entity to v2
        data_model = {
            "version": 0.1,
            "entities": [
                {
                    "id": "player",
                    "label": "Player",
                    "description": "Players competing in the NBA",
                    "dbt_model": "model.project.player.v2",
                }
            ],
            "relationships": [],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data_model, f)

        request_data = {
            "entity_id": "player",
            "model_name": "player",
            "fields": [
                {
                    "name": "player_uuid",
                    "datatype": "text",
                    "description": "New PK",
                }
            ],
            "description": "Players v2",
            "tags": ["core"],
        }

        response = test_client.post("/api/dbt-schema", json=request_data)
        assert response.status_code == 200

        with open(yml_path, "r") as f:
            schema = yaml.safe_load(f)

        model = schema["models"][0]
        assert model["latest_version"] == 2

        versions = {v["v"]: v for v in model["versions"]}
        assert 1 in versions  # keep existing v1
        assert 2 in versions  # add/update v2

        # v1 is unchanged
        assert versions[1]["columns"][0]["name"] == "player_id"

        # v2 reflects new request
        v2_columns = versions[2]["columns"]
        assert v2_columns[0]["name"] == "player_uuid"
        assert versions[2].get("config", {}).get("tags") == ["core"]


class TestSyncDbtTests:
    """Tests for POST /api/sync-dbt-tests endpoint."""

    def test_syncs_relationship_tests(
        self, test_client, temp_dir, temp_data_model_path
    ):
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

    def test_syncs_using_dbt_model_names(
        self, test_client, temp_dir, temp_data_model_path
    ):
        """
        Ensure relationship tests reference bound dbt model names, not raw entity IDs.
        """
        data_model = {
            "version": 0.1,
            "entities": [
                {
                    "id": "customer_entity",
                    "label": "Customers",
                    "dbt_model": "model.project.customers",
                    "position": {"x": 0, "y": 0},
                },
                {
                    "id": "order_entity",
                    "label": "Orders",
                    "dbt_model": "model.project.orders",
                    "drafted_fields": [{"name": "customer_id", "datatype": "int"}],
                },
            ],
            "relationships": [
                {
                    "source": "customer_entity",
                    "target": "order_entity",
                    "type": "one_to_many",
                    "source_field": "id",
                    "target_field": "customer_id",
                }
            ],
        }

        # Persist data model
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data_model, f)

        response = test_client.post("/api/sync-dbt-tests")
        assert response.status_code == 200

        # orders.yml should contain a relationship test pointing to customers (dbt model name)
        orders_yml = os.path.join(temp_dir, "models", "3_core", "orders.yml")
        assert os.path.exists(orders_yml)
        with open(orders_yml, "r") as f:
            schema = yaml.safe_load(f)

        rel_tests = schema["models"][0]["columns"][0]["data_tests"]
        assert rel_tests == [
            {
                "relationships": {
                    "arguments": {"to": "ref('customers')", "field": "id"},
                }
            }
        ]


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
        assert response.status_code == 400
        assert "No schema yml files found" in response.json()["detail"]

    def test_infers_relationships_from_tests(
        self, test_client, temp_dir, temp_data_model_path
    ):
        # Data model with bound entities
        data_model = {
            "version": 0.1,
            "entities": [
                {"id": "users", "dbt_model": "model.project.users"},
                {"id": "orders", "dbt_model": "model.project.orders"},
            ],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data_model, f)

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
                            "tests": [
                                {
                                    "relationships": {
                                        "arguments": {
                                            "to": "ref('users')",
                                            "field": "id",
                                        }
                                    }
                                }
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

    def test_infers_relationships_from_nested_directories(
        self, test_client, temp_dir, temp_data_model_path
    ):
        # Ensure nested model directories are also scanned
        nested_dir = os.path.join(temp_dir, "models", "3_core", "all")
        os.makedirs(nested_dir, exist_ok=True)

        data_model = {
            "version": 0.1,
            "entities": [
                {"id": "team", "dbt_model": "model.project.team"},
                {"id": "game", "dbt_model": "model.project.game"},
            ],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data_model, f)

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
                                        "arguments": {
                                            "to": "ref('team')",
                                            "field": "team_id",
                                        },
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
                                        "arguments": {
                                            "to": "ref('team')",
                                            "field": "team_id",
                                        },
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
        assert {
            "source": "team",
            "target": "game",
            "source_field": "team_id",
            "target_field": "home_team_id",
        } in [
            {
                "source": r["source"],
                "target": r["target"],
                "source_field": r["source_field"],
                "target_field": r["target_field"],
            }
            for r in rels
        ]
        assert {
            "source": "team",
            "target": "game",
            "source_field": "team_id",
            "target_field": "away_team_id",
        } in [
            {
                "source": r["source"],
                "target": r["target"],
                "source_field": r["source_field"],
                "target_field": r["target_field"],
            }
            for r in rels
        ]

    def test_infers_relationships_across_multiple_model_paths(
        self, test_client, temp_dir, temp_data_model_path
    ):
        """
        When multiple dbt model paths are configured (including with a models/ prefix),
        all should be scanned.
        """
        from trellis_datamodel import config as cfg

        # Add an extra model path and point to a different directory
        extra_models_dir = os.path.join(temp_dir, "models", "3_entity")
        os.makedirs(extra_models_dir, exist_ok=True)

        original_paths = list(cfg.DBT_MODEL_PATHS)
        try:
            cfg.DBT_MODEL_PATHS = ["3_core", "models/3_entity"]

            data_model = {
                "version": 0.1,
                "entities": [
                    {"id": "product", "dbt_model": "model.project.product"},
                    {"id": "opportunity", "dbt_model": "model.project.opportunity"},
                ],
            }
            with open(temp_data_model_path, "w") as f:
                yaml.dump(data_model, f)

            schema = {
                "version": 2,
                "models": [
                    {
                        "name": "opportunity",
                        "columns": [
                            {
                                "name": "product_id",
                                "data_tests": [
                                    {
                                        "relationships": {
                                            "arguments": {
                                                "to": "ref('product')",
                                                "field": "product_id",
                                            }
                                        }
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }

            with open(os.path.join(extra_models_dir, "opportunity.yml"), "w") as f:
                yaml.dump(schema, f)

            response = test_client.get("/api/infer-relationships")
            assert response.status_code == 200

            rels = response.json()["relationships"]
            assert {"source": "product", "target": "opportunity"} in [
                {"source": r["source"], "target": r["target"]} for r in rels
            ]
        finally:
            cfg.DBT_MODEL_PATHS = original_paths
            shutil.rmtree(extra_models_dir, ignore_errors=True)

    def test_infers_relationships_with_arguments_block(
        self, test_client, temp_dir, temp_data_model_path
    ):
        """
        The app should recognize dbt's arguments syntax for relationship tests.
        """
        models_dir = os.path.join(temp_dir, "models", "3_core")
        # Clean out prior test artifacts to avoid cross-test contamination
        shutil.rmtree(models_dir, ignore_errors=True)
        os.makedirs(models_dir, exist_ok=True)

        data_model = {
            "version": 0.1,
            "entities": [
                {"id": "customers", "dbt_model": "model.project.customers"},
                {"id": "orders", "dbt_model": "model.project.orders"},
            ],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data_model, f)

        schema = {
            "version": 2,
            "models": [
                {
                    "name": "orders",
                    "columns": [
                        {
                            "name": "customer_id",
                            "data_type": "int",
                            "data_tests": [
                                {
                                    "relationships": {
                                        "arguments": {
                                            "to": "ref('customers')",
                                            "field": "id",
                                        },
                                        "config": {"severity": "error"},
                                    }
                                }
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
        assert rels[0]["source"] == "customers"
        assert rels[0]["target"] == "orders"
        assert rels[0]["source_field"] == "id"
        assert rels[0]["target_field"] == "customer_id"

    def test_maps_additional_models_to_entity_ids(
        self, test_client, temp_dir, temp_data_model_path
    ):
        """
        Relationship inference should translate additional_models to their entity IDs.
        """
        # Data model maps additional model to entity
        data_model = {
            "version": 0.1,
            "entities": [
                {
                    "id": "customers",
                    "label": "Customers",
                    "additional_models": ["model.project.customers_alt"],
                },
                {"id": "orders", "label": "Orders", "dbt_model": "model.project.orders"},
            ],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data_model, f)

        # Create YML for additional model name with relationship test
        models_dir = os.path.join(temp_dir, "models", "3_core")
        os.makedirs(models_dir, exist_ok=True)
        schema = {
            "version": 2,
            "models": [
                {
                    "name": "customers_alt",
                    "columns": [
                        {
                            "name": "id",
                            "data_type": "int",
                            "data_tests": [
                                {
                                    "relationships": {
                                        "arguments": {
                                            "to": "ref('orders')",
                                            "field": "order_id",
                                        },
                                    }
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        with open(os.path.join(models_dir, "customers_alt.yml"), "w") as f:
            yaml.dump(schema, f)

        response = test_client.get("/api/infer-relationships")
        assert response.status_code == 200

        rels = response.json()["relationships"]
        # Find the relationship coming from the additional model file
        rel = next(
            r
            for r in rels
            if r["source_field"] == "order_id"
            and r["target_field"] == "id"
            and r["target"] == "customers"
            and r["source"] == "orders"
        )
        assert rel

    def test_resolves_versioned_refs_to_existing_entity(
        self, test_client, temp_dir, temp_data_model_path
    ):
        """
        ref('model', v=1) should resolve to an entity bound to v2 (or vice-versa)
        instead of creating a duplicate entity.
        """
        # Bind player to v2 in the data model
        data_model = {
            "version": 0.1,
            "entities": [
                {
                    "id": "player",
                    "label": "Player",
                    "dbt_model": "model.test.player.v2",
                },
                {
                    "id": "game_stats",
                    "label": "Game Stats",
                    "dbt_model": "model.test.game_stats",
                },
            ],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data_model, f)

        # YML with versioned ref to player v1
        schema = {
            "version": 2,
            "models": [
                {
                    "name": "game_stats",
                    "columns": [
                        {
                            "name": "player_id",
                            "data_tests": [
                                {
                                    "relationships": {
                                        "arguments": {
                                            "to": "ref('player', v=1)",
                                            "field": "player_id",
                                        }
                                    }
                                }
                            ],
                        }
                    ],
                }
            ],
        }

        models_dir = os.path.join(temp_dir, "models", "3_core")
        os.makedirs(models_dir, exist_ok=True)
        with open(os.path.join(models_dir, "game_stats.yml"), "w") as f:
            yaml.dump(schema, f)

        response = test_client.get("/api/infer-relationships")
        assert response.status_code == 200

        rels = response.json()["relationships"]
        assert len(rels) == 1
        rel = rels[0]
        assert rel["source"] == "player"
        assert rel["target"] == "game_stats"
        assert rel["source_field"] == "player_id"
        assert rel["target_field"] == "player_id"


class TestModelSchemaVersionHandling:
    """Ensure schema read/write honors requested dbt model version."""

    def _write_versioned_manifest(self, temp_dir: str):
        manifest_data = {
            "nodes": {
                "model.project.player.v1": {
                    "unique_id": "model.project.player.v1",
                    "resource_type": "model",
                    "name": "player",
                    "version": 1,
                    "schema": "public",
                    "alias": "player",
                    "original_file_path": "models/3_core/all/player_v1.sql",
                    "columns": {},
                    "description": "Player v1",
                    "config": {"materialized": "table"},
                    "tags": [],
                },
                "model.project.player.v2": {
                    "unique_id": "model.project.player.v2",
                    "resource_type": "model",
                    "name": "player",
                    "version": 2,
                    "schema": "public",
                    "alias": "player",
                    "original_file_path": "models/3_core/all/player_v2.sql",
                    "columns": {},
                    "description": "Player v2",
                    "config": {"materialized": "table"},
                    "tags": [],
                },
            }
        }

        manifest_path = os.path.join(temp_dir, "manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(manifest_data, f)

    def _write_versioned_schema(self, temp_dir: str) -> str:
        models_dir = os.path.join(temp_dir, "models", "3_core", "all")
        os.makedirs(models_dir, exist_ok=True)
        yml_path = os.path.join(models_dir, "player.yml")

        existing_schema = {
            "version": 2,
            "models": [
                {
                    "name": "player",
                    "latest_version": 2,
                    "versions": [
                        {
                            "v": 1,
                            "description": "v1 description",
                            "columns": [{"name": "player_id", "data_type": "text"}],
                        },
                        {
                            "v": 2,
                            "description": "v2 description",
                            "columns": [{"name": "player_uuid", "data_type": "text"}],
                        },
                    ],
                }
            ],
        }

        with open(yml_path, "w") as f:
            yaml.dump(existing_schema, f)

        return yml_path

    def test_get_model_schema_uses_requested_version(self, test_client, temp_dir):
        self._write_versioned_manifest(temp_dir)
        self._write_versioned_schema(temp_dir)

        response = test_client.get(
            "/api/models/player/schema", params={"version": 2}
        )
        assert response.status_code == 200

        schema = response.json()
        col_names = [col["name"] for col in schema["columns"]]
        assert "player_uuid" in col_names
        assert "player_id" not in col_names
        assert schema["description"] == "v2 description"

    def test_save_model_schema_targets_requested_version(self, test_client, temp_dir):
        self._write_versioned_manifest(temp_dir)
        yml_path = self._write_versioned_schema(temp_dir)

        response = test_client.post(
            "/api/models/player/schema",
            json={
                "columns": [
                    {
                        "name": "player_uuid",
                        "data_type": "text",
                        "description": "Updated PK",
                    }
                ],
                "description": "Players v2 updated",
                "tags": ["core"],
                "version": 2,
            },
        )
        assert response.status_code == 200

        with open(yml_path, "r") as f:
            updated = yaml.safe_load(f)

        versions = {v["v"]: v for v in updated["models"][0]["versions"]}
        assert versions[1]["columns"][0]["name"] == "player_id"

        v2_cols = versions[2]["columns"]
        assert v2_cols[0]["name"] == "player_uuid"
        assert v2_cols[0]["description"] == "Updated PK"
        assert versions[2].get("config", {}).get("tags") == ["core"]
        assert updated["models"][0]["latest_version"] == 2
