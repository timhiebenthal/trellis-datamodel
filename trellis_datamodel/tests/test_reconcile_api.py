"""Tests for POST /api/reconcile endpoint."""

import os
import json
import yaml
import pytest


def test_map_column_type_renamed_from_map_dbt_type():
    """_map_dbt_type was renamed to the framework-neutral _map_column_type."""
    from trellis_datamodel.services.reconciliation import _map_column_type

    assert _map_column_type("bigint") == "int"
    assert _map_column_type("varchar") == "text"
    assert _map_column_type(None) == "unknown"


class TestReconcileDbtEndpoint:
    """Tests for POST /api/reconcile."""

    def test_reconciles_bound_entity_from_manifest(
        self, test_client, temp_dir, mock_manifest, temp_data_model_path
    ):
        """Bound entity with matching manifest model gets dbt columns reconciled."""
        # users model is in the mock manifest with columns id + name
        data_model = {
            "version": 0.1,
            "entities": [
                {
                    "id": "users",
                    "label": "Users",
                    "dbt_model": "model.project.users",
                    "drafted_fields": [],
                }
            ],
            "relationships": [],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data_model, f)

        response = test_client.post("/api/reconcile")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["changed"] is True

        entities = data["data_model"]["entities"]
        users = next(e for e in entities if e["id"] == "users")
        fields = users["drafted_fields"]
        assert len(fields) == 2
        assert all(f["source"] == "dbt" for f in fields)
        names = [f["name"] for f in fields]
        assert "id" in names
        assert "name" in names

    def test_noop_when_already_reconciled(
        self, test_client, temp_dir, mock_manifest, temp_data_model_path
    ):
        """Reconciling an already-reconciled model returns changed=False."""
        data_model = {
            "version": 0.1,
            "entities": [
                {
                    "id": "users",
                    "label": "Users",
                    "dbt_model": "model.project.users",
                    "dbt_tags": ["core"],  # matches mock_manifest's model.project.users tags
                    "ui_tags": [],  # migration already ran; nothing Trellis-authored
                    "drafted_fields": [
                        {
                            "name": "id",
                            "datatype": "int",
                            "native_data_type": "integer",
                            "description": "Primary key",
                            "source": "dbt",
                        },
                        {
                            "name": "name",
                            "datatype": "text",
                            "native_data_type": "varchar",
                            "description": "Full name",
                            "source": "dbt",
                        },
                    ],
                }
            ],
            "relationships": [],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data_model, f)

        response = test_client.post("/api/reconcile")
        assert response.status_code == 200
        assert response.json()["changed"] is False

    def test_noop_when_no_data_model(self, test_client, temp_dir, mock_manifest):
        """Missing data_model.yml is a no-op — endpoint succeeds without error."""
        # No data_model.yml written
        response = test_client.post("/api/reconcile")
        assert response.status_code == 200
        assert response.json()["changed"] is False

    def test_reconcile_framework_function_matches_endpoint_behavior(
        self, test_client, temp_dir, mock_manifest, temp_data_model_path
    ):
        """The framework-neutral `reconcile_framework()` service function
        (renamed from `reconcile_dbt()`) is callable directly and produces
        the same result as the /api/reconcile endpoint."""
        from trellis_datamodel.services.reconciliation import reconcile_framework

        data_model = {
            "version": 0.1,
            "entities": [
                {
                    "id": "users",
                    "label": "Users",
                    "dbt_model": "model.project.users",
                    "drafted_fields": [],
                }
            ],
            "relationships": [],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data_model, f)

        result, changed = reconcile_framework()
        assert changed is True

        entities = result["entities"]
        users = next(e for e in entities if e["id"] == "users")
        fields = users["drafted_fields"]
        assert len(fields) == 2
        assert all(f["source"] == "dbt" for f in fields)
        names = [f["name"] for f in fields]
        assert "id" in names
        assert "name" in names

    def test_absent_model_non_destructive(
        self, test_client, temp_dir, mock_manifest, temp_data_model_path
    ):
        """Entity bound to a model NOT in the manifest keeps its existing fields."""
        data_model = {
            "version": 0.1,
            "entities": [
                {
                    "id": "products",
                    "label": "Products",
                    "dbt_model": "model.project.products",  # not in mock_manifest
                    "drafted_fields": [
                        {"name": "sku", "datatype": "text", "source": "dbt"}
                    ],
                }
            ],
            "relationships": [],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data_model, f)

        response = test_client.post("/api/reconcile")
        assert response.status_code == 200
        data = response.json()
        assert data["changed"] is False
        fields = data["data_model"]["entities"][0]["drafted_fields"]
        assert fields == [{"name": "sku", "datatype": "text", "source": "dbt"}]


class TestFrameworkNeutralReconcileEndpoint:
    """POST /api/reconcile (framework-neutral) works end-to-end. The legacy
    POST /api/reconcile-dbt alias was removed in Sprint 6 once the frontend
    fully migrated."""

    @staticmethod
    def _write_data_model(temp_data_model_path):
        data_model = {
            "version": 0.1,
            "entities": [
                {
                    "id": "users",
                    "label": "Users",
                    "dbt_model": "model.project.users",
                    "drafted_fields": [],
                }
            ],
            "relationships": [],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data_model, f)

    def test_new_framework_endpoints_respond(
        self, test_client, temp_dir, mock_manifest, temp_data_model_path
    ):
        self._write_data_model(temp_data_model_path)

        response = test_client.post("/api/reconcile")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["changed"] is True

        entities = data["data_model"]["entities"]
        users = next(e for e in entities if e["id"] == "users")
        fields = users["drafted_fields"]
        assert len(fields) == 2
        names = [f["name"] for f in fields]
        assert "id" in names
        assert "name" in names
