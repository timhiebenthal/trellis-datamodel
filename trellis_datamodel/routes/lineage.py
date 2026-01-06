"""Routes for lineage operations."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any
from datetime import datetime
import json
import os

from trellis_datamodel import config as cfg
from trellis_datamodel.services.lineage import extract_upstream_lineage, LineageError

router = APIRouter(prefix="/api", tags=["lineage"])

# Debug log file path
DEBUG_LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "debug.log")


class DebugLogEntry(BaseModel):
    """Debug log entry from frontend."""
    action: str
    data: Any


@router.post("/debug-log")
async def write_debug_log(entry: DebugLogEntry):
    """
    Write debug log entry to debug.log file.
    
    This is a temporary endpoint for debugging lineage rendering issues.
    """
    try:
        timestamp = datetime.now().isoformat()
        log_line = f"\n{'='*80}\n[{timestamp}] {entry.action}\n{'='*80}\n"
        
        if isinstance(entry.data, (dict, list)):
            log_line += json.dumps(entry.data, indent=2, default=str)
        else:
            log_line += str(entry.data)
        
        log_line += "\n"
        
        with open(DEBUG_LOG_PATH, "a") as f:
            f.write(log_line)
        
        return {"status": "ok", "path": DEBUG_LOG_PATH}
    except Exception as e:
        return {"status": "error", "message": str(e)}


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

