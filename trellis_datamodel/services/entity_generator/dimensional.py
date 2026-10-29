"""
Dimensional-model generation: dimensions from annotation entries, facts from events and processes.
"""

import logging
from typing import Dict, List, Optional

from trellis_datamodel import config as cfg
from trellis_datamodel.models.business_event import (
    BusinessEvent,
    BusinessEventProcess,
    AnnotationEntry,
    GeneratedEntitiesResult,
)
from trellis_datamodel.services.data_model import merge_roles

from trellis_datamodel.services.entity_generator.common import (
    _bind_result_to_models,
    _create_relationships,
    _load_existing_entities,
    _text_to_snake_case,
    _text_to_title_case,
    slugify_domain,
)

logger = logging.getLogger(__name__)


def _create_dimension_from_annotation_entry(
    entry: AnnotationEntry,
    annotation_type: str,
    prefixes: List[str],
    domain_tag: Optional[str] = None,
    domain: Optional[str] = None,
    existing_entities: Optional[Dict[str, dict]] = None,
    source_id: Optional[str] = None,
) -> dict:
    """
    Create a dimension entity dictionary from an annotation entry.

    Args:
        entry: AnnotationEntry object
        annotation_type: The annotation category (who, what, when, where, how, why)
        prefixes: List of dimension prefixes to apply (e.g., ['dim_'])
        domain_tag: Optional domain tag to add to entity (slugified domain)
        domain: Optional explicit domain value (not slugified)
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
        # Path A: dimension_id set + entity exists
        existing_entity = existing_entities[entry.dimension_id]
        existing_annotation_type = existing_entity.get("annotation_type") or (
            existing_entity.get("metadata", {}) or {}
        ).get("annotation_type")
        entity = {
            "id": existing_entity["id"],
            "label": existing_entity.get("label", entry.text),
            "entity_type": "dimension",
            "description": existing_entity.get(
                "description", entry.description or f"Dimension: {entry.text}"
            ),
            # Keep existing annotation type when present; otherwise infer from current 7W bucket.
            "annotation_type": existing_annotation_type or annotation_type,
        }
        # Add explicit domain field if provided
        if domain:
            entity["domain"] = domain
        # Add domain tag if provided (backward compatibility)
        if domain_tag:
            entity["tags"] = [domain_tag]
        # Attach role entry for dimension_id path
        role_entry = {k: v for k, v in {"label": entry.text, "role": entry.role, "source": source_id}.items() if v is not None}
        entity.setdefault("roles", []).append(role_entry)
        return entity
    elif entry.dimension_id:
        # Path B: dimension_id set + entity does NOT exist — create from dimension_id
        dim_id = entry.dimension_id
        # Derive label: strip known prefix, title-case the remainder
        remainder = dim_id
        # Sort prefixes longest-first so dim__ is tried before dim_
        sorted_prefixes = sorted(prefixes, key=len, reverse=True)
        for prefix in sorted_prefixes:
            if dim_id.lower().startswith(prefix.lower()):
                remainder = dim_id[len(prefix):]
                break
        label = _text_to_title_case(remainder) if remainder else _text_to_title_case(dim_id)
        entity = {
            "id": dim_id,
            "label": label,
            "entity_type": "dimension",
            "description": entry.description or f"Dimension: {entry.text}",
            "metadata": {
                "annotation_type": annotation_type,
            },
        }
        # Add explicit domain field if provided
        if domain:
            entity["domain"] = domain
        # Add domain tag if provided (backward compatibility)
        if domain_tag:
            entity["tags"] = [domain_tag]
        # Attach role entry for dimension_id path
        role_entry = {k: v for k, v in {"label": entry.text, "role": entry.role, "source": source_id}.items() if v is not None}
        entity.setdefault("roles", []).append(role_entry)
        return entity

    # Path C: no dimension_id — create a new dimension from annotation text
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

    # Add explicit domain field if provided
    if domain:
        entity["domain"] = domain

    # Add domain tag if provided (backward compatibility)
    if domain_tag:
        entity["tags"] = [domain_tag]

    return entity


def _create_fact_from_annotation_entries(
    entries: List[AnnotationEntry],
    prefixes: List[str],
    event_type: str,
    domain_tag: Optional[str] = None,
    domain: Optional[str] = None,
    event_text: Optional[str] = None,
    event_description: Optional[str] = None,
) -> dict:
    """
    Create a fact entity dictionary from how_many entries.

    All how_many entries become attributes/columns in the fact table.

    Args:
        entries: List of AnnotationEntry objects (how_many category)
        prefixes: List of fact prefixes to apply (e.g., ['fct_'])
        event_type: Business event type (discrete, evolving, recurring)
        domain_tag: Optional domain tag to add to entity (slugified domain)
        domain: Optional explicit domain value (not slugified)
        event_text: Optional event text for default fact name
        event_description: Optional description for the fact entity

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
        "description": event_description or f"Fact: {label}",
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

    # Add explicit domain field if provided
    if domain:
        entity["domain"] = domain

    # Add domain tag if provided (backward compatibility)
    if domain_tag:
        entity["tags"] = [domain_tag]

    return entity


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
    domain = None
    if event.domain:
        domain = event.domain  # Store original domain value
        domain_tag = slugify_domain(event.domain)  # Also keep slugified for backward compat

    # Generate dimension entities from all dimension entries
    dimension_entities = []
    dimension_ids = []
    for annotation_type, entry in dimension_entries:
        entity = _create_dimension_from_annotation_entry(
            entry,
            annotation_type=annotation_type,
            prefixes=dim_prefixes,
            domain_tag=domain_tag,
            domain=domain,
            existing_entities=existing_entities,
            source_id=event.id,
        )
        # Avoid duplicates (same dimension_id referenced multiple times)
        if entity["id"] not in dimension_ids:
            dimension_entities.append(entity)
            dimension_ids.append(entity["id"])
        else:
            # Merge roles from duplicate into existing entity
            existing = dimension_entities[dimension_ids.index(entity["id"])]
            if "roles" in entity:
                existing["roles"] = merge_roles(
                    existing.get("roles", []), entity["roles"]
                )

    # Generate fact entity from how_many entries
    fact_entity = _create_fact_from_annotation_entries(
        entries=how_many_entries,
        prefixes=fact_prefixes,
        event_type=event.type.value,
        domain_tag=domain_tag,
        domain=domain,
        event_text=event.text,
        event_description=event.description,
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


def _generate_from_process(
    process: BusinessEventProcess,
    process_events: List[BusinessEvent],
    config=None,
) -> GeneratedEntitiesResult:
    """Generate dimensions and a fact from a process's annotations_superset."""
    errors = []
    annotations = process.annotations_superset

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
    domain = None
    if process.domain:
        domain = process.domain  # Store original domain value
        domain_tag = slugify_domain(process.domain)
    elif process_events[0].domain:
        domain = process_events[0].domain  # Store original domain value
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
            domain=domain,
            existing_entities=existing_entities,
            source_id=process.id,
        )
        # Avoid duplicates (same dimension_id referenced multiple times)
        if entity["id"] not in dimension_ids:
            dimension_entities.append(entity)
            dimension_ids.append(entity["id"])
        else:
            # Merge roles from duplicate into existing entity
            existing = dimension_entities[dimension_ids.index(entity["id"])]
            if "roles" in entity:
                existing["roles"] = merge_roles(
                    existing.get("roles", []), entity["roles"]
                )

    # Generate fact entity based on process type
    if process.type.value == "discrete" or process.type.value == "recurring":
        fact_entity = _create_fact_from_process_discrete(
            entries=how_many_entries,
            prefixes=fact_prefixes,
            process=process,
            process_events=process_events,
            domain_tag=domain_tag,
            domain=domain,
            process_description=process.description,
        )
    elif process.type.value == "evolving":
        fact_entity = _create_fact_from_process_evolving(
            entries=how_many_entries,
            prefixes=fact_prefixes,
            process=process,
            process_events=process_events,
            domain_tag=domain_tag,
            domain=domain,
            process_description=process.description,
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

    return _bind_result_to_models(result)


def _create_fact_from_process_discrete(
    entries: List[AnnotationEntry],
    prefixes: List[str],
    process: BusinessEventProcess,
    process_events: List[BusinessEvent],
    domain_tag: Optional[str] = None,
    domain: Optional[str] = None,
    process_description: Optional[str] = None,
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
        domain_tag: Optional domain tag to add to entity (slugified domain)
        domain: Optional explicit domain value (not slugified)
        process_description: Optional description for the fact entity

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
        "description": process_description or f"Fact: {label} (discrete process)",
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

    # Add explicit domain field if provided
    if domain:
        entity["domain"] = domain

    # Add domain tag if provided (backward compatibility)
    if domain_tag:
        entity["tags"] = [domain_tag]

    return entity


def _create_fact_from_process_evolving(
    entries: List[AnnotationEntry],
    prefixes: List[str],
    process: BusinessEventProcess,
    process_events: List[BusinessEvent],
    domain_tag: Optional[str] = None,
    domain: Optional[str] = None,
    process_description: Optional[str] = None,
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
        domain_tag: Optional domain tag to add to entity (slugified domain)
        domain: Optional explicit domain value (not slugified)
        process_description: Optional description for the fact entity

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
        "description": process_description or f"Fact: {label} (evolving process)",
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

    # Add explicit domain field if provided
    if domain:
        entity["domain"] = domain

    # Add domain tag if provided (backward compatibility)
    if domain_tag:
        entity["tags"] = [domain_tag]

    return entity
