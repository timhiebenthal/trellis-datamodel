"""
Config service for managing trellis.yml through the API.

Handles loading, validation, conflict detection, backup, and atomic writes.
"""

import hashlib
import logging
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import json

import yaml
from pydantic import ValidationError

from trellis_datamodel.config import find_config_file
from trellis_datamodel.exceptions import (
    ConfigurationError,
    ValidationError as CustomValidationError,
)
from trellis_datamodel.models.schemas import (
    ConfigSchema,
    ConfigSchemaResponse,
    ConfigFieldMetadata,
)

logger = logging.getLogger(__name__)


# Define field metadata for UI
_FIELD_DEFINITIONS: Dict[str, ConfigFieldMetadata] = {
    "framework": ConfigFieldMetadata(
        type="enum",
        enum_values=["dbt-core"],
        default="dbt-core",
        required=True,
        description="Transformation framework",
        beta=False,
    ),
    "modeling_style": ConfigFieldMetadata(
        type="enum",
        enum_values=["dimensional_model", "entity_model"],
        default="entity_model",
        required=True,
        description="Modeling style approach",
        beta=False,
    ),
    "dbt_project_path": ConfigFieldMetadata(
        type="string",
        default="",
        required=False,
        description="Path to dbt project directory (relative or absolute)",
        beta=False,
    ),
    "dbt_manifest_path": ConfigFieldMetadata(
        type="string",
        default="",
        required=False,
        description="Path to manifest.json (relative to project or absolute)",
        beta=False,
    ),
    "dbt_catalog_path": ConfigFieldMetadata(
        type="string",
        default="",
        required=False,
        description="Path to catalog.json (relative to project or absolute)",
        beta=False,
    ),
    "data_model_file": ConfigFieldMetadata(
        type="string",
        default="data_model.yml",
        required=False,
        description="Path where data model YAML will be saved",
        beta=False,
    ),
    "dbt_model_paths": ConfigFieldMetadata(
        type="list",
        default=[],
        required=False,
        description="Path patterns to include (filters dbt models by original_file_path)",
        beta=False,
    ),
    "dbt_company_dummy_path": ConfigFieldMetadata(
        type="string",
        default="",
        required=False,
        description="Optional path to company dummy project",
        beta=False,
    ),
    "lineage.enabled": ConfigFieldMetadata(
        type="boolean",
        default=False,
        required=False,
        description="Enable lineage visualization",
        beta=True,
    ),
    "lineage.layers": ConfigFieldMetadata(
        type="list",
        default=[],
        required=False,
        description="Ordered list of folder names to organize lineage into layers",
        beta=True,
    ),
    "entity_creation_guidance.enabled": ConfigFieldMetadata(
        type="boolean",
        default=False,
        required=False,
        description="Enable entity creation wizard",
        beta=False,
    ),
    "entity_creation_guidance.push_warning_enabled": ConfigFieldMetadata(
        type="boolean",
        default=True,
        required=False,
        description="Show push-to-dbt warnings",
        beta=False,
    ),
    "entity_creation_guidance.min_description_length": ConfigFieldMetadata(
        type="integer",
        default=10,
        required=False,
        description="Minimum description length for entity creation",
        beta=False,
    ),
    "entity_creation_guidance.disabled_guidance": ConfigFieldMetadata(
        type="list",
        default=[],
        required=False,
        description="List of guidance features to disable",
        beta=False,
    ),
    "exposures.enabled": ConfigFieldMetadata(
        type="boolean",
        default=False,
        required=False,
        description="Enable exposures tracking and visualization",
        beta=True,
    ),
    "exposures.default_layout": ConfigFieldMetadata(
        type="enum",
        enum_values=["dashboards-as-rows", "entities-as-rows"],
        default="dashboards-as-rows",
        required=False,
        description="Default layout for exposures visualization",
        beta=True,
    ),
    "dimensional_modeling.inference_patterns.dimension_prefix": ConfigFieldMetadata(
        type="string",
        default="dim_",
        required=False,
        description="Prefix for dimension tables",
        beta=False,
    ),
    "dimensional_modeling.inference_patterns.fact_prefix": ConfigFieldMetadata(
        type="string",
        default="fact_",
        required=False,
        description="Prefix for fact tables",
        beta=False,
    ),
    "entity_modeling.inference_patterns.prefix": ConfigFieldMetadata(
        type="string",
        default="",
        required=False,
        description="Prefix for entity tables",
        beta=False,
    ),
    "business_events.enabled": ConfigFieldMetadata(
        type="boolean",
        default=False,
        required=False,
        description="Enable business events modeling with BEAM* methodology",
        beta=True,
    ),
    "business_events.file": ConfigFieldMetadata(
        type="string",
        default="",
        required=False,
        description="Path to business events YAML file (defaults to business_events.yml in data model directory)",
        beta=True,
    ),
}

# List of fields that are beta features
_BETA_FIELDS = [
    "lineage.enabled",
    "lineage.layers",
    "exposures.enabled",
    "exposures.default_layout",
    "business_events.enabled",
    "business_events.file",
]


