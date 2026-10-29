"""
Entity-model generation: one entity per event or process.
"""

import logging
from typing import List

from trellis_datamodel.models.business_event import (
    BusinessEvent,
    BusinessEventProcess,
    GeneratedEntitiesResult,
)

from trellis_datamodel.services.entity_generator.common import (
    _entity_prefixes,
    _text_to_snake_case,
    _text_to_title_case,
    slugify_domain,
)

logger = logging.getLogger(__name__)


def _generate_from_annotations_entity_model(
    event: BusinessEvent, config=None
) -> GeneratedEntitiesResult:
    """
    Generate an entity-model entity from annotation entries (entity_model style).

    Creates a central entity from the event, relationship stubs for entries with
    dimension_id, and drafted_fields for entries without dimension_id.
    """
    errors = []

    # Collect all non-how_many annotation entries
    non_how_many_entries = []
    for annotation_type, entries in [
        ("who", event.annotations.who),
        ("what", event.annotations.what),
        ("when", event.annotations.when),
        ("where", event.annotations.where),
        ("how", event.annotations.how),
        ("why", event.annotations.why),
    ]:
        for entry in entries:
            non_how_many_entries.append((annotation_type, entry))

    how_many_entries = event.annotations.how_many

    all_entries = non_how_many_entries + [("how_many", e) for e in how_many_entries]
    if not all_entries:
        errors.append("Event must have annotation entries")
        return GeneratedEntitiesResult(entities=[], relationships=[], errors=errors)

    prefixes = _entity_prefixes(config)

    # Build central entity id/label — prefer first What annotation as the core concept
    # name (e.g. "Employee makes Booking" → "booking"), fall back to full event text
    # when no What entries exist at all.
    first_what = next((e for e in (event.annotations.what or [])), None)
    if first_what:
        base_name = _text_to_snake_case(first_what.text)
        label = _text_to_title_case(first_what.text)
    else:
        base_name = _text_to_snake_case(event.text)
        label = _text_to_title_case(event.text)

    entity_id = base_name
    if prefixes:
        has_prefix = any(base_name.lower().startswith(p.lower()) for p in prefixes)
        if not has_prefix:
            entity_id = f"{prefixes[0]}{base_name}"

    # Build domain/tags
    domain = event.domain or None
    domain_tag = slugify_domain(domain) if domain else None
    tags = [domain_tag] if domain_tag else []

    central_entity: dict = {
        "id": entity_id,
        "label": label,
        "entity_type": "entity",
        "metadata": {
            "event_id": event.id,
            "modeling_style": "entity_model",
        },
    }
    if domain:
        central_entity["domain"] = domain
    if tags:
        central_entity["tags"] = tags

    # Process annotation entries into relationships or drafted_fields
    relationships = []
    drafted_fields = []
    seen_rel_pairs: set = set()

    for annotation_type, entry in non_how_many_entries:
        if entry.dimension_id:
            # Skip self-referential relationships (linked What whose id matches
            # the central entity we derived from its text)
            if entry.dimension_id == entity_id:
                continue
            pair = (entity_id, entry.dimension_id)
            if pair not in seen_rel_pairs:
                relationships.append(
                    {
                        "source": entity_id,
                        "target": entry.dimension_id,
                        "type": "many_to_one",
                        "label": entry.text,
                    }
                )
                seen_rel_pairs.add(pair)
        else:
            drafted_fields.append(
                {"name": _text_to_snake_case(entry.text), "datatype": "unknown"}
            )

    # how_many entries become drafted_fields
    for entry in how_many_entries:
        drafted_fields.append(
            {"name": _text_to_snake_case(entry.text), "datatype": "unknown"}
        )

    if drafted_fields:
        central_entity["drafted_fields"] = drafted_fields

    logger.info(
        f"Generated entity_model entity from event {event.id}: "
        f"1 entity, {len(relationships)} relationships, {len(drafted_fields)} drafted fields"
    )

    return GeneratedEntitiesResult(
        entities=[central_entity],
        relationships=relationships,
        errors=errors,
    )


def _generate_from_process_entity_model(
    process: BusinessEventProcess,
    process_events: List[BusinessEvent],
    config=None,
) -> GeneratedEntitiesResult:
    """
    Generate an entity-model entity from process annotations_superset (entity_model style).
    """
    errors = []
    annotations = process.annotations_superset

    non_how_many_entries = []
    for annotation_type, entries in [
        ("who", annotations.who),
        ("what", annotations.what),
        ("when", annotations.when),
        ("where", annotations.where),
        ("how", annotations.how),
        ("why", annotations.why),
    ]:
        for entry in entries:
            non_how_many_entries.append((annotation_type, entry))

    how_many_entries = annotations.how_many

    all_entries = non_how_many_entries + [("how_many", e) for e in how_many_entries]
    if not all_entries:
        errors.append("Process must have annotation entries")
        return GeneratedEntitiesResult(entities=[], relationships=[], errors=errors)

    prefixes = _entity_prefixes(config)

    base_name = _text_to_snake_case(process.name)
    entity_id = base_name
    if prefixes:
        has_prefix = any(base_name.lower().startswith(p.lower()) for p in prefixes)
        if not has_prefix:
            entity_id = f"{prefixes[0]}{base_name}"

    label = _text_to_title_case(process.name)

    domain = None
    domain_tag = None
    if process.domain:
        domain = process.domain
        domain_tag = slugify_domain(process.domain)
    elif process_events and process_events[0].domain:
        domain = process_events[0].domain
        domain_tag = slugify_domain(process_events[0].domain)

    tags = [domain_tag] if domain_tag else []

    central_entity: dict = {
        "id": entity_id,
        "label": label,
        "entity_type": "entity",
        "metadata": {
            "process_id": process.id,
            "modeling_style": "entity_model",
        },
    }
    if domain:
        central_entity["domain"] = domain
    if tags:
        central_entity["tags"] = tags

    relationships = []
    drafted_fields = []
    seen_rel_pairs: set = set()

    for annotation_type, entry in non_how_many_entries:
        if entry.dimension_id:
            pair = (entity_id, entry.dimension_id)
            if pair not in seen_rel_pairs:
                relationships.append(
                    {
                        "source": entity_id,
                        "target": entry.dimension_id,
                        "type": "many_to_one",
                        "label": entry.text,
                    }
                )
                seen_rel_pairs.add(pair)
        else:
            drafted_fields.append(
                {"name": _text_to_snake_case(entry.text), "datatype": "unknown"}
            )

    for entry in how_many_entries:
        drafted_fields.append(
            {"name": _text_to_snake_case(entry.text), "datatype": "unknown"}
        )

    if drafted_fields:
        central_entity["drafted_fields"] = drafted_fields

    logger.info(
        f"Generated entity_model entity from process {process.id}: "
        f"1 entity, {len(relationships)} relationships, {len(drafted_fields)} drafted fields"
    )

    return GeneratedEntitiesResult(
        entities=[central_entity],
        relationships=relationships,
        errors=errors,
    )
