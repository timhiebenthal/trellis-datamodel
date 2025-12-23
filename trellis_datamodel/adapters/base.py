"""
Base adapter protocol for transformation framework integrations.

This module defines the contract that all framework adapters must implement,
enabling support for dbt-core, SQLMesh, Bruin, etc.
"""

from pathlib import Path
from typing import Protocol, TypedDict, Optional, Any


class ColumnInfo(TypedDict):
    """Column metadata from a transformation framework."""

    name: str
    type: Optional[str]


class ModelInfo(TypedDict):
    """Model metadata returned by get_models()."""

    unique_id: str
    name: str
    version: Optional[int]
    schema: str
    table: str
    columns: list[ColumnInfo]
    description: Optional[str]
    materialization: str
    file_path: str
    tags: list[str]


class ColumnSchema(TypedDict, total=False):
    """Column schema for reading/writing model definitions."""

    name: str
    data_type: Optional[str]
    description: Optional[str]
    data_tests: Optional[list[dict[str, Any]]]


class ModelSchema(TypedDict, total=False):
    """Model schema for reading/writing model definitions."""

    model_name: str
    description: str
    columns: list[ColumnSchema]
    tags: list[str]
    file_path: str


class Relationship(TypedDict, total=False):
    """Relationship inferred from framework metadata."""

    source: str
    target: str
    label: str
    type: str  # e.g., "one_to_many"
    source_field: str
    target_field: str
    source_model_name: str  # name of the source model (e.g., "employee")
    source_model_version: Optional[int]  # version of the source model if versioned
    target_model_name: str  # name of the target model (e.g., "employee_history")
    target_model_version: Optional[int]  # version of the target model if versioned


class TransformationAdapter(Protocol):
    """
    Protocol defining the interface for transformation framework adapters.

    Implementations should handle framework-specific parsing and schema generation.
    """

    def get_models(self) -> list[ModelInfo]:
        """
        Parse framework metadata and return available models.

        Returns:
            List of model metadata dictionaries.
        """
        ...

    def get_model_schema(self, model_name: str, version: Optional[int] = None) -> ModelSchema:
        """
        Get the current schema definition for a specific model.

        Args:
            model_name: Name of the model to retrieve.
            version: Optional version number to disambiguate versioned models.

        Returns:
            Model schema including columns and metadata.
        """
        ...

    def save_model_schema(
        self,
        model_name: str,
        columns: list[ColumnSchema],
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        version: Optional[int] = None,
    ) -> Path:
        """
        Save/update the schema definition for a model.

        Args:
            model_name: Name of the model to update.
            version: Optional version number to target for versioned models.
            columns: Column definitions to save.
            description: Optional model description.
            tags: Optional list of tags.

        Returns:
            Path to the saved schema file.
        """
        ...

    def infer_relationships(self, include_unbound: bool = False) -> list[Relationship]:
        """
        Scan framework schema files and infer entity relationships.

        Args:
            include_unbound: When True, also include relationships for entities
                that exist in the data model but are not yet bound to a dbt
                model. Useful for frontends that want immediate inference right
                after a bind action, before the data model file is persisted.

        Returns:
            List of inferred relationships.
        """
        ...

    def sync_relationships(
        self,
        entities: list[dict[str, Any]],
        relationships: list[dict[str, Any]],
    ) -> list[Path]:
        """
        Sync relationship definitions from data model to framework schema files.

        Args:
            entities: List of entity definitions from the data model.
            relationships: List of relationship definitions to sync.

        Returns:
            List of paths to updated schema files.
        """
        ...

