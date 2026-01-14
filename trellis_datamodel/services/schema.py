"""
Schema service for dbt schema file operations.

Handles reading, writing, and syncing dbt schema YAML files. This service
encapsulates all business logic for dbt schema.yml operations, including:
- Reading model schemas from YAML files
- Writing/updating model schemas
- Syncing relationship tests from data model to schema files
- Inferring relationships from existing schema files

All operations validate configuration and paths before execution, raising
appropriate domain exceptions for error conditions.
"""

from pathlib import Path
from typing import Any

import yaml

from trellis_datamodel import config as cfg
from trellis_datamodel.adapters import get_adapter
from trellis_datamodel.exceptions import (
    ConfigurationError,
    FileOperationError,
    NotFoundError,
    ValidationError,
)
from trellis_datamodel.utils.path_validation import (
    ensure_data_model_path_exists,
    validate_data_model_path,
    validate_dbt_project_path,
)


def save_dbt_schema(
    entity_id: str,
    model_name: str,
    fields: list[dict[str, str]],
    description: str | None = None,
    tags: list[str] | None = None,
) -> Path:
    """
    Generate and save a schema YAML file for drafted fields.

    Args:
        entity_id: Entity ID from data model
        model_name: dbt model name
        fields: List of field definitions
        description: Optional model description
        tags: Optional list of tags

    Returns:
        Path to the saved schema file

    Raises:
        ConfigurationError: If dbt_project_path is not configured
        FileOperationError: If schema save fails
    """
    validate_dbt_project_path()

    try:
        adapter = get_adapter()
        output_path = adapter.save_dbt_schema(
            entity_id=entity_id,
            model_name=model_name,
            fields=fields,
            description=description,
            tags=tags,
        )
        return output_path
    except Exception as e:
        raise FileOperationError(f"Error saving schema: {str(e)}") from e


def sync_dbt_tests() -> list[Path]:
    """
    Sync relationship tests from data model to schema files.

    Returns:
        List of paths to updated schema files

    Raises:
        ConfigurationError: If dbt_project_path or data_model_path is not configured
        FileOperationError: If data model file not found or sync fails
    """
    validate_dbt_project_path()
    data_model_path = validate_data_model_path()

    import os

    if not os.path.exists(data_model_path):
        raise FileOperationError("Data model file not found")

    try:
        with open(data_model_path, "r") as f:
            data_model = yaml.safe_load(f) or {}

        entities = data_model.get("entities", [])
        relationships = data_model.get("relationships", [])

        # Merge inferred relationships from dbt yml to avoid missing tests when
        # the data_model.yml payload is prefix-stripped or outdated.
        try:
            inferred = adapter.infer_relationships(include_unbound=False)
        except Exception:
            inferred = []

        merged: dict[tuple, dict] = {}
        for rel in relationships:
            key = (
                rel.get("source"),
                rel.get("target"),
                rel.get("source_field"),
                rel.get("target_field"),
            )
            merged[key] = rel
        for rel in inferred:
            key = (
                rel.get("source"),
                rel.get("target"),
                rel.get("source_field"),
                rel.get("target_field"),
            )
            if key not in merged:
                merged[key] = rel
        relationships = list(merged.values())

        adapter = get_adapter()
        updated_files = adapter.sync_relationships(entities, relationships)

        return updated_files
    except Exception as e:
        raise FileOperationError(f"Error syncing tests: {str(e)}") from e


def get_model_schema(model_name: str, version: int | None = None) -> dict[str, Any]:
    """
    Get the schema for a specific model from its YAML file.

    Args:
        model_name: Name of the model
        version: Optional version number for versioned models

    Returns:
        Dictionary with model_name, description, columns, tags, file_path

    Raises:
        ConfigurationError: If dbt_project_path is not configured
        NotFoundError: If model not found
        FileOperationError: If schema read fails
    """
    validate_dbt_project_path()

    try:
        adapter = get_adapter()
        schema = adapter.get_model_schema(model_name, version=version)

        return {
            "model_name": schema.get("model_name", model_name),
            "description": schema.get("description", ""),
            "columns": schema.get("columns", []),
            "tags": schema.get("tags", []),
            "file_path": schema.get("file_path", ""),
        }
    except FileNotFoundError as e:
        raise NotFoundError(f"Model schema not found: {str(e)}") from e
    except ValueError as e:
        raise NotFoundError(f"Model not found: {str(e)}") from e
    except Exception as e:
        raise FileOperationError(f"Error reading model schema: {str(e)}") from e


def update_model_schema(
    model_name: str,
    columns: list[dict[str, Any]],
    description: str | None = None,
    tags: list[str] | None = None,
    version: int | None = None,
) -> Path:
    """
    Update the schema for a specific model in its YAML file.

    Args:
        model_name: Name of the model to update
        columns: Column definitions
        description: Optional model description
        tags: Optional list of tags
        version: Optional version number for versioned models

    Returns:
        Path to the updated schema file

    Raises:
        ConfigurationError: If dbt_project_path is not configured
        NotFoundError: If model not found
        FileOperationError: If schema update fails
    """
    validate_dbt_project_path()

    try:
        adapter = get_adapter()
        output_path = adapter.save_model_schema(
            model_name=model_name,
            columns=columns,
            description=description,
            tags=tags,
            version=version,
        )
        return output_path
    except FileNotFoundError as e:
        raise NotFoundError(f"Model schema not found: {str(e)}") from e
    except ValueError as e:
        raise NotFoundError(f"Model not found: {str(e)}") from e
    except Exception as e:
        raise FileOperationError(f"Error updating model schema: {str(e)}") from e


def infer_relationships(include_unbound: bool = False) -> list[dict[str, Any]]:
    """
    Scan schema files and infer entity relationships from relationship tests.

    Args:
        include_unbound: If True, include relationships for unbound entities

    Returns:
        List of inferred relationships

    Raises:
        ConfigurationError: If dbt_project_path is not configured or no schema files found
        FileOperationError: If schema files cannot be read
    """
    validate_dbt_project_path()

    try:
        adapter = get_adapter()
        relationships = adapter.infer_relationships(include_unbound=include_unbound)
        return relationships
    except FileNotFoundError as e:
        # When no yml files found, raise ConfigurationError (maps to 400)
        # to match existing API behavior
        error_msg = str(e).lower()
        if "no schema yml files found" in error_msg:
            raise ConfigurationError(str(e)) from e
        raise FileOperationError(f"Schema files not found: {str(e)}") from e
    except Exception as e:
        raise FileOperationError(f"Error inferring relationships: {str(e)}") from e
