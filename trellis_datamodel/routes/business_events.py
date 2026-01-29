"""Routes for business events operations."""

from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel

from trellis_datamodel import config as cfg
from trellis_datamodel.exceptions import (
    ConfigurationError,
    FileOperationError,
    ValidationError,
    NotFoundError,
    FeatureDisabledError,
)
from trellis_datamodel.models.business_event import (
    BusinessEvent,
    BusinessEventType,
    GeneratedEntitiesResult,
    BusinessEventAnnotations,
    BusinessEventProcess,
)
from trellis_datamodel.services.business_events_service import (
    load_business_events,
    create_event,
    update_event,
    delete_event,
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

router = APIRouter(prefix="/api", tags=["business-events"])


class CreateEventRequest(BaseModel):
    """Request model for creating a business event."""

    text: str
    type: str
    domain: str | None = None
    annotations: BusinessEventAnnotations | None = None


class UpdateEventRequest(BaseModel):
    """Request model for updating a business event."""

    text: str | None = None
    type: str | None = None
    domain: str | None = None
    derived_entities: list[dict] | None = None
    annotations: BusinessEventAnnotations | dict | None = None


class UpdateEventAnnotationsRequest(BaseModel):
    """Request model for updating annotations of a business event."""

    annotations: BusinessEventAnnotations | None = None


class AddAnnotationEntryRequest(BaseModel):
    """Request model for adding an annotation entry to a business event."""

    annotation_type: str
    text: str
    dimension_id: str | None = None
    description: str | None = None
    attributes: dict | None = None


class UpdateAnnotationEntryRequest(BaseModel):
    """Request model for updating an annotation entry in a business event."""

    text: str | None = None
    dimension_id: str | None = None
    description: str | None = None
    attributes: dict | None = None


class CreateProcessRequest(BaseModel):
    """Request model for creating a business event process."""

    name: str
    type: str
    domain: str
    event_ids: list[str] | None = None


class UpdateProcessRequest(BaseModel):
    """Request model for updating a business event process."""

    name: str | None = None
    type: str | None = None
    domain: str | None = None
    annotations_superset: BusinessEventAnnotations | None = None
    event_ids: list[str] | None = None


class AttachEventsRequest(BaseModel):
    """Request model for attaching events to a process."""

    event_ids: list[str]


class DetachEventsRequest(BaseModel):
    """Request model for detaching events from a process."""

    event_ids: list[str]


def _check_feature_enabled():
    """Check if business events feature is enabled."""
    if not cfg.BUSINESS_EVENTS_ENABLED:
        raise FeatureDisabledError("Business events feature is disabled")


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
    _check_feature_enabled()

    try:
        domains = get_unique_domains()
        return domains
    except FileOperationError:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error loading business event domains: {str(e)}"
        )


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
    _check_feature_enabled()

    try:
        events = load_business_events()
        return events
    except ConfigurationError:
        raise
    except FileOperationError:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error loading business events: {str(e)}"
        )


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
    _check_feature_enabled()

    try:
        # Validate event type
        try:
            event_type = BusinessEventType(request.type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid event type: {request.type}. Must be one of: discrete, evolving, recurring",
            )

        event = create_event(request.text, event_type, domain=request.domain)

        # If annotations provided, update the event with it
        if request.annotations is not None:
            event = update_event(
                event.id, {"annotations": request.annotations.model_dump()}
            )

        return event
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileOperationError:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error creating business event: {str(e)}"
        )


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
    _check_feature_enabled()

    try:
        updates = {}
        if request.text is not None:
            updates["text"] = request.text
        if request.type is not None:
            updates["type"] = request.type
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

        event = update_event(event_id, updates)
        return event
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileOperationError:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error updating business event: {str(e)}"
        )


