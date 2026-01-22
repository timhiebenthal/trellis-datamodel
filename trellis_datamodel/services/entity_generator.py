"""
Entity Generator service for business events.

Generates dimensional entities (dimensions and facts) from annotated business events.
This service converts text annotations into entity definitions with proper naming,
labels, and relationships following dimensional modeling conventions.
"""

import logging
import re
from typing import List, Optional

from trellis_datamodel import config as cfg
from trellis_datamodel.exceptions import ValidationError
from trellis_datamodel.models.business_event import BusinessEvent, Annotation, GeneratedEntitiesResult

logger = logging.getLogger(__name__)


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


def _create_dimension_entity(annotation: Annotation, prefixes: List[str], domain_tag: Optional[str] = None) -> dict:
    """
    Create a dimension entity dictionary from an annotation.

    Args:
        annotation: Annotation marked as 'dimension'
        prefixes: List of dimension prefixes to apply (e.g., ['dim_'])
        domain_tag: Optional domain tag to add to entity (slugified domain)

    Returns:
        Entity dictionary with id, label, entity_type, tags, etc.
    """
    base_name = _text_to_snake_case(annotation.text)
    label = _text_to_title_case(annotation.text)

    # Apply prefix if configured and not already present
    entity_id = base_name
    if prefixes:
        prefix = prefixes[0]  # Use first prefix
        # Check if already has a prefix (case-insensitive)
        has_prefix = any(base_name.lower().startswith(p.lower()) for p in prefixes)
        if not has_prefix:
            entity_id = f"{prefix}{base_name}"

    entity = {
        "id": entity_id,
        "label": label,
        "entity_type": "dimension",
        "description": f"Dimension: {annotation.text}",
    }

    # Add domain tag if provided
    if domain_tag:
        entity["tags"] = [domain_tag]

    return entity


def _create_fact_entity(annotation: Annotation, prefixes: List[str], event_type: str, domain_tag: Optional[str] = None) -> dict:
    """
    Create a fact entity dictionary from an annotation.

    Args:
        annotation: Annotation marked as 'fact'
        prefixes: List of fact prefixes to apply (e.g., ['fct_'])
        event_type: Business event type (discrete, evolving, recurring)
        domain_tag: Optional domain tag to add to entity (slugified domain)

    Returns:
        Entity dictionary with id, label, entity_type, metadata, tags, etc.
    """
    base_name = _text_to_snake_case(annotation.text)
    label = _text_to_title_case(annotation.text)

    # Apply prefix if configured and not already present
    entity_id = base_name
    if prefixes:
        prefix = prefixes[0]  # Use first prefix
        # Check if already has a prefix (case-insensitive)
        has_prefix = any(base_name.lower().startswith(p.lower()) for p in prefixes)
        if not has_prefix:
            entity_id = f"{prefix}{base_name}"

    entity = {
        "id": entity_id,
        "label": label,
        "entity_type": "fact",
        "description": f"Fact: {annotation.text}",
    }

    # Add event type as metadata
    if event_type:
        entity["metadata"] = {"event_type": event_type}

    # Add domain tag if provided
    if domain_tag:
        entity["tags"] = [domain_tag]

    return entity


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
        relationships.append({
            "source": dim_id,
            "target": fact_id,
            "type": "one_to_many",  # Standard dimensional relationship
            "label": "",
        })
    return relationships


def generate_entities_from_event(event: BusinessEvent, config=None) -> GeneratedEntitiesResult:
    """
    Generate dimensional entities from an annotated business event.

    Args:
        event: BusinessEvent with annotations
        config: Optional config object (uses global config if not provided)

    Returns:
        GeneratedEntitiesResult with entities, relationships, and any errors

    Raises:
        ValidationError: If event doesn't have required annotations
    """
    errors = []

    # Validate: require at least 1 dimension and 1 fact annotation
    dimensions = [ann for ann in event.annotations if ann.type == "dimension"]
    facts = [ann for ann in event.annotations if ann.type == "fact"]

    if not dimensions:
        errors.append("At least one dimension annotation is required")
    if not facts:
        errors.append("At least one fact annotation is required")

    if errors:
        return GeneratedEntitiesResult(entities=[], relationships=[], errors=errors)

    # Get prefixes from config
    if config is None:
        dim_prefixes = cfg.DIMENSIONAL_MODELING_CONFIG.dimension_prefix or []
        fact_prefixes = cfg.DIMENSIONAL_MODELING_CONFIG.fact_prefix or []
    else:
        dim_prefixes = getattr(config, "dimension_prefix", []) or []
        fact_prefixes = getattr(config, "fact_prefix", []) or []

    # Check if event has domain and slugify it for tag
    domain_tag = None
    if event.domain:
        domain_tag = slugify_domain(event.domain)

    # Generate dimension entities
    dimension_entities = []
    dimension_ids = []
    for ann in dimensions:
        entity = _create_dimension_entity(ann, dim_prefixes, domain_tag=domain_tag)
        dimension_entities.append(entity)
        dimension_ids.append(entity["id"])

    # Generate fact entities (typically one fact per event)
    fact_entities = []
    fact_ids = []
    for ann in facts:
        entity = _create_fact_entity(ann, fact_prefixes, event.type.value, domain_tag=domain_tag)
        fact_entities.append(entity)
        fact_ids.append(entity["id"])

    # Check for duplicate entity names
    all_entity_ids = [e["id"] for e in dimension_entities + fact_entities]
    duplicates = [eid for eid in all_entity_ids if all_entity_ids.count(eid) > 1]
    if duplicates:
        errors.append(f"Duplicate entity names detected: {', '.join(set(duplicates))}")

    # Create relationships: each dimension connects to each fact
    relationships = []
    for fact_id in fact_ids:
        fact_rels = _create_relationships(fact_id, dimension_ids)
        relationships.extend(fact_rels)

    result = GeneratedEntitiesResult(
        entities=dimension_entities + fact_entities,
        relationships=relationships,
        errors=errors,
    )
    
    logger.info(
        f"Generated entities from event {event.id}: "
        f"{len(dimension_entities)} dimensions, {len(fact_entities)} facts, "
        f"{len(relationships)} relationships"
    )
    
    return result
