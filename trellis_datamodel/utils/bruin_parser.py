"""Parser for @bruin comment blocks in SQL and Python source files."""

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

# Regex patterns for extracting YAML from @bruin blocks
# SQL: /* @bruin\n...\n@bruin */
SQL_BRUIN_PATTERN = re.compile(
    r"/\*\s*@bruin\s*\n(.*?)\n\s*@bruin\s*\*/",
    re.DOTALL,
)
# Python: """@bruin\n...\n@bruin"""
PYTHON_BRUIN_PATTERN = re.compile(
    r'"""\s*@bruin\s*\n(.*?)\n\s*@bruin\s*"""',
    re.DOTALL,
)


@dataclass
class BruinAsset:
    """Represents a parsed @bruin asset block."""

    name: str = ""
    type: str = ""
    connection: str = ""
    depends: list[str] = field(default_factory=list)
    materialization: dict = field(default_factory=dict)
    columns: list[dict] = field(default_factory=list)
    description: str = ""
    tags: list[str] = field(default_factory=list)
    custom_checks: list[dict] = field(default_factory=list)
    file_path: str = ""


def _detect_pattern(file_path: str) -> Optional[re.Pattern]:
    """Return the appropriate regex pattern based on file extension."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".sql":
        return SQL_BRUIN_PATTERN
    elif ext == ".py":
        return PYTHON_BRUIN_PATTERN
    return None


def parse_bruin_block(file_path: str) -> Optional[BruinAsset]:
    """Parse a @bruin block from a SQL or Python file.

    Args:
        file_path: Path to the source file.

    Returns:
        A BruinAsset if a valid @bruin block is found and parsed, or None.
    """
    pattern = _detect_pattern(file_path)
    if pattern is None:
        return None

    try:
        with open(file_path, "r") as f:
            content = f.read()
    except (FileNotFoundError, IOError) as e:
        logger.warning("Failed to read file %s: %s", file_path, e)
        return None

    match = pattern.search(content)
    if match is None:
        return None

    yaml_str = match.group(1).strip()
    if not yaml_str:
        return None

    try:
        data = yaml.safe_load(yaml_str)
    except yaml.YAMLError as e:
        logger.warning(
            "Malformed YAML in @bruin block in %s: %s", file_path, e
        )
        return None

    if not isinstance(data, dict):
        logger.warning(
            "Malformed @bruin block in %s: YAML did not produce a mapping", file_path
        )
        return None

    return BruinAsset(
        name=data.get("name", ""),
        type=data.get("type", ""),
        connection=data.get("connection", ""),
        depends=data.get("depends", []),
        materialization=data.get("materialization", {}),
        columns=data.get("columns", []),
        description=data.get("description", ""),
        tags=data.get("tags", []),
        custom_checks=data.get("custom_checks", []),
        file_path=file_path,
    )


def scan_pipeline_assets(
    pipeline_path: str, asset_paths: list[str]
) -> list[BruinAsset]:
    """Scan a pipeline's assets directory for @bruin blocks.

    Walks ``pipeline_path/assets/`` recursively and parses each ``.sql`` and
    ``.py`` file.  When ``asset_paths`` is non-empty, only files whose relative
    subdirectory (under ``assets/``) matches one of the given path fragments are
    included.

    Args:
        pipeline_path: Root directory of the pipeline.
        asset_paths: List of subdirectory names to filter by (e.g.
            ``["01_clean"]``).  Empty list means *all* assets.

    Returns:
        Sorted list of :class:`BruinAsset` instances (sorted by ``name``).
    """
    assets_dir = os.path.join(pipeline_path, "assets")
    if not os.path.isdir(assets_dir):
        return []

    discovered: list[BruinAsset] = []

    for dirpath, _dirnames, filenames in os.walk(assets_dir):
        # Determine the relative subdirectory under assets/
        rel_dir = os.path.relpath(dirpath, assets_dir)

        # When asset_paths is non-empty, skip dirs that don't match
        if asset_paths:
            # rel_dir is "." for the root assets/ dir itself — always skip that
            if rel_dir == ".":
                continue
            # Match if any component of rel_dir is in asset_paths
            parts = rel_dir.replace(os.sep, "/").split("/")
            if not any(p in asset_paths for p in parts):
                continue

        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            if ext not in (".sql", ".py"):
                continue

            file_path = os.path.join(dirpath, filename)
            try:
                asset = parse_bruin_block(file_path)
                if asset is not None:
                    discovered.append(asset)
            except Exception as e:
                logger.warning(
                    "Error parsing @bruin block in %s: %s", file_path, e
                )

    discovered.sort(key=lambda a: a.name)
    return discovered
