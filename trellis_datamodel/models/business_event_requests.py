"""Request bodies for the business events and processes API."""

from pydantic import BaseModel

from trellis_datamodel.models.business_event import BusinessEventAnnotations


class CreateEventRequest(BaseModel):
    """Request model for creating a business event."""

    text: str
    type: str | None = None
    description: str | None = None
    domain: str | None = None
    annotations: BusinessEventAnnotations | None = None


class UpdateEventRequest(BaseModel):
    """Request model for updating a business event."""

    text: str | None = None
    type: str | None = None
    description: str | None = None
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
    description: str | None = None
    domain: str
    event_ids: list[str] | None = None


class UpdateProcessRequest(BaseModel):
    """Request model for updating a business event process."""

    name: str | None = None
    type: str | None = None
    description: str | None = None
    domain: str | None = None
    annotations_superset: BusinessEventAnnotations | None = None
    event_ids: list[str] | None = None
    derived_entities: list[dict] | None = None


class AttachEventsRequest(BaseModel):
    """Request model for attaching events to a process."""

    event_ids: list[str]


class DetachEventsRequest(BaseModel):
    """Request model for detaching events from a process."""

    event_ids: list[str]
