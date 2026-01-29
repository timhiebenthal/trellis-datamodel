"""
Entity Generator service for business events.

Generates dimensional entities (dimensions and facts) from business events with
annotation entries. This service converts annotation entries into entity definitions
with proper naming, labels, and relationships following dimensional modeling conventions.
"""

import logging
import os
import re
from typing import Dict, List, Optional

import yaml

from trellis_datamodel import config as cfg
from trellis_datamodel.exceptions import ValidationError
from trellis_datamodel.models.business_event import (
    BusinessEvent,
    BusinessEventProcess,
    AnnotationEntry,
    GeneratedEntitiesResult,
)
from trellis_datamodel.services.business_events_service import load_business_events

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
    if not cfg.DATA_MODEL_PATH or not os.path.exists(cfg.DATA_MODEL_PATH):
        return {}

    try:
        with open(cfg.DATA_MODEL_PATH, "r") as f:
            data = yaml.safe_load(f) or {}
            entities = data.get("entities", [])
            return {entity["id"]: entity for entity in entities if "id" in entity}
    except Exception as e:
        logger.warning(f"Could not load data_model.yml: {e}")
        return {}


def _create_dimension_from_annotation_entry(
    entry: AnnotationEntry,
    annotation_type: str,
    prefixes: List[str],
    domain_tag: Optional[str] = None,
    existing_entities: Optional[Dict[str, dict]] = None,
) -> dict:
    """
    Create a dimension entity dictionary from an annotation entry.

    Args:
        entry: AnnotationEntry object
        annotation_type: The annotation category (who, what, when, where, how, why)
        prefixes: List of dimension prefixes to apply (e.g., ['dim_'])
        domain_tag: Optional domain tag to add to entity (slugified domain)
        existing_entities: Dictionary of existing entities from data_model.yml

    Returns:
        Entity dictionary with id, label, entity_type, metadata, tags, etc.
    """
    # If entry references an existing dimension_id, use that entity
    if (
        entry.dimension_id
        and existing_entities
        and entry.dimension_id in existing_entities
    ):
        existing_entity = existing_entities[entry.dimension_id]
        entity = {
            "id": existing_entity["id"],
            "label": existing_entity.get("label", entry.text),
            "entity_type": "dimension",
            "description": existing_entity.get(
                "description", entry.description or f"Dimension: {entry.text}"
            ),
        }
        # Add domain tag if provided
        if domain_tag:
            entity["tags"] = [domain_tag]
        return entity

    # Otherwise, create a new dimension
    base_name = _text_to_snake_case(entry.text)
    label = _text_to_title_case(entry.text)

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
        "description": entry.description or f"Dimension: {entry.text}",
        "metadata": {
            "annotation_type": annotation_type
        },  # Track which annotation category this dimension represents
    }

    # Add domain tag if provided
    if domain_tag:
        entity["tags"] = [domain_tag]

    return entity


def _create_fact_from_annotation_entries(
    entries: List[AnnotationEntry],
    prefixes: List[str],
    event_type: str,
    domain_tag: Optional[str] = None,
    event_text: Optional[str] = None,
) -> dict:
    """
    Create a fact entity dictionary from how_many entries.

    All how_many entries become attributes/columns in the fact table.

    Args:
        entries: List of AnnotationEntry objects (how_many category)
        prefixes: List of fact prefixes to apply (e.g., ['fct_'])
        event_type: Business event type (discrete, evolving, recurring)
        domain_tag: Optional domain tag to add to entity (slugified domain)
        event_text: Optional event text for default fact name

    Returns:
        Entity dictionary with id, label, entity_type, metadata, drafted_fields, tags, etc.
    """
    # Generate fact name from event text or use a default
    if event_text:
        base_name = _text_to_snake_case(event_text)
    else:
        # Use first how_many entry or default
        base_name = entries[0].text if entries else "event"

    label = _text_to_title_case(base_name)

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
        "description": f"Fact: {label}",
    }

    # Add event type as metadata
    if event_type:
        entity["metadata"] = {"event_type": event_type}

    # Create drafted_fields from how_many entries
    drafted_fields = []
    for entry in entries:
        field_name = _text_to_snake_case(entry.text)
        field = {
            "name": field_name,
            "datatype": "unknown",  # Default type, can be refined later
        }
        if entry.description:
            field["description"] = entry.description
        drafted_fields.append(field)

    if drafted_fields:
        entity["drafted_fields"] = drafted_fields

    # Add domain tag if provided
    if domain_tag:
        entity["tags"] = [domain_tag]

    return entity


