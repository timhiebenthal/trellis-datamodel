"""
Provenance-aware reconciliation of dbt manifest columns into data_model.yml.

Governing rule: when Trellis and dbt disagree, dbt is right.
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


# ---------------------------------------------------------------------------
# dbt type → DraftedField datatype mapping
# ---------------------------------------------------------------------------

_INT_PREFIXES = ("int", "bigint", "smallint", "tinyint", "serial", "integer")
_FLOAT_PREFIXES = ("float", "double", "numeric", "decimal", "real", "money")
_BOOL_PREFIXES = ("bool",)
_DATE_EXACT = {"date"}
_TIMESTAMP_PREFIXES = ("timestamp", "datetime")
_TEXT_PREFIXES = ("varchar", "char", "text", "string", "nvarchar", "nchar", "clob")

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


def _map_dbt_type(dbt_type: str | None) -> str:
    """Map a dbt/warehouse column type string to a DraftedField datatype enum value."""
    if not dbt_type:
        return "unknown"
    t = dbt_type.lower().strip()
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
        field["datatype"] = _map_dbt_type(col.get("type"))
        field["source"] = "dbt"
        raw_type = col.get("type")
        if raw_type:
            # Preserve the exact warehouse/dbt type (e.g. "varchar") alongside
            # the coarse UI bucket above, so pushing back to dbt doesn't
            # downgrade a precise type to the bucket's generic default (#111).
            field["dbt_data_type"] = raw_type
        elif "dbt_data_type" in field:
            del field["dbt_data_type"]
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
    for model in manifest_models:
        uid = model.get("unique_id")
        if uid:
            manifest_by_id[uid] = model.get("columns") or []

    result = copy.deepcopy(data_model)
    changed = False

    for entity in result.get("entities", []):
        dbt_model = entity.get("dbt_model")
        if not dbt_model:
            continue  # unbound — untouched

        # None signals model absent from manifest (non-destructive)
        manifest_columns = manifest_by_id.get(dbt_model, None)
        if dbt_model not in manifest_by_id:
            manifest_columns = None

        existing = entity.get("drafted_fields") or []
        reconciled = reconcile_entity_fields(existing, manifest_columns)

        if reconciled != existing:
            entity["drafted_fields"] = reconciled
            changed = True

    return result, changed


# ---------------------------------------------------------------------------
# IO wrapper
# ---------------------------------------------------------------------------

def reconcile_dbt() -> tuple[dict[str, Any], bool]:
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
