"""Pydantic models for business events."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class BusinessEventType(str, Enum):
    """Business event type classification (BEAM* methodology)."""

    DISCRETE = "discrete"
    EVOLVING = "evolving"
    RECURRING = "recurring"


class SevenWsEntry(BaseModel):
    """Single entry in a 7 Ws category for a business event."""

    id: str = Field(..., description="Unique ID for this entry within the event")
    dimension_id: Optional[str] = Field(
        None, description="Reference to dimension in data_model.yml, or None for new"
    )
    text: str = Field(..., description="Entry text (e.g., 'customer')")
    description: Optional[str] = Field(
        None, description="Optional description for the entry"
    )
    attributes: Dict[str, Any] = Field(
        default_factory=dict, description="Additional attributes (future-proofing)"
    )


class BusinessEventSevenWs(BaseModel):
    """7 Ws structure for a business event (BEAM* methodology)."""

    who: List[SevenWsEntry] = Field(default_factory=list, description="Who entries")
    what: List[SevenWsEntry] = Field(default_factory=list, description="What entries")
    when: List[SevenWsEntry] = Field(default_factory=list, description="When entries")
    where: List[SevenWsEntry] = Field(default_factory=list, description="Where entries")
    how: List[SevenWsEntry] = Field(default_factory=list, description="How entries")
    how_many: List[SevenWsEntry] = Field(
        default_factory=list, description="How Many entries (becomes fact table)"
    )
    why: List[SevenWsEntry] = Field(default_factory=list, description="Why entries")

    @model_validator(mode="after")
    def validate_unique_entry_ids(self) -> "BusinessEventSevenWs":
        """Validate that all entry IDs are unique across all Ws."""
        all_entries: List[SevenWsEntry] = []
        for w_list in [
            self.who,
            self.what,
            self.when,
            self.where,
            self.how,
            self.how_many,
            self.why,
        ]:
            all_entries.extend(w_list)

        entry_ids = [entry.id for entry in all_entries]
        unique_ids = set(entry_ids)

        if len(entry_ids) != len(unique_ids):
            duplicates = [eid for eid in unique_ids if entry_ids.count(eid) > 1]
            raise ValueError(
                f"Duplicate entry IDs found in seven_ws structure: {', '.join(duplicates)}"
            )

        return self


class EntityDimensionMetadata(BaseModel):
    """Metadata for dimensions created from business events."""

    is_dimension_from_business_event: bool = Field(
        default=False,
        description="Whether this dimension was created from a business event",
    )
    business_event_sources: List[str] = Field(
        default_factory=list, description="List of event IDs using this dimension"
    )
    seven_w_type: Optional[str] = Field(
        None,
        description="7 Ws category: 'who', 'what', 'when', 'where', 'how', 'how_many', 'why'",
    )

    @field_validator("seven_w_type")
    @classmethod
    def validate_seven_w_type(cls, v: Optional[str]) -> Optional[str]:
        """Validate that seven_w_type is one of the valid 7 Ws values."""
        if v is None:
            return v

        valid_types = {"who", "what", "when", "where", "how", "how_many", "why"}
        if v not in valid_types:
            raise ValueError(
                f"Invalid seven_w_type '{v}'. Must be one of: {', '.join(sorted(valid_types))}"
            )

        return v


class DerivedEntity(BaseModel):
    """Entity derived from a business event."""

    entity_id: str = Field(..., description="ID of the generated entity")
    created_at: datetime = Field(..., description="When the entity was created")


class BusinessEvent(BaseModel):
    """A business event with 7 Ws structure and derived entities."""

    id: str = Field(..., description="Unique event ID (e.g., evt_YYYYMMDD_NNN)")
    text: str = Field(..., description="Event description text")
    type: BusinessEventType = Field(..., description="Event type classification")
    domain: Optional[str] = Field(
        None, description="Optional business domain (e.g., 'Sales', 'Marketing')"
    )
    created_at: datetime = Field(..., description="When the event was created")
    updated_at: datetime = Field(..., description="When the event was last updated")
    seven_ws: BusinessEventSevenWs = Field(
        default_factory=BusinessEventSevenWs,
        description="7 Ws structure (Who, What, When, Where, How, How Many, Why)",
    )
    derived_entities: List[DerivedEntity] = Field(
        default_factory=list, description="Entities generated from this event"
    )


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
