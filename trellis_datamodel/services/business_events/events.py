"""
CRUD operations for business events.

Business events capture business processes (e.g., "customer buys product")
and can be annotated with categories (Who, What, When, Where, How, How Many,
Why) for entity generation.
"""
import logging
from datetime import datetime
from typing import List, Optional

from trellis_datamodel.exceptions import NotFoundError, ValidationError
from trellis_datamodel.models.business_event import (
    BusinessEvent,
    BusinessEventType,
    BusinessEventAnnotations,
)
from trellis_datamodel.services.business_events.role_sync import (
    _sync_roles_to_dimensions,
)
from trellis_datamodel.services.business_events.storage import (
    load_business_events,
    load_processes,
    save_business_events,
    save_processes,
)
from trellis_datamodel.services.business_events.supersets import (
    _compute_annotation_union,
    recompute_process_superset,
)

logger = logging.getLogger(__name__)


def get_unique_domains() -> List[str]:
    """
    Get unique domain values from all business events.

    Returns:
        Sorted list of unique domain strings (excluding None/null values)
    """
    events = load_business_events()
    domains = set()
    for event in events:
        if event.domain:
            domains.add(event.domain)
    return sorted(list(domains))


def parse_business_event_type(value: BusinessEventType | str, kind: str) -> BusinessEventType:
    """
    Parse an event or process type, naming the allowed values on failure.

    Args:
        value: Raw type value from the request
        kind: "event" or "process", used in the error message

    Raises:
        ValidationError: If the value is not a known BusinessEventType
    """
    try:
        return BusinessEventType(value)
    except ValueError:
        raise ValidationError(
            f"Invalid {kind} type: {value}. Must be one of: discrete, evolving, recurring"
        ) from None


def get_event(event_id: str) -> BusinessEvent:
    """
    Return one business event by ID.

    Raises:
        NotFoundError: If event not found
        FileOperationError: If file cannot be read
    """
    for event in load_business_events():
        if event.id == event_id:
            return event
    raise NotFoundError(f"Business event '{event_id}' not found")


def create_event(
    text: str,
    type: BusinessEventType | str | None = None,
    domain: Optional[str] = None,
    description: Optional[str] = None,
) -> BusinessEvent:
    """
    Create a new business event with auto-generated ID.

    Args:
        text: Event description text
        type: Event type (discrete, evolving, recurring); None means discrete
        domain: Optional business domain

    Returns:
        New BusinessEvent object with empty 7 Ws structure

    Raises:
        ValidationError: If type or text is invalid
        FileOperationError: If file operations fail
    """
    type = parse_business_event_type(
        type if type is not None else BusinessEventType.DISCRETE, "event"
    )
    if not text or not text.strip():
        raise ValidationError("Event text is required")

    # Generate ID: evt_YYYYMMDD_NNN
    today = datetime.now().strftime("%Y%m%d")
    events = load_business_events()
    # Find highest number for today
    max_num = 0
    for event in events:
        if event.id.startswith(f"evt_{today}_"):
            try:
                num = int(event.id.split("_")[-1])
                max_num = max(max_num, num)
            except ValueError:
                pass
    new_id = f"evt_{today}_{max_num + 1:03d}"

    now = datetime.now()
    new_event = BusinessEvent(
        id=new_id,
        text=text.strip(),
        description=description.strip() if description else None,
        type=type,
        domain=domain.strip() if domain else None,
        created_at=now,
        updated_at=now,
        annotations=BusinessEventAnnotations(),
        derived_entities=[],
    )

    events.append(new_event)
    save_business_events(events)
    logger.info(f"Created business event: {new_id} (type: {type.value})")
    return new_event


