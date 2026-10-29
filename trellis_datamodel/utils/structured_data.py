"""Load and save plain-data YAML files (data model, business events, config, ...).

These helpers return plain Python data. Edits that must keep a file's comments,
quoting and key order go through :mod:`trellis_datamodel.utils.yaml_handler`
instead.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

import yaml

from trellis_datamodel.utils.atomic_write import atomic_write

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


def load_yaml_file(path: Optional[str | Path], default: Any = None) -> Any:
    """Load a YAML file, treating a missing file as *default*.

    Contract:
        - *path* unset (``None``/``""``) or not an existing file -> *default*.
        - empty document (or one that parses to a falsy value) -> *default*.
        - unreadable file -> ``OSError``; malformed YAML -> ``yaml.YAMLError``.
          Both propagate untranslated so each caller keeps its own error type.
    """
    if not path or not Path(path).exists():
        return default
    return load_yaml_or_json(path) or default


def try_load_yaml_file(path: Optional[str | Path], default: Any = None) -> Any:
    """Like :func:`load_yaml_file`, but a file that cannot be read or parsed is
    logged as a warning and yields *default* instead of raising.

    For best-effort reads where a broken file must not fail the request.
    """
    try:
        return load_yaml_file(path, default)
    except Exception as e:
        logger.warning("Could not load %s: %s", path, e)
        return default


def save_yaml_file(path: str | Path, data: Any) -> None:
    """Write plain *data* to *path* as block-style YAML, keeping key order.

    The write is atomic (see :func:`trellis_datamodel.utils.atomic_write.atomic_write`)
    and creates missing parent directories. Errors propagate untranslated.
    """
    atomic_write(path, yaml.safe_dump(data, default_flow_style=False, sort_keys=False))


def load_data_model_file(path: str | Path | None) -> dict[str, Any]:
    """Load the data model file, returning ``{}`` if it is unset, missing or unreadable."""
    try:
        return load_yaml_file(path, {})
    except Exception as e:
        logger.warning("Could not load data model: %s", e)
        return {}
