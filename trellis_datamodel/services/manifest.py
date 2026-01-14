"""
Manifest and catalog service.

Handles parsing and retrieval of dbt manifest.json and catalog.json files.
Provides a service layer for manifest operations, abstracting adapter details
from route handlers.
"""

from typing import Any

from trellis_datamodel.adapters import get_adapter
from trellis_datamodel.exceptions import FileOperationError
from trellis_datamodel.utils.path_validation import validate_manifest_path


def get_models() -> list[dict[str, Any]]:
    """
    Get parsed models from the transformation framework.

    Parses the dbt manifest.json file and returns a list of model metadata
    dictionaries. Models are filtered according to configured dbt_model_paths
    if specified in trellis.yml.

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
        FileOperationError: If manifest cannot be read or parsed
        ConfigurationError: If manifest path is not configured

    Example:
        >>> models = get_models()
        >>> len(models) > 0
        True
        >>> models[0]["name"]
        'users'
    """
    try:
        validate_manifest_path()
        adapter = get_adapter()
        models = adapter.get_models()
        return models
    except FileNotFoundError as e:
        raise FileOperationError(f"Manifest not found: {str(e)}") from e
    except Exception as e:
        raise FileOperationError(f"Error reading manifest: {str(e)}") from e
