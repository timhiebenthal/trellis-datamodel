"""Routes for lineage operations."""

from fastapi import APIRouter, Depends

from trellis_datamodel import config as cfg
from trellis_datamodel.routes.dependencies import require_feature
from trellis_datamodel.services.lineage import extract_upstream_lineage


router = APIRouter(
    prefix="/api",
    tags=["lineage"],
    dependencies=[
        Depends(
            require_feature(
                lambda: cfg.LINEAGE_ENABLED,
                "Lineage is disabled. Set lineage.enabled: true in trellis.yml to enable.",
            )
        )
    ],
)


@router.get("/lineage/{model_id}")
async def get_lineage(model_id: str):
    """
    Get upstream table-level lineage for a given model.

    Args:
        model_id: Unique ID of the model (e.g., "model.project.model_name")

    Returns:
        JSON response with nodes, edges, and metadata

    Raises:
        403: If lineage is disabled
        404: If model not found
        500: If lineage extraction fails
    """
    # Missing-metadata and unknown-model errors surface from the adapter.
    return extract_upstream_lineage(model_unique_id=model_id)
