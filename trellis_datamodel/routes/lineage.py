"""Routes for lineage operations."""

from fastapi import APIRouter, HTTPException
import os

from trellis_datamodel import config as cfg
from trellis_datamodel.services.lineage import extract_upstream_lineage, LineageError

router = APIRouter(prefix="/api", tags=["lineage"])


@router.get("/lineage/{model_id}")
async def get_lineage(model_id: str):
    """
    Get upstream table-level lineage for a given model.

    Args:
        model_id: Unique ID of the model (e.g., "model.project.model_name")

    Returns:
        JSON response with nodes, edges, and metadata

    Raises:
        404: If model not found
        500: If lineage extraction fails
    """
    try:
        # Validate paths exist
        if not cfg.MANIFEST_PATH or not os.path.exists(cfg.MANIFEST_PATH):
            raise HTTPException(
                status_code=500,
                detail=f"Manifest not found at {cfg.MANIFEST_PATH}. Please ensure manifest.json exists.",
            )

        # Extract lineage
        lineage_data = extract_upstream_lineage(
            manifest_path=cfg.MANIFEST_PATH,
            catalog_path=cfg.CATALOG_PATH,
            model_unique_id=model_id,
        )

        return lineage_data

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except LineageError as e:
        # Check if it's a catalog missing error
        error_msg = str(e)
        if "catalog" in error_msg.lower() and "not found" in error_msg.lower():
            raise HTTPException(
                status_code=500,
                detail=f"{error_msg}. Please run 'dbt docs generate' to create catalog.json",
            )
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error extracting lineage: {str(e)}",
        )

