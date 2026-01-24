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
    BusinessEventsFile,
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
        updates: Dictionary with fields to update (text, type, domain, annotations, derived_entities)

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
