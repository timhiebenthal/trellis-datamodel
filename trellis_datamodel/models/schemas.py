"""Pydantic models for API request/response schemas."""
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Dict, Any, Union, Literal
from enum import Enum


# Enums for config values
class FrameworkEnum(str, Enum):
    """Frameworks Trellis has a working adapter for.

    A value only belongs here once its adapter exists: this enum is what the
    config UI offers, so an entry without an adapter behind it lets a user pick
    a framework that cannot work.
    """
    DBT_CORE = "dbt-core"
    BRUIN = "bruin"


class ModelingStyleEnum(str, Enum):
    """Modeling style options."""
    DIMENSIONAL_MODEL = "dimensional_model"
    ENTITY_MODEL = "entity_model"


class ExposuresLayoutEnum(str, Enum):
    """Exposures default layout options."""
    DASHBOARDS_AS_ROWS = "dashboards-as-rows"
    ENTITIES_AS_ROWS = "entities-as-rows"


class StartPageEnum(str, Enum):
    """Root route options."""
    CANVAS = "canvas"
    ENTITY_LIST = "entity-list"


# Nested config models
class LineageConfig(BaseModel):
    """Lineage configuration (beta)."""
    enabled: bool = False
    layers: List[str] = Field(default_factory=list)


class DimensionalInferencePatterns(BaseModel):
    """Dimensional modeling inference patterns."""
    dimension_prefix: Union[str, List[str]] = Field(default_factory=lambda: ["dim_", "d_"])
    fact_prefix: Union[str, List[str]] = Field(default_factory=lambda: ["fct_", "fact_"])


class DimensionalModelingConfigSchema(BaseModel):
    """Dimensional modeling configuration."""
    inference_patterns: DimensionalInferencePatterns = Field(default_factory=DimensionalInferencePatterns)


class EntityInferencePatterns(BaseModel):
    """Entity modeling inference patterns."""
    prefix: Union[str, List[str]] = Field(default_factory=list)


class EntityModelingConfigSchema(BaseModel):
    """Entity modeling configuration."""
    inference_patterns: EntityInferencePatterns = Field(default_factory=EntityInferencePatterns)


class EntityCreationGuidance(BaseModel):
    """Entity creation guidance configuration."""
    enabled: bool = True
    push_warning_enabled: bool = True
    min_description_length: int = Field(default=10, ge=0)
    disabled_guidance: List[str] = Field(default_factory=list)


class ExposuresConfig(BaseModel):
    """Exposures configuration (beta)."""
    enabled: bool = False
    default_layout: ExposuresLayoutEnum = ExposuresLayoutEnum.DASHBOARDS_AS_ROWS


class BusinessEventsConfig(BaseModel):
    """Business events configuration (beta)."""
    enabled: bool = False
    file: str = Field(default="", description="Path to business events YAML file")


class OssieSourceConfig(BaseModel):
    """Address segments for the Ossie dataset names (beta).

    The wire key is `schema`, but the attribute is `schema_name`: pydantic
    warns when a field shadows `BaseModel.schema`. The alias keeps the YAML
    and JSON spelling unchanged, so nothing consuming the config sees the
    difference.
    """
    model_config = ConfigDict(populate_by_name=True)

    database: str = ""
    schema_name: str = Field(default="", alias="schema")


class OssieConfigSchema(BaseModel):
    """Apache Ossie semantic model export configuration (beta)."""
    enabled: bool = False
    file: str = ""
    source: OssieSourceConfig = Field(default_factory=OssieSourceConfig)


class MetricsConfigSchema(BaseModel):
    """Metric tree canvas configuration (beta)."""
    enabled: bool = False
    file: str = ""
    expression_dialect: str = "ANSI_SQL"


class CanvasDefaultFilters(BaseModel):
    """Project-wide default filters for the Canvas."""
    domains: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class CanvasConfig(BaseModel):
    """Canvas configuration."""
    default_filters: CanvasDefaultFilters = Field(default_factory=CanvasDefaultFilters)


