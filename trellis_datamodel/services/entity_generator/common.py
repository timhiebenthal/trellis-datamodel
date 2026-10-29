"""
Helpers shared by the entity-model and dimensional-model generators.
"""

import logging
import re
from typing import Dict, List, Optional

from trellis_datamodel import config as cfg
from trellis_datamodel.models.business_event import (
    GeneratedEntitiesResult,
)
from trellis_datamodel.utils.structured_data import load_yaml_file

logger = logging.getLogger(__name__)


def bind_entities_to_models(
    entities: List[dict], models: List[dict], prefixes: Optional[List[str]] = None
) -> List[dict]:
    """Bind unbound entities to an existing model when the match is unambiguous.

    A generated entity id or label often corresponds to a pipeline asset that
    already exists (e.g. entity ``player`` vs asset ``dim__player``). Without a
    binding the entity can never inherit the asset's folder, which breaks
    canvas grouping. Ambiguous keys (several models normalizing to the same
    short name) are skipped so a generated entity is never bound to the wrong
    asset. Already-bound entities are passed through untouched.

    Returns a new list; the input entities are not mutated.
    """
    if prefixes is None:
        prefixes = list(cfg.DIMENSIONAL_MODELING_CONFIG.dimension_prefix or []) + list(
            cfg.DIMENSIONAL_MODELING_CONFIG.fact_prefix or []
        )

    def normalise(value: str) -> str:
        name = (value or "").strip().lower()
        if "." in name:
            name = name.rsplit(".", 1)[1]
        # Type prefixes use a double-underscore separator (dim__player); take
        # the tail. Single-underscore prefixes from config are stripped too.
        if "__" in name:
            name = name.rsplit("__", 1)[1]
        for prefix in prefixes:
            if prefix and name.startswith(prefix.strip("_").lower() + "_"):
                name = name[len(prefix.strip("_")) + 1:]
        return re.sub(r"[\s_-]+", "", name)

    models_by_key: Dict[str, List[str]] = {}
    for model in models:
        unique_id = model.get("unique_id")
        if not unique_id:
            continue
        key = normalise(model.get("name") or unique_id)
        if key:
            models_by_key.setdefault(key, []).append(unique_id)

    # A key several models share cannot be bound safely.
    unique_models_by_key = {
        key: ids[0] for key, ids in models_by_key.items() if len(ids) == 1
    }

    bound: List[dict] = []
    for entity in entities:
        if entity.get("model_ref"):
            bound.append(entity)
            continue
        ref = None
        for key in (normalise(entity.get("id", "")), normalise(entity.get("label", ""))):
            if key and key in unique_models_by_key:
                ref = unique_models_by_key[key]
                break
        if ref:
            bound.append({**entity, "model_ref": ref})
        else:
            bound.append(entity)
    return bound


def slugify_domain(domain: str) -> str:
    """
    Convert domain string to slug format for use as tag.

    Args:
        domain: Domain string (e.g., "Sales Operations", "Finance")

    Returns:
        Slugified string (e.g., "sales-operations", "finance")
    """
    import re

    # Convert to lowercase
    slug = domain.lower()
    # Replace spaces with hyphens
    slug = slug.replace(" ", "-")
    # Remove special characters except hyphens
    slug = re.sub(r"[^a-z0-9\-]", "", slug)
    # Remove multiple consecutive hyphens
    slug = re.sub(r"-+", "-", slug)
    # Remove leading/trailing hyphens
    slug = slug.strip("-")
    return slug


def _text_to_snake_case(text: str) -> str:
    """
    Convert text to snake_case identifier.

    Args:
        text: Text to convert (e.g., "Customer Name" or "customer-name")

    Returns:
        Snake case string (e.g., "customer_name")
    """
    # Convert to lowercase
    text = text.lower()
    # Replace spaces, hyphens, and special chars with underscores
    text = re.sub(r"[^a-z0-9]+", "_", text)
    # Remove leading/trailing underscores
    text = text.strip("_")
    # Handle empty result
    if not text:
        return "entity"
    return text


def _text_to_title_case(text: str) -> str:
    """
    Convert text to Title Case label.

    Args:
        text: Text to convert (e.g., "customer_name" or "customer name")

    Returns:
        Title case string (e.g., "Customer Name")
    """
    # Split by spaces, underscores, hyphens
    words = re.split(r"[\s_\-]+", text)
    # Capitalize first letter of each word, lowercase the rest
    title_words = [word.capitalize() if word else "" for word in words if word]
    return " ".join(title_words) if title_words else text


def _is_entity_model(config=None) -> bool:
    """Return True when entity_model modeling style is active."""
    if config is not None:
        return getattr(config, "MODELING_STYLE", None) == "entity_model"
    return getattr(cfg, "MODELING_STYLE", None) == "entity_model"


def _entity_prefixes(config=None) -> List[str]:
    """Return entity prefixes from config, defaulting to empty list."""
    if config is not None:
        entity_modeling_cfg = getattr(config, "ENTITY_MODELING_CONFIG", None)
        if entity_modeling_cfg is not None:
            return getattr(entity_modeling_cfg, "entity_prefix", None) or []
        return []
    return getattr(cfg.ENTITY_MODELING_CONFIG, "entity_prefix", None) or []


def _create_relationships(fact_id: str, dimension_ids: List[str]) -> List[dict]:
    """
    Create relationship dictionaries connecting dimensions to a fact.

    Args:
        fact_id: ID of the fact entity
        dimension_ids: List of dimension entity IDs

    Returns:
        List of relationship dictionaries (source: dimension, target: fact)
    """
    relationships = []
    for dim_id in dimension_ids:
        relationships.append(
            {
                "source": dim_id,
                "target": fact_id,
                "type": "one_to_many",  # Standard dimensional relationship
                "label": "",
            }
        )
    return relationships


def _load_existing_entities() -> Dict[str, dict]:
    """
    Load existing entities from data_model.yml.

    Returns:
        Dictionary mapping entity IDs to entity dictionaries
    """
    try:
        data = load_yaml_file(cfg.DATA_MODEL_PATH, {})
        entities = data.get("entities", [])
        return {entity["id"]: entity for entity in entities if "id" in entity}
    except Exception as e:
        logger.warning(f"Could not load data_model.yml: {e}")
        return {}


def _bind_result_to_models(result: GeneratedEntitiesResult) -> GeneratedEntitiesResult:
    """Attach model_ref to generated entities that match an existing asset.

    Model metadata lives behind the active framework adapter; when it cannot be
    read (project not configured, artifacts missing) generation still succeeds
    with unbound entities rather than failing the whole request.
    """
    if not result.entities:
        return result
    try:
        from trellis_datamodel.services.manifest import get_models

        models = get_models()
    except Exception as e:  # noqa: BLE001 - binding is best-effort
        logger.debug("Skipping model binding for generated entities: %s", e)
        return result
    return GeneratedEntitiesResult(
        entities=bind_entities_to_models(result.entities, models),
        relationships=result.relationships,
        errors=result.errors,
    )
