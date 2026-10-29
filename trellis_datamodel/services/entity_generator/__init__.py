"""
Entity Generator service for business events.

Generates dimensional entities (dimensions and facts) from business events with
annotation entries. This service converts annotation entries into entity definitions
with proper naming, labels, and relationships following dimensional modeling conventions.

Modules:
- common: naming helpers, model binding and existing-entity lookup
- dimensional: dimensions and facts for the dimensional modeling style
- entity_model: one entity per event or process for the entity modeling style
"""

import logging

from trellis_datamodel.models.business_event import (
    BusinessEvent,
    BusinessEventProcess,
    GeneratedEntitiesResult,
)
from trellis_datamodel.services.business_events import load_business_events
from trellis_datamodel.services.entity_generator.common import (
    _bind_result_to_models,
    _is_entity_model,
    bind_entities_to_models,
    slugify_domain,
)
from trellis_datamodel.services.entity_generator.dimensional import (
    _generate_from_annotations,
    _generate_from_process,
)
from trellis_datamodel.services.entity_generator.entity_model import (
    _generate_from_annotations_entity_model,
    _generate_from_process_entity_model,
)

logger = logging.getLogger(__name__)

__all__ = [
    "bind_entities_to_models",
    "generate_entities_from_event",
    "generate_entities_from_process",
    "slugify_domain",
]


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
        if _is_entity_model(config):
            return _generate_from_annotations_entity_model(event, config)
        return _bind_result_to_models(_generate_from_annotations(event, config))
    else:
        errors.append("Event must have annotation entries")
        return GeneratedEntitiesResult(entities=[], relationships=[], errors=errors)


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

    if _is_entity_model(config):
        return _generate_from_process_entity_model(process, process_events, config)

    return _bind_result_to_models(
        _generate_from_process(process, process_events, config)
    )
