"""
Business Events service for dimensional modeling.

Handles CRUD operations for business events stored in YAML files.
Business events capture business processes (e.g., "customer buys product")
and can be annotated with dimensions and facts for entity generation.

This service:
- Loads and saves business events from/to YAML files
- Provides CRUD operations for events
- Manages annotations within events
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
        events_file = BusinessEventsFile(**data)
        return events_file.events
    except Exception as e:
        logger.error(f"Invalid business events file structure in {path}: {e}")
        raise FileOperationError("Invalid business events file format")


def save_business_events(events: List[BusinessEvent], path: Optional[str] = None) -> None:
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


def create_event(text: str, type: BusinessEventType, domain: Optional[str] = None) -> BusinessEvent:
    """
    Create a new business event with auto-generated ID.

    Args:
        text: Event description text
        type: Event type (discrete, evolving, recurring)

    Returns:
        New BusinessEvent object

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
        updates: Dictionary with fields to update (text, type, annotations, derived_entities)

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
        if domain_value is None or (isinstance(domain_value, str) and not domain_value.strip()):
            event.domain = None
        else:
            event.domain = domain_value.strip() if isinstance(domain_value, str) else domain_value

    if "annotations" in updates:
        event.annotations = [Annotation(**ann) for ann in updates["annotations"]]

    if "derived_entities" in updates:
        from trellis_datamodel.models.business_event import DerivedEntity
        event.derived_entities = [DerivedEntity(**de) for de in updates["derived_entities"]]

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
        updated_event = update_event(event_id, {"annotations": [ann.model_dump() for ann in updated_annotations]})
    except Exception as e:
        if "overlap" in str(e).lower():
            raise ValidationError("Annotation overlaps with existing annotation") from e
        raise

    return updated_event


def remove_annotation(event_id: str, annotation_index: int) -> BusinessEvent:
    """
    Remove an annotation from a business event by index.

    Args:
        event_id: ID of event
        annotation_index: Index of annotation to remove

    Returns:
        Updated BusinessEvent object

    Raises:
        NotFoundError: If event not found or annotation index out of bounds
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

    if annotation_index < 0 or annotation_index >= len(event.annotations):
        raise NotFoundError(f"Annotation index {annotation_index} out of bounds")

    updated_annotations = [ann for i, ann in enumerate(event.annotations) if i != annotation_index]
    updated_event = update_event(event_id, {"annotations": [ann.model_dump() for ann in updated_annotations]})
    return updated_event
