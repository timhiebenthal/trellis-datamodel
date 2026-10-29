"""
Config service for managing trellis.yml through the API.

Handles loading, validation, conflict detection, and atomic writes.
"""

import hashlib
import logging
import os
import re
from datetime import datetime
from io import StringIO
from pathlib import Path, PureWindowsPath
from typing import Any, Dict, Optional, Tuple
import json
from enum import Enum

from pydantic import ValidationError
from ruamel.yaml.comments import CommentedMap

from trellis_datamodel.config import resolve_config_path
from trellis_datamodel.exceptions import (
    ConfigurationError,
    FileOperationError,
    ValidationError as CustomValidationError,
)
from trellis_datamodel.models.schemas import (
    ConfigSchema,
    ExposuresLayoutEnum,
    FrameworkEnum,
    ModelingStyleEnum,
    StartPageEnum,
    ConfigSchemaResponse,
    ConfigFieldMetadata,
)
from trellis_datamodel.utils.atomic_write import atomic_write
from trellis_datamodel.utils.structured_data import load_yaml_file
from trellis_datamodel.utils.yaml_handler import round_trip_yaml

logger = logging.getLogger(__name__)


def _schema_default(path: str) -> Any:
    """Default for a dotted trellis.yml key, read from the pydantic schema."""
    node: Any = ConfigSchema()
    for part in path.split("."):
        # `ossie.source.schema` is exposed as `schema_name` (see OssieSourceConfig).
        node = getattr(node, "schema_name" if part == "schema" else part)
    if isinstance(node, Enum):
        return node.value
    return list(node) if isinstance(node, list) else node



