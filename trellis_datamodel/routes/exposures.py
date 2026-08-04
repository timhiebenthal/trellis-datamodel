"""Routes for exposures operations."""

from fastapi import APIRouter

from trellis_datamodel.models.schemas import ExposuresResponse
from trellis_datamodel.services.exposures import get_exposures

router = APIRouter(prefix="/api", tags=["exposures"])


"""Routes for exposures operations."""

from fastapi import APIRouter

from trellis_datamodel.models.schemas import ExposuresResponse
from trellis_datamodel.services.exposures import get_exposures

router = APIRouter(prefix="/api", tags=["exposures"])


@router.get("/exposures", response_model=ExposuresResponse)
async def get_exposures_endpoint():
    """
    Return exposures data and entity usage mapping.

    Where the exposures come from is the active framework's adapter's business;
    frameworks with no exposure concept report none.
    """
    result = get_exposures()
    return ExposuresResponse(**result)
