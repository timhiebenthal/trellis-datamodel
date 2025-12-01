"""Tests for data model API endpoints."""
import os
import yaml
import pytest


class TestGetDataModel:
    """Tests for GET /api/data-model endpoint."""

    def test_returns_empty_model_when_file_missing(self, test_client):
        response = test_client.get("/api/data-model")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == 0.1
        assert data["entities"] == []
        assert data["relationships"] == []

    def test_returns_existing_model(self, test_client, temp_data_model_path):
        # Create a data model file
        model_data = {
            "version": 0.1,
            "entities": [{"id": "users", "label": "Users", "position": {"x": 0, "y": 0}}],
            "relationships": [{"source": "orders", "target": "users", "type": "one_to_many"}],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(model_data, f)

        response = test_client.get("/api/data-model")
        assert response.status_code == 200
        data = response.json()
        assert len(data["entities"]) == 1
        assert data["entities"][0]["id"] == "users"

    def test_handles_file_with_missing_keys(self, test_client, temp_data_model_path):
        # Create a minimal data model file
        with open(temp_data_model_path, "w") as f:
            yaml.dump({"version": 0.1}, f)

        response = test_client.get("/api/data-model")
        assert response.status_code == 200
        data = response.json()
        assert data["entities"] == []
        assert data["relationships"] == []


class TestSaveDataModel:
    """Tests for POST /api/data-model endpoint."""

    def test_saves_new_model(self, test_client, temp_data_model_path):
        model_data = {
            "version": 0.1,
            "entities": [{"id": "users", "label": "Users", "position": {"x": 100, "y": 200}}],
            "relationships": [],
        }
        response = test_client.post("/api/data-model", json=model_data)
        assert response.status_code == 200
        assert response.json()["status"] == "success"

        # Verify file was written
        assert os.path.exists(temp_data_model_path)
        with open(temp_data_model_path, "r") as f:
            saved = yaml.safe_load(f)
        assert saved["entities"][0]["id"] == "users"

    def test_overwrites_existing_model(self, test_client, temp_data_model_path):
        # Create initial model
        with open(temp_data_model_path, "w") as f:
            yaml.dump({"version": 0.1, "entities": [{"id": "old"}], "relationships": []}, f)

        # Overwrite with new model
        model_data = {
            "version": 0.1,
            "entities": [{"id": "new", "label": "New", "position": {"x": 0, "y": 0}}],
            "relationships": [],
        }
        response = test_client.post("/api/data-model", json=model_data)
        assert response.status_code == 200

        with open(temp_data_model_path, "r") as f:
            saved = yaml.safe_load(f)
        assert len(saved["entities"]) == 1
        assert saved["entities"][0]["id"] == "new"

    def test_validates_required_fields(self, test_client):
        # Missing required fields should fail validation
        response = test_client.post("/api/data-model", json={})
        assert response.status_code == 422  # Pydantic validation error

