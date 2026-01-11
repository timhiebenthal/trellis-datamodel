"""
Path validation utilities for trellis.yml and dbt project paths.

Centralizes validation logic to avoid duplication across routes and services.
"""

import os
from pathlib import Path

from trellis_datamodel import config as cfg
from trellis_datamodel.exceptions import ConfigurationError, FileOperationError, ValidationError


def validate_dbt_project_path() -> str:
    """
    Validate that dbt_project_path is configured and exists.

    Returns:
        The validated dbt_project_path

    Raises:
        ConfigurationError: If path is not configured or doesn't exist
    """
    if not cfg.DBT_PROJECT_PATH:
        raise ConfigurationError(
            "dbt_project_path is not configured. Please set it in trellis.yml"
        )

    if not os.path.exists(cfg.DBT_PROJECT_PATH):
        raise ConfigurationError(
            f"dbt_project_path does not exist: {cfg.DBT_PROJECT_PATH}"
        )

    return cfg.DBT_PROJECT_PATH


def validate_manifest_path() -> str:
    """
    Validate that manifest_path is configured and exists.

    Returns:
        The validated manifest_path

    Raises:
        ConfigurationError: If path is not configured
        FileOperationError: If path doesn't exist
    """
    if not cfg.MANIFEST_PATH or cfg.MANIFEST_PATH == "":
        raise ConfigurationError(
            "dbt_manifest_path is not configured. Please set it in trellis.yml"
        )

    if not os.path.exists(cfg.MANIFEST_PATH):
        raise FileOperationError(
            f"Manifest not found at {cfg.MANIFEST_PATH}. "
            "Please ensure manifest.json exists (run 'dbt compile' or 'dbt run')."
        )

    return cfg.MANIFEST_PATH


def validate_catalog_path() -> str | None:
    """
    Validate that catalog_path exists if configured.

    Returns:
        The validated catalog_path, or None if not configured

    Raises:
        FileOperationError: If path is configured but doesn't exist
    """
    if not cfg.CATALOG_PATH:
        return None

    if not os.path.exists(cfg.CATALOG_PATH):
        raise FileOperationError(
            f"Catalog not found at {cfg.CATALOG_PATH}. "
            "Please run 'dbt docs generate' to create catalog.json."
        )

    return cfg.CATALOG_PATH


def validate_data_model_path() -> str:
    """
    Validate that data_model_path is configured.

    Returns:
        The validated data_model_path

    Raises:
        ConfigurationError: If path is not configured
    """
    if not cfg.DATA_MODEL_PATH:
        raise ConfigurationError(
            "data_model_file is not configured. Please set it in trellis.yml"
        )

    return cfg.DATA_MODEL_PATH


def ensure_data_model_path_exists() -> str:
    """
    Ensure data_model_path exists, creating parent directories if needed.

    Returns:
        The validated data_model_path

    Raises:
        ConfigurationError: If path is not configured
        FileOperationError: If directory creation fails
    """
    path = validate_data_model_path()

    parent_dir = os.path.dirname(path)
    if parent_dir and not os.path.exists(parent_dir):
        try:
            os.makedirs(parent_dir, exist_ok=True)
        except OSError as e:
            raise FileOperationError(
                f"Failed to create directory for data_model.yml: {e}"
            ) from e

    return path


def ensure_canvas_layout_path_exists() -> str:
    """
    Ensure canvas_layout_path exists, creating parent directories if needed.

    Returns:
        The validated canvas_layout_path

    Raises:
        ConfigurationError: If path is not configured
        FileOperationError: If directory creation fails
    """
    if not cfg.CANVAS_LAYOUT_PATH:
        raise ConfigurationError(
            "canvas_layout_file is not configured. Please set it in trellis.yml"
        )

    parent_dir = os.path.dirname(cfg.CANVAS_LAYOUT_PATH)
    if parent_dir and not os.path.exists(parent_dir):
        try:
            os.makedirs(parent_dir, exist_ok=True)
        except OSError as e:
            raise FileOperationError(
                f"Failed to create directory for canvas_layout.yml: {e}"
            ) from e

    return cfg.CANVAS_LAYOUT_PATH


def validate_path_is_safe(path: str, base_dir: str) -> Path:
    """
    Validate that a path is safe (doesn't escape base_dir).

    Args:
        path: Path to validate (can be relative or absolute)
        base_dir: Base directory that path must be within

    Returns:
        Resolved Path object

    Raises:
        ValidationError: If path escapes base_dir
    """
    from trellis_datamodel.exceptions import ValidationError

    # Resolve to absolute path
    if os.path.isabs(path):
        resolved = Path(path).resolve()
    else:
        resolved = (Path(base_dir) / path).resolve()

    base = Path(base_dir).resolve()

    try:
        # Check if resolved path is within base directory
        resolved.relative_to(base)
    except ValueError:
        raise ValidationError(
            f"Path '{path}' is outside base directory '{base_dir}'"
        )

    return resolved
