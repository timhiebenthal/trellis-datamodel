"""Fast loading for JSON-shaped YAML files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


def load_yaml_or_json(path: str | Path) -> Any:
    """Load a YAML file, using the faster JSON parser for JSON-shaped input."""
    text = Path(path).read_text()
    if text.lstrip().startswith(("{", "[")):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
    return yaml.safe_load(text)
