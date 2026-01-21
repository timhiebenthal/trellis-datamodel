"""Pydantic models for API request/response schemas."""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union, Literal
from enum import Enum


# Enums for config values
class FrameworkEnum(str, Enum):
    """Framework options."""
    DBT_CORE = "dbt-core"


class ModelingStyleEnum(str, Enum):
    """Modeling style options."""
    DIMENSIONAL_MODEL = "dimensional_model"
    ENTITY_MODEL = "entity_model"


class ExposuresLayoutEnum(str, Enum):
    """Exposures default layout options."""
    DASHBOARDS_AS_ROWS = "dashboards-as-rows"
    ENTITIES_AS_ROWS = "entities-as-rows"


# Nested config models
class LineageConfig(BaseModel):
    """Lineage configuration (beta)."""
    enabled: bool = False
    layers: List[str] = Field(default_factory=list)


class DimensionalInferencePatterns(BaseModel):
    """Dimensional modeling inference patterns."""
    dimension_prefix: Union[str, List[str]] = Field(default_factory=lambda: ["dim_", "d_"])
    fact_prefix: Union[str, List[str]] = Field(default_factory=lambda: ["fct_", "fact_"])


class DimensionalModelingConfig(BaseModel):
    """Dimensional modeling configuration."""
    inference_patterns: DimensionalInferencePatterns = Field(default_factory=DimensionalInferencePatterns)


class EntityInferencePatterns(BaseModel):
    """Entity modeling inference patterns."""
    prefix: Union[str, List[str]] = Field(default_factory=list)


class EntityModelingConfig(BaseModel):
    """Entity modeling configuration."""
    inference_patterns: EntityInferencePatterns = Field(default_factory=EntityInferencePatterns)


class EntityCreationGuidance(BaseModel):
    """Entity creation guidance configuration."""
    enabled: bool = False
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


# Main config models
class ConfigSchema(BaseModel):
    """Complete trellis.yml configuration schema for validation."""
    framework: FrameworkEnum = FrameworkEnum.DBT_CORE
    modeling_style: ModelingStyleEnum = ModelingStyleEnum.ENTITY_MODEL
    dbt_project_path: str = Field(default="", description="Path to dbt project directory")
    dbt_manifest_path: str = Field(default="", description="Path to manifest.json")
    dbt_catalog_path: str = Field(default="", description="Path to catalog.json")
    data_model_file: str = Field(default="data_model.yml", description="Path to data model file")
    dbt_model_paths: List[str] = Field(default_factory=list, description="Path patterns to filter models")
    dbt_company_dummy_path: Optional[str] = Field(default=None, description="Optional path to company dummy project")
    lineage: LineageConfig = Field(default_factory=LineageConfig)
    entity_creation_guidance: EntityCreationGuidance = Field(default_factory=EntityCreationGuidance)
    exposures: ExposuresConfig = Field(default_factory=ExposuresConfig)
    business_events: BusinessEventsConfig = Field(default_factory=BusinessEventsConfig)
    dimensional_modeling: Optional[DimensionalModelingConfig] = Field(default=None)
    entity_modeling: Optional[EntityModelingConfig] = Field(default=None)


# Request Models
class DataModelUpdate(BaseModel):
    """Schema for updating the data model."""
    version: float = 0.1
    entities: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    source_colors: Optional[Dict[str, str]] = None  # Map of source name to color from canvas_layout.yml


class DbtSchemaRequest(BaseModel):
    """Schema for creating a new dbt schema file."""
    entity_id: str
    model_name: str
    fields: List[Dict[str, str]]
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class ModelSchemaRequest(BaseModel):
    """Schema for updating model columns and metadata."""
    columns: List[Dict[str, Any]]
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


class ConfigStatusResponse(BaseModel):
    """Response for configuration status."""
    config_present: bool
    config_filename: str
    framework: str
    dbt_project_path: Optional[str]
    manifest_path: Optional[str]
    catalog_path: Optional[str]
    manifest_exists: bool
    catalog_exists: bool
    data_model_exists: bool
    error: Optional[str] = None


class ConfigInfoResponse(BaseModel):
    """Response for detailed configuration info."""
    config_path: Optional[str]
    framework: str
    dbt_project_path: Optional[str]
    manifest_path: Optional[str]
    manifest_exists: bool
    catalog_path: Optional[str]
    catalog_exists: bool
    data_model_path: Optional[str]
    data_model_exists: bool
    canvas_layout_path: Optional[str]
    canvas_layout_exists: bool
    frontend_build_dir: Optional[str]
    model_paths_configured: List[str]
    model_paths_resolved: List[str]
    guidance: Dict[str, Any]
    entity_creation_guidance: Dict[str, Any]
    lineage_enabled: bool
    lineage_layers: List[str]
    exposures_enabled: bool
    exposures_default_layout: str
    bus_matrix_enabled: bool
    modeling_style: str
    label_prefixes: List[str]
    dimension_prefix: List[str]
    fact_prefix: List[str]
    entity_prefix: List[str]


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

