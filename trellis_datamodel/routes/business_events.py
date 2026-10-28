"""Routes for business events operations.

Handlers stay thin: domain exceptions raised by the service are mapped to
HTTP responses by the global handlers in server.py.
"""

from fastapi import APIRouter, Body, Depends

from trellis_datamodel import config as cfg
from trellis_datamodel.models.business_event import (
    BusinessEvent,
    GeneratedEntitiesResult,
    BusinessEventAnnotations,
    BusinessEventProcess,
)
from trellis_datamodel.models.business_event_requests import (
    AddAnnotationEntryRequest,
    AttachEventsRequest,
    CreateEventRequest,
    CreateProcessRequest,
    DetachEventsRequest,
    UpdateAnnotationEntryRequest,
    UpdateEventRequest,
    UpdateProcessRequest,
)
from trellis_datamodel.routes.dependencies import require_feature
from trellis_datamodel.services.business_events_service import (
    load_business_events,
    create_event,
    update_event,
    delete_event,
    get_event,
    get_process,
    get_unique_domains,
    add_annotation_entry,
    remove_annotation_entry,
    update_annotation_entry,
    load_processes,
    create_process,
    update_process,
    resolve_process,
    attach_events_to_process,
    detach_events_from_process,
)
from trellis_datamodel.services.entity_generator import (
    generate_entities_from_event,
    generate_entities_from_process,
)

router = APIRouter(
    prefix="/api",
    tags=["business-events"],
    dependencies=[
        Depends(
            require_feature(
                lambda: cfg.BUSINESS_EVENTS_ENABLED,
                "Business events feature is disabled",
            )
        )
    ],
)


@router.get("/business-events/domains", response_model=list[str])
async def get_business_event_domains():
    """
    Return unique domain values from all business events for autocomplete.

    Returns:
        Sorted list of unique domain strings

    Raises:
        FeatureDisabledError: If business events feature is disabled
        FileOperationError: If file cannot be read
    """
    return get_unique_domains()


@router.get("/business-events", response_model=list[BusinessEvent])
async def get_business_events():
    """
    Return all business events from business_events.yml.

    Returns:
        List of BusinessEvent objects

    Raises:
        FeatureDisabledError: If business events feature is disabled
        ConfigurationError: If path is not configured
        FileOperationError: If file cannot be read
    """
    return load_business_events()


@router.post("/business-events", response_model=BusinessEvent, status_code=201)
async def create_business_event(request: CreateEventRequest = Body(...)):
    """
    Create a new business event.

    Args:
        request: CreateEventRequest with text, type, and optional annotations

    Returns:
        Created BusinessEvent object

    Raises:
        FeatureDisabledError: If business events feature is disabled
        ValidationError: If input is invalid
        FileOperationError: If file operations fail
    """
    event = create_event(
        request.text,
        request.type,
        domain=request.domain,
        description=request.description,
    )

    # If annotations provided, update the event with it
    if request.annotations is not None:
        event = update_event(event.id, {"annotations": request.annotations.model_dump()})

    return event


@router.put("/business-events/{event_id}", response_model=BusinessEvent)
async def update_business_event(event_id: str, request: UpdateEventRequest = Body(...)):
    """
    Update an existing business event.

    Args:
        event_id: ID of event to update
        request: UpdateEventRequest with fields to update

    Returns:
        Updated BusinessEvent object

    Raises:
        FeatureDisabledError: If business events feature is disabled
        NotFoundError: If event not found
        ValidationError: If updates are invalid
        FileOperationError: If file operations fail
    """
    updates = {}
    if request.text is not None:
        updates["text"] = request.text
    if request.type is not None:
        updates["type"] = request.type
    if request.description is not None:
        updates["description"] = request.description
    if request.domain is not None:
        updates["domain"] = request.domain
    if request.derived_entities is not None:
        updates["derived_entities"] = request.derived_entities
    if request.annotations is not None:
        # Convert to dict if it's a BusinessEventAnnotations object
        if isinstance(request.annotations, BusinessEventAnnotations):
            updates["annotations"] = request.annotations.model_dump()
        else:
            updates["annotations"] = request.annotations

    return update_event(event_id, updates)


