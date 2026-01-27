"""
Business Events service for dimensional modeling.

Handles CRUD operations for business events stored in YAML files.
Business events capture business processes (e.g., "customer buys product")
and can be annotated with categories (Who, What, When, Where, How, How Many, Why)
for entity generation.

This service:
- Loads and saves business events from/to YAML files
- Provides CRUD operations for events
- Manages annotation entries within events (Who, What, When, Where, How, How Many, Why)
- Validates event data
"""

import logging
import os
from datetime import datetime
from typing import Dict, List, Optional

import yaml

from trellis_datamodel import config as cfg
from trellis_datamodel.exceptions import (
    ConfigurationError,
    FileOperationError,
    ValidationError,
    NotFoundError,
)
from trellis_datamodel.models.business_event import (
    BusinessEvent,
    BusinessEventType,
    BusinessEventsFile,
    BusinessEventProcess,
    BusinessEventProcessFile,
    AnnotationEntry,
    BusinessEventAnnotations,
)

logger = logging.getLogger(__name__)


def _get_business_events_path() -> str:
    """
    Get the path to business_events.yml file.

    Returns BUSINESS_EVENTS_PATH if set, otherwise defaults to same directory
    as DATA_MODEL_PATH with filename 'business_events.yml'.
    """
    if cfg.BUSINESS_EVENTS_PATH:
        return cfg.BUSINESS_EVENTS_PATH

    # Default to same directory as data_model.yml
    if cfg.DATA_MODEL_PATH:
        data_model_dir = os.path.dirname(cfg.DATA_MODEL_PATH)
        return os.path.abspath(os.path.join(data_model_dir, "business_events.yml"))

    # Fallback to current directory
    return os.path.abspath("business_events.yml")


def load_business_events(path: Optional[str] = None) -> List[BusinessEvent]:
    """
    Load business events from YAML file.

    Args:
        path: Optional path to business_events.yml. If not provided, uses
              configured BUSINESS_EVENTS_PATH or default location.

    Returns:
        List of BusinessEvent objects.

    Raises:
        FileOperationError: If file exists but cannot be read or parsed.
    """
    if path is None:
        path = _get_business_events_path()

    # If file doesn't exist, return empty list
    if not os.path.exists(path):
        logger.info(f"Business events file not found at {path}, returning empty list")
        return []

    try:
        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        logger.error(f"YAML parse error in business events file {path}: {e}")
        raise FileOperationError("Invalid business events file format")
    except Exception as e:
        logger.error(f"Error reading business events file {path}: {e}")
        raise FileOperationError(f"Failed to read business events file: {e}")

    # Parse file structure
    try:
        if "events" not in data:
            logger.error(f"Missing 'events' key in business events file {path}")
            raise FileOperationError("Invalid business events file format")
        events_file = BusinessEventsFile(**data)
        return events_file.events
    except Exception as e:
        logger.error(f"Invalid business events file structure in {path}: {e}")
        raise FileOperationError("Invalid business events file format")


def save_business_events(
    events: List[BusinessEvent], path: Optional[str] = None
) -> None:
    """
    Save business events to YAML file.

    This function preserves existing processes when saving events.

    Args:
        events: List of BusinessEvent objects to save.
        path: Optional path to business_events.yml. If not provided, uses
              configured BUSINESS_EVENTS_PATH or default location.

    Raises:
        FileOperationError: If file cannot be written.
    """
    if path is None:
        path = _get_business_events_path()

    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # Load existing processes to preserve them
    existing_processes = []
    if os.path.exists(path):
        try:
            existing_processes = load_processes(path)
        except Exception:
            # If we can't load processes, continue without them
            pass

    # Create file structure with events and processes
    events_file = BusinessEventsFile(events=events, processes=existing_processes)

    try:
        # Convert to dict for YAML serialization
        data = events_file.model_dump(mode="json")

        with open(path, "w") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
        logger.info(f"Saved {len(events)} business events to {path}")
    except Exception as e:
        raise FileOperationError(f"Failed to write business events file: {e}")


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


