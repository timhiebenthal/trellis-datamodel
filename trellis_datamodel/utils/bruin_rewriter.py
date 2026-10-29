"""
Rewriter for Bruin asset definitions.

Parses, modifies, and serializes @bruin YAML comment blocks inline,
preserving surrounding source code exactly. A standalone ``*.asset.yml`` asset
is rewritten as a whole YAML document with the same round-trip guarantees.
"""

import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from trellis_datamodel.utils.atomic_write import atomic_write
from trellis_datamodel.utils.bruin_parser import (
    block_pattern,
    is_python_asset,
    is_yaml_asset,
)
from trellis_datamodel.utils.bruin_yaml import bruin_yaml


# Bruin's own `Asset` struct orders the block's fields (bruin-data/bruin
# `pkg/pipeline/pipeline.go`) and its writer groups `description` in the top
# header, right after `name`/`type`. ruamel appends a key it has not seen
# before, so a freshly pushed `description` used to land below `columns`. This
# is the order new keys are placed in; keys the block already carries keep their
# own position and comments.
_BRUIN_KEY_ORDER = (
    "name",
    "type",
    "enabled",
    "description",
    "start_date",
    "connection",
    "tags",
    "domains",
    "meta",
    "materialization",
    "depends",
    "columns",
    "custom_checks",
    "routing",
    "secrets",
    "parameters",
    "hooks",
)
_KEY_RANK = {key: index for index, key in enumerate(_BRUIN_KEY_ORDER)}


def _rank(key: str) -> int:
    return _KEY_RANK.get(key, len(_BRUIN_KEY_ORDER))


def _insert_index(parsed: CommentedMap, rank: int) -> int:
    """Index where a key of *rank* belongs in Bruin's field order."""
    for index, existing in enumerate(parsed):
        if _rank(existing) > rank:
            return index
    return len(parsed)


_BODY_RANK = _KEY_RANK["columns"]


def _follows_the_body(ranks_before: "Iterable[int]", rank: int) -> bool:
    """True when a header key (rank above the body) trails the column body.

    Only that pattern is stale: a pre-#149 push appended a new key at the very
    end of the block, so the file carries ``description`` below ``columns`` and
    in-place updates keep it there forever. Anything else - ``connection``
    before ``description``, say - is a hand-arranged but sensible layout and
    must never be churned.
    """
    return rank < _BODY_RANK and any(earlier >= _BODY_RANK for earlier in ranks_before)


def _is_misplaced(parsed: CommentedMap, key: str) -> bool:
    """True when *key* sits below the column body in *parsed*.

    Relocating such a key on push heals the file; keys above the body are
    never touched, so well-formed blocks see no churn.
    """
    rank = _rank(key)
    ranks_before: "list[int]" = []
    for existing in parsed:
        if existing == key:
            return _follows_the_body(ranks_before, rank)
        ranks_before.append(_rank(existing))
    return False


def misplaced_header_keys(keys: "Iterable[str]") -> "list[str]":
    """Header keys in *keys* that sit below the column body.

    Same rule the rewriter enforces on write, exposed so callers that see a
    block only as its key list (the asset parser keeps no positions) can
    detect a stale push layout: a pre-#149 push left ``description`` below
    ``columns`` with the value already in sync, and value-diff-only updates
    never moved it.
    """
    misplaced: "list[str]" = []
    ranks_before: "list[int]" = []
    for key in keys:
        if _follows_the_body(ranks_before, _rank(key)):
            misplaced.append(key)
        ranks_before.append(_rank(key))
    return misplaced


def _set_key(parsed: CommentedMap, key: str, value: Any) -> None:
    """Assign *key* to *parsed*, placing it in Bruin's field order.

    An existing key keeps its position - and any comment on it - as long as
    that position respects the canonical order; only its value changes. A new
    key is inserted at the index of the first existing key that comes after
    it, so a pushed description sits in the header instead of being appended
    below ``columns``. An existing key that is provably out of order (stale
    position from an older push) is relocated to the same spot.
    """
    if key in parsed:
        parsed[key] = value
        if not _is_misplaced(parsed, key):
            return
        del parsed[key]
    parsed.insert(_insert_index(parsed, _rank(key)), key, value)


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


def _replace_meta(parsed: CommentedMap, meta: Dict[str, Any]) -> None:
    """Make the asset-level `meta` equal *meta*, editing the existing map in
    place so comments on the keys that stay are kept. An empty *meta* drops
    the key altogether rather than leaving `meta: {}` behind. A `meta` key
    left below `columns` by a pre-#149 push is relocated like any other
    misplaced header key."""
    if not meta:
        parsed.pop("meta", None)
        return
    current = parsed.get("meta")
    if not isinstance(current, dict):
        current = CommentedMap()
        _set_key(parsed, "meta", current)
    for key in [key for key in current if key not in meta]:
        del current[key]
    for key, value in meta.items():
        if current.get(key) != value:
            current[key] = value
    if "meta" in parsed and _is_misplaced(parsed, "meta"):
        del parsed["meta"]
        parsed.insert(_insert_index(parsed, _rank("meta")), "meta", current)


def _atomic_write(path: Path, content: str) -> None:
    """Write an asset file atomically, UTF-8, owner-only permissions (0600)."""
    atomic_write(path, content, encoding="utf-8", mode=0o600)


def _apply_updates(yaml_rt: YAML, yaml_str: str, updates: dict) -> str:
    """Load *yaml_str* round-trip, apply *updates* and return the new YAML."""
    parsed = yaml_rt.load(yaml_str)
    if parsed is None:
        parsed = CommentedMap()

    if updates.get("description") is not None:
        _set_key(parsed, "description", updates["description"])

    if updates.get("tags") is not None:
        _set_key(parsed, "tags", updates["tags"])

    if updates.get("columns") is not None:
        parsed["columns"] = _normalize_columns(updates["columns"])

    if updates.get("meta") is not None:
        _replace_meta(parsed, updates["meta"])

    return _dump_to_str(yaml_rt, parsed)


def rewrite_bruin_block(file_path: str, updates: dict) -> Path:
    """Rewrite an asset's definition with merged updates.

    Args:
        file_path: Path to the SQL or Python source file, or to a standalone
                   ``.asset.yml``/``.asset.yaml`` file (rewritten whole).
        updates: Dict with keys like 'description', 'tags', 'columns',
                 'meta'.
                 Columns may use either 'data_type' or 'type'.

    Returns:
        Path to the modified file.

    Raises:
        ValueError: If no @bruin block is found in a source file.
    """
    path = Path(file_path)
    original_content = path.read_text(encoding="utf-8")
    yaml_rt = bruin_yaml()

    if is_yaml_asset(str(path)):
        new_yaml_str = _apply_updates(yaml_rt, original_content, updates)
        _atomic_write(path, f"{new_yaml_str}\n")
        return path

    pattern = block_pattern(str(path))
    match = pattern.search(original_content)
    if not match:
        raise ValueError("No @bruin block found in file")

    new_yaml_str = _apply_updates(yaml_rt, match.group(1), updates)

    replacement = _wrap_block(
        new_yaml_str,
        is_python=is_python_asset(str(path)),
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

    yaml_rt = bruin_yaml()
    body = sql_body if sql_body.endswith("\n") else f"{sql_body}\n"
    content = (
        _wrap_block(_dump_to_str(yaml_rt, block), is_python=is_python_asset(str(path)))
        + "\n"
        + body
    )

    _atomic_write(path, content)
    return path