def generate_entities_from_event(
    event: BusinessEvent, config=None
) -> GeneratedEntitiesResult:
    """
    Generate dimensional entities from a business event.

    Uses 7 Ws structured entries (Who, What, When, Where, How, How Many, Why).

    Args:
        event: BusinessEvent with annotations
        config: Optional config object (uses global config if not provided)

    Returns:
        GeneratedEntitiesResult with entities, relationships, and any errors

    Raises:
        ValidationError: If event doesn't have required data
    """
    errors = []

    # Check if event has annotations
    has_annotations = event.annotations and any(
        [
            event.annotations.who,
            event.annotations.what,
            event.annotations.when,
            event.annotations.where,
            event.annotations.how,
            event.annotations.how_many,
            event.annotations.why,
        ]
    )

    if has_annotations:
        return _generate_from_annotations(event, config)
    else:
        errors.append("Event must have annotation entries")
        return GeneratedEntitiesResult(entities=[], relationships=[], errors=errors)


def _generate_from_annotations(
    event: BusinessEvent, config=None
) -> GeneratedEntitiesResult:
    """
    Generate entities from annotation entries.

    Args:
        event: BusinessEvent with annotations
        config: Optional config object

    Returns:
        GeneratedEntitiesResult
    """
    errors = []

    # Collect dimension entries from all annotation categories except how_many
    dimension_entries = []
    for annotation_type, entries in [
        ("who", event.annotations.who),
        ("what", event.annotations.what),
        ("when", event.annotations.when),
        ("where", event.annotations.where),
        ("how", event.annotations.how),
        ("why", event.annotations.why),
    ]:
        for entry in entries:
            dimension_entries.append((annotation_type, entry))

    # Validate: require at least 1 dimension entry
    if not dimension_entries:
        errors.append(
            "At least one dimension entry (Who, What, When, Where, How, or Why) is required"
        )

    # Validate: require at least 1 how_many entry (fact)
    how_many_entries = event.annotations.how_many
    if not how_many_entries:
        errors.append("At least one 'How Many' entry is required for fact table")

    if errors:
        return GeneratedEntitiesResult(entities=[], relationships=[], errors=errors)

    # Get prefixes from config
    if config is None:
        dim_prefixes = cfg.DIMENSIONAL_MODELING_CONFIG.dimension_prefix or []
        fact_prefixes = cfg.DIMENSIONAL_MODELING_CONFIG.fact_prefix or []
    else:
        dim_prefixes = getattr(config, "dimension_prefix", []) or []
        fact_prefixes = getattr(config, "fact_prefix", []) or []

    # Load existing entities for dimension_id references
    existing_entities = _load_existing_entities()

    # Check if event has domain and slugify it for tag
    domain_tag = None
    if event.domain:
        domain_tag = slugify_domain(event.domain)

    # Generate dimension entities from all dimension entries
    dimension_entities = []
    dimension_ids = []
    for annotation_type, entry in dimension_entries:
        entity = _create_dimension_from_annotation_entry(
            entry,
            annotation_type=annotation_type,
            prefixes=dim_prefixes,
            domain_tag=domain_tag,
            existing_entities=existing_entities,
        )
        # Avoid duplicates (same dimension_id referenced multiple times)
        if entity["id"] not in dimension_ids:
            dimension_entities.append(entity)
            dimension_ids.append(entity["id"])

    # Generate fact entity from how_many entries
    fact_entity = _create_fact_from_annotation_entries(
        entries=how_many_entries,
        prefixes=fact_prefixes,
        event_type=event.type.value,
        domain_tag=domain_tag,
        event_text=event.text,
    )
    fact_id = fact_entity["id"]

    # Check for duplicate entity names
    all_entity_ids = [e["id"] for e in dimension_entities + [fact_entity]]
    duplicates = [eid for eid in all_entity_ids if all_entity_ids.count(eid) > 1]
    if duplicates:
        errors.append(f"Duplicate entity names detected: {', '.join(set(duplicates))}")

    # Create relationships: all dimensions connect to fact
    relationships = _create_relationships(fact_id, dimension_ids)

    result = GeneratedEntitiesResult(
        entities=dimension_entities + [fact_entity],
        relationships=relationships,
        errors=errors,
    )

    logger.info(
        f"Generated entities from 7 Ws for event {event.id}: "
        f"{len(dimension_entities)} dimensions, 1 fact, "
        f"{len(relationships)} relationships"
    )

    return result


