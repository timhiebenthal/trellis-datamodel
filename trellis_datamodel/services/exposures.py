"""
Exposures service.

Maps the active framework's exposures — declared downstream consumers such as
dashboards — onto the entities in the data model, so the canvas can show which
entities are actually used.

Reading the exposures themselves is the adapter's job. What lives here is the
Trellis-owned half: expanding each exposure's dependencies to their full
upstream set, then resolving those models to the entities bound to them. The
expansion matters because an exposure usually points at a mart model while the
entities live further upstream — without it, almost nothing would be marked as
used.
"""

import logging
import os
from typing import Any

import yaml

from trellis_datamodel import config as cfg
from trellis_datamodel.adapters import get_adapter
from trellis_datamodel.exceptions import FeatureDisabledError
from trellis_datamodel.models.entity_keys import get_model_ref

logger = logging.getLogger(__name__)


def _load_data_model() -> dict[str, Any]:
    """Load data model YAML."""
    if not cfg.DATA_MODEL_PATH or not os.path.exists(cfg.DATA_MODEL_PATH):
        return {}
    try:
        with open(cfg.DATA_MODEL_PATH, "r") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning("Could not load data model: %s", e)
        return {}


def _find_entities_for_model(unique_id: str, data_model: dict[str, Any]) -> list[str]:
    """
    Find all entity IDs that are bound to the given model unique_id.

    Checks both the bound model reference and additional_models fields.
    """
    entity_ids = []
    entities = data_model.get("entities", [])
    for entity in entities:
        entity_id = entity.get("id")
        if not entity_id:
            continue

        # Check primary model binding
        if get_model_ref(entity) == unique_id:
            entity_ids.append(entity_id)
            continue

        # Check additional_models
        additional_models = entity.get("additional_models", [])
        if isinstance(additional_models, list) and unique_id in additional_models:
            entity_ids.append(entity_id)

    return entity_ids


def _collect_upstream_model_ids(adapter, model_unique_id: str) -> set[str]:
    """
    Collect a model's upstream models, including the model itself.

    Notes:
    - This is table-level lineage, not column-level.
    - Only models are returned; sources are traversal stopping points.
    - A model the framework does not know about yields just itself, so a stale
      exposure reference still maps whatever it can instead of dropping out.
    """
    if not model_unique_id:
        return set()

    try:
        graph = adapter.get_lineage(model_unique_id)
    except Exception as e:
        logger.warning("Could not resolve upstreams for %s: %s", model_unique_id, e)
        return {model_unique_id}

    return {
        node["unique_id"]
        for node in graph["nodes"]
        if node["resource_type"] == "model"
    }


def get_exposures() -> dict[str, Any]:
    """
    Return exposures data and entity usage mapping.

    Returns:
        Dictionary with 'exposures' list and 'entityUsage' mapping

    Raises:
        FeatureDisabledError: If exposures are disabled
    """
    # Check if exposures feature is enabled
    if not cfg.EXPOSURES_ENABLED:
        raise FeatureDisabledError(
            "Exposures are disabled. Set 'exposures.enabled: true' in trellis.yml to enable."
        )

    adapter = get_adapter()
    try:
        exposures_list = adapter.get_exposures()
    except Exception as e:
        logger.warning("Could not read exposures: %s", e)
        exposures_list = []

    # If no exposures found, return empty response
    if not exposures_list:
        return {"exposures": [], "entityUsage": {}}

    data_model = _load_data_model()

    # Build response: extract exposure metadata
    exposures_response = []
    entity_usage: dict[str, list[str]] = {}  # entity_id -> [exposure_names]
    upstream_cache: dict[str, set[str]] = {}  # model_unique_id -> upstream model ids

    for exposure in exposures_list:
        if not isinstance(exposure, dict):
            continue

        exposure_name = exposure.get("name", "")
        if not exposure_name:
            continue

        exposure_meta = {
            "name": exposure_name,
            "label": exposure.get("label"),
            "type": exposure.get("type"),
            "description": exposure.get("description"),
        }
        if exposure.get("owner"):
            exposure_meta["owner"] = exposure["owner"]

        exposures_response.append(exposure_meta)

        # `depends_on` arrives from the adapter already resolved to unique_ids.
        for unique_id in exposure.get("depends_on") or []:
            if not isinstance(unique_id, str):
                continue

            # Expand to *all upstream models* before mapping to entities.
            # This ensures exposures that depend on mart/int models still mark
            # the underlying entity-bound models as "used".
            if unique_id not in upstream_cache:
                upstream_cache[unique_id] = _collect_upstream_model_ids(
                    adapter, unique_id
                )

            for upstream_model_id in upstream_cache[unique_id]:
                for entity_id in _find_entities_for_model(
                    upstream_model_id, data_model
                ):
                    usage = entity_usage.setdefault(entity_id, [])
                    if exposure_name not in usage:
                        usage.append(exposure_name)

    return {
        "exposures": exposures_response,
        "entityUsage": entity_usage,
    }
