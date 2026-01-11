"""Tests for exception handling and HTTP status code mapping."""

from fastapi.testclient import TestClient

from trellis_datamodel.exceptions import (
    ConfigurationError,
    DomainError,
    FeatureDisabledError,
    FileOperationError,
    NotFoundError,
    ValidationError,
)
from trellis_datamodel.server import app


def test_not_found_error_maps_to_404(test_client: TestClient):
    """Test that NotFoundError maps to 404 status code."""
    # This would be raised by a service, but we'll test via a route that can trigger it
    # For now, we'll verify the exception handler is registered
    # In practice, NotFoundError would come from services like get_model_schema
    response = test_client.get("/api/models/nonexistent_model/schema")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert data.get("error") == "not_found"


def test_validation_error_maps_to_422(test_client: TestClient):
    """Test that ValidationError maps to 422 status code."""
    # Validation errors would come from invalid input
    # Test via data model endpoint with invalid entity_type
    invalid_data = {
        "version": 0.1,
        "entities": [{"id": "test", "label": "Test", "entity_type": "invalid_type"}],
        "relationships": [],
    }
    response = test_client.post("/api/data-model", json=invalid_data)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert "Invalid entity_type" in data["detail"]


def test_configuration_error_maps_to_400(test_client: TestClient, monkeypatch):
    """Test that ConfigurationError maps to 400 status code."""
    import sys
    import trellis_datamodel.config as cfg

    # Temporarily clear DBT_PROJECT_PATH to trigger ConfigurationError
    original_path = cfg.DBT_PROJECT_PATH
    try:
        config_module = sys.modules["trellis_datamodel.config"]
        monkeypatch.setattr(config_module, "DBT_PROJECT_PATH", "")

        # This should trigger ConfigurationError from path validation
        response = test_client.post(
            "/api/dbt-schema",
            json={
                "entity_id": "test",
                "model_name": "test",
                "fields": [],
            },
        )
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert data.get("error") == "configuration_error"
        assert "dbt_project_path" in data["detail"].lower()
    finally:
        monkeypatch.setattr(config_module, "DBT_PROJECT_PATH", original_path)


def test_feature_disabled_error_maps_to_403(test_client: TestClient, monkeypatch):
    """Test that FeatureDisabledError maps to 403 status code."""
    import sys
    import trellis_datamodel.config as cfg

    config_module = sys.modules["trellis_datamodel.config"]
    monkeypatch.setattr(config_module, "EXPOSURES_ENABLED", False)

    # Reload routes to pick up config change
    import importlib
    if "trellis_datamodel.routes.exposures" in sys.modules:
        importlib.reload(sys.modules["trellis_datamodel.routes.exposures"])
    if "trellis_datamodel.server" in sys.modules:
        importlib.reload(sys.modules["trellis_datamodel.server"])

    from trellis_datamodel.server import app
    with TestClient(app) as fresh_client:
        response = fresh_client.get("/api/exposures")
        assert response.status_code == 403
        data = response.json()
        assert "detail" in data
        assert data.get("error") == "feature_disabled"
        assert "disabled" in data["detail"].lower()


def test_file_operation_error_maps_to_500(test_client: TestClient, monkeypatch):
    """Test that FileOperationError maps to 500 status code."""
    import sys
    import trellis_datamodel.config as cfg

    # Set manifest path to non-existent file
    config_module = sys.modules["trellis_datamodel.config"]
    monkeypatch.setattr(
        config_module, "MANIFEST_PATH", "/nonexistent/manifest.json"
    )
    monkeypatch.setattr(config_module, "LINEAGE_ENABLED", True)

    # Reload routes
    import importlib
    if "trellis_datamodel.routes.lineage" in sys.modules:
        importlib.reload(sys.modules["trellis_datamodel.routes.lineage"])
    if "trellis_datamodel.server" in sys.modules:
        importlib.reload(sys.modules["trellis_datamodel.server"])

    from trellis_datamodel.server import app
    with TestClient(app) as fresh_client:
        response = fresh_client.get("/api/lineage/model.project.test")
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert data.get("error") == "file_operation_error"


def test_error_response_structure():
    """Test that all error responses have consistent structure."""
    # Verify exception handlers return consistent structure
    # This is tested indirectly through the above tests, but we can verify the structure
    error_types = [
        NotFoundError("Not found"),
        ValidationError("Invalid input"),
        ConfigurationError("Config error"),
        FeatureDisabledError("Feature disabled"),
        FileOperationError("File error"),
        DomainError("Generic error"),
    ]

    for error in error_types:
        assert hasattr(error, "message")
        assert isinstance(error.message, str)
        assert len(error.message) > 0