# Main config models
class ConfigSchema(BaseModel):
    """Complete trellis.yml configuration schema for validation."""
    framework: FrameworkEnum = FrameworkEnum.DBT_CORE
    modeling_style: ModelingStyleEnum = ModelingStyleEnum.ENTITY_MODEL
    start_page: StartPageEnum = StartPageEnum.CANVAS
    canvas: CanvasConfig = Field(default_factory=CanvasConfig)
    dbt_project_path: str = Field(default="", description="Path to dbt project directory")
    dbt_manifest_path: str = Field(default="", description="Path to manifest.json")
    dbt_catalog_path: str = Field(default="", description="Path to catalog.json")
    data_model_file: str = Field(default="data_model.yml", description="Path to data model file")
    dbt_model_paths: List[str] = Field(default_factory=list, description="Path patterns to filter models")
    dbt_company_dummy_path: str = Field(default="", description="Optional path to company dummy project")
    bruin_pipeline_path: str = Field(default="", description="Path to Bruin pipeline directory")
    bruin_asset_paths: List[str] = Field(default_factory=list, description="Path patterns to filter Bruin assets")
    bruin_default_asset_type: str = Field(default="duckdb.sql", description="Asset type used when Trellis scaffolds a new Bruin asset")
    lineage: LineageConfig = Field(default_factory=LineageConfig)
    entity_creation_guidance: EntityCreationGuidance = Field(default_factory=EntityCreationGuidance)
    exposures: ExposuresConfig = Field(default_factory=ExposuresConfig)
    business_events: BusinessEventsConfig = Field(default_factory=BusinessEventsConfig)
    ossie: OssieConfigSchema = Field(default_factory=OssieConfigSchema)
    metrics: MetricsConfigSchema = Field(default_factory=MetricsConfigSchema)
    dimensional_modeling: Optional[DimensionalModelingConfigSchema] = Field(default=None)
    entity_modeling: Optional[EntityModelingConfigSchema] = Field(default=None)


# Request Models
class DataModelUpdate(BaseModel):
    """Schema for updating the data model."""
    version: float = 0.1
    entities: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    source_colors: Optional[Dict[str, str]] = None  # Map of source name to color from canvas_layout.yml


class ModelSchemaRequest(BaseModel):
    """Schema for creating/updating a model's schema file.

    Supports two call shapes used by the schema routes:
    - POST /api/schema: entity_id + model_name + fields (resolves the model
      binding from entity_id and writes the given fields as columns).
    - POST /api/models/{model_name}/schema: columns (+ optional version),
      updating an already-identified model's schema in place.
    """
    entity_id: Optional[str] = None
    model_name: Optional[str] = None
    fields: Optional[List[Dict[str, Any]]] = None
    columns: Optional[List[Dict[str, Any]]] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    version: Optional[int] = None


# Response Models
class SuccessResponse(BaseModel):
    """Standard success response."""
    status: str = "success"
    message: Optional[str] = None


class SyncTestsResponse(SuccessResponse):
    """Response for sync-dbt-tests endpoint."""
    files: List[str] = []
    warnings: List[str] = Field(default_factory=list)


class FileOperationResponse(SuccessResponse):
    """Response for file operations."""
    file_path: str
    message: Optional[str] = None


class ModelSchemaResponse(BaseModel):
    """Response for model schema retrieval."""
    model_name: str
    description: str
    columns: List[Dict[str, Any]]
    tags: List[str]
    file_path: str


class ManifestResponse(BaseModel):
    """Response for manifest endpoint."""
    models: List[Dict[str, Any]]


class RelationshipsResponse(BaseModel):
    """Response for relationship inference."""
    relationships: List[Dict[str, Any]]


class ExposuresResponse(BaseModel):
    """Response for exposures endpoint."""
    exposures: List[Dict[str, Any]]
    entityUsage: Dict[str, List[str]]


class BusMatrixResponse(BaseModel):
    """Response for bus matrix endpoint."""
    dimensions: List[Dict[str, Any]]
    facts: List[Dict[str, Any]]
    connections: List[Dict[str, str]]


# Config API Models
class ConfigFieldMetadata(BaseModel):
    """Metadata for a config field."""
    type: str  # "string", "boolean", "integer", "list", "enum"
    enum_values: Optional[List[str]] = None
    default: Any = None
    required: bool = False
    description: str = ""
    beta: bool = False


class ConfigSchemaResponse(BaseModel):
    """Response with schema metadata for the config UI."""
    fields: Dict[str, ConfigFieldMetadata]
    beta_flags: List[str] = Field(default_factory=list)


class ConfigGetResponse(BaseModel):
    """Response for GET /api/config."""
    config: Dict[str, Any]
    schema_metadata: ConfigSchemaResponse
    file_info: Optional[Dict[str, Any]] = None
    trellis_version: Optional[str] = None
    error: Optional[str] = None


class ConfigUpdateRequest(BaseModel):
    """Request for PUT /api/config."""
    config: Dict[str, Any]
    expected_mtime: Optional[float] = None
    expected_hash: Optional[str] = None


class ConfigConflictInfo(BaseModel):
    """Information about a config conflict."""
    current_mtime: float
    current_hash: str
    expected_mtime: Optional[float]
    expected_hash: Optional[str]

