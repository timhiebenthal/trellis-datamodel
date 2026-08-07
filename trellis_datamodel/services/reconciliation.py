"""
Provenance-aware reconciliation of framework manifest columns into data_model.yml.

Governing rule: the active framework's materialized model wins over a
drafted concept.
- manifest_columns=None means the model is absent from a (possibly partial)
  manifest — the non-destructive invariant applies: existing fields untouched.
- Reconciliation is idempotent: reconciling an already-reconciled model
  returns the identical field list and changed=False.
"""

from __future__ import annotations

import copy
import os
from typing import Any

import yaml

from trellis_datamodel.models.entity_keys import (
    get_framework_tags,
    get_model_ref,
    set_framework_tags,
    set_model_ref,
    set_physical_datatype,
)


# ---------------------------------------------------------------------------
# dbt type → DraftedField datatype mapping
# ---------------------------------------------------------------------------

_INT_PREFIXES = (
    "int",
    "bigint",
    "smallint",
    "tinyint",
    "byteint",
    "serial",
    "bigserial",
    "smallserial",
    "integer",
)
_FLOAT_PREFIXES = ("float", "double", "real", "money")
_BOOL_PREFIXES = ("bool",)
_DATE_EXACT = {"date"}
_TIMESTAMP_PREFIXES = ("timestamp", "datetime")
_TEXT_PREFIXES = (
    "varchar",
    "char",
    "text",
    "string",
    "nvarchar",
    "nchar",
    "clob",
    "uuid",
)

# Fixed-point families whose bucket depends on the declared scale: a scale of 0
# is an integer (Snowflake's NUMBER(38,0) is the canonical case), anything else
# — including an unparameterized NUMBER, where the catalog does not report the
# scale — is treated as float, the wider of the two buckets.
_NUMERIC_BASES = ("number", "numeric", "decimal", "dec", "bignumeric")

_ORIGIN_SEPARATOR = " | Origin: "
_ORIGIN_PREFIX = "Origin: "


def _parse_description_with_origin(
    raw_description: str | None,
) -> tuple[str | None, str | None]:
    """Split a description into (description, origin).

    The write paths embed origin into the description as:
      - "desc | Origin: value"  (both present)
      - "Origin: value"         (only origin, no description)

    This reverses that encoding so origin round-trips through a
    dedicated field.
    """
    if not raw_description:
        return raw_description, None

    sep_idx = raw_description.find(_ORIGIN_SEPARATOR)
    if sep_idx != -1:
        desc = raw_description[:sep_idx]
        origin = raw_description[sep_idx + len(_ORIGIN_SEPARATOR) :]
        return (desc or None), (origin or None)

    if raw_description.startswith(_ORIGIN_PREFIX):
        origin = raw_description[len(_ORIGIN_PREFIX) :]
        return None, (origin or None)

    return raw_description, None


def _split_column_type(column_type: str) -> tuple[str, list[str]]:
    """Split a raw warehouse type into its lowercase base name and parameters.

    "NUMBER(38,0)" -> ("number", ["38", "0"])
    "VARCHAR(16777216)" -> ("varchar", ["16777216"])
    "TIMESTAMP_NTZ" -> ("timestamp_ntz", [])

    Collection wrappers (ARRAY, STRUCT<...>, "int[]") are deliberately left
    intact so they fall through to "unknown" rather than being flattened to
    the bucket of their element type.
    """
    t = column_type.lower().strip()
    open_paren = t.find("(")
    if open_paren == -1:
        return t, []
    base = t[:open_paren].strip()
    inner = t[open_paren + 1 :].rstrip().removesuffix(")")
    return base, [arg.strip() for arg in inner.split(",") if arg.strip()]