@router.delete("/business-events/{event_id}", status_code=204)
async def delete_business_event(event_id: str):
    """
    Delete a business event.

    Args:
        event_id: ID of event to delete

    Raises:
        FeatureDisabledError: If business events feature is disabled
        NotFoundError: If event not found
        FileOperationError: If file operations fail
    """
    delete_event(event_id)


@router.post(
    "/business-events/{event_id}/annotations",
    response_model=BusinessEvent,
)
async def add_event_annotation_entry(
    event_id: str, request: AddAnnotationEntryRequest = Body(...)
):
    """
    Add a new entry to an annotation category in a business event.

    Args:
        event_id: ID of event
        request: AddAnnotationEntryRequest with annotation_type, text, dimension_id, description

    Returns:
        Updated BusinessEvent object

    Raises:
        FeatureDisabledError: If business events feature is disabled
        NotFoundError: If event not found
        ValidationError: If annotation_type is invalid or text is empty
        FileOperationError: If file operations fail
    """
    return add_annotation_entry(
        event_id,
        request.annotation_type,
        request.text,
        dimension_id=request.dimension_id,
        description=request.description,
        attributes=request.attributes,
    )


@router.delete(
    "/business-events/{event_id}/annotations/{entry_id}",
    response_model=BusinessEvent,
)
async def remove_event_annotation_entry(event_id: str, entry_id: str):
    """
    Remove an annotation entry from a business event.

    Args:
        event_id: ID of event
        entry_id: ID of entry to remove

    Returns:
        Updated BusinessEvent object

    Raises:
        FeatureDisabledError: If business events feature is disabled
        NotFoundError: If event or entry not found
        FileOperationError: If file operations fail
    """
    return remove_annotation_entry(event_id, entry_id)


@router.put(
    "/business-events/{event_id}/annotations/{entry_id}",
    response_model=BusinessEvent,
)
async def update_event_annotation_entry(
    event_id: str, entry_id: str, request: UpdateAnnotationEntryRequest = Body(...)
):
    """
    Update an existing annotation entry in a business event.

    Args:
        event_id: ID of event
        entry_id: ID of entry to update
        request: UpdateAnnotationEntryRequest with fields to update

    Returns:
        Updated BusinessEvent object

    Raises:
        FeatureDisabledError: If business events feature is disabled
        NotFoundError: If event or entry not found
        ValidationError: If text is invalid
        FileOperationError: If file operations fail
    """
    return update_annotation_entry(
        event_id,
        entry_id,
        text=request.text,
        dimension_id=request.dimension_id,
        description=request.description,
        attributes=request.attributes,
    )


@router.post(
    "/business-events/{event_id}/generate-entities",
    response_model=GeneratedEntitiesResult,
)
async def generate_entities_from_business_event(event_id: str):
    """
    Generate dimensional entities from a business event with annotations.

    Args:
        event_id: ID of event to generate entities from

    Returns:
        GeneratedEntitiesResult with entities, relationships, and any errors

    Raises:
        FeatureDisabledError: If business events feature is disabled
        NotFoundError: If event not found
        ValidationError: If event doesn't have required annotations
        FileOperationError: If file operations fail
    """
    return generate_entities_from_event(get_event(event_id))


@router.get("/processes", response_model=list[BusinessEventProcess])
async def get_processes():
    """
    Return all business event processes from business_events.yml.

    Returns:
        List of BusinessEventProcess objects

    Raises:
        FeatureDisabledError: If business events feature is disabled
        FileOperationError: If file cannot be read
    """
    return load_processes()


@router.post("/processes", response_model=BusinessEventProcess, status_code=201)
async def create_business_event_process(request: CreateProcessRequest = Body(...)):
    """
    Create a new business event process.

    Args:
        request: CreateProcessRequest with name, type, and optional event_ids

    Returns:
        Created BusinessEventProcess object

    Raises:
        FeatureDisabledError: If business events feature is disabled
        ValidationError: If input is invalid
        NotFoundError: If any event_id doesn't exist
        FileOperationError: If file operations fail
    """
    return create_process(
        request.name,
        request.type,
        request.domain,
        event_ids=request.event_ids,
        description=request.description,
    )