@router.delete("/business-events/{event_id}", status_code=204)
async def delete_business_event(event_id: str):
    """
    Delete a business event.

    Args:
        event_id: ID of event to delete

    Raises:
        FeatureDisabledError: If business events feature is disabled
        NotFoundError: If event not found
        ValidationError: If event doesn't have required 7 Ws data
        FileOperationError: If file operations fail
    """
    _check_feature_enabled()

    try:
        delete_event(event_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileOperationError:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error deleting business event: {str(e)}"
        )


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
    _check_feature_enabled()

    # Validate annotation_type
    valid_types = ["who", "what", "when", "where", "how", "why", "how_many"]
    if request.annotation_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid annotation_type: '{request.annotation_type}'. Must be one of: {', '.join(valid_types)}",
        )

    try:
        event = add_annotation_entry(
            event_id,
            request.annotation_type,
            request.text,
            dimension_id=request.dimension_id,
            description=request.description,
            attributes=request.attributes,
        )
        return event
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileOperationError:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error adding annotation entry: {str(e)}"
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
    _check_feature_enabled()

    try:
        event = remove_annotation_entry(event_id, entry_id)
        return event
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileOperationError:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error removing annotation entry: {str(e)}"
        )


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
    _check_feature_enabled()

    try:
        event = update_annotation_entry(
            event_id,
            entry_id,
            text=request.text,
            dimension_id=request.dimension_id,
            description=request.description,
            attributes=request.attributes,
        )
        return event
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileOperationError:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error updating annotation entry: {str(e)}"
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
    _check_feature_enabled()

    try:
        events = load_business_events()
        event = None
        for e in events:
            if e.id == event_id:
                event = e
                break

        if event is None:
            raise HTTPException(
                status_code=404, detail=f"Business event '{event_id}' not found"
            )

        result = generate_entities_from_event(event)
        return result
    except NotFoundError:
        raise
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileOperationError:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating entities: {str(e)}"
        )


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
    _check_feature_enabled()

    try:
        processes = load_processes()
        return processes
    except FileOperationError:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error loading processes: {str(e)}"
        )


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
    _check_feature_enabled()

    try:
        # Validate process type
        try:
            process_type = BusinessEventType(request.type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid process type: {request.type}. Must be one of: discrete, evolving, recurring",
            )

        # Validate event_ids if provided
        if request.event_ids:
            events = load_business_events()
            existing_event_ids = {e.id for e in events}
            invalid_ids = [
                eid for eid in request.event_ids if eid not in existing_event_ids
            ]
            if invalid_ids:
                raise HTTPException(
                    status_code=404,
                    detail=f"Events not found: {', '.join(invalid_ids)}",
                )

            # Check if events are already in another process
            for event in events:
                if event.id in request.event_ids and event.process_id is not None:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Event '{event.id}' is already attached to process '{event.process_id}'",
                    )

        if not request.domain or not request.domain.strip():
            raise HTTPException(status_code=400, detail="Process domain is required")

        process = create_process(
            request.name,
            process_type,
            request.domain.strip(),
            event_ids=request.event_ids,
        )
        return process
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileOperationError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating process: {str(e)}")


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
        ValidationError: If updates are invalid or process is resolved
        FileOperationError: If file operations fail
    """
    _check_feature_enabled()

    try:
        updates = {}
        if request.name is not None:
            updates["name"] = request.name
        if request.type is not None:
            # Validate process type
            try:
                BusinessEventType(request.type)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid process type: {request.type}. Must be one of: discrete, evolving, recurring",
                )
            updates["type"] = request.type

        if request.domain is not None:
            if not request.domain.strip():
                raise HTTPException(
                    status_code=400, detail="Process domain cannot be empty"
                )
            updates["domain"] = request.domain.strip()

        if request.annotations_superset is not None:
            updates["annotations_superset"] = request.annotations_superset.model_dump()

        if request.event_ids is not None:
            if len(request.event_ids) == 0:
                raise HTTPException(
                    status_code=400, detail="event_ids list cannot be empty"
                )
            updates["event_ids"] = request.event_ids

        if not updates:
            raise HTTPException(status_code=400, detail="No fields provided to update")

        process = update_process(process_id, updates)
        return process
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileOperationError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating process: {str(e)}")


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
    _check_feature_enabled()

    try:
        process = resolve_process(process_id)
        return process
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileOperationError:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error resolving process: {str(e)}"
        )


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
        ValidationError: If events are already in another process or process is resolved
        FileOperationError: If file operations fail
    """
    _check_feature_enabled()

    try:
        if not request.event_ids:
            raise HTTPException(
                status_code=400, detail="event_ids list cannot be empty"
            )

        # Validate event_ids exist
        events = load_business_events()
        existing_event_ids = {e.id for e in events}
        invalid_ids = [
            eid for eid in request.event_ids if eid not in existing_event_ids
        ]
        if invalid_ids:
            raise HTTPException(
                status_code=404,
                detail=f"Events not found: {', '.join(invalid_ids)}",
            )

        process = attach_events_to_process(process_id, request.event_ids)
        return process
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileOperationError:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error attaching events to process: {str(e)}"
        )


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
        FileOperationError: If file operations fail
    """
    _check_feature_enabled()

    try:
        if not request.event_ids:
            raise HTTPException(
                status_code=400, detail="event_ids list cannot be empty"
            )

        process = detach_events_from_process(process_id, request.event_ids)
        return process
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileOperationError:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error detaching events from process: {str(e)}"
        )


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
    _check_feature_enabled()

    try:
        processes = load_processes()
        process = None
        for p in processes:
            if p.id == process_id:
                process = p
                break

        if process is None:
            raise HTTPException(
                status_code=404,
                detail=f"Business event process '{process_id}' not found",
            )

        result = generate_entities_from_process(process)
        return result
    except NotFoundError:
        raise
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileOperationError:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error generating entities from process: {str(e)}"
        )
