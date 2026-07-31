"""Shared entity-key compat accessors for characterization tests.

These helpers read the model binding and framework-mirrored tags with a
new-key-first, legacy-key-fallback, presence-based lookup — mirroring the
`model_ref`/`framework_tags` generalization planned for
`trellis_datamodel/models/entity_keys.py` (not yet built as of this test).

Tests that read entity dict keys through these helpers (instead of raw
`"dbt_model"`/`"dbt_tags"` literals) survive the future rename unmodified:
only fixture keys change, never assertions.

Lookup is presence-based, not truthiness-based: if the new key is present at
all, it wins, even when its value is `None` or `[]`. An explicitly cleared
binding must not fall back to a stale legacy value.
"""
from typing import Any, Optional

MODEL_REF_KEY = "model_ref"
LEGACY_MODEL_REF_KEY = "dbt_model"
FRAMEWORK_TAGS_KEY = "framework_tags"
LEGACY_FRAMEWORK_TAGS_KEY = "dbt_tags"


def get_model_ref(entity: dict[str, Any]) -> Optional[str]:
    """Return the entity's bound model reference, new key first."""
    if MODEL_REF_KEY in entity:
        return entity[MODEL_REF_KEY] or None
    return entity.get(LEGACY_MODEL_REF_KEY) or None


def get_framework_tags(entity: dict[str, Any]) -> list:
    """Return the entity's framework-mirrored tags, new key first."""
    if FRAMEWORK_TAGS_KEY in entity:
        return list(entity[FRAMEWORK_TAGS_KEY] or [])
    return list(entity.get(LEGACY_FRAMEWORK_TAGS_KEY) or [])


def _normalize_entity(entity: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of `entity` with the binding/tags collapsed onto the
    generic key names, for spelling-independent comparison in tests.

    This is the one place a raw key literal is allowed; assertions built on
    top of this helper never depend on which spelling the underlying code
    currently uses.
    """
    normalized = {
        k: v
        for k, v in entity.items()
        if k
        not in (
            MODEL_REF_KEY,
            LEGACY_MODEL_REF_KEY,
            FRAMEWORK_TAGS_KEY,
            LEGACY_FRAMEWORK_TAGS_KEY,
        )
    }
    normalized[MODEL_REF_KEY] = get_model_ref(entity)
    normalized[FRAMEWORK_TAGS_KEY] = get_framework_tags(entity)
    return normalized