def create_event(
    text: str, type: BusinessEventType, domain: Optional[str] = None
) -> BusinessEvent:
    """
    Create a new business event with auto-generated ID.

    Args:
        text: Event description text
        type: Event type (discrete, evolving, recurring)
        domain: Optional business domain

    Returns:
        New BusinessEvent object with empty 7 Ws structure

    Raises:
        ValidationError: If text is invalid
        FileOperationError: If file operations fail
    """
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


def update_event_annotations(event_id: str, annotations_data: dict) -> BusinessEvent:
    """
    Update the entire annotations structure for a business event.

    Args:
        event_id: ID of event to update
        annotations_data: Dictionary with annotation structure (who, what, when, where, how, how_many, why)

    Returns:
        Updated BusinessEvent object

    Raises:
        NotFoundError: If event not found
        ValidationError: If annotations data is invalid
        FileOperationError: If file operations fail
    """
    return update_event(event_id, {"annotations": annotations_data})


def add_annotation_entry(
    event_id: str,
    annotation_type: str,
    text: str,
    dimension_id: Optional[str] = None,
    description: Optional[str] = None,
    attributes: Optional[dict] = None,
) -> BusinessEvent:
    """
    Add a new entry to a specific annotation category in a business event.

    Args:
        event_id: ID of event
        annotation_type: Type of annotation ('who', 'what', 'when', 'where', 'how', 'how_many', 'why')
        text: Entry text
        dimension_id: Optional ID of existing dimension entity to link
        description: Optional description
        attributes: Optional additional attributes dict

    Returns:
        Updated BusinessEvent object

    Raises:
        NotFoundError: If event not found
        ValidationError: If annotation_type is invalid or entry_id is not unique
        FileOperationError: If file operations fail
    """
    valid_types = ["who", "what", "when", "where", "how", "how_many", "why"]
    if annotation_type not in valid_types:
        raise ValidationError(
            f"Invalid annotation_type: '{annotation_type}'. Must be one of: {', '.join(valid_types)}"
        )

    if not text or not text.strip():
        raise ValidationError("Entry text is required")

    events = load_business_events()
    event_index = None
    for i, event in enumerate(events):
        if event.id == event_id:
            event_index = i
            break

    if event_index is None:
        raise NotFoundError(f"Business event '{event_id}' not found")

    event = events[event_index]

    # Ensure annotations exists
    if event.annotations is None:
        event.annotations = BusinessEventAnnotations()

    # Generate unique entry_id
    import uuid

    entry_id = f"entry_{uuid.uuid4().hex[:12]}"

    # Check uniqueness across all annotation categories
    all_entry_ids = _collect_all_entry_ids(event.annotations)
    if entry_id in all_entry_ids:
        raise ValidationError(f"Entry ID '{entry_id}' already exists in event")

    # Create new entry
    new_entry = AnnotationEntry(
        id=entry_id,
        text=text.strip(),
        dimension_id=dimension_id,
        description=description,
        attributes=attributes or {},
    )

    # Add to appropriate annotation category
    current_annotations = event.annotations.model_dump()
    category_list = current_annotations.get(annotation_type, [])
    category_list.append(new_entry.model_dump())
    current_annotations[annotation_type] = category_list

    # Update event
    updated_event = update_event(event_id, {"annotations": current_annotations})
    return updated_event


