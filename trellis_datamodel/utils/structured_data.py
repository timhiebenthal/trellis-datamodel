"""Fast loading for JSON-shaped YAML files."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


def load_yaml_or_json(path: str | Path) -> Any:
    """Load a YAML file, using the faster JSON parser for JSON-shaped input."""
    text = Path(path).read_text()
    if text.lstrip().startswith(("{", "[")):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
    return yaml.safe_load(text)


def load_data_model_file(path: str | Path | None) -> dict[str, Any]:
    """Load the data model file, returning ``{}`` if it is unset, missing or unreadable."""
    if not path or not os.path.exists(path):
        return {}
    try:
        return load_yaml_or_json(path) or {}
    except Exception as e:
        logger.warning("Could not load data model: %s", e)
        return {}
