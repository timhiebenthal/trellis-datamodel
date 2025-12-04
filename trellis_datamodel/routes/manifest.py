"""Routes for manifest and catalog operations."""

from fastapi import APIRouter, HTTPException
import os

from trellis_datamodel.config import (
    CONFIG_PATH,
    FRAMEWORK,
    MANIFEST_PATH,
    CATALOG_PATH,
    DATA_MODEL_PATH,
    DBT_PROJECT_PATH,
)
from trellis_datamodel.adapters import get_adapter

router = APIRouter(prefix="/api", tags=["manifest"])


@router.get("/config-status")
async def get_config_status():
    """Return configuration status for the frontend."""
    config_present = os.path.exists(CONFIG_PATH)
    manifest_exists = os.path.exists(MANIFEST_PATH) if MANIFEST_PATH else False
    catalog_exists = os.path.exists(CATALOG_PATH) if CATALOG_PATH else False
    data_model_exists = os.path.exists(DATA_MODEL_PATH) if DATA_MODEL_PATH else False

    error = None
    if not config_present:
        error = "Config file not found."
    elif not DBT_PROJECT_PATH:
        error = "dbt_project_path not set in config."
    elif not manifest_exists:
        error = f"Manifest not found at {MANIFEST_PATH}"

    return {
        "config_present": config_present,
        "framework": FRAMEWORK,
        "dbt_project_path": DBT_PROJECT_PATH,
        "manifest_path": MANIFEST_PATH,
        "catalog_path": CATALOG_PATH,
        "manifest_exists": manifest_exists,
        "catalog_exists": catalog_exists,
        "data_model_exists": data_model_exists,
        "error": error,
    }


@router.get("/manifest")
async def get_manifest():
    """Return parsed models from the transformation framework."""
    try:
        adapter = get_adapter()
        models = adapter.get_models()
        return {"models": models}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading manifest: {str(e)}")

