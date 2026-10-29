"""Routes for data model CRUD operations."""

from fastapi import APIRouter

from trellis_datamodel.models.schemas import (
    DataModelResponse,
    DataModelUpdate,
    SourceSystemSuggestionsResponse,
    SuccessResponse,
)
from trellis_datamodel.observability import timed_phase
from trellis_datamodel.services import data_model as data_model_service

router = APIRouter(prefix="/api", tags=["data-model"])


@router.get("/data-model", response_model=DataModelResponse)
async def get_data_model():
    """Return current data model with layout merged in, with a read boundary."""
    with timed_phase("data_model_read"):
        return data_model_service.get_data_model()


@router.get(
    "/source-systems/suggestions", response_model=SourceSystemSuggestionsResponse
)
async def get_source_system_suggestions():
    """Return a consolidated list of known source system names for suggestions."""
    return {"suggestions": data_model_service.get_source_system_suggestions()}


@router.post("/data-model", response_model=SuccessResponse)
async def save_data_model(data: DataModelUpdate):
    """Save data model, splitting model and layout into separate files."""
    data_model_service.save_data_model(data.model_dump())
    return SuccessResponse()
