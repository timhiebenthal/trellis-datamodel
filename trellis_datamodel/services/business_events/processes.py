"""
Business event processes: grouping events, attaching/detaching them, and
resolving (ungrouping) processes.
"""
import logging
from datetime import datetime
from typing import List, Optional

from trellis_datamodel.exceptions import NotFoundError, ValidationError
from trellis_datamodel.models.business_event import (
    BusinessEvent,
    BusinessEventType,
    BusinessEventProcess,
    BusinessEventAnnotations,
)
from trellis_datamodel.services.business_events.events import (
    parse_business_event_type,
    update_event,
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
)

logger = logging.getLogger(__name__)


def get_process(process_id: str) -> BusinessEventProcess:
    """
    Return one business event process by ID.

    Raises:
        NotFoundError: If process not found
        FileOperationError: If file cannot be read
    """
    for process in load_processes():
        if process.id == process_id:
            return process
    raise NotFoundError(f"Business event process '{process_id}' not found")


def _require_events_exist(event_ids: List[str], events: List[BusinessEvent]) -> None:
    """Raise NotFoundError naming every requested event ID that does not exist."""
    existing_event_ids = {e.id for e in events}
    invalid_ids = [eid for eid in event_ids if eid not in existing_event_ids]
    if invalid_ids:
        raise NotFoundError(f"Events not found: {', '.join(invalid_ids)}")


def _require_event_ids(event_ids: List[str]) -> None:
    """Reject an empty event ID list in attach/detach/update requests."""
    if not event_ids:
        raise ValidationError("event_ids list cannot be empty")


def attach_events_to_process(process_id: str, event_ids: List[str]) -> BusinessEventProcess:
    """
    Attach events to a process.

    Args:
        process_id: ID of process
        event_ids: List of event IDs to attach

    Returns:
        Updated BusinessEventProcess object

    Raises:
        NotFoundError: If process or any event not found
        ValidationError: If event_ids is empty, events are already in another
            process, or process is resolved
        FileOperationError: If file operations fail
    """
    _require_event_ids(event_ids)
    _require_events_exist(event_ids, load_business_events())

    processes = load_processes()
    process_index = None
    for i, process in enumerate(processes):
        if process.id == process_id:
            process_index = i
            break

    if process_index is None:
        raise NotFoundError(f"Process '{process_id}' not found")

    process = processes[process_index]

    # Don't allow attaching to resolved processes
    if process.resolved_at is not None:
        raise ValidationError(f"Cannot attach events to resolved process '{process_id}'")

    # Validate events aren't already in another process
    events = load_business_events()
    for event_id in event_ids:
        for e in events:
            if e.id == event_id and e.process_id is not None and e.process_id != process_id:
                raise ValidationError(
                    f"Event '{event_id}' is already attached to process '{e.process_id}'"
                )

    # Attach events
    for event_id in event_ids:
        if event_id not in process.event_ids:
            process.event_ids.append(event_id)

        # Update event's process_id
        events = load_business_events()
        for i, event in enumerate(events):
            if event.id == event_id:
                events[i].process_id = process_id
                events[i].updated_at = datetime.now()
                break
        save_business_events(events)

    process.updated_at = datetime.now()
    processes[process_index] = process
    save_processes(processes)
    logger.info(f"Attached {len(event_ids)} events to process: {process_id}")
    return process


def detach_events_from_process(process_id: str, event_ids: List[str]) -> BusinessEventProcess:
    """
    Detach events from a process.

    Args:
        process_id: ID of process
        event_ids: List of event IDs to detach

    Returns:
        Updated BusinessEventProcess object

    Raises:
        NotFoundError: If process not found
        ValidationError: If event_ids is empty
        FileOperationError: If file operations fail
    """
    _require_event_ids(event_ids)

    processes = load_processes()
    process_index = None
    for i, process in enumerate(processes):
        if process.id == process_id:
            process_index = i
            break

    if process_index is None:
        raise NotFoundError(f"Process '{process_id}' not found")

    process = processes[process_index]

    # Detach events
    original_count = len(process.event_ids)
    process.event_ids = [eid for eid in process.event_ids if eid not in event_ids]

    # Update events' process_id
    events = load_business_events()
    for i, event in enumerate(events):
        if event.id in event_ids and event.process_id == process_id:
            events[i].process_id = None
            events[i].updated_at = datetime.now()
    save_business_events(events)

    process.updated_at = datetime.now()
    processes[process_index] = process
    save_processes(processes)
    logger.info(f"Detached {original_count - len(process.event_ids)} events from process: {process_id}")
    return process


