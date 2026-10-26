"""Apache Ossie semantic model exporter.

Writes one flat `0.2.0.dev0` document from the entities bound in
`data_model.yml`. The spec is a draft, so the version is pinned in one constant
and the whole mapping lives here rather than leaking into routes or adapters.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import trellis_datamodel.config as cfg
from trellis_datamodel.adapters.base import ColumnSchema, ModelInfo, ModelSchema
from trellis_datamodel.models.entity_keys import (
    get_model_ref,
    get_physical_datatype,
)
from trellis_datamodel.services.fk_placement import place_foreign_key
from trellis_datamodel.utils.yaml_handler import YamlHandler

OSSIE_VERSION = "0.2.0.dev0"
FIELD_DIALECT = "ANSI_SQL"
DEFAULT_FILENAME = "semantic_model.yml"

# Portable logical types. Anything absent here is omitted rather than guessed;
# `Opaque` is reserved for known types outside this vocabulary.
_SQL_TYPE_MAP: dict[str, str] = {
    "varchar": "String",
    "char": "String",
    "text": "String",
    "string": "String",
    "integer": "Integer",
    "int": "Integer",
    "bigint": "Integer",
    "smallint": "Integer",
    "decimal": "Decimal",
    "numeric": "Decimal",
    "number": "Decimal",
    "float": "Float",
    "double": "Float",
    "real": "Float",
    "boolean": "Boolean",
    "bool": "Boolean",
    "date": "Date",
    "time": "Time",
    "timestamp": "DateTime",
    "datetime": "DateTime",
    "timestamp_ntz": "DateTime",
    "timestamp_tz": "DateTimeTz",
    "timestamptz": "DateTimeTz",
    "timestamp_ltz": "DateTimeTz",
}

# Trellis's logical buckets, used for drafted fields without a usable
# physical type. `unknown` is intentionally absent so the key is omitted.
_BUCKET_TYPE_MAP: dict[str, str] = {
    "text": "String",
    "int": "Integer",
    "float": "Float",
    "bool": "Boolean",
    "date": "Date",
    "timestamp": "DateTime",
}

_TIME_DATATYPES = frozenset({"Date", "Time", "DateTime", "DateTimeTz"})


@dataclass
class OssieExport:
    """Result of an export: the written path (None if nothing was written)."""

    path: Path | None
    warnings: list[str] = field(default_factory=list)


def _normalise_type(raw: str | None) -> str:
    """Lowercase a warehouse type and drop precision/scale, e.g. numeric(38,0)."""
    value = (raw or "").strip().lower()
    if "(" in value:
        value = value.split("(", 1)[0].strip()
    return value


def _ossie_datatype(sql_type: str | None) -> str | None:
    return _SQL_TYPE_MAP.get(_normalise_type(sql_type))


def _drafted_datatype(drafted: dict[str, Any]) -> str | None:
    """Prefer a recognised physical type, else map the logical bucket."""
    physical = get_physical_datatype(drafted)
    mapped = _ossie_datatype(physical) if physical else None
    if mapped:
        return mapped
    bucket = _normalise_type(drafted.get("datatype"))
    return _BUCKET_TYPE_MAP.get(bucket)


def _build_field(
    name: str, datatype: str | None, description: str | None
) -> dict[str, Any]:
    field: dict[str, Any] = {
        "name": name,
        "expression": {
            "dialects": [
                {"dialect": FIELD_DIALECT, "expression": name},
            ]
        },
    }
    if datatype:
        field["datatype"] = datatype
    # Emitted explicitly so a temporal column can opt out of time-dimension
    # treatment without relying on the schema default.
    field["dimension"] = {"is_time": datatype in _TIME_DATATYPES}
    if description:
        field["description"] = description
    return field


def _build_fields(
    entity: dict[str, Any], model: ModelInfo
) -> list[dict[str, Any]]:
    """Model columns in order, then drafted-only fields sorted by name."""
    fields: list[dict[str, Any]] = []
    seen: set[str] = set()

    for column in model.get("columns") or []:
        name = (column.get("name") or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        fields.append(
            _build_field(
                name,
                _ossie_datatype(column.get("type")),
                column.get("description"),
            )
        )

    drafted_only: list[dict[str, Any]] = []
    for drafted in entity.get("drafted_fields") or []:
        name = (drafted.get("name") or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        drafted_only.append(drafted)

    for drafted in sorted(drafted_only, key=lambda f: (f.get("name") or "").strip()):
        name = drafted["name"].strip()
        fields.append(
            _build_field(
                name,
                _drafted_datatype(drafted),
                drafted.get("description"),
            )
        )

    return fields


def _build_source(model: ModelInfo) -> str:
    """Join non-empty database, schema and table segments."""
    config = cfg.OSSIE_CONFIG
    database = (config.database or "").strip()
    schema = (config.schema or "").strip() or (model.get("schema") or "").strip()
    table = (model.get("table") or "").strip() or (model.get("name") or "").strip()
    return ".".join(part for part in (database, schema, table) if part)


def _test_names(column: ColumnSchema) -> set[str]:
    """Test names on a dbt-shaped column, dict- or string-shaped."""
    names: set[str] = set()
    for test in column.get("data_tests") or []:
        if isinstance(test, dict):
            names.update(str(key).strip().lower() for key in test)
        elif isinstance(test, str):
            names.add(test.strip().lower())
    return names


def _is_key_candidate(column: ColumnSchema) -> bool:
    """Bruin's `primary_key: true`, or dbt's unique *and* not_null pair.

    `unique` alone does not identify rows, so it is not a candidate.
    """
    if column.get("primary_key") is True:
        return True
    names = _test_names(column)
    return "unique" in names and "not_null" in names


def _key_candidates(
    entity_id: str,
    schema: ModelSchema | None,
    relationships: list[dict],
) -> list[str]:
    """Distinct candidate field names, metadata first, then the FK fallback."""
    candidates: list[str] = []
    for column in (schema or {}).get("columns") or []:
        name = (column.get("name") or "").strip()
        if name and name not in candidates and _is_key_candidate(column):
            candidates.append(name)

    if candidates:
        return candidates

    # No framework metadata: the referenced side of an inbound relationship is
    # the only evidence of uniqueness available.
    for relationship in relationships:
        placement = place_foreign_key(
            relationship.get("type") or "",
            relationship.get("source") or "",
            relationship.get("source_field") or "",
            relationship.get("target") or "",
            relationship.get("target_field") or "",
        )
        if placement.ref_entity != entity_id:
            continue
        name = (placement.ref_field or "").strip()
        if name and name not in candidates:
            candidates.append(name)
    return candidates


def _key_entries(candidates: list[str]) -> dict[str, Any]:
    """One candidate is the primary key; independent candidates are unique keys.

    A multi-element `primary_key` would mean one composite key, which is not
    what independent unique columns describe.
    """
    if len(candidates) == 1:
        return {"primary_key": [candidates[0]]}
    if candidates:
        return {"unique_keys": [[candidate] for candidate in candidates]}
    return {}


def _build_dataset(
    entity: dict[str, Any],
    entity_id: str,
    model: ModelInfo,
    model_schemas: dict[str, ModelSchema] | None,
    relationships: list[dict],
) -> dict[str, Any]:
    dataset: dict[str, Any] = {
        "name": (model.get("name") or model.get("unique_id") or "").strip(),
        "source": _build_source(model),
    }
    description = entity.get("description")
    if description:
        dataset["description"] = description

    fields = _build_fields(entity, model)
    field_names = {field["name"] for field in fields}
    schema = (model_schemas or {}).get(model.get("unique_id") or "")
    candidates = [
        candidate
        for candidate in _key_candidates(entity_id, schema, relationships)
        if candidate in field_names
    ]
    dataset.update(_key_entries(candidates))

    dataset["fields"] = fields
    return dataset


def _relationship_label(relationship: dict[str, Any]) -> str:
    """Identify a relationship by its endpoint entity ids, for warning text."""
    source = (relationship.get("source") or "").strip()
    target = (relationship.get("target") or "").strip()
    rel_type = (relationship.get("type") or "").strip() or "untyped"
    return f'relationship "{source}" -> "{target}" ({rel_type})'


def _endpoint_problem(
    entity_id: str,
    role: str,
    label: str,
    emitted: dict[str, str],
    entities_by_id: dict[str, dict[str, Any]],
) -> str | None:
    """Why a relationship endpoint produced no dataset, or None when it did."""
    if entity_id in emitted:
        return None
    entity = entities_by_id.get(entity_id)
    if entity is None:
        return (
            f'{label} skipped: {role} entity "{entity_id}" is not in the data model'
        )
    model_ref = get_model_ref(entity)
    if not model_ref:
        return (
            f'{label} skipped: {role} entity "{entity_id}" is a draft entity '
            "(no model_ref)"
        )
    return (
        f'{label} skipped: {role} entity "{entity_id}" references model '
        f'"{model_ref}", which the adapter does not report'
    )


def _build_relationships(
    entities: list[dict],
    relationships: list[dict],
    emitted: dict[str, str],
    field_names: dict[str, set[str]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Orient, filter, deduplicate and name every relationship worth emitting.

    `emitted` maps an entity id to the dataset name actually written, and
    `field_names` maps that same entity id to its dataset's field names. A
    relationship survives only when both endpoints became datasets, both field
    names are present, and both fields are declared: Ossie resolves column
    lists against declared fields, so a dangling name is a hard error upstream.
    """
    warnings: list[str] = []
    entities_by_id = {
        (entity.get("id") or "").strip(): entity for entity in entities
    }

    entries: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()

    for relationship in relationships:
        label = _relationship_label(relationship)
        source = (relationship.get("source") or "").strip()
        target = (relationship.get("target") or "").strip()

        problem = _endpoint_problem(source, "source", label, emitted, entities_by_id)
        if problem is None:
            problem = _endpoint_problem(
                target, "target", label, emitted, entities_by_id
            )
        if problem is not None:
            warnings.append(problem)
            continue

        source_field = (relationship.get("source_field") or "").strip()
        target_field = (relationship.get("target_field") or "").strip()
        missing = [
            name
            for name, value in (
                ("source_field", source_field),
                ("target_field", target_field),
            )
            if not value
        ]
        if missing:
            warnings.append(f"{label} skipped: {' and '.join(missing)} is empty")
            continue

        placement = place_foreign_key(
            relationship.get("type") or "",
            source,
            source_field,
            target,
            target_field,
        )

        declarations = (
            ("fk", placement.fk_entity, placement.fk_field),
            ("ref", placement.ref_entity, placement.ref_field),
        )
        absent: str | None = None
        for role, entity_id, field_name in declarations:
            if field_name not in field_names.get(entity_id, set()):
                role_name = "from" if role == "fk" else "to"
                absent = (
                    f'{label} skipped: {role_name}_columns field "{field_name}" '
                    f'is not declared on dataset "{emitted[entity_id]}" '
                    f'(entity "{entity_id}")'
                )
                break
        if absent is not None:
            warnings.append(absent)
            continue

        key = (
            emitted[placement.fk_entity],
            emitted[placement.ref_entity],
            placement.fk_field,
            placement.ref_field,
        )
        if key in seen:
            continue
        seen.add(key)
        entries.append(
            {
                "from": key[0],
                "to": key[1],
                "from_columns": [key[2]],
                "to_columns": [key[3]],
            }
        )

    # `to_columns` only breaks ties, so input order cannot leak into the file.
    entries.sort(
        key=lambda entry: (
            entry["from"],
            entry["to"],
            tuple(entry["from_columns"]),
            tuple(entry["to_columns"]),
        )
    )

    used: set[str] = set()
    named: list[dict[str, Any]] = []
    for entry in entries:
        base = f'{entry["from"]}_to_{entry["to"]}'
        name = base
        if name in used:
            name = f'{base}_{entry["from_columns"][0]}'
        if name in used:
            suffix = 2
            while f"{name}_{suffix}" in used:
                suffix += 1
            name = f"{name}_{suffix}"
        used.add(name)
        named.append({"name": name, **entry})

    return named, warnings


