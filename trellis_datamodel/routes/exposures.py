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

    First tries to read exposures from manifest.json (canonical source after dbt compilation).
    Falls back to reading exposures.yml from various locations if manifest doesn't have exposures.
    """
    result = get_exposures()
    return ExposuresResponse(**result)
