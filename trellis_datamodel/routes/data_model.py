"""Routes for data model CRUD operations."""
import logging

from fastapi import APIRouter, HTTPException

from trellis_datamodel.exceptions import ValidationError
from trellis_datamodel.models.schemas import DataModelUpdate
from trellis_datamodel.observability import timed_phase
from trellis_datamodel.services import data_model as data_model_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["data-model"])


@router.get("/data-model")
async def get_data_model():
    """Return current data model with layout merged in, with a read boundary."""
    with timed_phase("data_model_read"):
        try:
            return data_model_service.get_data_model()
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error reading data model: {str(e)}"
            )


@router.get("/source-systems/suggestions")
async def get_source_system_suggestions():
    """Return a consolidated list of known source system names for suggestions."""
    return {"suggestions": data_model_service.get_source_system_suggestions()}


@router.post("/data-model")
async def save_data_model(data: DataModelUpdate):
    """Save data model, splitting model and layout into separate files."""
    try:
        data_model_service.save_data_model(data.model_dump())
        return {"status": "success"}
    except ValidationError:
        # Let ValidationError propagate to exception handler
        raise
    except Exception as e:
        logger.exception("Error saving data model")
        raise HTTPException(
            status_code=500, detail=f"Error saving data model: {str(e)}"
        )
