"""Apache Ossie semantic model exporter.

Writes one flat `0.2.0.dev0` document from the entities bound in
`data_model.yml`. The spec is a draft, so the version is pinned in one constant
and the whole mapping lives here rather than leaking into routes or adapters.

Relationships and keys are filled by later tasks; this module currently emits
datasets and fields only.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import trellis_datamodel.config as cfg
from trellis_datamodel.adapters.base import ModelInfo
from trellis_datamodel.models.entity_keys import (
    get_model_ref,
    get_physical_datatype,
)
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


def _build_dataset(
    entity: dict[str, Any], model: ModelInfo
) -> dict[str, Any]:
    dataset: dict[str, Any] = {
        "name": (model.get("name") or model.get("unique_id") or "").strip(),
        "source": _build_source(model),
    }
    description = entity.get("description")
    if description:
        dataset["description"] = description
    dataset["fields"] = _build_fields(entity, model)
    return dataset


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
) -> OssieExport:
    """Write one Ossie document for every entity bound to an adapter model.

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

        datasets.append(_build_dataset(entity, model))

    datasets.sort(key=lambda dataset: dataset["name"])

    if not datasets:
        warnings.append(
            "no entities resolved to adapter models; nothing was written"
        )
        return OssieExport(path=None, warnings=warnings)

    document: dict[str, Any] = {
        "version": OSSIE_VERSION,
        "name": _resolve_name(project_name),
        "datasets": datasets,
        # Task 6 fills relationships from the `relationships` argument.
        "relationships": [],
        "metrics": [],
    }

    path = _output_path()
    YamlHandler().save_file(str(path), document)
    return OssieExport(path=path, warnings=warnings)
