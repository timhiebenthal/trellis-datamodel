"""Routes for lineage operations."""

from fastapi import APIRouter

from trellis_datamodel import config as cfg
from trellis_datamodel.exceptions import FeatureDisabledError
from trellis_datamodel.services.lineage import extract_upstream_lineage
from trellis_datamodel.utils.path_validation import validate_manifest_path


router = APIRouter(
    prefix="/api",
    tags=["lineage"],
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
    # Check if lineage is enabled
    if not cfg.LINEAGE_ENABLED:
        raise FeatureDisabledError(
            "Lineage is disabled. Set lineage.enabled: true in trellis.yml to enable."
        )

    # Validate manifest path exists
    manifest_path = validate_manifest_path()

    # Extract lineage
    lineage_data = extract_upstream_lineage(
        manifest_path=manifest_path,
        catalog_path=cfg.CATALOG_PATH,
        model_unique_id=model_id,
    )

    return lineage_data