def _require_process_domain(domain: Optional[str]) -> str:
    """
    Validate that a process domain is provided and return the normalized value.
    """
    if not isinstance(domain, str) or not domain.strip():
        raise ValidationError("Process domain is required")
    return domain.strip()


def create_process(
    name: str,
    type: BusinessEventType | str,
    domain: str,
    event_ids: Optional[List[str]],
    description: Optional[str] = None,
) -> BusinessEventProcess:
    """
    Create a new business event process with auto-generated ID.

    Args:
        name: Process name
        type: Process type (discrete, evolving, recurring)
        domain: Business domain for the process
        event_ids: List of event IDs to include in this process

    Returns:
        New BusinessEventProcess object with computed annotations superset

    Raises:
        ValidationError: If type or name is invalid, domain is missing,
            event_ids is empty, or an event already belongs to a process
        NotFoundError: If any event_id doesn't exist
        FileOperationError: If file operations fail
    """
    type = parse_business_event_type(type, "process")

    events = load_business_events()
    if event_ids:
        _require_events_exist(event_ids, events)
        for event in events:
            if event.id in event_ids and event.process_id is not None:
                raise ValidationError(
                    f"Event '{event.id}' is already attached to process '{event.process_id}'"
                )

    domain_value = _require_process_domain(domain)

    if not name or not name.strip():
        raise ValidationError("Process name is required")

    if not event_ids:
        raise ValidationError("At least one event ID is required")

    # Generate ID: proc_YYYYMMDD_NNN
    today = datetime.now().strftime("%Y%m%d")
    processes = load_processes()
    # Find highest number for today
    max_num = 0
    for proc in processes:
        if proc.id.startswith(f"proc_{today}_"):
            try:
                num = int(proc.id.split("_")[-1])
                max_num = max(max_num, num)
            except ValueError:
                pass
    new_id = f"proc_{today}_{max_num + 1:03d}"

    # Get events for this process
    process_events = [e for e in events if e.id in event_ids]

    # Compute annotations superset
    annotations_superset = _compute_annotation_union(process_events)

    now = datetime.now()
    new_process = BusinessEventProcess(
        id=new_id,
        name=name.strip(),
        description=description.strip() if description else None,
        type=type,
        domain=domain_value,
        event_ids=event_ids,
        created_at=now,
        updated_at=now,
        resolved_at=None,
        annotations_superset=annotations_superset,
        derived_entities=[],
    )

    # Update events to link them to this process
    for event_id in event_ids:
        update_event(event_id, {"process_id": new_id})

    # Save process
    processes.append(new_process)
    save_processes(processes)
    logger.info(
        f"Created business event process: {new_id} (type: {type.value}, domain: {domain_value})"
    )
    return new_process


def _validate_process_updates(updates: dict) -> None:
    """Reject an update request before the process is looked up."""
    if "type" in updates:
        parse_business_event_type(updates["type"], "process")
    if "domain" in updates:
        domain = updates["domain"]
        if not isinstance(domain, str) or not domain.strip():
            raise ValidationError("Process domain cannot be empty")
    if "event_ids" in updates:
        _require_event_ids(updates["event_ids"])
    if not updates:
        raise ValidationError("No fields provided to update")


