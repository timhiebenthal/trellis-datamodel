"""
Process annotation supersets: the union of the annotations of a process's
member events, and its recomputation.
"""
import logging
from datetime import datetime
from typing import Dict, List

from trellis_datamodel.exceptions import NotFoundError
from trellis_datamodel.models.business_event import (
    AnnotationEntry,
    BusinessEvent,
    BusinessEventAnnotations,
    BusinessEventProcess,
)
from trellis_datamodel.services.business_events.role_sync import (
    _sync_roles_to_dimensions,
)
from trellis_datamodel.services.business_events.storage import (
    load_business_events,
    load_processes,
    save_processes,
)

logger = logging.getLogger(__name__)


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
    
    # Sync roles from recomputed superset to dimension entities
    if process.annotations_superset:
        _sync_roles_to_dimensions(process.annotations_superset)

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