def generate_entities_from_process(
    process: BusinessEventProcess, config=None
) -> GeneratedEntitiesResult:
    """
    Generate dimensional entities from a business event process.

    Uses the process's annotations_superset (union of all member event annotations).
    Behavior differs by process type:
    - discrete: one fact table with per-event records (includes event_id/process_id)
    - evolving: one fact table with process-level records (includes process_id)
    - recurring: same as discrete

    Args:
        process: BusinessEventProcess with annotations_superset
        config: Optional config object (uses global config if not provided)

    Returns:
        GeneratedEntitiesResult with entities, relationships, and any errors

    Raises:
        ValidationError: If process doesn't have required data
    """
    errors = []

    # Check if process is resolved
    if process.resolved_at is not None:
        errors.append("Cannot generate entities from a resolved process")
        return GeneratedEntitiesResult(entities=[], relationships=[], errors=errors)

    # Check if process has annotations_superset
    if not process.annotations_superset:
        errors.append("Process must have annotations_superset computed")
        return GeneratedEntitiesResult(entities=[], relationships=[], errors=errors)

    # Load member events for metadata
    events = load_business_events()
    process_events = [e for e in events if e.id in process.event_ids]

    if not process_events:
        errors.append("Process must have at least one member event")
        return GeneratedEntitiesResult(entities=[], relationships=[], errors=errors)

    # Use annotations_superset for generation
    annotations = process.annotations_superset

    # Collect dimension entries from all annotation categories except how_many
    dimension_entries = []
    for annotation_type, entries in [
        ("who", annotations.who),
        ("what", annotations.what),
        ("when", annotations.when),
        ("where", annotations.where),
        ("how", annotations.how),
        ("why", annotations.why),
    ]:
        for entry in entries:
            dimension_entries.append((annotation_type, entry))

    # Validate: require at least 1 dimension entry
    if not dimension_entries:
        errors.append(
            "At least one dimension entry (Who, What, When, Where, How, or Why) is required"
        )

    # Validate: require at least 1 how_many entry (fact)
    how_many_entries = annotations.how_many
    if not how_many_entries:
        errors.append("At least one 'How Many' entry is required for fact table")

    if errors:
        return GeneratedEntitiesResult(entities=[], relationships=[], errors=errors)

    # Get prefixes from config
    if config is None:
        dim_prefixes = cfg.DIMENSIONAL_MODELING_CONFIG.dimension_prefix or []
        fact_prefixes = cfg.DIMENSIONAL_MODELING_CONFIG.fact_prefix or []
    else:
        dim_prefixes = getattr(config, "dimension_prefix", []) or []
        fact_prefixes = getattr(config, "fact_prefix", []) or []

    # Load existing entities for dimension_id references
    existing_entities = _load_existing_entities()

    # Get domain tag from process domain (preferred) or first event's domain (fallback)
    domain_tag = None
    if process.domain:
        domain_tag = slugify_domain(process.domain)
    elif process_events[0].domain:
        domain_tag = slugify_domain(process_events[0].domain)

    # Generate dimension entities from all dimension entries
    dimension_entities = []
    dimension_ids = []
    for annotation_type, entry in dimension_entries:
        entity = _create_dimension_from_annotation_entry(
            entry,
            annotation_type=annotation_type,
            prefixes=dim_prefixes,
            domain_tag=domain_tag,
            existing_entities=existing_entities,
        )
        # Avoid duplicates (same dimension_id referenced multiple times)
        if entity["id"] not in dimension_ids:
            dimension_entities.append(entity)
            dimension_ids.append(entity["id"])

    # Generate fact entity based on process type
    if process.type.value == "discrete" or process.type.value == "recurring":
        fact_entity = _create_fact_from_process_discrete(
            entries=how_many_entries,
            prefixes=fact_prefixes,
            process=process,
            process_events=process_events,
            domain_tag=domain_tag,
        )
    elif process.type.value == "evolving":
        fact_entity = _create_fact_from_process_evolving(
            entries=how_many_entries,
            prefixes=fact_prefixes,
            process=process,
            process_events=process_events,
            domain_tag=domain_tag,
        )
    else:
        errors.append(f"Unknown process type: {process.type.value}")
        return GeneratedEntitiesResult(entities=[], relationships=[], errors=errors)

    fact_id = fact_entity["id"]

    # Check for duplicate entity names
    all_entity_ids = [e["id"] for e in dimension_entities + [fact_entity]]
    duplicates = [eid for eid in all_entity_ids if all_entity_ids.count(eid) > 1]
    if duplicates:
        errors.append(f"Duplicate entity names detected: {', '.join(set(duplicates))}")

    # Create relationships: all dimensions connect to fact
    relationships = _create_relationships(fact_id, dimension_ids)

    result = GeneratedEntitiesResult(
        entities=dimension_entities + [fact_entity],
        relationships=relationships,
        errors=errors,
    )

    logger.info(
        f"Generated entities from process {process.id} (type: {process.type.value}): "
        f"{len(dimension_entities)} dimensions, 1 fact, "
        f"{len(relationships)} relationships"
    )

    return result


