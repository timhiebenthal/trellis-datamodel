"""Generic entity-key accessors with read-compat for legacy dbt-prefixed keys.

`model_ref` / `framework_tags` / `physical_datatype` are the current field names
in data_model.yml. `dbt_model` / `dbt_tags` / `dbt_data_type` are read for
backward compatibility with files written before this generalization; only the
new names are ever written.

`physical_datatype` pairs with a column's `datatype`: `datatype` is Trellis's
logical bucket (a closed set — text, int, float, bool, date, timestamp, unknown),
while `physical_datatype` is the concrete type the framework's catalog reports
for that column (varchar, timestamp, numeric(38,0)). Keeping both means a push
writes back the precise type rather than downgrading it to the bucket.

Lookup is presence-based, not truthiness-based: if the new key is present at all,
it wins, even when its value is None or []. An explicitly cleared binding must not
fall back to a stale legacy value.
"""
from typing import Any, Optional

MODEL_REF_KEY = "model_ref"
LEGACY_MODEL_REF_KEY = "dbt_model"
FRAMEWORK_TAGS_KEY = "framework_tags"
LEGACY_FRAMEWORK_TAGS_KEY = "dbt_tags"
PHYSICAL_DATATYPE_KEY = "physical_datatype"
LEGACY_PHYSICAL_DATATYPE_KEY = "dbt_data_type"


def get_model_ref(entity: dict[str, Any]) -> Optional[str]:
    if MODEL_REF_KEY in entity:
        return entity[MODEL_REF_KEY] or None
    return entity.get(LEGACY_MODEL_REF_KEY) or None


def set_model_ref(entity: dict[str, Any], value: Optional[str]) -> None:
    entity.pop(LEGACY_MODEL_REF_KEY, None)
    entity.pop(MODEL_REF_KEY, None)
    if value:
        entity[MODEL_REF_KEY] = value


def get_framework_tags(entity: dict[str, Any]) -> list[str]:
    if FRAMEWORK_TAGS_KEY in entity:
        return list(entity[FRAMEWORK_TAGS_KEY] or [])
    return list(entity.get(LEGACY_FRAMEWORK_TAGS_KEY) or [])


def set_framework_tags(entity: dict[str, Any], tags: list[str]) -> None:
    entity.pop(LEGACY_FRAMEWORK_TAGS_KEY, None)
    entity[FRAMEWORK_TAGS_KEY] = list(tags)


def has_legacy_keys(entity: dict[str, Any]) -> bool:
    return LEGACY_MODEL_REF_KEY in entity or LEGACY_FRAMEWORK_TAGS_KEY in entity


def get_physical_datatype(field: dict[str, Any]) -> Optional[str]:
    """Read a field's concrete framework/warehouse type, new key first.

    Contrast with the field's `datatype`, which is the coarse logical bucket.
    """
    if PHYSICAL_DATATYPE_KEY in field:
        return field[PHYSICAL_DATATYPE_KEY] or None
    return field.get(LEGACY_PHYSICAL_DATATYPE_KEY) or None


def set_physical_datatype(field: dict[str, Any], value: Optional[str]) -> None:
    field.pop(LEGACY_PHYSICAL_DATATYPE_KEY, None)
    field.pop(PHYSICAL_DATATYPE_KEY, None)
    if value:
        field[PHYSICAL_DATATYPE_KEY] = value
