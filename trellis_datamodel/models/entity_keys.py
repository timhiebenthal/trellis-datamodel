"""Generic entity-key accessors with read-compat for legacy dbt-prefixed keys.

`model_ref` / `framework_tags` are the current field names in data_model.yml.
`dbt_model` / `dbt_tags` are read for backward compatibility with files written
before this generalization; only the new names are ever written.

Lookup is presence-based, not truthiness-based: if the new key is present at all,
it wins, even when its value is None or []. An explicitly cleared binding must not
fall back to a stale legacy value.
"""
from typing import Any, Optional

MODEL_REF_KEY = "model_ref"
LEGACY_MODEL_REF_KEY = "dbt_model"
FRAMEWORK_TAGS_KEY = "framework_tags"
LEGACY_FRAMEWORK_TAGS_KEY = "dbt_tags"


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
