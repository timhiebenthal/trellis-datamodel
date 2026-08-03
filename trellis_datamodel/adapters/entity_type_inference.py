"""
Entity-type inference shared across transformation-framework adapters.

Classifying a model as a fact or a dimension is a naming-convention question
(``dimensional_modeling.dimension_prefix`` / ``fact_prefix`` in trellis.yml), not
a framework question — the only framework-specific parts are *which* models exist
and *when* the answer goes stale. Adapters supply both; this module owns the
matching and the cache.

The cache is keyed per framework. It used to be class-level state on
``DbtCoreAdapter``; a single shared dict would let two adapters clobber each
other's results within one process (which happens in the test suite, where
dbt-core and Bruin adapters are both exercised).
"""

import logging
from typing import Callable, Optional

from trellis_datamodel import config as cfg

logger = logging.getLogger(__name__)

# framework -> (cache_key, inferred types)
_CACHES: dict[str, tuple[str, dict[str, str]]] = {}


def reset_cache(framework: Optional[str] = None) -> None:
    """Drop cached inference results.

    Args:
        framework: Clear only this framework's cache. ``None`` clears every
            framework, which is what a config change wants — the prefix config
            the inference reads is global.
    """
    if framework is None:
        _CACHES.clear()
    else:
        _CACHES.pop(framework, None)


def infer_entity_types(
    framework: str,
    cache_key: str,
    get_models: Callable[[], list[dict]],
    get_model_to_entity_map: Callable[[], dict[str, str]],
) -> dict[str, str]:
    """Classify each model as ``fact``, ``dimension``, or ``unclassified``.

    Args:
        framework: Cache namespace, e.g. ``"dbt-core"``.
        cache_key: Opaque staleness token from the adapter — typically a path
            plus mtime. A changed key invalidates the cache.
        get_models: Called only on a cache miss, so a hit costs no scan.
        get_model_to_entity_map: Maps a model name to the entity bound to it.
            Models with no entity are keyed by their own name.

    Returns:
        Mapping from entity ID to inferred type. Empty when dimensional
        modeling is disabled.
    """
    if not cfg.DIMENSIONAL_MODELING_CONFIG.enabled:
        return {}

    cached = _CACHES.get(framework)
    if cached is not None and cached[0] == cache_key:
        logger.debug("Returning cached entity type inference for %s", framework)
        return cached[1]

    model_name_to_id = get_model_to_entity_map()
    dimension_prefixes = cfg.DIMENSIONAL_MODELING_CONFIG.dimension_prefix
    fact_prefixes = cfg.DIMENSIONAL_MODELING_CONFIG.fact_prefix

    entity_types: dict[str, str] = {}
    for model in get_models():
        model_name = model["name"]
        entity_id = model_name_to_id.get(model_name, model_name)
        entity_types[entity_id] = _classify(
            model_name, dimension_prefixes, fact_prefixes
        )

    _CACHES[framework] = (cache_key, entity_types)
    return entity_types


def _classify(
    model_name: str,
    dimension_prefixes: list[str],
    fact_prefixes: list[str],
) -> str:
    """Match a model name against the configured prefixes, dimensions first."""
    lowered = model_name.lower()

    for prefix in dimension_prefixes:
        if lowered.startswith(prefix.lower()):
            return "dimension"

    for prefix in fact_prefixes:
        if lowered.startswith(prefix.lower()):
            return "fact"

    return "unclassified"
