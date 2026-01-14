"""Routes for Bus Matrix operations."""

from fastapi import APIRouter, Query

from trellis_datamodel.models.schemas import BusMatrixResponse
from trellis_datamodel.services.bus_matrix import get_bus_matrix

router = APIRouter(prefix="/api", tags=["bus-matrix"])


@router.get("/bus-matrix", response_model=BusMatrixResponse)
async def get_bus_matrix_endpoint(
    dimension_id: str | None = Query(
        default=None, description="Filter by specific dimension entity ID"
    ),
    fact_id: str | None = Query(
        default=None, description="Filter by specific fact entity ID"
    ),
    tag: str | None = Query(
        default=None, description="Filter by tag (entities must have this tag)"
    ),
):
    """
    Return Bus Matrix data showing dimension-fact connections.

    Returns:
        Dictionary containing dimensions, facts, and their connections.
        - dimensions: List of dimension entities with entity_type == "dimension"
        - facts: List of fact entities with entity_type == "fact"
        - connections: List of dimension-fact connections derived from relationships
    """
    result = get_bus_matrix(
        dimension_id=dimension_id, fact_id=fact_id, tag=tag
    )
    return BusMatrixResponse(**result)