def _get_file_hash(file_path: str) -> str:
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def _get_file_mtime(file_path: str) -> float:
    """Get file modification time."""
    return os.path.getmtime(file_path)


def _normalize_nested_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize config to match Pydantic schema structure."""
    normalized = {}

    # Copy top-level fields
    for key in [
        "framework",
        "modeling_style",
        "dbt_project_path",
        "dbt_manifest_path",
        "dbt_catalog_path",
        "data_model_file",
        "dbt_model_paths",
        "dbt_company_dummy_path",
    ]:
        if key in config:
            normalized[key] = config[key]

    # Enforce mutual exclusion between dimensional_modeling and entity_modeling
    # based on the modeling_style setting
    modeling_style = normalized.get("modeling_style", "entity_model")
    if modeling_style == "dimensional_model":
        # Remove entity_modeling if present
        config = {k: v for k, v in config.items() if k != "entity_modeling"}
    elif modeling_style == "entity_model":
        # Remove dimensional_modeling if present
        config = {k: v for k, v in config.items() if k != "dimensional_modeling"}

    # Normalize nested sections
    # Lineage
    if "lineage" in config:
        lineage = config["lineage"]
        if isinstance(lineage, dict):
            normalized["lineage"] = {
                "enabled": bool(lineage.get("enabled", False)),
                "layers": (
                    list(lineage.get("layers", []))
                    if isinstance(lineage.get("layers"), list)
                    else []
                ),
            }

    # Entity creation guidance
    if "entity_creation_guidance" in config:
        guidance = config["entity_creation_guidance"]
        if isinstance(guidance, dict):
            normalized["entity_creation_guidance"] = {
                "enabled": bool(guidance.get("enabled", False)),
                "push_warning_enabled": bool(
                    guidance.get("push_warning_enabled", True)
                ),
                "min_description_length": int(
                    guidance.get("min_description_length", 10)
                ),
                "disabled_guidance": (
                    list(guidance.get("disabled_guidance", []))
                    if isinstance(guidance.get("disabled_guidance"), list)
                    else []
                ),
            }

    # Exposures
    if "exposures" in config:
        exposures = config["exposures"]
        if isinstance(exposures, dict):
            layout = exposures.get("default_layout", "dashboards-as-rows")
            if layout not in ["dashboards-as-rows", "entities-as-rows"]:
                layout = "dashboards-as-rows"
            normalized["exposures"] = {
                "enabled": bool(exposures.get("enabled", False)),
                "default_layout": layout,
            }

    # Business Events
    if "business_events" in config:
        business_events = config["business_events"]
        if isinstance(business_events, dict):
            normalized["business_events"] = {
                "enabled": bool(business_events.get("enabled", False)),
                "file": business_events.get("file", ""),
            }

    # Dimensional modeling
    if "dimensional_modeling" in config:
        dm = config["dimensional_modeling"]
        if isinstance(dm, dict):
            patterns = dm.get("inference_patterns", {})
            if isinstance(patterns, dict):
                normalized["dimensional_modeling"] = {
                    "inference_patterns": {
                        "dimension_prefix": (
                            patterns.get("dimension_prefix", ["dim_", "d_"])
                            if isinstance(patterns.get("dimension_prefix"), list)
                            else patterns.get("dimension_prefix", "dim_")
                        ),
                        "fact_prefix": (
                            patterns.get("fact_prefix", ["fct_", "fact_"])
                            if isinstance(patterns.get("fact_prefix"), list)
                            else patterns.get("fact_prefix", "fact_")
                        ),
                    }
                }

    # Entity modeling
    if "entity_modeling" in config:
        em = config["entity_modeling"]
        if isinstance(em, dict):
            patterns = em.get("inference_patterns", {})
            if isinstance(patterns, dict):
                normalized["entity_modeling"] = {
                    "inference_patterns": {
                        "prefix": (
                            patterns.get("prefix", [])
                            if isinstance(patterns.get("prefix"), list)
                            else patterns.get("prefix", "")
                        )
                    }
                }

    return normalized


def _validate_paths(config: Dict[str, Any], config_path: str) -> list[str]:
    """
    Validate that required paths exist.

    Returns list of warning/error messages.
    """
    messages = []
    base_dir = os.path.dirname(config_path) if config_path else os.getcwd()

    # Check dbt_project_path
    project_path = config.get("dbt_project_path", "")
    if project_path:
        full_path = (
            project_path
            if os.path.isabs(project_path)
            else os.path.abspath(os.path.join(base_dir, project_path))
        )
        if not os.path.exists(full_path):
            messages.append(f"dbt_project_path does not exist: {full_path}")

    # Check manifest path (relative to project or absolute)
    manifest_path = config.get("dbt_manifest_path", "")
    if manifest_path and project_path:
        full_manifest = (
            manifest_path
            if os.path.isabs(manifest_path)
            else os.path.abspath(os.path.join(full_path, manifest_path))
        )
        if not os.path.exists(full_manifest):
            messages.append(f"dbt_manifest_path does not exist: {full_manifest}")

    # Check catalog path (warning only, it's optional)
    catalog_path = config.get("dbt_catalog_path", "")
    if catalog_path and project_path:
        full_catalog = (
            catalog_path
            if os.path.isabs(catalog_path)
            else os.path.abspath(os.path.join(full_path, catalog_path))
        )
        if not os.path.exists(full_catalog):
            messages.append(f"Warning: dbt_catalog_path does not exist: {full_catalog}")

    return messages


def _create_backup(config_path: str) -> Optional[str]:
    """
    Create a backup of the config file.

    Returns path to backup file or None if backup failed.
    Uses a single .backup file instead of timestamped backups.
    """
    try:
        backup_path = f"{config_path}.backup"

        shutil.copy2(config_path, backup_path)
        logger.info(f"Created backup: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        return None


def _atomic_write(config_path: str, config: Dict[str, Any]) -> None:
    """
    Atomically write config to file.

    Uses temp file + move to ensure atomic operation.
    """
    # Write to temp file
    fd, temp_path = tempfile.mkstemp(
        prefix=os.path.basename(config_path), dir=os.path.dirname(config_path)
    )

    try:
        with os.fdopen(fd, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        # Atomic move
        os.replace(temp_path, config_path)
        logger.info(f"Atomically wrote config to: {config_path}")
    except Exception as e:
        # Clean up temp file on error
        try:
            os.unlink(temp_path)
        except Exception:
            pass
        raise ConfigurationError(f"Failed to write config: {e}")


def get_schema_metadata() -> ConfigSchemaResponse:
    """
    Get schema metadata for the config UI.

    Returns field definitions and list of beta flags.
    """
    return ConfigSchemaResponse(fields=_FIELD_DEFINITIONS, beta_flags=_BETA_FIELDS)


def load_config(
    config_path: Optional[str] = None,
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """
    Load and normalize config from trellis.yml.

    Returns:
        Tuple of (config_dict, file_info_dict)
        file_info contains mtime, hash if file exists

    Raises:
        ConfigurationError: If config file is not found or unreadable
    """
    if not config_path:
        config_path = find_config_file()

    if not config_path:
        raise ConfigurationError(
            "No config file found. Please create trellis.yml in the current directory."
        )

    if not os.path.exists(config_path):
        raise ConfigurationError(f"Config file not found: {config_path}")

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f) or {}
    except Exception as e:
        raise ConfigurationError(f"Failed to read config file: {e}")

    # Get file info for conflict detection
    file_info = {
        "path": config_path,
        "mtime": _get_file_mtime(config_path),
        "hash": _get_file_hash(config_path),
    }

    # Normalize config
    normalized = _normalize_nested_config(config)

    return normalized, file_info


def validate_config(config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate config against Pydantic schema.

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        ConfigSchema(**config)
        return True, None
    except ValidationError as e:
        error_details = []
        for error in e.errors():
            field = ".".join(str(x) for x in error["loc"])
            msg = error["msg"]
            error_details.append(f"{field}: {msg}")

        return False, "; ".join(error_details)
    except Exception as e:
        return False, f"Unexpected validation error: {e}"


def save_config(
    config: Dict[str, Any],
    config_path: Optional[str] = None,
    expected_mtime: Optional[float] = None,
    expected_hash: Optional[str] = None,
) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Save config with validation, conflict detection, and backup.

    Returns:
        Tuple of (saved_config, conflict_message)
        conflict_message is None if no conflict

    Raises:
        ConfigurationError: If config file is not found or validation fails
        ValidationError: If config validation fails
    """
    if not config_path:
        config_path = find_config_file()

    if not config_path:
        raise ConfigurationError(
            "No config file found. Please create trellis.yml in the current directory."
        )

    if not os.path.exists(config_path):
        raise ConfigurationError(f"Config file not found: {config_path}")

    # Check for conflicts
    current_mtime = _get_file_mtime(config_path)
    current_hash = _get_file_hash(config_path)

    conflict_message = None
    if expected_mtime and expected_mtime != current_mtime:
        conflict_message = f"Config file has been modified (mtime mismatch). Current: {current_mtime}, Expected: {expected_mtime}"
    elif expected_hash and expected_hash != current_hash:
        conflict_message = "Config file has been modified (hash mismatch)"

    # Normalize config
    normalized = _normalize_nested_config(config)

    # Validate config
    is_valid, error_msg = validate_config(normalized)
    if not is_valid:
        raise CustomValidationError(f"Config validation failed: {error_msg}")

    # Create backup before overwrite
    backup_path = _create_backup(config_path)

    # Atomically write config
    _atomic_write(config_path, normalized)

    # Return saved config with new file info
    file_info = {
        "path": config_path,
        "mtime": _get_file_mtime(config_path),
        "hash": _get_file_hash(config_path),
    }

    if backup_path:
        file_info["backup_path"] = backup_path

    return normalized, conflict_message
