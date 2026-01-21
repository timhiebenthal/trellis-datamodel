"""Pydantic models for business events and annotations."""
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class BusinessEventType(str, Enum):
    """Business event type classification (BEAM* methodology)."""

    DISCRETE = "discrete"
    EVOLVING = "evolving"
    RECURRING = "recurring"


class Annotation(BaseModel):
    """Text annotation within a business event."""

    text: str = Field(..., description="The annotated text segment")
    type: str = Field(..., description="Annotation type: 'dimension' or 'fact'")
    start_pos: int = Field(..., ge=0, description="Start position of annotation in event text")
    end_pos: int = Field(..., ge=0, description="End position of annotation in event text")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate annotation type is dimension or fact."""
        if v not in ["dimension", "fact"]:
            raise ValueError("Annotation type must be 'dimension' or 'fact'")
        return v

    @model_validator(mode="after")
    def validate_positions(self) -> "Annotation":
        """Validate start_pos < end_pos."""
        if self.start_pos >= self.end_pos:
            raise ValueError("start_pos must be less than end_pos")
        return self


class DerivedEntity(BaseModel):
    """Entity derived from a business event."""

    entity_id: str = Field(..., description="ID of the generated entity")
    created_at: datetime = Field(..., description="When the entity was created")


class BusinessEvent(BaseModel):
    """A business event with annotations and derived entities."""

    id: str = Field(..., description="Unique event ID (e.g., evt_YYYYMMDD_NNN)")
    text: str = Field(..., description="Event description text")
    type: BusinessEventType = Field(..., description="Event type classification")
    created_at: datetime = Field(..., description="When the event was created")
    updated_at: datetime = Field(..., description="When the event was last updated")
    annotations: List[Annotation] = Field(
        default_factory=list, description="Text annotations (dimensions/facts)"
    )
    derived_entities: List[DerivedEntity] = Field(
        default_factory=list, description="Entities generated from this event"
    )

    @model_validator(mode="after")
    def validate_annotations(self) -> "BusinessEvent":
        """Validate no overlapping annotations."""
        if not self.annotations:
            return self

        # Sort annotations by start position
        sorted_annotations = sorted(self.annotations, key=lambda a: a.start_pos)

        for i in range(len(sorted_annotations) - 1):
            current = sorted_annotations[i]
            next_annotation = sorted_annotations[i + 1]

            # Check for overlap: current end_pos > next start_pos
            if current.end_pos > next_annotation.start_pos:
                raise ValueError(
                    f"Overlapping annotations detected: '{current.text}' "
                    f"({current.start_pos}-{current.end_pos}) overlaps with "
                    f"'{next_annotation.text}' ({next_annotation.start_pos}-{next_annotation.end_pos})"
                )

        return self


class BusinessEventsFile(BaseModel):
    """YAML file structure for business events."""

    events: List[BusinessEvent] = Field(
        default_factory=list, description="List of business events"
    )


class GeneratedEntitiesResult(BaseModel):
    """Result of entity generation from a business event."""

    entities: List[dict] = Field(
        default_factory=list, description="Generated entity dictionaries"
    )
    relationships: List[dict] = Field(
        default_factory=list, description="Generated relationship dictionaries"
    )
    errors: List[str] = Field(
        default_factory=list, description="Validation errors if any"
    )