def _map_column_type(column_type: str | None) -> str:
    """Map a framework/warehouse column type string to a DraftedField datatype enum value."""
    if not column_type:
        return "unknown"
    t, args = _split_column_type(column_type)
    if t.endswith("[]") or t.startswith(("array", "struct", "map")) or "<" in t:
        # Collection / nested types have no scalar bucket — don't collapse them
        # onto their element type.
        return "unknown"
    if t in _NUMERIC_BASES:
        return "int" if len(args) >= 2 and args[1] == "0" else "float"
    if t in _DATE_EXACT:
        return "date"
    for prefix in _TIMESTAMP_PREFIXES:
        if t.startswith(prefix):
            return "timestamp"
    for prefix in _BOOL_PREFIXES:
        if t.startswith(prefix):
            return "bool"
    for prefix in _INT_PREFIXES:
        if t.startswith(prefix):
            return "int"
    for prefix in _FLOAT_PREFIXES:
        if t.startswith(prefix):
            return "float"
    for prefix in _TEXT_PREFIXES:
        if t.startswith(prefix):
            return "text"
    return "unknown"


# ---------------------------------------------------------------------------
# Pure reconciliation core
# ---------------------------------------------------------------------------

def reconcile_entity_fields(
    existing_fields: list[dict[str, Any]],
    manifest_columns: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """
    Merge manifest columns into existing drafted_fields with provenance.

    Args:
        existing_fields: Current drafted_fields list from data_model.yml.
        manifest_columns: Column list from the manifest for the bound model,
            or None when the model is absent from the manifest (non-destructive).

    Returns:
        Reconciled field list. Order: dbt fields (manifest order) then
        surviving draft fields (original order).
    """
    if manifest_columns is None:
        # Model absent from manifest — non-destructive, return unchanged.
        return existing_fields

    # Index existing fields by name for O(1) lookup
    existing_by_name: dict[str, dict[str, Any]] = {}
    for field in existing_fields:
        name = field.get("name")
        if name:
            existing_by_name[name] = field

    manifest_names: set[str] = set()
    result: list[dict[str, Any]] = []

    for col in manifest_columns:
        col_name = col.get("name")
        if not col_name:
            continue
        manifest_names.add(col_name)

        # Start from existing entry to preserve extra keys (e.g. origin, roles)
        existing = existing_by_name.get(col_name, {})
        field: dict[str, Any] = dict(existing)

        # dbt is authoritative for these attributes
        field["name"] = col_name
        field["datatype"] = _map_column_type(col.get("type"))
        field["source"] = "dbt"
        # Preserve the exact warehouse/adapter type (e.g. "varchar") alongside
        # the coarse UI bucket above, so pushing back to the adapter doesn't
        # downgrade a precise type to the bucket's generic default (#111).
        set_physical_datatype(field, col.get("type"))
        desc = col.get("description")
        if desc is not None:
            # Parse origin from description if embedded
            parsed_desc, parsed_origin = _parse_description_with_origin(desc)
            field["description"] = parsed_desc
            if parsed_origin is not None:
                field["origin"] = parsed_origin
            elif "origin" in field:
                # Remove stale origin if description no longer contains it
                del field["origin"]
        elif "description" not in field:
            pass  # keep absent rather than writing None

        result.append(field)

    # Append surviving draft fields (those not matched by any manifest column)
    for field in existing_fields:
        name = field.get("name")
        if name and name not in manifest_names:
            result.append(field)

    return result


def reconcile_entity_tags(
    existing_tags: list[str],
    manifest_tags: list[str] | None,
) -> list[str]:
    """The active framework is authoritative for the mirrored `framework_tags` field.
    manifest_tags=None -> model absent from manifest, non-destructive (unchanged).
    manifest_tags=[] (present, no tags) -> mirrored tags cleared.
    """
    if manifest_tags is None:
        return existing_tags
    return list(manifest_tags)


def compute_display_tags(entity: dict[str, Any]) -> list[str]:
    """The tag list to show/export for an entity — never persisted.

    Bound entities: the union of `framework_tags` (framework-owned,
    reconcile-refreshed) and `ui_tags` (user-added via the Trellis tag
    editor), deduplicated, framework_tags first. Unbound entities have no
    schema.yml to mirror — `tags` is their single, freely-editable,
    already-authoritative field.
    """
    if get_model_ref(entity):
        framework_tags = get_framework_tags(entity)
        ui_tags = entity.get("ui_tags") or []
        seen: set[str] = set()
        result: list[str] = []
        for tag in [*framework_tags, *ui_tags]:
            if tag not in seen:
                seen.add(tag)
                result.append(tag)
        return result
    return entity.get("tags") or []


def reconcile_data_model(
    data_model: dict[str, Any],
    manifest_models: list[dict[str, Any]],
) -> tuple[dict[str, Any], bool]:
    """
    Apply reconcile_entity_fields to each bound entity in the data model.

    Args:
        data_model: Parsed data_model.yml content.
        manifest_models: List of model dicts from get_models() (each has
            unique_id, name, columns).

    Returns:
        (reconciled_data_model, changed) where changed is True only if at
        least one entity's field list was modified.
    """
    # Index manifest by unique_id for O(1) lookup
    manifest_by_id: dict[str, list[dict[str, Any]]] = {}
    manifest_tags_by_id: dict[str, list[str]] = {}
    for model in manifest_models:
        uid = model.get("unique_id")
        if uid:
            manifest_by_id[uid] = model.get("columns") or []
            manifest_tags_by_id[uid] = model.get("tags") or []

    result = copy.deepcopy(data_model)
    changed = False

    for entity in result.get("entities", []):
        model_ref = get_model_ref(entity)
        if not model_ref:
            continue  # unbound — untouched

        # None signals model absent from manifest (non-destructive)
        manifest_columns = manifest_by_id.get(model_ref, None)
        if model_ref not in manifest_by_id:
            manifest_columns = None

        existing = entity.get("drafted_fields") or []
        reconciled = reconcile_entity_fields(existing, manifest_columns)

        if reconciled != existing:
            entity["drafted_fields"] = reconciled
            changed = True

        manifest_tags = manifest_tags_by_id.get(model_ref) if model_ref in manifest_by_id else None
        legacy_tags = entity.get("tags") or []
        existing_framework_tags = get_framework_tags(entity)
        reconciled_framework_tags = reconcile_entity_tags(existing_framework_tags, manifest_tags)

        # One-time migration: a bound entity's legacy `tags` value (from
        # before the framework_tags/ui_tags split existed) is folded into
        # ui_tags ONLY if it represents real legacy/user-curated data — i.e.
        # it differs from what framework reconciliation says right now. A
        # value that already matches is the framework's own tag list from an
        # earlier run under the old field name, not something the user
        # added, and must NOT be copied into ui_tags (that would wrongly
        # mark the framework's tags as Trellis-authored and defeat the
        # read-only/removable UI split). The legacy `tags` key itself is
        # always retired afterward — bound entities never persist `tags`
        # going forward, only framework_tags/ui_tags.
        if "tags" in entity:
            if (
                "ui_tags" not in entity
                and legacy_tags
                and legacy_tags != reconciled_framework_tags
            ):
                entity["ui_tags"] = list(legacy_tags)
            del entity["tags"]
            changed = True

        if reconciled_framework_tags != existing_framework_tags:
            changed = True

        # Normalize key spellings (migrates any legacy dbt_model/dbt_tags
        # keys onto model_ref/framework_tags) even when values are unchanged.
        set_model_ref(entity, model_ref)
        set_framework_tags(entity, reconciled_framework_tags)

    return result, changed


# ---------------------------------------------------------------------------
# IO wrapper
# ---------------------------------------------------------------------------

def reconcile_framework() -> tuple[dict[str, Any], bool]:
    """
    Load manifest + data_model.yml, reconcile, write back if changed.

    Returns:
        (data_model, changed) — the (possibly updated) data model dict and
        whether the file was rewritten. A missing, empty, or unparseable
        manifest is a safe no-op.
    """
    from trellis_datamodel import config as cfg
    from trellis_datamodel.adapters import get_adapter
    from trellis_datamodel.utils.yaml_handler import YamlHandler

    data_model_path = getattr(cfg, "DATA_MODEL_PATH", None)
    if not data_model_path or not os.path.exists(data_model_path):
        return {}, False

    try:
        with open(data_model_path, "r") as f:
            data_model = yaml.safe_load(f) or {}
    except Exception:
        return {}, False

    # Load manifest models — guard against missing/broken manifest
    try:
        adapter = get_adapter()
        manifest_models = adapter.get_models()
    except Exception:
        return data_model, False

    if not manifest_models:
        return data_model, False

    reconciled, changed = reconcile_data_model(data_model, manifest_models)

    if changed:
        handler = YamlHandler()
        handler.save_file(data_model_path, reconciled)

    return reconciled, changed
