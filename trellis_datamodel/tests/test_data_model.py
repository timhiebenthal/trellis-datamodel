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

    def test_returns_existing_model(
        self, test_client, temp_data_model_path, temp_canvas_layout_path
    ):
        # Create a data model file (model-only)
        model_data = {
            "version": 0.1,
            "entities": [{"id": "users", "label": "Users"}],
            "relationships": [
                {"source": "orders", "target": "users", "type": "one_to_many"}
            ],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(model_data, f)

        # Create a canvas layout file (layout-only)
        layout_data = {
            "version": 0.1,
            "entities": {
                "users": {
                    "position": {"x": 0, "y": 0},
                    "width": 280,
                    "collapsed": False,
                }
            },
            "relationships": {"orders-users-0": {"label_dx": 10, "label_dy": 20}},
        }
        with open(temp_canvas_layout_path, "w") as f:
            yaml.dump(layout_data, f)

        response = test_client.get("/api/data-model")
        assert response.status_code == 200
        data = response.json()
        assert len(data["entities"]) == 1
        assert data["entities"][0]["id"] == "users"
        # Verify layout is merged
        assert data["entities"][0]["position"] == {"x": 0, "y": 0}
        assert data["entities"][0]["width"] == 280
        assert data["relationships"][0]["label_dx"] == 10
        assert data["relationships"][0]["label_dy"] == 20

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

    def test_saves_new_model(
        self, test_client, temp_data_model_path, temp_canvas_layout_path
    ):
        model_data = {
            "version": 0.1,
            "entities": [
                {
                    "id": "users",
                    "label": "Users",
                    "position": {"x": 100, "y": 200},
                    "width": 300,
                    "collapsed": False,
                }
            ],
            "relationships": [],
        }
        response = test_client.post("/api/data-model", json=model_data)
        assert response.status_code == 200
        assert response.json()["status"] == "success"

        # Verify model file was written (without visual properties)
        assert os.path.exists(temp_data_model_path)
        with open(temp_data_model_path, "r") as f:
            saved = yaml.safe_load(f)
        assert saved["entities"][0]["id"] == "users"
        assert "position" not in saved["entities"][0]
        assert "width" not in saved["entities"][0]

        # Verify layout file was written (with visual properties only)
        assert os.path.exists(temp_canvas_layout_path)
        with open(temp_canvas_layout_path, "r") as f:
            layout = yaml.safe_load(f)
        assert "users" in layout["entities"]
        assert layout["entities"]["users"]["position"] == {"x": 100, "y": 200}
        assert layout["entities"]["users"]["width"] == 300

    def test_overwrites_existing_model(
        self, test_client, temp_data_model_path, temp_canvas_layout_path
    ):
        # Create initial model and layout
        with open(temp_data_model_path, "w") as f:
            yaml.dump(
                {"version": 0.1, "entities": [{"id": "old"}], "relationships": []}, f
            )
        with open(temp_canvas_layout_path, "w") as f:
            yaml.dump(
                {
                    "version": 0.1,
                    "entities": {"old": {"position": {"x": 50, "y": 50}}},
                    "relationships": {},
                },
                f,
            )

        # Overwrite with new model
        model_data = {
            "version": 0.1,
            "entities": [{"id": "new", "label": "New", "position": {"x": 0, "y": 0}}],
            "relationships": [],
        }
        response = test_client.post("/api/data-model", json=model_data)
        assert response.status_code == 200

        # Verify old entity is removed from both files
        with open(temp_data_model_path, "r") as f:
            saved = yaml.safe_load(f)
        assert len(saved["entities"]) == 1
        assert saved["entities"][0]["id"] == "new"

        with open(temp_canvas_layout_path, "r") as f:
            layout = yaml.safe_load(f)
        assert "old" not in layout["entities"]
        assert "new" in layout["entities"]

    def test_validates_required_fields(self, test_client):
        # Missing required fields should fail validation
        response = test_client.post("/api/data-model", json={})
        assert response.status_code == 422  # Pydantic validation error
