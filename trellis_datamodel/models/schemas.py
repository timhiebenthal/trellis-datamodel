"""Pydantic models for API request/response schemas."""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any


# Request Models
class DataModelUpdate(BaseModel):
    """Schema for updating the data model."""
    version: float = 0.1
    entities: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]


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

