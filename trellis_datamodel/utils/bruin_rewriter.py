"""
@bruin block rewriter for SQL and Python source files.

Parses, modifies, and serializes @bruin YAML comment blocks inline,
preserving surrounding source code exactly.
"""

import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap


# Regex patterns matching the parser's conventions
SQL_BRUIN_PATTERN = re.compile(
    r"/\*\s*@bruin\s*\n(.*?)\n\s*@bruin\s*\*/", re.DOTALL
)
PYTHON_BRUIN_PATTERN = re.compile(
    r'"""\s*@bruin\s*\n(.*?)\n\s*@bruin\s*"""', re.DOTALL
)


def _get_pattern(file_path: str) -> re.Pattern:
    """Return the appropriate regex pattern based on file extension."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".py":
        return PYTHON_BRUIN_PATTERN
    return SQL_BRUIN_PATTERN


def _get_bruin_indent(original_content: str) -> str:
    """Extract the leading whitespace before the closing @bruin delimiter."""
    for line in reversed(original_content.splitlines(keepends=True)):
        stripped = line.strip()
        if stripped.startswith("@bruin"):
            return line[: len(line) - len(line.lstrip())]
    return ""


def _normalize_columns(columns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Map each column's 'data_type' key to 'type' (Bruin format).

    Removes 'data_type' and sets 'type' so the YAML uses the Bruin-
    expected key. If both data_type and type are present, data_type wins.
    """
    normalized = []
    for col in columns:
        entry: Dict[str, Any] = {}
        for key, value in col.items():
            if key == "data_type":
                entry["type"] = value
            else:
                entry[key] = value
        normalized.append(entry)
    return normalized


def rewrite_bruin_block(file_path: str, updates: dict) -> Path:
    """Rewrite the @bruin block in a source file with merged updates.

    Args:
        file_path: Path to the SQL or Python source file.
        updates: Dict with keys like 'description', 'tags', 'columns'.
                 Columns should have 'data_type' mapped to 'type' for Bruin format.

    Returns:
        Path to the modified file.

    Raises:
        ValueError: If no @bruin block is found in the file.
    """
    path = Path(file_path)
    original_content = path.read_text(encoding="utf-8")

    pattern = _get_pattern(str(path))
    match = pattern.search(original_content)
    if not match:
        raise ValueError("No @bruin block found in file")

    # --- Parse existing YAML with round-trip preservation ---
    yaml_rt = YAML()
    yaml_rt.preserve_quotes = True
    yaml_rt.default_flow_style = False
    yaml_rt.width = 4096
    yaml_rt.indent(mapping=2, sequence=4, offset=2)
    yaml_rt.indentless_sequences = False

    existing_yaml_str = match.group(1)
    parsed = yaml_rt.load(existing_yaml_str)
    if parsed is None:
        parsed = CommentedMap()

    # --- Apply updates ---
    if "description" in updates and updates["description"] is not None:
        parsed["description"] = updates["description"]

    if "tags" in updates and updates["tags"] is not None:
        parsed["tags"] = updates["tags"]

    if "columns" in updates and updates["columns"] is not None:
        # Map data_type → type for Bruin format
        parsed["columns"] = _normalize_columns(updates["columns"])

    # --- Serialize updated YAML back to string ---
    tmp_yaml = tempfile.NamedTemporaryFile(
        mode="w+", encoding="utf-8", suffix=".yml", delete=False
    )
    try:
        yaml_rt.dump(parsed, tmp_yaml)
        tmp_yaml.seek(0)
        new_yaml_str = tmp_yaml.read().rstrip("\n")
    finally:
        tmp_yaml.close()
        if os.path.exists(tmp_yaml.name):
            os.unlink(tmp_yaml.name)

    # --- Determine block type and replacement text ---
    is_python = os.path.splitext(str(path))[1].lower() == ".py"
    indent = _get_bruin_indent(original_content)

    if is_python:
        replacement = f'"""@bruin\n{new_yaml_str}\n{indent}@bruin"""'
    else:
        replacement = f"/* @bruin\n{new_yaml_str}\n{indent}@bruin */"

    # Replace only the first occurrence of the @bruin block
    new_content = pattern.sub(replacement, original_content, count=1)

    # --- Atomic write ---
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
            tmp_file.write(new_content)
        os.replace(tmp_path, str(path))
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    return path
