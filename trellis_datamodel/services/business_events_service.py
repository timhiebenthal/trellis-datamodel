"""
Business Events service for dimensional modeling.

Handles CRUD operations for business events stored in YAML files.
Business events capture business processes (e.g., "customer buys product")
and can be structured with the 7 Ws framework (Who, What, When, Where, How, How Many, Why)
or annotated with dimensions and facts for entity generation.

This service:
- Loads and saves business events from/to YAML files
- Provides CRUD operations for events
- Manages 7 Ws entries within events (Who, What, When, Where, How, How Many, Why)
- Manages legacy annotations within events (deprecated)
- Validates event data and prevents overlapping annotations
"""

import logging
import os
from datetime import datetime
from typing import List, Optional

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
    Annotation,
    BusinessEventsFile,
    SevenWsEntry,
    BusinessEventSevenWs,
)

logger = logging.getLogger(__name__)
_ANNOTATIONS_DEPRECATION_LOGGED = False


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
        events_file = BusinessEventsFile(**data)
        events = events_file.events
        global _ANNOTATIONS_DEPRECATION_LOGGED
        if not _ANNOTATIONS_DEPRECATION_LOGGED and any(
            event.annotations for event in events
        ):
            logger.warning(
                "Detected legacy annotations in business_events.yml. "
                "Annotations are deprecated; prefer seven_ws entries."
            )
            _ANNOTATIONS_DEPRECATION_LOGGED = True
        return events
    except Exception as e:
        logger.error(f"Invalid business events file structure in {path}: {e}")
        raise FileOperationError("Invalid business events file format")