def _resolve_name(project_name: str) -> str:
    """Project name, falling back to the data model file stem."""
    name = (project_name or "").strip()
    if name:
        return name
    data_model_path = (getattr(cfg, "DATA_MODEL_PATH", "") or "").strip()
    if data_model_path:
        stem = Path(data_model_path).stem
        if stem:
            return stem
    return "semantic_model"


def _output_path() -> Path:
    """The configured Ossie file, or the default beside data_model.yml."""
    configured = (cfg.OSSIE_CONFIG.file or "").strip()
    if configured:
        return Path(configured)
    data_model_path = (getattr(cfg, "DATA_MODEL_PATH", "") or "").strip()
    if data_model_path:
        return Path(data_model_path).parent / DEFAULT_FILENAME
    return Path(DEFAULT_FILENAME)


def export_ossie(
    entities: list[dict],
    relationships: list[dict],
    project_name: str,
    models: list[ModelInfo],
    model_schemas: dict[str, ModelSchema] | None = None,
) -> OssieExport:
    """Write one Ossie document for every entity bound to an adapter model.

    `model_schemas` is keyed by `unique_id` and carries the column metadata the
    key rules need; the exporter never calls an adapter itself. When a model has
    no entry, key inference falls back to inbound relationships.

    Returns the written path (None when no dataset resolved) plus warnings for
    every skipped entity, so the push flow can explain an empty document.
    """
    warnings: list[str] = []

    model_index = {
        model.get("unique_id"): model
        for model in models
        if model.get("unique_id")
    }

    datasets: list[dict[str, Any]] = []
    emitted: dict[str, str] = {}
    field_names: dict[str, set[str]] = {}
    for entity in entities:
        entity_id = entity.get("id") or ""
        model_ref = get_model_ref(entity)
        if not model_ref:
            warnings.append(
                f'entity "{entity_id}" is not bound to a model; not exported'
            )
            continue

        model = model_index.get(model_ref)
        if model is None:
            warnings.append(
                f'entity "{entity_id}" references model "{model_ref}", which the '
                "adapter does not report; dbt_model_paths / bruin_asset_paths "
                "filtering may exclude it"
            )
            continue

        dataset = _build_dataset(
            entity, entity_id, model, model_schemas, relationships
        )
        datasets.append(dataset)
        emitted[entity_id.strip()] = dataset["name"]
        field_names[entity_id.strip()] = {
            field["name"] for field in dataset["fields"]
        }

    datasets.sort(key=lambda dataset: dataset["name"])

    if not datasets:
        warnings.append(
            "no entities resolved to adapter models; nothing was written"
        )
        return OssieExport(path=None, warnings=warnings)

    relationship_entries, relationship_warnings = _build_relationships(
        entities, relationships, emitted, field_names
    )
    warnings.extend(relationship_warnings)

    document: dict[str, Any] = {
        "version": OSSIE_VERSION,
        "name": _resolve_name(project_name),
        "datasets": datasets,
        "relationships": relationship_entries,
        "metrics": [],
    }

    path = _output_path()
    YamlHandler().save_file(str(path), document)
    return OssieExport(path=path, warnings=warnings)
