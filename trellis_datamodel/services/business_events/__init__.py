"""
Business Events service for dimensional modeling.

Business events capture business processes (e.g., "customer buys product")
and can be annotated with categories (Who, What, When, Where, How, How Many,
Why) for entity generation. Events can be grouped into processes.

Modules:
- storage: load/save events and processes in business_events.yml
- events: CRUD for business events
- annotations: annotation entries within events
- processes: CRUD for processes, attaching/detaching events
- supersets: process annotation supersets (union of member annotations)
- role_sync: sync annotation roles onto dimension entities in the data model
"""
from trellis_datamodel.services.business_events.annotations import (
    add_annotation_entry,
    remove_annotation_entry,
    update_annotation_entry,
    update_event_annotations,
)
from trellis_datamodel.services.business_events.events import (
    create_event,
    delete_event,
    get_event,
    get_unique_domains,
    parse_business_event_type,
    update_event,
)
from trellis_datamodel.services.business_events.processes import (
    attach_events_to_process,
    create_process,
    detach_events_from_process,
    get_process,
    resolve_process,
    update_process,
)
from trellis_datamodel.services.business_events.storage import (
    load_business_events,
    load_processes,
    save_business_events,
    save_processes,
)
from trellis_datamodel.services.business_events.supersets import (
    recompute_all_process_supersets,
    recompute_process_superset,
)

__all__ = [
    "add_annotation_entry",
    "attach_events_to_process",
    "create_event",
    "create_process",
    "delete_event",
    "detach_events_from_process",
    "get_event",
    "get_process",
    "get_unique_domains",
    "load_business_events",
    "load_processes",
    "parse_business_event_type",
    "recompute_all_process_supersets",
    "recompute_process_superset",
    "remove_annotation_entry",
    "resolve_process",
    "save_business_events",
    "save_processes",
    "update_annotation_entry",
    "update_event",
    "update_event_annotations",
    "update_process",
]