def update_event(event_id: str, updates: dict) -> BusinessEvent:
    """
    Update an existing business event.

    Args:
        event_id: ID of event to update
        updates: Dictionary with fields to update (text, type, domain, annotations, derived_entities, process_id)

    Returns:
        Updated BusinessEvent object

    Raises:
        NotFoundError: If event not found
        ValidationError: If updates are invalid
        FileOperationError: If file operations fail
    """
    events = load_business_events()
    event_index = None
    for i, event in enumerate(events):
        if event.id == event_id:
            event_index = i
            break

    if event_index is None:
        raise NotFoundError(f"Business event '{event_id}' not found")

    event = events[event_index]

    # Update fields
    if "text" in updates:
        text = updates["text"]
        if not text or not text.strip():
            raise ValidationError("Event text cannot be empty")
        event.text = text.strip()

    if "description" in updates:
        description_value = updates["description"]
        event.description = description_value.strip() if description_value and isinstance(description_value, str) else None

    if "type" in updates:
        try:
            event.type = BusinessEventType(updates["type"])
        except ValueError:
            raise ValidationError(f"Invalid event type: {updates['type']}")

    if "domain" in updates:
        domain_value = updates["domain"]
        # Allow setting to None/empty string to clear domain
        if domain_value is None or (
            isinstance(domain_value, str) and not domain_value.strip()
        ):
            event.domain = None
        else:
            event.domain = (
                domain_value.strip() if isinstance(domain_value, str) else domain_value
            )

    if "derived_entities" in updates:
        from trellis_datamodel.models.business_event import DerivedEntity

        event.derived_entities = [
            DerivedEntity(**de) for de in updates["derived_entities"]
        ]

    if "annotations" in updates:
        event.annotations = BusinessEventAnnotations(**updates["annotations"])
        # Sync roles from annotations to dimension entities
        _sync_roles_to_dimensions(event.annotations)

    # Track if we need to recompute process superset
    old_process_id = event.process_id
    annotations_changed = "annotations" in updates
    process_id_changed = "process_id" in updates

    if process_id_changed:
        process_value = updates["process_id"]
        if process_value is None or (
            isinstance(process_value, str) and not process_value.strip()
        ):
            event.process_id = None
        else:
            event.process_id = process_value

    event.updated_at = datetime.now()

    # Validate updated event
    try:
        updated_event = BusinessEvent(**event.model_dump())
    except Exception as e:
        raise ValidationError(f"Invalid event data: {str(e)}") from e

    events[event_index] = updated_event
    save_business_events(events)
    logger.info(f"Updated business event: {event_id}")

    # Recompute process supersets if needed
    if annotations_changed or process_id_changed:
        # Recompute for old process if event was moved or annotations changed
        if old_process_id:
            try:
                recompute_process_superset(old_process_id)
            except NotFoundError:
                # Process might have been deleted, ignore
                pass
            except Exception as e:
                logger.warning(f"Failed to recompute superset for old process {old_process_id}: {e}")

        # Recompute for new process if event was moved
        new_process_id = updated_event.process_id
        if process_id_changed and new_process_id and new_process_id != old_process_id:
            try:
                recompute_process_superset(new_process_id)
            except NotFoundError:
                # Process might not exist yet, ignore
                pass
            except Exception as e:
                logger.warning(f"Failed to recompute superset for new process {new_process_id}: {e}")

    return updated_event


def delete_event(event_id: str) -> None:
    """
    Delete a business event.

    If the event was part of a process, the process superset will be recomputed.

    Args:
        event_id: ID of event to delete

    Raises:
        NotFoundError: If event not found
        FileOperationError: If file operations fail
    """
    events = load_business_events()
    event_to_delete = None
    for event in events:
        if event.id == event_id:
            event_to_delete = event
            break

    if event_to_delete is None:
        raise NotFoundError(f"Business event '{event_id}' not found")

    # Track process_id before deletion
    process_id = event_to_delete.process_id

    events = [e for e in events if e.id != event_id]
    save_business_events(events)
    logger.info(f"Deleted business event: {event_id}")

    # Recompute process superset if event was part of a process
    if process_id:
        try:
            # Remove event from process's event_ids list
            processes = load_processes()
            process_index = None
            for i, proc in enumerate(processes):
                if proc.id == process_id:
                    process_index = i
                    break

            if process_index is not None:
                process = processes[process_index]
                if event_id in process.event_ids:
                    process.event_ids = [eid for eid in process.event_ids if eid != event_id]
                    # Only recompute if process still has events
                    if process.event_ids:
                        process.annotations_superset = _compute_annotation_union(
                            [e for e in load_business_events() if e.id in process.event_ids]
                        )
                        process.updated_at = datetime.now()
                    else:
                        # Process has no events left, resolve it
                        process.resolved_at = datetime.now()
                        process.updated_at = datetime.now()
                    save_processes(processes)
        except Exception as e:
            logger.warning(f"Failed to update process after event deletion: {e}")
