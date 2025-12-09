"""Pydantic models for API request/response schemas."""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any


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

