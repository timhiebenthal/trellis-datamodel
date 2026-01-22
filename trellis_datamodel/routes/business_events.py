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
)
from trellis_datamodel.services.business_events_service import (
    load_business_events,
    create_event,
    update_event,
    delete_event,
    add_annotation,
    remove_annotation,
    get_unique_domains,
)
from trellis_datamodel.services.entity_generator import generate_entities_from_event

router = APIRouter(prefix="/api", tags=["business-events"])


class CreateEventRequest(BaseModel):
    """Request model for creating a business event."""

    text: str
    type: str
    domain: str | None = None


class UpdateEventRequest(BaseModel):
    """Request model for updating a business event."""

    text: str | None = None
    type: str | None = None
    domain: str | None = None
    annotations: list[dict] | None = None
    derived_entities: list[dict] | None = None


class AddAnnotationRequest(BaseModel):
    """Request model for adding an annotation."""

    text: str
    type: str
    start_pos: int
    end_pos: int


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
        raise HTTPException(status_code=500, detail=f"Error loading business event domains: {str(e)}")


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
        raise HTTPException(status_code=500, detail=f"Error loading business events: {str(e)}")


@router.post("/business-events", response_model=BusinessEvent, status_code=201)
async def create_business_event(request: CreateEventRequest = Body(...)):
    """
    Create a new business event.

    Args:
        request: CreateEventRequest with text and type

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
        return event
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileOperationError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating business event: {str(e)}")


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

        event = update_event(event_id, updates)
        return event
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileOperationError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating business event: {str(e)}")


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
    _check_feature_enabled()

    try:
        delete_event(event_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileOperationError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting business event: {str(e)}")


@router.post("/business-events/{event_id}/annotations", response_model=BusinessEvent)
async def add_event_annotation(event_id: str, request: AddAnnotationRequest = Body(...)):
    """
    Add an annotation to a business event.

    Args:
        event_id: ID of event to annotate
        request: AddAnnotationRequest with annotation details

    Returns:
        Updated BusinessEvent object

    Raises:
        FeatureDisabledError: If business events feature is disabled
        NotFoundError: If event not found
        ValidationError: If annotation is invalid or overlaps existing annotations
        FileOperationError: If file operations fail
    """
    _check_feature_enabled()

    try:
        event = add_annotation(
            event_id, request.text, request.type, request.start_pos, request.end_pos
        )
        return event
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileOperationError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding annotation: {str(e)}")


@router.delete("/business-events/{event_id}/annotations/{index}", response_model=BusinessEvent)
async def remove_event_annotation(event_id: str, index: int):
    """
    Remove an annotation from a business event by index.

    Args:
        event_id: ID of event
        index: Index of annotation to remove

    Returns:
        Updated BusinessEvent object

    Raises:
        FeatureDisabledError: If business events feature is disabled
        NotFoundError: If event not found or annotation index out of bounds
        FileOperationError: If file operations fail
    """
    _check_feature_enabled()

    try:
        event = remove_annotation(event_id, index)
        return event
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except FileOperationError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error removing annotation: {str(e)}")


@router.post("/business-events/{event_id}/generate-entities", response_model=GeneratedEntitiesResult)
async def generate_entities_from_business_event(event_id: str):
    """
    Generate dimensional entities from an annotated business event.

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
            raise HTTPException(status_code=404, detail=f"Business event '{event_id}' not found")

        result = generate_entities_from_event(event)
        return result
    except NotFoundError:
        raise
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FileOperationError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating entities: {str(e)}")
