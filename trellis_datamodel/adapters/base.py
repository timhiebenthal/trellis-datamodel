"""
Base adapter protocol for transformation framework integrations.

This module defines the contract that all framework adapters must implement,
enabling support for dbt-core, SQLMesh, Bruin, etc.
"""

from pathlib import Path
from typing import Protocol, TypedDict, Optional, Any, NotRequired


class ColumnInfo(TypedDict):
    """Column metadata from a transformation framework."""

    name: str
    type: Optional[str]
    description: NotRequired[Optional[str]]
    origin: NotRequired[list[dict[str, str]]]


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
    origin: Optional[list[dict[str, str]]]


class ModelSchema(TypedDict, total=False):
    """Model schema for reading/writing model definitions."""

    model_name: str
    description: str
    columns: list[ColumnSchema]
    tags: list[str]
    file_path: str


class Entity(TypedDict, total=False):
    """Entity definition in the data model."""

    id: str
    label: str
    description: Optional[str]
    model_ref: Optional[str]
    additional_models: Optional[list[str]]
    drafted_fields: Optional[list[dict[str, Any]]]
    tags: Optional[list[str]]
    entity_type: Optional[str]  # "fact", "dimension", or "unclassified"


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


class LineageNode(TypedDict):
    """A node in an upstream lineage graph.

    Everything the lineage service needs to lay a node out, with no framework
    artifact structure leaking through: the service maps `folder` onto the
    configured lineage layers and computes levels from the edges.
    """

    unique_id: str
    name: str  # display label
    resource_type: str  # "model" | "source"
    is_source: bool
    source_name: Optional[str]  # dbt source name, Bruin ingestr source_connection
    folder: Optional[str]  # first path segment under the framework's model root
    file_path: NotRequired[str]


class LineageGraph(TypedDict):
    """Upstream lineage for a single model, as a node/edge graph."""

    nodes: list[LineageNode]
    edges: list[dict[str, str]]  # {"source": unique_id, "target": unique_id}


class Exposure(TypedDict, total=False):
    """A downstream consumer of the models in a project."""

    name: str
    label: str
    type: str
    url: Optional[str]
    maturity: Optional[str]
    owner: Optional[dict[str, str]]
    description: Optional[str]
    depends_on: list[str]  # upstream unique_ids


class Capabilities(TypedDict):
    """What the active framework can actually do.

    The frontend and the services gate optional features on these flags rather
    than on the framework name, so a new adapter never needs a
    `if framework == "..."` branch added on its behalf.
    """

    lineage: bool
    column_lineage: bool
    exposures: bool
    relationships: bool
    scaffolding: bool  # can save_schema_file create a model that does not exist yet


class ProjectStatus(TypedDict):
    """Health and configuration of the active framework's project.

    `artifacts` is framework-shaped on purpose — dbt reports manifest.json and
    catalog.json, Bruin reports its pipeline definition — but callers only ever
    read it generically, as {label: {path, exists, hint}}.
    """

    framework: str
    artifacts_present: bool
    artifacts: dict[str, dict[str, Any]]
    project_path: str
    project_path_exists: bool
    model_paths_configured: list[str]
    model_paths_resolved: list[str]
    capabilities: Capabilities
    error: Optional[str]


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
                that exist in the data model but are not yet bound to a framework
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

    def save_schema_file(
        self,
        entity_id: str,
        model_name: str,
        fields: list[dict[str, str]],
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> Path:
        """
        Generate and save a framework schema definition file for drafted fields.

        This is used for creating new schema files from the data model editor.

        Args:
            entity_id: Entity ID from the data model.
            model_name: Name of the framework model backing the entity.
            fields: List of field definitions.
            description: Optional model description.
            tags: Optional list of tags to additively union onto whatever is
                already present in the schema file.

        Returns:
            Path to the saved schema file.
        """
        ...

    def infer_entity_types(self) -> dict[str, str]:
        """
        Infer entity types from framework model naming patterns.

        Returns:
            dict[entity_id, entity_type]: Mapping from entity ID to inferred
            type ("fact", "dimension", or "unclassified").
        """
        ...

    def get_model_dirs(self) -> list[str]:
        """
        Return the directories where the active framework's models live.

        Returns:
            List of absolute directory paths.
        """
        ...

    def reset_inference_cache(self) -> None:
        """
        Reset any cached entity type inference results.

        Should be called when configuration changes that affect inference
        (e.g., dimensional modeling config, manifest path changes).
        """
        ...

    def get_lineage(self, model_unique_id: str) -> LineageGraph:
        """
        Return the upstream lineage graph for a model.

        Traverses the framework's dependency metadata from the given model back
        to its sources. The graph is raw: node levels, layer assignment, and
        display formatting are the caller's business.

        Args:
            model_unique_id: Framework-native identifier of the root model.

        Returns:
            Nodes (including the root) and directed upstream→downstream edges.

        Raises:
            NotFoundError: If the model is not present in the project.
        """
        ...

    def get_exposures(self) -> list[Exposure]:
        """
        Return the project's exposures — declared downstream consumers.

        Frameworks with no exposure concept return an empty list; check
        `get_project_status()["capabilities"]["exposures"]` to tell "none
        declared" apart from "not supported".

        Returns:
            List of exposures, each naming the upstream models it depends on.
        """
        ...

    def get_source_systems_for_model(self, model_unique_id: str) -> list[str]:
        """
        Return the names of the source systems feeding a model.

        Args:
            model_unique_id: Framework-native identifier of the model.

        Returns:
            Sorted, de-duplicated source system names. Empty when the model has
            no identifiable sources upstream — never raises, because this feeds
            optional display.
        """
        ...

    def get_project_status(self) -> ProjectStatus:
        """
        Report whether the configured project is present and usable.

        This is what lets routes answer "is Trellis wired up correctly?" without
        knowing which artifacts the active framework happens to use.

        Returns:
            Paths, existence flags, capabilities, and a user-facing `error`
            string when the project cannot be read.
        """
        ...

