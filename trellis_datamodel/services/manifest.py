"""
Manifest and catalog service.

Handles parsing and retrieval of transformation framework manifest and catalog
information — dbt manifest.json and catalog.json files when using dbt-core, or
Bruin pipeline assets when using the Bruin framework. Provides a service layer
for manifest operations, abstracting adapter details from route handlers.
"""

from typing import Any

from trellis_datamodel import config as cfg
from trellis_datamodel.adapters import get_adapter
from trellis_datamodel.exceptions import FileOperationError
from trellis_datamodel.utils.path_validation import (
    validate_manifest_path,
    validate_pipeline_path,
)


def get_models() -> list[dict[str, Any]]:
    """
    Get parsed models from the transformation framework.

    When framework is dbt-core, parses the dbt manifest.json file and returns
    a list of model metadata dictionaries. Models are filtered according to
    configured dbt_model_paths if specified in trellis.yml.

    When framework is bruin, scans pipeline asset files for @bruin blocks and
    returns a list of asset metadata dictionaries.

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
        FileOperationError: If manifest/pipeline cannot be read or parsed
        ConfigurationError: If manifest/pipeline path is not configured

    Example:
        >>> models = get_models()
        >>> len(models) > 0
        True
        >>> models[0]["name"]
        'users'
    """
    try:
        if cfg.FRAMEWORK == "bruin":
            validate_pipeline_path()
        else:
            validate_manifest_path()
        adapter = get_adapter()
        models = adapter.get_models()
        return models
    except FileNotFoundError as e:
        raise FileOperationError(f"Manifest not found: {str(e)}") from e
    except Exception as e:
        raise FileOperationError(f"Error reading manifest: {str(e)}") from e