@router.put("/processes/{process_id}", response_model=BusinessEventProcess)
async def update_business_event_process(
    process_id: str, request: UpdateProcessRequest = Body(...)
):
    """
    Update an existing business event process.

    Args:
        process_id: ID of process to update
        request: UpdateProcessRequest with fields to update

    Returns:
        Updated BusinessEventProcess object

    Raises:
        FeatureDisabledError: If business events feature is disabled
        NotFoundError: If process not found
        ValidationError: If updates are empty or invalid, or process is resolved
        FileOperationError: If file operations fail
    """
    updates = {}
    if request.name is not None:
        updates["name"] = request.name
    if request.description is not None:
        updates["description"] = request.description
    if request.type is not None:
        updates["type"] = request.type
    if request.domain is not None:
        updates["domain"] = request.domain
    if request.annotations_superset is not None:
        updates["annotations_superset"] = request.annotations_superset.model_dump()
    if request.event_ids is not None:
        updates["event_ids"] = request.event_ids
    if request.derived_entities is not None:
        updates["derived_entities"] = request.derived_entities

    return update_process(process_id, updates)


@router.post("/processes/{process_id}/resolve", response_model=BusinessEventProcess)
async def resolve_business_event_process(process_id: str):
    """
    Resolve (ungroup) a business event process.

    Args:
        process_id: ID of process to resolve

    Returns:
        Resolved BusinessEventProcess object

    Raises:
        FeatureDisabledError: If business events feature is disabled
        NotFoundError: If process not found
        ValidationError: If process is already resolved
        FileOperationError: If file operations fail
    """
    return resolve_process(process_id)


@router.post("/processes/{process_id}/attach", response_model=BusinessEventProcess)
async def attach_events_to_business_event_process(
    process_id: str, request: AttachEventsRequest = Body(...)
):
    """
    Attach events to a business event process.

    Args:
        process_id: ID of process
        request: AttachEventsRequest with event_ids list

    Returns:
        Updated BusinessEventProcess object

    Raises:
        FeatureDisabledError: If business events feature is disabled
        NotFoundError: If process or any event not found
        ValidationError: If event_ids is empty, events are already in another
            process, or process is resolved
        FileOperationError: If file operations fail
    """
    return attach_events_to_process(process_id, request.event_ids)


@router.post("/processes/{process_id}/detach", response_model=BusinessEventProcess)
async def detach_events_from_business_event_process(
    process_id: str, request: DetachEventsRequest = Body(...)
):
    """
    Detach events from a business event process.

    Args:
        process_id: ID of process
        request: DetachEventsRequest with event_ids list

    Returns:
        Updated BusinessEventProcess object

    Raises:
        FeatureDisabledError: If business events feature is disabled
        NotFoundError: If process not found
        ValidationError: If event_ids is empty
        FileOperationError: If file operations fail
    """
    return detach_events_from_process(process_id, request.event_ids)


@router.post(
    "/processes/{process_id}/generate-entities",
    response_model=GeneratedEntitiesResult,
)
async def generate_entities_from_business_event_process(process_id: str):
    """
    Generate dimensional entities from a business event process.

    Uses the process's annotations_superset (union of all member event annotations).
    Behavior differs by process type:
    - discrete: one fact table with per-event records (includes event_id/process_id)
    - evolving: one fact table with process-level records (includes process_id)
    - recurring: same as discrete

    Args:
        process_id: ID of process to generate entities from

    Returns:
        GeneratedEntitiesResult with entities, relationships, and any errors

    Raises:
        FeatureDisabledError: If business events feature is disabled
        NotFoundError: If process not found
        ValidationError: If process doesn't have required annotations or is resolved
        FileOperationError: If file operations fail
    """
    return generate_entities_from_process(get_process(process_id))