# Define field metadata for UI
_FIELD_DEFINITIONS: Dict[str, ConfigFieldMetadata] = {
    "framework": ConfigFieldMetadata(
        type="enum",
        enum_values=[e.value for e in FrameworkEnum],
        default=_schema_default("framework"),
        required=True,
        description="Transformation framework",
        beta=False,
    ),
    "start_page": ConfigFieldMetadata(
        type="enum",
        enum_values=[e.value for e in StartPageEnum],
        default=_schema_default("start_page"),
        required=False,
        description="Project default for the root route only; explicit routes remain authoritative",
        beta=False,
    ),
    "canvas.default_filters.domains": ConfigFieldMetadata(
        type="list",
        default=_schema_default("canvas.default_filters.domains"),
        required=False,
        description="Project-wide default Canvas domain filters, not per-user preferences",
        beta=False,
    ),
    "canvas.default_filters.tags": ConfigFieldMetadata(
        type="list",
        default=_schema_default("canvas.default_filters.tags"),
        required=False,
        description="Project-wide default Canvas tag filters, not per-user preferences",
        beta=False,
    ),
    "modeling_style": ConfigFieldMetadata(
        type="enum",
        enum_values=[e.value for e in ModelingStyleEnum],
        default=_schema_default("modeling_style"),
        required=True,
        description="Modeling style approach",
        beta=False,
    ),
    "dbt_project_path": ConfigFieldMetadata(
        type="string",
        default=_schema_default("dbt_project_path"),
        required=False,
        description="Path to dbt project directory (relative or absolute)",
        beta=False,
    ),
    "dbt_manifest_path": ConfigFieldMetadata(
        type="string",
        default=_schema_default("dbt_manifest_path"),
        required=False,
        description="Path to manifest.json (relative to project or absolute)",
        beta=False,
    ),
    "dbt_catalog_path": ConfigFieldMetadata(
        type="string",
        default=_schema_default("dbt_catalog_path"),
        required=False,
        description="Path to catalog.json (relative to project or absolute)",
        beta=False,
    ),
    "data_model_file": ConfigFieldMetadata(
        type="string",
        default=_schema_default("data_model_file"),
        required=False,
        description="Path where data model YAML will be saved",
        beta=False,
    ),
    "dbt_model_paths": ConfigFieldMetadata(
        type="list",
        default=_schema_default("dbt_model_paths"),
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
    "bruin_pipeline_path": ConfigFieldMetadata(
        type="string",
        default=_schema_default("bruin_pipeline_path"),
        required=False,
        description="Path to Bruin pipeline directory holding pipeline.yml and assets/ (relative or absolute)",
        beta=False,
    ),
    "bruin_asset_paths": ConfigFieldMetadata(
        type="list",
        default=_schema_default("bruin_asset_paths"),
        required=False,
        description="Subdirectories under assets/ to include (filters Bruin assets)",
        beta=False,
    ),
    "bruin_default_asset_type": ConfigFieldMetadata(
        type="string",
        default=_schema_default("bruin_default_asset_type"),
        required=False,
        description="Asset type used when Trellis scaffolds a new Bruin asset (e.g. bq.sql, sf.sql)",
        beta=False,
    ),
    "lineage.enabled": ConfigFieldMetadata(
        type="boolean",
        default=_schema_default("lineage.enabled"),
        required=False,
        description="Enable lineage visualization",
        beta=True,
    ),
    "lineage.layers": ConfigFieldMetadata(
        type="list",
        default=_schema_default("lineage.layers"),
        required=False,
        description="Ordered list of folder names to organize lineage into layers",
        beta=True,
    ),
    "entity_creation_guidance.enabled": ConfigFieldMetadata(
        type="boolean",
        default=_schema_default("entity_creation_guidance.enabled"),
        required=False,
        description="Enable entity creation wizard",
        beta=False,
    ),
    "entity_creation_guidance.push_warning_enabled": ConfigFieldMetadata(
        type="boolean",
        default=_schema_default("entity_creation_guidance.push_warning_enabled"),
        required=False,
        description="Show push-to-dbt warnings",
        beta=False,
    ),
    "entity_creation_guidance.min_description_length": ConfigFieldMetadata(
        type="integer",
        default=_schema_default("entity_creation_guidance.min_description_length"),
        required=False,
        description="Minimum description length for entity creation",
        beta=False,
    ),
    "entity_creation_guidance.disabled_guidance": ConfigFieldMetadata(
        type="list",
        default=_schema_default("entity_creation_guidance.disabled_guidance"),
        required=False,
        description="List of guidance features to disable",
        beta=False,
    ),
    "exposures.enabled": ConfigFieldMetadata(
        type="boolean",
        default=_schema_default("exposures.enabled"),
        required=False,
        description="Enable exposures tracking and visualization",
        beta=True,
    ),
    "exposures.default_layout": ConfigFieldMetadata(
        type="enum",
        enum_values=[e.value for e in ExposuresLayoutEnum],
        default=_schema_default("exposures.default_layout"),
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
        default=_schema_default("business_events.enabled"),
        required=False,
        description="Enable business events modeling with BEAM* methodology",
        beta=True,
    ),
    "business_events.file": ConfigFieldMetadata(
        type="string",
        default=_schema_default("business_events.file"),
        required=False,
        description="Path to business events YAML file (defaults to business_events.yml in data model directory)",
        beta=True,
    ),
    "ossie.enabled": ConfigFieldMetadata(
        type="boolean",
        default=_schema_default("ossie.enabled"),
        required=False,
        description="Enable Apache Ossie semantic model export alongside framework pushes",
        beta=True,
    ),
    "ossie.file": ConfigFieldMetadata(
        type="string",
        default=_schema_default("ossie.file"),
        required=False,
        description="Path to the Ossie semantic model file (defaults to semantic_model.yml beside the data model)",
        beta=True,
    ),
    "ossie.source.database": ConfigFieldMetadata(
        type="string",
        default=_schema_default("ossie.source.database"),
        required=False,
        description=(
            "Database segment for Ossie dataset names; empty omits the database segment. "
            "Adapter-derived values come from the last dbt run's target, so set this field to override them."
        ),
        beta=True,
    ),
    "ossie.source.schema": ConfigFieldMetadata(
        type="string",
        default=_schema_default("ossie.source.schema"),
        required=False,
        description="Schema segment override for Ossie dataset names; empty uses the adapter-derived schema",
        beta=True,
    ),
    "metrics.enabled": ConfigFieldMetadata(
        type="boolean",
        default=_schema_default("metrics.enabled"),
        required=False,
        description="Enable the metric tree canvas and metric emission on push",
        beta=True,
    ),
    "metrics.file": ConfigFieldMetadata(
        type="string",
        default=_schema_default("metrics.file"),
        required=False,
        description="Path to the metric tree file (defaults to metric_tree.yml beside the data model)",
        beta=True,
    ),
    "metrics.expression_dialect": ConfigFieldMetadata(
        type="enum",
        enum_values=["ANSI_SQL", "OSSIE_SQL_2026"],
        default=_schema_default("metrics.expression_dialect"),
        required=False,
        description="Dialect label emitted with each metric expression; it is not validated against the SQL",
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
    "ossie.enabled",
    "ossie.file",
    "ossie.source.database",
    "ossie.source.schema",
    "metrics.enabled",
    "metrics.file",
    "metrics.expression_dialect",
]

# Dialects the metric tree may emit. A label, not a parser: nothing validates
# the SQL against it.
_METRICS_DIALECTS = ["ANSI_SQL", "OSSIE_SQL_2026"]


# Top-level keys _normalize_nested_config owns; anything else in trellis.yml is
# left alone on save.
_MANAGED_KEYS = (
    "framework",
    "modeling_style",
    "start_page",
    "dbt_project_path",
    "dbt_manifest_path",
    "dbt_catalog_path",
    "data_model_file",
    "dbt_model_paths",
    "dbt_company_dummy_path",
    "bruin_pipeline_path",
    "bruin_asset_paths",
    "bruin_default_asset_type",
    "canvas",
    "lineage",
    "entity_creation_guidance",
    "exposures",
    "business_events",
    "ossie",
    "dimensional_modeling",
    "entity_modeling",
)


# Fields whose value becomes a file the server writes. A hand-edited trellis.yml
# may point them anywhere; a value arriving over HTTP may not escape the project.
_WRITE_PATH_FIELDS = (
    ("data_model_file",),
    ("business_events", "file"),
    ("ossie", "file"),
)


def _nested_get(config: Any, path: Tuple[str, ...]) -> Any:
    for key in path:
        if not isinstance(config, dict):
            return None
        config = config.get(key)
    return config


def _escapes_project(value: str) -> bool:
    """True for an absolute path or one with a `..` segment, on any OS."""
    if os.path.isabs(value) or PureWindowsPath(value).is_absolute():
        return True
    return ".." in re.split(r"[\\/]+", value)


def _unsafe_write_paths(
    normalized: Dict[str, Any], current: Dict[str, Any]
) -> list[str]:
    """
    Name the write-path fields that were changed to an absolute or `..` path.

    A value already in the file is left alone, so an existing config that
    reaches outside its directory stays saveable from the UI.
    """
    problems = []
    for path in _WRITE_PATH_FIELDS:
        value = _nested_get(normalized, path)
        if (
            isinstance(value, str)
            and _escapes_project(value)
            and value != _nested_get(current, path)
        ):
            problems.append(".".join(path))
    return problems


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
        "start_page",
        "dbt_project_path",
        "dbt_manifest_path",
        "dbt_catalog_path",
        "data_model_file",
        "dbt_model_paths",
        "dbt_company_dummy_path",
        "bruin_pipeline_path",
        "bruin_asset_paths",
        "bruin_default_asset_type",
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
    # Canvas navigation and project defaults
    if "canvas" in config:
        canvas = config["canvas"]
        filters = canvas.get("default_filters") if isinstance(canvas, dict) else {}
        if not isinstance(filters, dict):
            filters = {}

        def normalize_filter_values(value: Any) -> list[str]:
            if not isinstance(value, list):
                return []
            return [
                item.strip()
                for item in value
                if isinstance(item, str) and item.strip()
            ]

        normalized["canvas"] = {
            "default_filters": {
                "domains": normalize_filter_values(filters.get("domains")),
                "tags": normalize_filter_values(filters.get("tags")),
            }
        }

    # Lineage
    if "lineage" in config:
        lineage = config["lineage"]
        if isinstance(lineage, dict):
            normalized["lineage"] = {
                "enabled": bool(lineage.get("enabled", _schema_default("lineage.enabled"))),
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
                "enabled": bool(
                    guidance.get(
                        "enabled", _schema_default("entity_creation_guidance.enabled")
                    )
                ),
                "push_warning_enabled": bool(
                    guidance.get(
                        "push_warning_enabled",
                        _schema_default("entity_creation_guidance.push_warning_enabled"),
                    )
                ),
                "min_description_length": int(
                    guidance.get(
                        "min_description_length",
                        _schema_default("entity_creation_guidance.min_description_length"),
                    )
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
            layout_default = _schema_default("exposures.default_layout")
            layout = exposures.get("default_layout", layout_default)
            if layout not in [e.value for e in ExposuresLayoutEnum]:
                layout = layout_default
            normalized["exposures"] = {
                "enabled": bool(exposures.get("enabled", _schema_default("exposures.enabled"))),
                "default_layout": layout,
            }

    # Business Events
    if "business_events" in config:
        business_events = config["business_events"]
        if isinstance(business_events, dict):
            normalized["business_events"] = {
                "enabled": bool(
                    business_events.get("enabled", _schema_default("business_events.enabled"))
                ),
                "file": business_events.get("file", _schema_default("business_events.file")),
            }

    # Ossie export. Only emitted when the file already declares the block, the
    # way the other optional sections behave: an unrelated config save must not
    # inject an opt-in feature into a version-controlled trellis.yml. A
    # malformed value falls back to the defaults instead of raising.
    if "ossie" in config:
        ossie = config.get("ossie")
        if not isinstance(ossie, dict):
            ossie = {}
        ossie_source = ossie.get("source")
        if not isinstance(ossie_source, dict):
            ossie_source = {}

        def as_str(value: Any) -> str:
            return value if isinstance(value, str) else ""

        normalized["ossie"] = {
            "enabled": bool(ossie.get("enabled", _schema_default("ossie.enabled"))),
            "file": as_str(ossie.get("file")),
            "source": {
                "database": as_str(ossie_source.get("database")),
                "schema": as_str(ossie_source.get("schema")),
            },
        }

    # Metric tree. Same guard as Ossie: only emitted when the file already
    # declares the block, so an unrelated save cannot inject an opt-in feature
    # into a version-controlled trellis.yml. A malformed value falls back to
    # the defaults instead of raising.
    if "metrics" in config:
        metrics = config.get("metrics")
        if not isinstance(metrics, dict):
            metrics = {}

        dialect_default = _schema_default("metrics.expression_dialect")
        dialect = metrics.get("expression_dialect", dialect_default)
        if dialect not in _METRICS_DIALECTS:
            dialect = dialect_default

        def metrics_str(value: Any) -> str:
            return value if isinstance(value, str) else ""

        normalized["metrics"] = {
            "enabled": bool(metrics.get("enabled", _schema_default("metrics.enabled"))),
            "file": metrics_str(metrics.get("file")),
            "expression_dialect": dialect,
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

    # Check bruin_pipeline_path
    pipeline_path = config.get("bruin_pipeline_path", "")
    if pipeline_path:
        full_pipeline = (
            pipeline_path
            if os.path.isabs(pipeline_path)
            else os.path.abspath(os.path.join(base_dir, pipeline_path))
        )
        if not os.path.exists(full_pipeline):
            messages.append(f"bruin_pipeline_path does not exist: {full_pipeline}")

        # Check asset paths (relative to the pipeline's assets/; warning only,
        # since a filter may also match a deeper subdirectory)
        for asset_path in config.get("bruin_asset_paths") or []:
            full_asset = os.path.abspath(
                os.path.join(full_pipeline, "assets", asset_path)
            )
            if not os.path.exists(full_asset):
                messages.append(
                    f"Warning: bruin_asset_paths entry does not exist: {full_asset}"
                )

    return messages



def _merge_into_document(raw: Any, normalized: Dict[str, Any]) -> Any:
    """
    Merge the normalized config into the document read from disk.

    Keys the normalizer owns are set, or removed when it left them out. Keys it
    does not know are kept untouched, along with comments and key order.
    """
    if not isinstance(raw, CommentedMap):
        raw = CommentedMap()

    for key in _MANAGED_KEYS:
        if key not in normalized:
            raw.pop(key, None)
    for key, value in normalized.items():
        current = raw.get(key)
        if isinstance(value, dict) and isinstance(current, CommentedMap):
            _merge_into_document(current, value)
        elif current != value:
            raw[key] = value
    return raw


def render_config(text: str, normalized: Dict[str, Any]) -> str:
    """Merge the normalized config into trellis.yml text and return the new text."""
    ryaml = round_trip_yaml()
    document = _merge_into_document(ryaml.load(text), normalized)
    out = StringIO()
    ryaml.dump(document, out)
    return out.getvalue()


def _atomic_write(config_path: str, normalized: Dict[str, Any]) -> None:
    """
    Atomically write config to file, merged into the existing document so
    unknown keys, comments and key order survive.

    The file is replaced atomically and ends up owner-only (0600).
    """
    try:
        with open(config_path, "r") as f:
            rendered = render_config(f.read(), normalized)
    except Exception as e:
        raise ConfigurationError(f"Failed to read config file: {e}")

    try:
        atomic_write(config_path, rendered, mode=0o600)
    except Exception as e:
        raise FileOperationError(f"Failed to write config: {e}") from e
    logger.info(f"Atomically wrote config to: {config_path}")


def get_schema_metadata() -> ConfigSchemaResponse:
    """
    Get schema metadata for the config UI.

    Returns field definitions and list of beta flags.
    """
    return ConfigSchemaResponse(fields=_FIELD_DEFINITIONS, beta_flags=_BETA_FIELDS)


def require_config_path(config_path: Optional[str] = None) -> str:
    """Resolve the trellis.yml to operate on, raising if there isn't one."""
    resolved = resolve_config_path(config_path)

    if not resolved:
        raise ConfigurationError(
            "No config file found. Please create trellis.yml in the current directory."
        )

    if not os.path.exists(resolved):
        raise ConfigurationError(f"Config file not found: {resolved}")

    return resolved


def read_config(
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
    config_path = require_config_path(config_path)

    try:
        config = load_yaml_file(config_path, {})
    except Exception as e:
        raise ConfigurationError(f"Failed to read config file: {e}")
    if not isinstance(config, dict):
        raise ConfigurationError(
            "Failed to read config file: expected a mapping of settings at the top level"
        )

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
    Save config with validation, conflict detection, and atomic write.

    Returns:
        Tuple of (saved_config, conflict_message)
        conflict_message is None if no conflict

    Raises:
        ConfigurationError: If config file is not found or unreadable
        ValidationError: If config validation fails
        FileOperationError: If the config file cannot be written
    """
    config_path = require_config_path(config_path)

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

    try:
        current = load_yaml_file(config_path, {})
    except Exception as e:
        raise ConfigurationError(f"Failed to read config file: {e}")
    unsafe = _unsafe_write_paths(normalized, current)
    if unsafe:
        raise CustomValidationError(
            f"{', '.join(unsafe)}: must be a path inside the project "
            "(no absolute paths or '..'); edit trellis.yml directly to point outside it"
        )

    # A conflict leaves the file as it is; omitting the expected mtime/hash is
    # how the caller forces the overwrite.
    if conflict_message:
        return normalized, conflict_message

    # Atomically write config
    _atomic_write(config_path, normalized)

    return normalized, None
