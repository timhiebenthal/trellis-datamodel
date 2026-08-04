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
SQL_BRUIN_PATTERN = re.compile(r"/\*\s*@bruin\s*\n(.*?)\n\s*@bruin\s*\*/", re.DOTALL)
PYTHON_BRUIN_PATTERN = re.compile(
    r'"""\s*@bruin\s*\n(.*?)\n\s*@bruin\s*"""', re.DOTALL
)


def _is_python(file_path: str) -> bool:
    return os.path.splitext(str(file_path))[1].lower() == ".py"


def _get_pattern(file_path: str) -> re.Pattern:
    """Return the appropriate regex pattern based on file extension."""
    if _is_python(file_path):
        return PYTHON_BRUIN_PATTERN
    return SQL_BRUIN_PATTERN


def _yaml() -> YAML:
    """A round-trip YAML instance configured to match Bruin's block style."""
    yaml_rt = YAML()
    yaml_rt.preserve_quotes = True
    yaml_rt.default_flow_style = False
    yaml_rt.width = 4096
    yaml_rt.indent(mapping=2, sequence=4, offset=2)
    yaml_rt.indentless_sequences = False
    return yaml_rt


def _dump_to_str(yaml_rt: YAML, data: Any) -> str:
    """Serialize *data* to a YAML string with no trailing newline."""
    tmp_yaml = tempfile.NamedTemporaryFile(
        mode="w+", encoding="utf-8", suffix=".yml", delete=False
    )
    try:
        yaml_rt.dump(data, tmp_yaml)
        tmp_yaml.seek(0)
        return tmp_yaml.read().rstrip("\n")
    finally:
        tmp_yaml.close()
        if os.path.exists(tmp_yaml.name):
            os.unlink(tmp_yaml.name)


def _get_bruin_indent(original_content: str) -> str:
    """Extract the leading whitespace before the closing @bruin delimiter."""
    for line in reversed(original_content.splitlines(keepends=True)):
        stripped = line.strip()
        if stripped.startswith("@bruin"):
            return line[: len(line) - len(line.lstrip())]
    return ""


def _wrap_block(yaml_str: str, is_python: bool, indent: str = "") -> str:
    """Wrap a YAML string in the @bruin delimiters for the given file type."""
    if is_python:
        return f'"""@bruin\n{yaml_str}\n{indent}@bruin"""'
    return f"/* @bruin\n{yaml_str}\n{indent}@bruin */"


def _normalize_columns(columns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Rewrite each column into Bruin's on-disk spelling.

    Trellis carries a column's type as ``data_type`` (the adapter-protocol
    spelling); Bruin writes it as ``type``. Every other key is copied through
    untouched, which is what lets Bruin-owned metadata Trellis does not model
    — ``primary_key``, ``nullable``, ``checks``, ``foreign_key`` — round-trip
    when a caller passes it back.

    Note this replaces the column list wholesale: a key the caller omits is
    pruned. That is deliberate, and is how a removed relationship's
    ``foreign_key`` gets cleaned up.
    """
    normalized = []
    for col in columns:
        entry: Dict[str, Any] = {}
        for key, value in col.items():
            if key == "data_type":
                entry["type"] = value
            else:
                entry[key] = value
        # A None type would serialize as `type:` with an empty value, which
        # Bruin reads as a typeless column — drop it instead.
        if entry.get("type") is None:
            entry.pop("type", None)
        normalized.append(entry)
    return normalized


def _atomic_write(path: Path, content: str) -> None:
    """Write *content* to *path* atomically, within the same directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
            tmp_file.write(content)
        os.replace(tmp_path, str(path))
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


def rewrite_bruin_block(file_path: str, updates: dict) -> Path:
    """Rewrite the @bruin block in a source file with merged updates.

    Args:
        file_path: Path to the SQL or Python source file.
        updates: Dict with keys like 'description', 'tags', 'columns'.
                 Columns may use either 'data_type' or 'type'.

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
    yaml_rt = _yaml()
    parsed = yaml_rt.load(match.group(1))
    if parsed is None:
        parsed = CommentedMap()

    # --- Apply updates ---
    if updates.get("description") is not None:
        parsed["description"] = updates["description"]

    if updates.get("tags") is not None:
        parsed["tags"] = updates["tags"]

    if updates.get("columns") is not None:
        parsed["columns"] = _normalize_columns(updates["columns"])

    new_yaml_str = _dump_to_str(yaml_rt, parsed)

    replacement = _wrap_block(
        new_yaml_str,
        is_python=_is_python(str(path)),
        indent=_get_bruin_indent(original_content),
    )

    # Replace only the first occurrence of the @bruin block. Escape the
    # replacement so backslashes and \g-style sequences in user YAML are not
    # interpreted as regex group references.
    new_content = pattern.sub(lambda _m: replacement, original_content, count=1)

    _atomic_write(path, new_content)
    return path


def write_bruin_asset(file_path: str, asset: dict, sql_body: str) -> Path:
    """Create a new asset file carrying an @bruin block.

    Used when Trellis pushes drafted fields for an entity that has no asset in
    the pipeline yet. The body is a placeholder the user must fill in — Trellis
    cannot know the asset's query — so keep it obviously unfinished.

    Args:
        file_path: Destination path; parent directories are created. ``.py``
            yields a docstring-delimited block, anything else a SQL comment one.
        asset: The @bruin block contents (``name``, ``type``, ``columns``, ...).
            ``columns`` is normalized to Bruin's spelling.
        sql_body: Source body written below the block.

    Returns:
        Path to the created file.

    Raises:
        FileExistsError: If the destination already exists. Scaffolding never
            overwrites a user's asset; the caller should merge into it instead.
    """
    path = Path(file_path)
    if path.exists():
        raise FileExistsError(
            f"Refusing to scaffold over an existing asset file: {file_path}"
        )

    block = CommentedMap()
    for key, value in asset.items():
        block[key] = _normalize_columns(value) if key == "columns" else value

    yaml_rt = _yaml()
    body = sql_body if sql_body.endswith("\n") else f"{sql_body}\n"
    content = (
        _wrap_block(_dump_to_str(yaml_rt, block), is_python=_is_python(str(path)))
        + "\n"
        + body
    )

    _atomic_write(path, content)
    return path
