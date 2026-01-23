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
    BusinessEventSevenWs,
)
from trellis_datamodel.services.business_events_service import (
    load_business_events,
    create_event,
    update_event,
    delete_event,
    get_unique_domains,
    add_seven_ws_entry,
    remove_seven_ws_entry,
    update_seven_ws_entry,
)
from trellis_datamodel.services.entity_generator import generate_entities_from_event

router = APIRouter(prefix="/api", tags=["business-events"])


class CreateEventRequest(BaseModel):
    """Request model for creating a business event."""

    text: str
    type: str
    domain: str | None = None
    seven_ws: BusinessEventSevenWs | None = None


class UpdateEventRequest(BaseModel):
    """Request model for updating a business event."""

    text: str | None = None
    type: str | None = None
    domain: str | None = None
    derived_entities: list[dict] | None = None
    seven_ws: BusinessEventSevenWs | dict | None = None


class UpdateEventSevenWsRequest(BaseModel):
    """Request model for updating 7 Ws structure of a business event."""

    seven_ws: BusinessEventSevenWs | None = None


class AddSevenWsEntryRequest(BaseModel):
    """Request model for adding a 7 Ws entry to a business event."""

    w_type: str
    text: str
    dimension_id: str | None = None
    description: str | None = None
    attributes: dict | None = None


class UpdateSevenWsEntryRequest(BaseModel):
    """Request model for updating a 7 Ws entry in a business event."""

    text: str | None = None
    dimension_id: str | None = None
    description: str | None = None
    attributes: dict | None = None


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
        request: CreateEventRequest with text, type, and optional seven_ws

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

        # If seven_ws provided, update the event with it
        if request.seven_ws is not None:
            event = update_event(event.id, {"seven_ws": request.seven_ws.model_dump()})

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
        if request.annotations is not None:
            updates["annotations"] = request.annotations
        if request.derived_entities is not None:
            updates["derived_entities"] = request.derived_entities
        if request.seven_ws is not None:
            # Convert to dict if it's a BusinessEventSevenWs object
            if isinstance(request.seven_ws, BusinessEventSevenWs):
                updates["seven_ws"] = request.seven_ws.model_dump()
            else:
                updates["seven_ws"] = request.seven_ws

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
    "/business-events/{event_id}/seven-entries",
    response_model=BusinessEvent,
)
async def add_event_seven_ws_entry(
    event_id: str, request: AddSevenWsEntryRequest = Body(...)
):
    """
    Add a new entry to a 7 Ws category in a business event.

    Args:
        event_id: ID of event
        request: AddSevenWsEntryRequest with w_type, text, dimension_id, description

    Returns:
        Updated BusinessEvent object

    Raises:
        FeatureDisabledError: If business events feature is disabled
        NotFoundError: If event not found
        ValidationError: If w_type is invalid or text is empty
        FileOperationError: If file operations fail
    """
    _check_feature_enabled()

    # Validate w_type
    valid_w_types = ["who", "what", "when", "where", "how", "how_many", "why"]
    if request.w_type not in valid_w_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid w_type: '{request.w_type}'. Must be one of: {', '.join(valid_w_types)}",
        )

    try:
        event = add_seven_ws_entry(
            event_id,
            request.w_type,
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
            status_code=500, detail=f"Error adding 7 Ws entry: {str(e)}"
        )


@router.delete(
    "/business-events/{event_id}/seven-entries/{entry_id}",
    response_model=BusinessEvent,
)
async def remove_event_seven_ws_entry(event_id: str, entry_id: str):
    """
    Remove a 7 Ws entry from a business event.

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
        event = remove_seven_ws_entry(event_id, entry_id)
        return event
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileOperationError:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error removing 7 Ws entry: {str(e)}"
        )


@router.put(
    "/business-events/{event_id}/seven-entries/{entry_id}",
    response_model=BusinessEvent,
)
async def update_event_seven_ws_entry(
    event_id: str, entry_id: str, request: UpdateSevenWsEntryRequest = Body(...)
):
    """
    Update an existing 7 Ws entry in a business event.

    Args:
        event_id: ID of event
        entry_id: ID of entry to update
        request: UpdateSevenWsEntryRequest with fields to update

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
        event = update_seven_ws_entry(
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
            status_code=500, detail=f"Error updating 7 Ws entry: {str(e)}"
        )


@router.post(
    "/business-events/{event_id}/generate-entities",
    response_model=GeneratedEntitiesResult,
)
async def generate_entities_from_business_event(event_id: str):
    """
    Generate dimensional entities from a business event with 7 Ws structure.

    Args:
        event_id: ID of event to generate entities from

    Returns:
        GeneratedEntitiesResult with entities, relationships, and any errors

    Raises:
        FeatureDisabledError: If business events feature is disabled
        NotFoundError: If event not found
        ValidationError: If event doesn't have required 7 Ws data
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
