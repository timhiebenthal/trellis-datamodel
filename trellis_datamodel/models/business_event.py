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


class AnnotationEntry(BaseModel):
    """Single entry in an annotation category for a business event."""

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


class BusinessEventAnnotations(BaseModel):
    """Annotation structure for a business event (7 Ws from BEAM* methodology)."""

    who: List[AnnotationEntry] = Field(default_factory=list, description="Who entries")
    what: List[AnnotationEntry] = Field(default_factory=list, description="What entries")
    when: List[AnnotationEntry] = Field(default_factory=list, description="When entries")
    where: List[AnnotationEntry] = Field(default_factory=list, description="Where entries")
    how: List[AnnotationEntry] = Field(default_factory=list, description="How entries")
    why: List[AnnotationEntry] = Field(default_factory=list, description="Why entries")
    how_many: List[AnnotationEntry] = Field(
        default_factory=list, description="How Many entries (becomes fact table)"
    )

    @model_validator(mode="after")
    def validate_unique_entry_ids(self) -> "BusinessEventAnnotations":
        """Validate that all entry IDs are unique across all annotation categories."""
        all_entries: List[AnnotationEntry] = []
        for w_list in [
            self.who,
            self.what,
            self.when,
            self.where,
            self.how,
            self.why,
            self.how_many,
        ]:
            all_entries.extend(w_list)

        entry_ids = [entry.id for entry in all_entries]
        unique_ids = set(entry_ids)

        if len(entry_ids) != len(unique_ids):
            duplicates = [eid for eid in unique_ids if entry_ids.count(eid) > 1]
            raise ValueError(
                f"Duplicate entry IDs found in annotations structure: {', '.join(duplicates)}"
            )

        return self

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison (lowercase, strip whitespace)."""
        return text.lower().strip()

    def _get_entry_unique_key(
        self, entry: AnnotationEntry, annotation_type: str
    ) -> tuple:
        """
        Get unique key for an annotation entry based on union rules.

        Union rules:
        - Primary key: (annotation_type, dimension_id) when dimension_id exists
        - Fallback key: (annotation_type, normalized_text, description)

        Args:
            entry: The annotation entry
            annotation_type: The annotation category ('who', 'what', etc.)

        Returns:
            Tuple representing the unique key for this entry
        """
        if entry.dimension_id:
            return (annotation_type, entry.dimension_id)
        else:
            normalized_text = self._normalize_text(entry.text)
            return (annotation_type, normalized_text, entry.description or "")

    def validate_superset_uniqueness(self) -> "BusinessEventAnnotations":
        """
        Validate that superset annotations follow union uniqueness rules.

        For process-level superset annotations, entries should be unique based on:
        - Primary key: annotation_type + dimension_id (when dimension_id exists)
        - Fallback key: annotation_type + normalized_text + description

        This ensures that when multiple events are grouped, duplicate annotations
        are properly unioned at the process level.

        Returns:
            Self (for chaining)

        Raises:
            ValueError: If duplicate entries violate union uniqueness rules
        """
        annotation_categories = {
            "who": self.who,
            "what": self.what,
            "when": self.when,
            "where": self.where,
            "how": self.how,
            "why": self.why,
            "how_many": self.how_many,
        }

        seen_keys: Dict[tuple, AnnotationEntry] = {}
        duplicates: List[str] = []

        for annotation_type, entries in annotation_categories.items():
            for entry in entries:
                key = self._get_entry_unique_key(entry, annotation_type)
                if key in seen_keys:
                    existing = seen_keys[key]
                    duplicates.append(
                        f"{annotation_type}: '{entry.text}' (id: {entry.id}) "
                        f"conflicts with '{existing.text}' (id: {existing.id})"
                    )
                else:
                    seen_keys[key] = entry

        if duplicates:
            raise ValueError(
                f"Duplicate entries in superset annotations violate union uniqueness rules:\n"
                + "\n".join(f"  - {dup}" for dup in duplicates)
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
    annotation_type: Optional[str] = Field(
        None,
        description="Annotation category: 'who', 'what', 'when', 'where', 'how', 'how_many', 'why'",
    )

    @field_validator("annotation_type")
    @classmethod
    def validate_annotation_type(cls, v: Optional[str]) -> Optional[str]:
        """Validate that annotation_type is one of the valid annotation values."""
        if v is None:
            return v

        valid_types = {"who", "what", "when", "where", "how", "how_many", "why"}
        if v not in valid_types:
            raise ValueError(
                f"Invalid annotation_type '{v}'. Must be one of: {', '.join(sorted(valid_types))}"
            )

        return v


class DerivedEntity(BaseModel):
    """Entity derived from a business event."""

    entity_id: str = Field(..., description="ID of the generated entity")
    created_at: datetime = Field(..., description="When the entity was created")


class BusinessEvent(BaseModel):
    """A business event with annotations and derived entities."""

    id: str = Field(..., description="Unique event ID (e.g., evt_YYYYMMDD_NNN)")
    text: str = Field(..., description="Event description text")
    type: BusinessEventType = Field(..., description="Event type classification")
    domain: Optional[str] = Field(
        None, description="Optional business domain (e.g., 'Sales', 'Marketing')"
    )
    process_id: Optional[str] = Field(
        None, description="Optional ID of the process this event belongs to"
    )
    created_at: datetime = Field(..., description="When the event was created")
    updated_at: datetime = Field(..., description="When the event was last updated")
    annotations: BusinessEventAnnotations = Field(
        default_factory=BusinessEventAnnotations,
        description="Event annotations (Who, What, When, Where, How, How Many, Why)",
    )
    derived_entities: List[DerivedEntity] = Field(
        default_factory=list, description="Entities generated from this event"
    )


class BusinessEventProcess(BaseModel):
    """A process that groups related business events."""

    id: str = Field(..., description="Unique process ID (e.g., proc_YYYYMMDD_NNN)")
    name: str = Field(..., description="Process name")
    type: BusinessEventType = Field(
        ..., description="Process type classification (discrete, evolving, or recurring)"
    )
    domain: Optional[str] = Field(
        None,
        description="Business domain (e.g., 'Sales', 'Marketing') associated with the process",
    )
    event_ids: List[str] = Field(
        default_factory=list, description="List of event IDs belonging to this process"
    )
    created_at: datetime = Field(..., description="When the process was created")
    updated_at: datetime = Field(..., description="When the process was last updated")
    resolved_at: Optional[datetime] = Field(
        None, description="When the process was resolved (ungrouped), if applicable"
    )
    annotations_superset: Optional[BusinessEventAnnotations] = Field(
        None,
        description="Union of all member event annotations (computed or persisted)",
    )

    @model_validator(mode="after")
    def validate_event_ids_not_empty(self) -> "BusinessEventProcess":
        """Validate that a process has at least one event when not resolved."""
        if self.resolved_at is None and len(self.event_ids) == 0:
            raise ValueError("Process must have at least one event when not resolved")
        return self

    @field_validator("domain", mode="before")
    @classmethod
    def _normalize_domain(cls, value: Optional[str]) -> Optional[str]:
        """Trim domain text and reject empty strings."""
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("Process domain cannot be empty")
        return stripped


class BusinessEventProcessFile(BaseModel):
    """YAML file structure for business event processes."""

    processes: List[BusinessEventProcess] = Field(
        default_factory=list, description="List of business event processes"
    )


class BusinessEventsFile(BaseModel):
    """YAML file structure for business events."""

    events: List[BusinessEvent] = Field(
        default_factory=list, description="List of business events"
    )
    processes: Optional[List[BusinessEventProcess]] = Field(
        default_factory=list, description="List of business event processes"
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
