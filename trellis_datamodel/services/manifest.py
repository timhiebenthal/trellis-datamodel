"""
Model metadata service.

Provides a service layer over the active framework's model list, abstracting
adapter details from route handlers.
"""

from typing import Any

from trellis_datamodel.adapters import get_adapter
from trellis_datamodel.exceptions import ConfigurationError, FileOperationError


def get_models() -> list[dict[str, Any]]:
    """
    Get parsed models from the transformation framework.

    Returns model metadata for every model the active framework exposes,
    filtered to the configured model paths if any are set in trellis.yml.

    Returns:
        List of model dictionaries with metadata including:
        - unique_id: Full model identifier (e.g., "model.project.model_name")
        - name: Model name
        - version: Optional version number for versioned models
        - schema: Database schema name
        - table: Table/view name
        - columns: List of column metadata
        - description: Model description
        - materialization: Materialization type (table/view/incremental)
        - file_path: Path to model SQL file
        - tags: List of tags

    Raises:
        ConfigurationError: If the framework's project path is not configured
        FileOperationError: If the project's metadata cannot be read or parsed

    Example:
        >>> models = get_models()
        >>> len(models) > 0
        True
        >>> models[0]["name"]
        'users'
    """
    adapter = get_adapter()

    # Check the project is usable before parsing, so a misconfigured path gives
    # the user its own error rather than a parse failure further down.
    status = adapter.get_project_status()
    if not status["project_path"]:
        raise ConfigurationError(status["error"] or "Project path is not configured.")
    if not status["artifacts_present"]:
        raise FileOperationError(
            status["error"] or "The framework's model metadata is not available."
        )

    try:
        return adapter.get_models()
    except FileNotFoundError as e:
        raise FileOperationError(f"Model metadata not found: {str(e)}") from e
    except Exception as e:
        raise FileOperationError(f"Error reading model metadata: {str(e)}") from e