def _create_fact_from_process_discrete(
    entries: List[AnnotationEntry],
    prefixes: List[str],
    process: BusinessEventProcess,
    process_events: List[BusinessEvent],
    domain_tag: Optional[str] = None,
) -> dict:
    """
    Create a fact entity dictionary for a discrete process.

    Discrete processes create one fact table with per-event records.
    Includes event_id and process_id columns for traceability.

    Args:
        entries: List of AnnotationEntry objects (how_many category)
        prefixes: List of fact prefixes to apply (e.g., ['fct_'])
        process: BusinessEventProcess object
        process_events: List of BusinessEvent objects in the process
        domain_tag: Optional domain tag to add to entity

    Returns:
        Entity dictionary with id, label, entity_type, metadata, drafted_fields, tags, etc.
    """
    # Generate fact name from process name
    base_name = _text_to_snake_case(process.name)
    label = _text_to_title_case(process.name)

    # Apply prefix if configured and not already present
    entity_id = base_name
    if prefixes:
        prefix = prefixes[0]  # Use first prefix
        has_prefix = any(base_name.lower().startswith(p.lower()) for p in prefixes)
        if not has_prefix:
            entity_id = f"{prefix}{base_name}"

    entity = {
        "id": entity_id,
        "label": label,
        "entity_type": "fact",
        "description": f"Fact: {label} (discrete process)",
    }

    # Add process and event metadata
    entity["metadata"] = {
        "process_id": process.id,
        "process_name": process.name,
        "process_type": process.type.value,
        "event_ids": process.event_ids,
        "event_count": len(process_events),
    }

    # Create drafted_fields from how_many entries
    drafted_fields = []
    for entry in entries:
        field_name = _text_to_snake_case(entry.text)
        field = {
            "name": field_name,
            "datatype": "unknown",
        }
        if entry.description:
            field["description"] = entry.description
        drafted_fields.append(field)

    # Add process/event traceability fields
    drafted_fields.append(
        {
            "name": "event_id",
            "datatype": "text",
            "description": "ID of the business event this record represents",
        }
    )
    drafted_fields.append(
        {
            "name": "process_id",
            "datatype": "text",
            "description": "ID of the process this record belongs to",
        }
    )

    if drafted_fields:
        entity["drafted_fields"] = drafted_fields

    # Add domain tag if provided
    if domain_tag:
        entity["tags"] = [domain_tag]

    return entity


def _create_fact_from_process_evolving(
    entries: List[AnnotationEntry],
    prefixes: List[str],
    process: BusinessEventProcess,
    process_events: List[BusinessEvent],
    domain_tag: Optional[str] = None,
) -> dict:
    """
    Create a fact entity dictionary for an evolving process.

    Evolving processes create a fact table from the how_many entries.
    Includes process_id for traceability.

    Args:
        entries: List of AnnotationEntry objects (how_many category)
        prefixes: List of fact prefixes to apply (e.g., ['fct_'])
        process: BusinessEventProcess object
        process_events: List of BusinessEvent objects in the process
        domain_tag: Optional domain tag to add to entity

    Returns:
        Entity dictionary with id, label, entity_type, metadata, drafted_fields, tags, etc.
    """
    # Generate fact name from process name
    base_name = _text_to_snake_case(process.name)
    label = _text_to_title_case(process.name)

    # Apply prefix if configured and not already present
    entity_id = base_name
    if prefixes:
        prefix = prefixes[0]  # Use first prefix
        has_prefix = any(base_name.lower().startswith(p.lower()) for p in prefixes)
        if not has_prefix:
            entity_id = f"{prefix}{base_name}"

    entity = {
        "id": entity_id,
        "label": label,
        "entity_type": "fact",
        "description": f"Fact: {label} (evolving process)",
    }

    # Add process and event metadata
    entity["metadata"] = {
        "process_id": process.id,
        "process_name": process.name,
        "process_type": process.type.value,
        "event_ids": process.event_ids,
        "event_count": len(process_events),
    }

    # Create drafted_fields from how_many entries
    drafted_fields = []
    for entry in entries:
        field_name = _text_to_snake_case(entry.text)
        field = {
            "name": field_name,
            "datatype": "unknown",
        }
        if entry.description:
            field["description"] = entry.description
        drafted_fields.append(field)

    # Add process_id for traceability
    drafted_fields.append(
        {
            "name": "process_id",
            "datatype": "text",
            "description": "ID of the process this record belongs to",
        }
    )

    if drafted_fields:
        entity["drafted_fields"] = drafted_fields

    # Add domain tag if provided
    if domain_tag:
        entity["tags"] = [domain_tag]

    return entity
