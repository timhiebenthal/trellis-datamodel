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

from dataclasses import dataclass
from pathlib import Path
from typing import Any


from trellis_datamodel import config as cfg
from trellis_datamodel.adapters import get_adapter
from trellis_datamodel.adapters.base import ModelInfo, ModelSchema, TransformationAdapter
from trellis_datamodel.exceptions import (
    ConfigurationError,
    FileOperationError,
    NotFoundError,
    ValidationError,
)
from trellis_datamodel.models.entity_keys import get_model_ref
from trellis_datamodel.services.ossie import export_ossie
from trellis_datamodel.services.tag_ownership import PUSHED_TAGS_KEY
from trellis_datamodel.utils.path_validation import validate_data_model_path
from trellis_datamodel.utils.structured_data import load_yaml_file, load_yaml_or_json
from trellis_datamodel.utils.yaml_handler import YamlHandler


@dataclass
class SyncOutcome:
    """What one push produced: framework files, warnings, and the Ossie file."""

    files: list[Path]
    warnings: list[str]
    ossie_path: Path | None


def save_model_schema_from_request(
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
        ConfigurationError: If the project path is not configured
        FileOperationError: If schema save fails
    """
    get_adapter().validate_project_path()

    try:
        adapter = get_adapter()
        output_path = adapter.save_schema_file(
            entity_id=entity_id,
            model_name=model_name,
            fields=fields,
            description=description,
            tags=tags,
        )
        return output_path
    except ValidationError:
        raise
    except Exception as e:
        raise FileOperationError(f"Error saving schema: {str(e)}") from e


def sync_framework_tests() -> SyncOutcome:
    """
    Sync relationship tests from data model to schema files.

    When `ossie.enabled` is set, the semantic model is exported after the
    framework files are written and the pushed tags persisted, so a failed
    export can never leave the framework half-pushed.

    Returns:
        The updated framework files, exporter warnings, and the Ossie path

    Raises:
        ConfigurationError: If the project path or data_model_path is not configured
        FileOperationError: If data model file not found or sync fails
    """
    get_adapter().validate_project_path()
    data_model_path = validate_data_model_path()

    import os

    if not os.path.exists(data_model_path):
        raise FileOperationError("Data model file not found")

    try:
        data_model = load_yaml_file(data_model_path, {})

        entities = data_model.get("entities", [])
        relationships = data_model.get("relationships", [])

        adapter = get_adapter()

        # Merge inferred relationships from the framework's schema files to
        # avoid missing tests when the data_model.yml payload is prefix-stripped
        # or outdated.
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

        pushed_before = {e.get("id"): e.get(PUSHED_TAGS_KEY) for e in entities}
        updated_files = adapter.sync_relationships(entities, relationships)
        _persist_pushed_tags(data_model_path, entities, pushed_before)
    except ValidationError:
        raise
    except Exception as e:
        raise FileOperationError(f"Error syncing tests: {str(e)}") from e

    if not cfg.OSSIE_CONFIG.enabled:
        return SyncOutcome(files=updated_files, warnings=[], ossie_path=None)

    # Outside the block above on purpose: the framework push already succeeded,
    # so the error must say so rather than reporting a failed sync.
    try:
        models = adapter.get_models()
        project_name = adapter.get_project_status()["project_name"]
        model_schemas, schema_warnings = _ossie_model_schemas(
            adapter, entities, models
        )
        export = export_ossie(
            entities, relationships, project_name, models, model_schemas
        )
    except Exception as e:
        raise FileOperationError(
            "Framework schema files were updated, but the Ossie file was not "
            f"written: {e}"
        ) from e

    if export.path is not None:
        updated_files.append(export.path)
    return SyncOutcome(
        files=updated_files,
        warnings=schema_warnings + export.warnings,
        ossie_path=export.path,
    )


def _ossie_model_schemas(
    adapter: TransformationAdapter,
    entities: list[dict[str, Any]],
    models: list[ModelInfo],
) -> tuple[dict[str, ModelSchema], list[str]]:
    """Read key metadata for the models bound entities actually name.

    Unreadable schemas are only a warning: the dataset is still exported, it
    just loses key inference, and one broken schema file must not fail a push.
    """
    wanted = {
        model_ref for model_ref in (get_model_ref(e) for e in entities) if model_ref
    }
    schemas: dict[str, ModelSchema] = {}
    warnings: list[str] = []

    for model in models:
        unique_id = model.get("unique_id") or ""
        if not unique_id or unique_id not in wanted:
            continue
        try:
            schemas[unique_id] = adapter.get_model_schema(
                model["name"], version=model.get("version")
            )
        except Exception as e:
            warnings.append(
                f'model "{model.get("name")}" schema could not be read, so its '
                f"key metadata was skipped: {e}"
            )
    return schemas, warnings


def _persist_pushed_tags(
    data_model_path: str,
    entities: list[dict[str, Any]],
    pushed_before: dict[Any, Any],
) -> None:
    """Record in data_model.yml which tags this push put into the schema files.

    The adapter sets `pushed_tags` on the entity dicts it was handed. Only bound
    entities whose record changed are written, onto a fresh read of the file,
    and only while the entity is still bound to the model that was pushed — a
    rebound entity's old record must not drive removals on its new model.
    """
    changed = {
        entity["id"]: (get_model_ref(entity), entity[PUSHED_TAGS_KEY])
        for entity in entities
        if entity.get("id")
        and get_model_ref(entity)
        and PUSHED_TAGS_KEY in entity
        and entity[PUSHED_TAGS_KEY] != pushed_before.get(entity["id"])
    }
    if not changed:
        return

    data_model = load_yaml_or_json(data_model_path) or {}
    for entity in data_model.get("entities", []):
        model_ref, pushed_tags = changed.get(entity.get("id"), (None, None))
        if model_ref and get_model_ref(entity) == model_ref:
            entity[PUSHED_TAGS_KEY] = pushed_tags
    YamlHandler().save_file(data_model_path, data_model)


def get_model_schema(model_name: str, version: int | None = None) -> dict[str, Any]:
    """
    Get the schema for a specific model from its YAML file.

    Args:
        model_name: Name of the model
        version: Optional version number for versioned models

    Returns:
        Dictionary with model_name, description, columns, tags, file_path

    Raises:
        ConfigurationError: If the project path is not configured
        NotFoundError: If model not found
        FileOperationError: If schema read fails
    """
    get_adapter().validate_project_path()

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
    except ValidationError:
        raise
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
        ConfigurationError: If the project path is not configured
        NotFoundError: If model not found
        FileOperationError: If schema update fails
    """
    get_adapter().validate_project_path()

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
    except ValidationError:
        raise
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
        ConfigurationError: If the project path is not configured or no schema files found
        FileOperationError: If schema files cannot be read
    """
    get_adapter().validate_project_path()

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