def remove_annotation_entry(event_id: str, entry_id: str) -> BusinessEvent:
    """
    Remove an annotation entry by entry_id from a business event.

    Args:
        event_id: ID of event
        entry_id: ID of entry to remove

    Returns:
        Updated BusinessEvent object

    Raises:
        NotFoundError: If event or entry not found
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

    if event.annotations is None:
        raise NotFoundError(f"Entry '{entry_id}' not found (event has no annotations)")

    # Find and remove entry
    current_annotations = event.annotations.model_dump()
    entry_found = False

    for annotation_type in ["who", "what", "when", "where", "how", "how_many", "why"]:
        category_list = current_annotations.get(annotation_type, [])
        original_length = len(category_list)
        category_list = [
            entry for entry in category_list if entry.get("id") != entry_id
        ]
        current_annotations[annotation_type] = category_list
        if len(category_list) < original_length:
            entry_found = True

    if not entry_found:
        raise NotFoundError(f"Entry '{entry_id}' not found in any annotation category")

    updated_event = update_event(event_id, {"annotations": current_annotations})
    return updated_event


def update_annotation_entry(
    event_id: str,
    entry_id: str,
    text: Optional[str] = None,
    dimension_id: Optional[str] = None,
    description: Optional[str] = None,
    attributes: Optional[dict] = None,
) -> BusinessEvent:
    """
    Update an existing annotation entry in a business event.

    Args:
        event_id: ID of event
        entry_id: ID of entry to update
        text: New text (optional)
        dimension_id: New dimension_id (optional)
        description: New description (optional)
        attributes: New attributes (optional)

    Returns:
        Updated BusinessEvent object

    Raises:
        NotFoundError: If event or entry not found
        ValidationError: If text is invalid
        FileOperationError: If file operations fail
    """
    if text is not None and (not text or not text.strip()):
        raise ValidationError("Entry text cannot be empty")

    events = load_business_events()
    event_index = None
    for i, event in enumerate(events):
        if event.id == event_id:
            event_index = i
            break

    if event_index is None:
        raise NotFoundError(f"Business event '{event_id}' not found")

    event = events[event_index]

    if event.annotations is None:
        raise NotFoundError(f"Entry '{entry_id}' not found (event has no annotations)")

    # Find and update entry
    current_annotations = event.annotations.model_dump()
    entry_found = False

    for annotation_type in ["who", "what", "when", "where", "how", "how_many", "why"]:
        category_list = current_annotations.get(annotation_type, [])
        for entry in category_list:
            if entry.get("id") == entry_id:
                entry_found = True
                if text is not None:
                    entry["text"] = text.strip()
                if dimension_id is not None:
                    entry["dimension_id"] = dimension_id
                if description is not None:
                    entry["description"] = description
                if attributes is not None:
                    entry["attributes"] = attributes
                break

    if not entry_found:
        raise NotFoundError(f"Entry '{entry_id}' not found in any annotation category")

    updated_event = update_event(event_id, {"annotations": current_annotations})
    return updated_event


def _collect_all_entry_ids(annotations: BusinessEventAnnotations) -> set:
    """
    Collect all entry IDs from an annotations structure.

    Args:
        annotations: BusinessEventAnnotations object

    Returns:
        Set of entry IDs
    """
    entry_ids = set()
    for annotation_type in ["who", "what", "when", "where", "how", "how_many", "why"]:
        category_list = getattr(annotations, annotation_type, [])
        for entry in category_list:
            if hasattr(entry, "id"):
                entry_ids.add(entry.id)
    return entry_ids


def _get_processes_path() -> str:
    """
    Get the path to processes YAML file (same as business_events.yml).

    Returns BUSINESS_EVENTS_PATH if set, otherwise defaults to same directory
    as DATA_MODEL_PATH with filename 'business_events.yml'.
    """
    return _get_business_events_path()


def load_processes(path: Optional[str] = None) -> List[BusinessEventProcess]:
    """
    Load business event processes from YAML file.

    Args:
        path: Optional path to business_events.yml. If not provided, uses
              configured BUSINESS_EVENTS_PATH or default location.

    Returns:
        List of BusinessEventProcess objects.

    Raises:
        FileOperationError: If file exists but cannot be read or parsed.
    """
    if path is None:
        path = _get_processes_path()

    # If file doesn't exist, return empty list
    if not os.path.exists(path):
        logger.info(f"Business events file not found at {path}, returning empty processes list")
        return []

    try:
        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        logger.error(f"YAML parse error in business events file {path}: {e}")
        raise FileOperationError("Invalid business events file format")
    except Exception as e:
        logger.error(f"Error reading business events file {path}: {e}")
        raise FileOperationError(f"Failed to read business events file: {e}")

    # Parse processes section
    try:
        if "processes" not in data:
            return []
        processes_file = BusinessEventProcessFile(**{"processes": data["processes"]})
        return processes_file.processes
    except Exception as e:
        logger.error(f"Invalid processes structure in {path}: {e}")
        raise FileOperationError("Invalid business events file format")


def save_processes(
    processes: List[BusinessEventProcess], path: Optional[str] = None
) -> None:
    """
    Save business event processes to YAML file.

    Args:
        processes: List of BusinessEventProcess objects to save.
        path: Optional path to business_events.yml. If not provided, uses
              configured BUSINESS_EVENTS_PATH or default location.

    Raises:
        FileOperationError: If file cannot be written.
    """
    if path is None:
        path = _get_processes_path()

    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # Load existing file data to preserve events section
    existing_data = {}
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                existing_data = yaml.safe_load(f) or {}
        except Exception:
            pass  # If we can't read, we'll create new file

    # Create processes file structure
    processes_file = BusinessEventProcessFile(processes=processes)

    try:
        # Merge with existing data (preserve events)
        data = existing_data.copy()
        data["processes"] = processes_file.model_dump(mode="json")["processes"]

        with open(path, "w") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
        logger.info(f"Saved {len(processes)} processes to {path}")
    except Exception as e:
        raise FileOperationError(f"Failed to write processes file: {e}")


def update_process(process_id: str, updates: dict) -> BusinessEventProcess:
    """
    Update an existing business event process.

    Args:
        process_id: ID of process to update
        updates: Dictionary with fields to update (name, type, domain)

    Returns:
        Updated BusinessEventProcess object

    Raises:
        NotFoundError: If process not found
        ValidationError: If updates are invalid
        FileOperationError: If file operations fail
    """
    processes = load_processes()
    process_index = None
    for i, process in enumerate(processes):
        if process.id == process_id:
            process_index = i
            break

    if process_index is None:
        raise NotFoundError(f"Process '{process_id}' not found")

    process = processes[process_index]

    # Don't allow updating resolved processes
    if process.resolved_at is not None:
        raise ValidationError(f"Cannot update resolved process '{process_id}'")

    # Update fields
    if "name" in updates:
        name = updates["name"]
        if not name or not name.strip():
            raise ValidationError("Process name cannot be empty")
        process.name = name.strip()

    if "type" in updates:
        try:
            process.type = BusinessEventType(updates["type"])
        except ValueError:
            raise ValidationError(f"Invalid process type: {updates['type']}")

    if "domain" in updates:
        domain_value = updates["domain"]
        if domain_value is None or (
            isinstance(domain_value, str) and not domain_value.strip()
        ):
            raise ValidationError("Process domain cannot be empty")
        process.domain = domain_value.strip()

    process.updated_at = datetime.now()

    # Validate updated process
    try:
        updated_process = BusinessEventProcess(**process.model_dump())
    except Exception as e:
        raise ValidationError(f"Invalid process data: {str(e)}") from e

    processes[process_index] = updated_process
    save_processes(processes)
    logger.info(f"Updated process: {process_id}")
    return updated_process


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
        ValidationError: If events are already in another process or process is resolved
        FileOperationError: If file operations fail
    """
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

    # Validate events exist and aren't already in another process
    events = load_business_events()
    existing_event_ids = {e.id for e in events}
    for event_id in event_ids:
        if event_id not in existing_event_ids:
            raise NotFoundError(f"Event '{event_id}' not found")

        # Check if event is already in another process
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
        FileOperationError: If file operations fail
    """
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


# ============================================================================
# Process Management Functions
# ============================================================================


def load_processes(path: Optional[str] = None) -> List[BusinessEventProcess]:
    """
    Load business event processes from YAML file.

    Processes are stored in the same file as events, under a 'processes' key.

    Args:
        path: Optional path to business_events.yml. If not provided, uses
              configured BUSINESS_EVENTS_PATH or default location.

    Returns:
        List of BusinessEventProcess objects.

    Raises:
        FileOperationError: If file exists but cannot be read or parsed.
    """
    if path is None:
        path = _get_business_events_path()

    # If file doesn't exist, return empty list
    if not os.path.exists(path):
        logger.info(f"Business events file not found at {path}, returning empty processes list")
        return []

    try:
        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        logger.error(f"YAML parse error in business events file {path}: {e}")
        raise FileOperationError("Invalid business events file format")
    except Exception as e:
        logger.error(f"Error reading business events file {path}: {e}")
        raise FileOperationError(f"Failed to read business events file: {e}")

    # Parse file structure
    try:
        processes_data = data.get("processes", [])
        if not processes_data:
            return []
        
        processes = []
        for proc_data in processes_data:
            # Handle resolved_at being None
            if "resolved_at" in proc_data and proc_data["resolved_at"] is None:
                proc_data = {k: v for k, v in proc_data.items() if k != "resolved_at"}
            processes.append(BusinessEventProcess(**proc_data))
        return processes
    except Exception as e:
        logger.error(f"Invalid processes structure in {path}: {e}")
        raise FileOperationError("Invalid business events file format")


def save_processes(
    processes: List[BusinessEventProcess], path: Optional[str] = None
) -> None:
    """
    Save business event processes to YAML file.

    Processes are saved alongside events in the same file, under a 'processes' key.
    This function preserves existing events and only updates the processes section.

    Args:
        processes: List of BusinessEventProcess objects to save.
        path: Optional path to business_events.yml. If not provided, uses
              configured BUSINESS_EVENTS_PATH or default location.

    Raises:
        FileOperationError: If file cannot be written.
    """
    if path is None:
        path = _get_business_events_path()

    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(path), exist_ok=True)

    # Load existing events to preserve them
    existing_events = []
    if os.path.exists(path):
        try:
            existing_events = load_business_events(path)
        except Exception:
            # If we can't load events, continue without them
            pass

    # Create file structure with events and processes
    events_file = BusinessEventsFile(events=existing_events, processes=processes)

    try:
        # Convert to dict for YAML serialization
        data = events_file.model_dump(mode="json")

        with open(path, "w") as f:
            yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
        logger.info(f"Saved {len(processes)} business event processes to {path}")
    except Exception as e:
        raise FileOperationError(f"Failed to write business events file: {e}")


def _compute_annotation_union(
    events: List[BusinessEvent],
) -> BusinessEventAnnotations:
    """
    Compute the union of annotations from multiple events.

    Union rules:
    - Unique key: `annotation_type + dimension_id` when `dimension_id` exists
    - Fallback unique key: `annotation_type + normalized text + description`
    - Preserve original entries even if duplicates collapse at the process level

    Args:
        events: List of BusinessEvent objects to union

    Returns:
        BusinessEventAnnotations with unioned entries
    """
    annotation_types = ["who", "what", "when", "where", "how", "how_many", "why"]
    annotations_by_type: Dict[str, List[AnnotationEntry]] = {t: [] for t in annotation_types}

    def _normalize_key(entry: AnnotationEntry) -> tuple[str, str]:
        normalized_text = entry.text.lower().strip() if entry.text else ""
        normalized_desc = entry.description.lower().strip() if entry.description else ""
        return normalized_text, normalized_desc

    for annotation_type in annotation_types:
        seen_by_dimension: Dict[str, int] = {}
        seen_by_text_no_dim: Dict[tuple[str, str], int] = {}
        seen_text_with_dim: set[tuple[str, str]] = set()

        for event in events:
            if not event.annotations:
                continue

            category_list = getattr(event.annotations, annotation_type, [])
            for entry in category_list:
                text_key = _normalize_key(entry)

                if entry.dimension_id:
                    if entry.dimension_id in seen_by_dimension:
                        continue

                    if text_key in seen_by_text_no_dim:
                        index = seen_by_text_no_dim.pop(text_key)
                        annotations_by_type[annotation_type][index] = entry
                        seen_by_dimension[entry.dimension_id] = index
                    else:
                        index = len(annotations_by_type[annotation_type])
                        annotations_by_type[annotation_type].append(entry)
                        seen_by_dimension[entry.dimension_id] = index

                    seen_text_with_dim.add(text_key)
                else:
                    if text_key in seen_by_text_no_dim:
                        continue
                    if text_key in seen_text_with_dim:
                        continue

                    index = len(annotations_by_type[annotation_type])
                    annotations_by_type[annotation_type].append(entry)
                    seen_by_text_no_dim[text_key] = index

    result = BusinessEventAnnotations()
    for annotation_type in annotation_types:
        setattr(result, annotation_type, annotations_by_type[annotation_type])

    return result


def _require_process_domain(domain: Optional[str]) -> str:
    """
    Validate that a process domain is provided and return the normalized value.
    """
    if not isinstance(domain, str) or not domain.strip():
        raise ValidationError("Process domain is required")
    return domain.strip()


def create_process(
    name: str,
    type: BusinessEventType,
    domain: str,
    event_ids: List[str],
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
        ValidationError: If name is invalid, domain is missing, or event_ids is empty
        NotFoundError: If any event_id doesn't exist
        FileOperationError: If file operations fail
    """
    if not name or not name.strip():
        raise ValidationError("Process name is required")

    if not event_ids:
        raise ValidationError("At least one event ID is required")

    domain_value = _require_process_domain(domain)

    # Validate all events exist
    events = load_business_events()
    existing_event_ids = {event.id for event in events}
    for event_id in event_ids:
        if event_id not in existing_event_ids:
            raise NotFoundError(f"Business event '{event_id}' not found")

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
        type=type,
        domain=domain_value,
        event_ids=event_ids,
        created_at=now,
        updated_at=now,
        resolved_at=None,
        annotations_superset=annotations_superset,
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
        ValidationError: If updates are invalid
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

    # Check if process is resolved
    if process.resolved_at is not None:
        raise ValidationError("Cannot update a resolved process")

    # Update fields
    if "name" in updates:
        name = updates["name"]
        if not name or not name.strip():
            raise ValidationError("Process name cannot be empty")
        process.name = name.strip()

    if "type" in updates:
        try:
            process.type = BusinessEventType(updates["type"])
        except ValueError:
            raise ValidationError(f"Invalid process type: {updates['type']}")

    if "domain" in updates:
        process.domain = _require_process_domain(updates["domain"])

    if "annotations_superset" in updates:
        annotations_value = updates["annotations_superset"]
        if annotations_value is None:
            process.annotations_superset = None
        elif isinstance(annotations_value, BusinessEventAnnotations):
            process.annotations_superset = annotations_value
        else:
            process.annotations_superset = BusinessEventAnnotations(**annotations_value)

    old_event_ids = set(process.event_ids)
    if "event_ids" in updates:
        new_event_ids = updates["event_ids"]
        if not new_event_ids:
            raise ValidationError("Process must have at least one event")
        
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


def recompute_process_superset(process_id: str) -> BusinessEventProcess:
    """
    Recompute the annotations superset for a process.

    This should be called when:
    - An event's annotations are updated
    - Events are added/removed from a process

    Args:
        process_id: ID of process to recompute

    Returns:
        Updated BusinessEventProcess object

    Raises:
        NotFoundError: If process not found
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

    # Skip if resolved
    if process.resolved_at is not None:
        return process

    # Get current events for this process
    events = load_business_events()
    process_events = [e for e in events if e.id in process.event_ids]

    # Recompute superset
    process.annotations_superset = _compute_annotation_union(process_events)
    process.updated_at = datetime.now()

    processes[process_index] = process
    save_processes(processes)
    logger.info(f"Recomputed annotations superset for process: {process_id}")
    return process


def recompute_all_process_supersets() -> None:
    """
    Recompute annotations supersets for all active (non-resolved) processes.

    Useful after bulk event updates or migrations.
    """
    processes = load_processes()
    active_processes = [p for p in processes if p.resolved_at is None]

    for process in active_processes:
        try:
            recompute_process_superset(process.id)
        except Exception as e:
            logger.warning(f"Failed to recompute superset for process {process.id}: {e}")