def update_process(process_id: str, updates: dict) -> BusinessEventProcess:
    """
    Update an existing business event process.

    Args:
        process_id: ID of process to update
        updates: Dictionary with fields to update (name, type, domain, event_ids)

    Returns:
        Updated BusinessEventProcess object

    Raises:
        NotFoundError: If process not found
        ValidationError: If updates are empty or invalid
        FileOperationError: If file operations fail
    """
    _validate_process_updates(updates)

    processes = load_processes()
    process_index = None
    for i, proc in enumerate(processes):
        if proc.id == process_id:
            process_index = i
            break

    if process_index is None:
        raise NotFoundError(f"Business event process '{process_id}' not found")

    process = processes[process_index]

    # Check if process is resolved
    if process.resolved_at is not None:
        raise ValidationError("Cannot update a resolved process")

    # Update fields
    if "name" in updates:
        name = updates["name"]
        if not name or not name.strip():
            raise ValidationError("Process name cannot be empty")
        process.name = name.strip()

    if "description" in updates:
        description_value = updates["description"]
        process.description = description_value.strip() if description_value and isinstance(description_value, str) else None

    if "type" in updates:
        process.type = BusinessEventType(updates["type"])

    if "domain" in updates:
        process.domain = _require_process_domain(updates["domain"])

    if "annotations_superset" in updates:
        annotations_value = updates["annotations_superset"]
        if annotations_value is None:
            process.annotations_superset = None
        elif isinstance(annotations_value, BusinessEventAnnotations):
            process.annotations_superset = annotations_value
            # Sync roles from process annotations to dimension entities
            _sync_roles_to_dimensions(annotations_value)
        else:
            process.annotations_superset = BusinessEventAnnotations(**annotations_value)
            # Sync roles from process annotations to dimension entities
            _sync_roles_to_dimensions(process.annotations_superset)

    if "derived_entities" in updates:
        from trellis_datamodel.models.business_event import DerivedEntity

        process.derived_entities = [
            DerivedEntity(**de) for de in updates["derived_entities"]
        ]

    old_event_ids = set(process.event_ids)
    if "event_ids" in updates:
        new_event_ids = updates["event_ids"]

        # Validate all events exist
        events = load_business_events()
        existing_event_ids = {event.id for event in events}
        for event_id in new_event_ids:
            if event_id not in existing_event_ids:
                raise NotFoundError(f"Business event '{event_id}' not found")
        
        process.event_ids = new_event_ids
        new_event_ids_set = set(new_event_ids)

        # Update event links: remove process_id from events no longer in process
        for event_id in old_event_ids - new_event_ids_set:
            event = next((e for e in events if e.id == event_id), None)
            if event and event.process_id == process_id:
                update_event(event_id, {"process_id": None})

        # Add process_id to newly added events
        for event_id in new_event_ids_set - old_event_ids:
            update_event(event_id, {"process_id": process_id})

    # Recompute annotations superset if event_ids changed
    if "event_ids" in updates:
        events = load_business_events()
        process_events = [e for e in events if e.id in process.event_ids]
        process.annotations_superset = _compute_annotation_union(process_events)

    process.updated_at = datetime.now()

    # Validate updated process
    try:
        updated_process = BusinessEventProcess(**process.model_dump())
    except Exception as e:
        raise ValidationError(f"Invalid process data: {str(e)}") from e

    processes[process_index] = updated_process
    save_processes(processes)
    logger.info(f"Updated business event process: {process_id}")
    return updated_process


def resolve_process(process_id: str) -> BusinessEventProcess:
    """
    Resolve (ungroup) a business event process.

    This removes the grouping by:
    - Setting resolved_at timestamp
    - Removing process_id from all member events
    - Preserving the process record for history

    Args:
        process_id: ID of process to resolve

    Returns:
        Resolved BusinessEventProcess object

    Raises:
        NotFoundError: If process not found
        ValidationError: If process is already resolved
        FileOperationError: If file operations fail
    """
    processes = load_processes()
    process_index = None
    for i, proc in enumerate(processes):
        if proc.id == process_id:
            process_index = i
            break

    if process_index is None:
        raise NotFoundError(f"Business event process '{process_id}' not found")

    process = processes[process_index]

    if process.resolved_at is not None:
        raise ValidationError("Process is already resolved")

    # Mark process as resolved FIRST (before detaching events)
    # This allows the process to have empty event_ids without validation error
    process.resolved_at = datetime.now()
    process.updated_at = datetime.now()
    process.annotations_superset = None
    process.derived_entities = []  # Clear derived entities when resolving
    processes[process_index] = process
    save_processes(processes)

    # Now detach all events so process_id is cleared from events
    # Note: detach_events_from_process will reload and save processes again,
    # but since resolved_at is set, empty event_ids is valid
    if process.event_ids:
        event_ids_to_detach = list(process.event_ids)
        detach_events_from_process(process_id, event_ids_to_detach)

    # Reload to get final state
    processes = load_processes()
    process_index = None
    for i, proc in enumerate(processes):
        if proc.id == process_id:
            process_index = i
            break

    if process_index is None:
        raise NotFoundError(f"Business event process '{process_id}' not found")

    process = processes[process_index]
    save_processes(processes)
    logger.info(f"Resolved business event process: {process_id}")
    return process