def save_business_events(
    events: List[BusinessEvent], path: Optional[str] = None
) -> None:
    """
    Save business events to YAML file.

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

    # Create file structure
    events_file = BusinessEventsFile(events=events)

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
        annotations=[],
        derived_entities=[],
        seven_ws=BusinessEventSevenWs(),
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
        updates: Dictionary with fields to update (text, type, annotations, derived_entities, seven_ws)

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
        # Clear annotations if text changed (simpler than position tracking)
        event.annotations = []

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

    if "annotations" in updates:
        event.annotations = [Annotation(**ann) for ann in updates["annotations"]]

    if "derived_entities" in updates:
        from trellis_datamodel.models.business_event import DerivedEntity

        event.derived_entities = [
            DerivedEntity(**de) for de in updates["derived_entities"]
        ]

    if "seven_ws" in updates:
        event.seven_ws = BusinessEventSevenWs(**updates["seven_ws"])

    event.updated_at = datetime.now()

    # Validate updated event
    try:
        updated_event = BusinessEvent(**event.model_dump())
    except Exception as e:
        raise ValidationError(f"Invalid event data: {str(e)}") from e

    events[event_index] = updated_event
    save_business_events(events)
    logger.info(f"Updated business event: {event_id}")
    return updated_event


def delete_event(event_id: str) -> None:
    """
    Delete a business event.

    Args:
        event_id: ID of event to delete

    Raises:
        NotFoundError: If event not found
        FileOperationError: If file operations fail
    """
    events = load_business_events()
    original_count = len(events)
    events = [e for e in events if e.id != event_id]

    if len(events) == original_count:
        raise NotFoundError(f"Business event '{event_id}' not found")

    save_business_events(events)
    logger.info(f"Deleted business event: {event_id}")


def add_annotation(
    event_id: str, text: str, type: str, start_pos: int, end_pos: int
) -> BusinessEvent:
    """
    Add an annotation to a business event.

    DEPRECATED: Use 7 Ws structure (add_seven_ws_entry) instead.

    Args:
        event_id: ID of event to annotate
        text: Annotated text segment
        type: Annotation type ('dimension' or 'fact')
        start_pos: Start position in event text
        end_pos: End position in event text

    Returns:
        Updated BusinessEvent object

    Raises:
        NotFoundError: If event not found
        ValidationError: If annotation is invalid or overlaps existing annotations
        FileOperationError: If file operations fail
    """
    logger.warning(
        "add_annotation is deprecated. Use seven_ws entries instead of annotations."
    )
    events = load_business_events()
    event_index = None
    for i, event in enumerate(events):
        if event.id == event_id:
            event_index = i
            break

    if event_index is None:
        raise NotFoundError(f"Business event '{event_id}' not found")

    event = events[event_index]

    # Validate positions are within event text bounds
    if start_pos < 0 or end_pos > len(event.text):
        raise ValidationError("Annotation positions are out of bounds")

    # Create new annotation
    new_annotation = Annotation(
        text=text, type=type, start_pos=start_pos, end_pos=end_pos
    )

    # Add to annotations list (validation will check for overlaps)
    updated_annotations = list(event.annotations) + [new_annotation]

    # Update event with new annotations
    try:
        updated_event = update_event(
            event_id, {"annotations": [ann.model_dump() for ann in updated_annotations]}
        )
    except Exception as e:
        if "overlap" in str(e).lower():
            raise ValidationError("Annotation overlaps with existing annotation") from e
        raise

    return updated_event


def remove_annotation(event_id: str, annotation_index: int) -> BusinessEvent:
    """
    Remove an annotation from a business event by index.

    DEPRECATED: Use 7 Ws structure (remove_seven_ws_entry) instead.

    Args:
        event_id: ID of event
        annotation_index: Index of annotation to remove

    Returns:
        Updated BusinessEvent object

    Raises:
        NotFoundError: If event not found or annotation index out of bounds
        FileOperationError: If file operations fail
    """
    logger.warning(
        "remove_annotation is deprecated. Use seven_ws entries instead of annotations."
    )
    events = load_business_events()
    event_index = None
    for i, event in enumerate(events):
        if event.id == event_id:
            event_index = i
            break

    if event_index is None:
        raise NotFoundError(f"Business event '{event_id}' not found")

    event = events[event_index]

    if annotation_index < 0 or annotation_index >= len(event.annotations):
        raise NotFoundError(f"Annotation index {annotation_index} out of bounds")

    updated_annotations = [
        ann for i, ann in enumerate(event.annotations) if i != annotation_index
    ]
    updated_event = update_event(
        event_id, {"annotations": [ann.model_dump() for ann in updated_annotations]}
    )
    return updated_event


def update_event_seven_ws(event_id: str, seven_ws_data: dict) -> BusinessEvent:
    """
    Update the entire 7 Ws structure for a business event.

    Args:
        event_id: ID of event to update
        seven_ws_data: Dictionary with 7 Ws structure (who, what, when, where, how, how_many, why)

    Returns:
        Updated BusinessEvent object

    Raises:
        NotFoundError: If event not found
        ValidationError: If seven_ws data is invalid
        FileOperationError: If file operations fail
    """
    return update_event(event_id, {"seven_ws": seven_ws_data})


def add_seven_ws_entry(
    event_id: str,
    w_type: str,
    text: str,
    dimension_id: Optional[str] = None,
    description: Optional[str] = None,
    attributes: Optional[dict] = None,
) -> BusinessEvent:
    """
    Add a new entry to a specific W list in a business event.

    Args:
        event_id: ID of event
        w_type: Type of W ('who', 'what', 'when', 'where', 'how', 'how_many', 'why')
        text: Entry text
        dimension_id: Optional ID of existing dimension entity to link
        description: Optional description
        attributes: Optional additional attributes dict

    Returns:
        Updated BusinessEvent object

    Raises:
        NotFoundError: If event not found
        ValidationError: If w_type is invalid or entry_id is not unique
        FileOperationError: If file operations fail
    """
    valid_w_types = ["who", "what", "when", "where", "how", "how_many", "why"]
    if w_type not in valid_w_types:
        raise ValidationError(
            f"Invalid w_type: '{w_type}'. Must be one of: {', '.join(valid_w_types)}"
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

    # Ensure seven_ws exists
    if event.seven_ws is None:
        event.seven_ws = BusinessEventSevenWs()

    # Generate unique entry_id
    import uuid

    entry_id = f"entry_{uuid.uuid4().hex[:12]}"

    # Check uniqueness across all Ws
    all_entry_ids = _collect_all_entry_ids(event.seven_ws)
    if entry_id in all_entry_ids:
        raise ValidationError(f"Entry ID '{entry_id}' already exists in event")

    # Create new entry
    new_entry = SevenWsEntry(
        id=entry_id,
        text=text.strip(),
        dimension_id=dimension_id,
        description=description,
        attributes=attributes or {},
    )

    # Add to appropriate W list
    current_seven_ws = event.seven_ws.model_dump()
    w_list = current_seven_ws.get(w_type, [])
    w_list.append(new_entry.model_dump())
    current_seven_ws[w_type] = w_list

    # Update event
    updated_event = update_event(event_id, {"seven_ws": current_seven_ws})
    return updated_event


def remove_seven_ws_entry(event_id: str, entry_id: str) -> BusinessEvent:
    """
    Remove a 7 Ws entry by entry_id from a business event.

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

    if event.seven_ws is None:
        raise NotFoundError(f"Entry '{entry_id}' not found (event has no 7 Ws data)")

    # Find and remove entry
    current_seven_ws = event.seven_ws.model_dump()
    entry_found = False

    for w_type in ["who", "what", "when", "where", "how", "how_many", "why"]:
        w_list = current_seven_ws.get(w_type, [])
        original_length = len(w_list)
        w_list = [entry for entry in w_list if entry.get("id") != entry_id]
        current_seven_ws[w_type] = w_list
        if len(w_list) < original_length:
            entry_found = True

    if not entry_found:
        raise NotFoundError(f"Entry '{entry_id}' not found in any W list")

    updated_event = update_event(event_id, {"seven_ws": current_seven_ws})
    return updated_event


def update_seven_ws_entry(
    event_id: str,
    entry_id: str,
    text: Optional[str] = None,
    dimension_id: Optional[str] = None,
    description: Optional[str] = None,
    attributes: Optional[dict] = None,
) -> BusinessEvent:
    """
    Update an existing 7 Ws entry in a business event.

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

    if event.seven_ws is None:
        raise NotFoundError(f"Entry '{entry_id}' not found (event has no 7 Ws data)")

    # Find and update entry
    current_seven_ws = event.seven_ws.model_dump()
    entry_found = False

    for w_type in ["who", "what", "when", "where", "how", "how_many", "why"]:
        w_list = current_seven_ws.get(w_type, [])
        for entry in w_list:
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
        raise NotFoundError(f"Entry '{entry_id}' not found in any W list")

    updated_event = update_event(event_id, {"seven_ws": current_seven_ws})
    return updated_event


def _collect_all_entry_ids(seven_ws: BusinessEventSevenWs) -> set:
    """
    Collect all entry IDs from a 7 Ws structure.

    Args:
        seven_ws: BusinessEventSevenWs object

    Returns:
        Set of entry IDs
    """
    entry_ids = set()
    for w_type in ["who", "what", "when", "where", "how", "how_many", "why"]:
        w_list = getattr(seven_ws, w_type, [])
        for entry in w_list:
            if hasattr(entry, "id"):
                entry_ids.add(entry.id)
    return entry_ids
