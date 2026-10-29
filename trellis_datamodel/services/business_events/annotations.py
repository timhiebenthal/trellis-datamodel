"""
Annotation entries (Who, What, When, Where, How, How Many, Why) within
business events.
"""
from typing import Optional

from trellis_datamodel.exceptions import NotFoundError, ValidationError
from trellis_datamodel.models.business_event import (
    AnnotationEntry,
    BusinessEvent,
    BusinessEventAnnotations,
)
from trellis_datamodel.services.business_events.events import update_event
from trellis_datamodel.services.business_events.storage import load_business_events


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
    valid_types = ["who", "what", "when", "where", "how", "why", "how_many"]
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
