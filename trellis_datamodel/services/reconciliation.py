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
from collections.abc import Mapping
from typing import Any

from trellis_datamodel.models.entity_keys import (
    get_framework_tags,
    get_model_ref,
    set_framework_tags,
    set_model_ref,
    set_physical_datatype,
)
# compute_display_tags and reconcile_entity_tags are re-exported: tests import
# them from here.
from trellis_datamodel.services.tag_ownership import (
    compute_display_tags,  # noqa: F401
    migrate_legacy_tags,
    reconcile_entity_tags,
)
from trellis_datamodel.utils.column_metadata import resolve_column_metadata
from trellis_datamodel.utils.sql_types import classify_sql_type
from trellis_datamodel.utils.structured_data import load_yaml_or_json


def _timed_phase(name: str):
    """Resolve timing from the live observability module after config reloads."""
    from trellis_datamodel import observability

    return observability.timed_phase(name)


# ---------------------------------------------------------------------------
# dbt type → DraftedField datatype mapping
# ---------------------------------------------------------------------------

def _map_column_type(column_type: str | None) -> str:
    """Map a framework/warehouse column type string to a DraftedField datatype enum value."""
    resolved = classify_sql_type(column_type)
    return resolved.bucket if resolved else "unknown"


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
        Reconciled field list. Order: the fields already in the data model
        keep their position; materialized columns the data model doesn't have
        yet are appended in manifest order. The manifest is authoritative for
        a field's content, never for where it sits - re-deriving the order
        from the manifest on every boot silently undid whatever the user
        arranged, and rewrote data_model.yml on each page load (see #152).
    """
    if manifest_columns is None:
        # Model absent from manifest — non-destructive, return unchanged.
        return existing_fields

    manifest_by_name: dict[str, dict[str, Any]] = {}
    manifest_order: list[str] = []
    for col in manifest_columns:
        col_name = col.get("name")
        if not col_name or col_name in manifest_by_name:
            continue
        manifest_by_name[col_name] = col
        manifest_order.append(col_name)

    result: list[dict[str, Any]] = []
    placed: set[str] = set()

    # Index existing fields by name for O(1) lookup
    existing_by_name: dict[str, dict[str, Any]] = {}
    for field in existing_fields:
        name = field.get("name")
        if name:
            existing_by_name[name] = field

    def reconcile_field(name: str, col: Mapping[str, Any]) -> dict[str, Any]:
        # Start from existing entry to preserve extra keys (e.g. origin, roles)
        field: dict[str, Any] = dict(existing_by_name.get(name, {}))

        # dbt is authoritative for these attributes
        field["name"] = name
        field["datatype"] = _map_column_type(col.get("type"))
        field["source"] = "dbt"
        # Preserve the exact warehouse/adapter type (e.g. "varchar") alongside
        # the coarse UI bucket above, so pushing back to the adapter doesn't
        # downgrade a precise type to the bucket's generic default (#111).
        set_physical_datatype(field, col.get("type"))
        desc = col.get("description")
        parsed_desc, origin = resolve_column_metadata(col)
        if desc is not None:
            field["description"] = parsed_desc
        if origin:
            field["origin"] = origin
        elif desc is not None and "origin" in field:
            # No source (meta, resolved origin, description) carries origin
            # anymore: drop the stale one.
            del field["origin"]
        placed.add(name)
        return field

    # Index existing fields by name for O(1) lookup
    existing_by_name: dict[str, dict[str, Any]] = {}
    for field in existing_fields:
        name = field.get("name")
        if name:
            existing_by_name[name] = field

    # Existing fields keep their position; drafts survive untouched.
    for field in existing_fields:
        name = field.get("name")
        if not name:
            continue
        col = manifest_by_name.get(name)
        if col is None:
            result.append(field)
            placed.add(name)
        else:
            result.append(reconcile_field(name, col))

    # Materialized columns the data model doesn't know yet, in manifest order.
    for name in manifest_order:
        if name in placed:
            continue
        result.append(reconcile_field(name, manifest_by_name[name]))

    return result


def _snapshot_columns(
    model: Mapping[str, Any],
    unique_id: str,
    schema_index: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    """Normalize an indexed schema into the columns reconciliation consumes."""
    model_columns = model.get("columns") or []
    if isinstance(model_columns, Mapping):
        model_columns_by_name = {
            name: column
            for name, column in model_columns.items()
            if isinstance(name, str) and isinstance(column, Mapping)
        }
        model_column_items = list(model_columns_by_name.items())
    elif isinstance(model_columns, (list, tuple)):
        model_column_items = [
            (column.get("name"), column)
            for column in model_columns
            if isinstance(column, Mapping) and column.get("name")
        ]
        model_columns_by_name = dict(model_column_items)
    else:
        model_column_items = []
        model_columns_by_name = {}

    indexed_columns = schema_index.get(unique_id) if schema_index else None
    if isinstance(indexed_columns, Mapping):
        column_items = [
            (name, column)
            for name, column in indexed_columns.items()
            if isinstance(name, str) and isinstance(column, Mapping)
        ]
    elif isinstance(indexed_columns, (list, tuple)):
        column_items = [
            (column.get("name"), column)
            for column in indexed_columns
            if isinstance(column, Mapping) and column.get("name")
        ]
    else:
        column_items = model_column_items

    columns: list[dict[str, Any]] = []
    for column_name, indexed_column in column_items:
        if not column_name:
            continue
        model_column = model_columns_by_name.get(column_name, {})
        normalized = dict(model_column) if isinstance(model_column, Mapping) else {}
        normalized.update(indexed_column)
        normalized["name"] = normalized.get("name") or column_name
        if "type" not in normalized and "data_type" in normalized:
            normalized["type"] = normalized["data_type"]
        if normalized.get("description") is None and normalized.get("comment") is not None:
            normalized["description"] = normalized["comment"]
        columns.append(normalized)
    return columns


def _models_from_snapshot_indexes(
    model_index: Mapping[str, Any] | None,
    schema_index: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    """Build the legacy model-list contract from immutable snapshot indexes."""
    model_items = list(model_index.items()) if isinstance(model_index, Mapping) else []
    if not model_items and isinstance(schema_index, Mapping):
        model_items = [(unique_id, {}) for unique_id in schema_index]

    models: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index_key, raw_model in model_items:
        if not isinstance(raw_model, Mapping):
            continue
        unique_id = raw_model.get("unique_id") or index_key
        if not isinstance(unique_id, str) or unique_id in seen_ids:
            continue
        seen_ids.add(unique_id)
        model = dict(raw_model)
        model["unique_id"] = unique_id
        model["columns"] = _snapshot_columns(model, unique_id, schema_index)
        models.append(model)
    return models


def reconcile_data_model(
    data_model: dict[str, Any],
    manifest_models: list[dict[str, Any]] | None = None,
    *,
    snapshot: Any | None = None,
    model_index: Mapping[str, Any] | None = None,
    schema_index: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], bool]:
    """
    Apply reconcile_entity_fields to each bound entity in the data model.

    Args:
        data_model: Parsed data_model.yml content.
        manifest_models: List of model dicts from get_models() (each has
            unique_id, name, columns). When snapshot indexes are supplied,
            this argument is not required.
        snapshot: Optional artifact snapshot exposing model_index and
            schema_index.
        model_index: Optional indexed model metadata from an artifact snapshot.
        schema_index: Optional indexed column metadata from an artifact snapshot.

    Returns:
        (reconciled_data_model, changed) where changed is True only if at
        least one entity's field list was modified.
    """
    if snapshot is not None:
        model_index = model_index if model_index is not None else getattr(
            snapshot, "model_index", None
        )
        schema_index = schema_index if schema_index is not None else getattr(
            snapshot, "schema_index", None
        )

    with _timed_phase("model_index"):
        if model_index is not None or schema_index is not None:
            manifest_models = _models_from_snapshot_indexes(model_index, schema_index)
        else:
            manifest_models = manifest_models or []

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
        existing_framework_tags = get_framework_tags(entity)
        reconciled_framework_tags = reconcile_entity_tags(existing_framework_tags, manifest_tags)

        if migrate_legacy_tags(entity, reconciled_framework_tags):
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

def reconcile_framework(
    snapshot: Any | None = None,
    *,
    model_index: Mapping[str, Any] | None = None,
    schema_index: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], bool]:
    """Reconcile framework metadata while timing the service boundary."""
    with _timed_phase("reconciliation"):
        return _reconcile_framework(
            snapshot=snapshot,
            model_index=model_index,
            schema_index=schema_index,
        )


def _reconcile_framework(
    *,
    snapshot: Any | None = None,
    model_index: Mapping[str, Any] | None = None,
    schema_index: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], bool]:
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
        with _timed_phase("data_model_read"):
            data_model = load_yaml_or_json(data_model_path) or {}
    except Exception:
        return {}, False

    # A caller that already loaded the shared snapshot can supply its indexes
    # directly. This avoids both adapter lookup and reopening artifacts.
    if snapshot is not None:
        model_index = model_index if model_index is not None else getattr(
            snapshot, "model_index", None
        )
        schema_index = schema_index if schema_index is not None else getattr(
            snapshot, "schema_index", None
        )

    if model_index is not None or schema_index is not None:
        manifest_models = None
    else:
        # Load manifest models — guard against missing/broken manifest
        try:
            with _timed_phase("model_index"):
                adapter = get_adapter()
                manifest_models = adapter.get_models()
        except Exception:
            return data_model, False

    if not manifest_models and model_index is None and schema_index is None:
        return data_model, False

    reconciled, changed = reconcile_data_model(
        data_model,
        manifest_models,
        snapshot=snapshot,
        model_index=model_index,
        schema_index=schema_index,
    )

    if changed:
        handler = YamlHandler()
        handler.save_file(data_model_path, reconciled)

    return reconciled, changed
