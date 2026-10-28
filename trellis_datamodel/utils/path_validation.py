"""
Path validation utilities for trellis.yml paths.

Centralizes validation logic to avoid duplication across routes and services.
"""

import os
import re
from pathlib import Path

from trellis_datamodel import config as cfg
from trellis_datamodel.exceptions import ConfigurationError, ValidationError


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


# Model names become file names (`<models_dir>/<name>.yml`, a Bruin asset's
# `<name>.sql`), so they may not carry a path separator or `..`. Dots stay
# allowed for Bruin's `schema.asset` names, hyphens for dbt file-named models.
_MODEL_NAME_PATTERN = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.\-]*")


def validate_model_name(model_name: str) -> str:
    """
    Validate that a model name is safe to turn into a file name.

    Raises:
        ValidationError: If the name is empty, contains a path separator or
            any character outside letters, digits, `_`, `.` and `-`, or `..`
    """
    if not _MODEL_NAME_PATTERN.fullmatch(model_name or "") or ".." in model_name:
        raise ValidationError(
            f"Invalid model name '{model_name}': use letters, digits, '_', '.' "
            "or '-', with no path separators or '..'"
        )
    return model_name
