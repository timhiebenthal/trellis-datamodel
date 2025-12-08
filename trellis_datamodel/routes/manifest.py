"""Routes for manifest and catalog operations."""

from fastapi import APIRouter, HTTPException
import os

from trellis_datamodel.config import (
    CANVAS_LAYOUT_PATH,
    CATALOG_PATH,
    CONFIG_PATH,
    DATA_MODEL_PATH,
    DBT_MODEL_PATHS,
    DBT_PROJECT_PATH,
    FRAMEWORK,
    FRONTEND_BUILD_DIR,
    MANIFEST_PATH,
    find_config_file,
)
from trellis_datamodel.adapters import get_adapter

router = APIRouter(prefix="/api", tags=["manifest"])


@router.get("/config-status")
async def get_config_status():
    """Return configuration status for the frontend."""
    # Check if config exists - use CONFIG_PATH from startup if available
    # If CONFIG_PATH is set (loaded at startup), use that. Otherwise search.
    if CONFIG_PATH and os.path.exists(CONFIG_PATH):
        found_config = CONFIG_PATH
        config_present = True
    else:
        found_config = find_config_file()
        config_present = found_config is not None

    # Determine expected config filename for display
    if config_present:
        config_filename = os.path.basename(found_config)
    else:
        # Default to trellis.yml (primary config file name)
        config_filename = "trellis.yml"

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
        "config_filename": config_filename,
        "framework": FRAMEWORK,
        "dbt_project_path": DBT_PROJECT_PATH,
        "manifest_path": MANIFEST_PATH,
        "catalog_path": CATALOG_PATH,
        "manifest_exists": manifest_exists,
        "catalog_exists": catalog_exists,
        "data_model_exists": data_model_exists,
        "error": error,
    }


@router.get("/config-info")
async def get_config_info():
    """
    Return resolved config paths and their existence for transparency/debugging.
    """
    if CONFIG_PATH and os.path.exists(CONFIG_PATH):
        config_path = CONFIG_PATH
    else:
        config_path = find_config_file()

    adapter = get_adapter()
    try:
        model_dirs = adapter.get_model_dirs()  # type: ignore[attr-defined]
    except Exception:
        model_dirs = []

    return {
        "config_path": config_path,
        "framework": FRAMEWORK,
        "dbt_project_path": DBT_PROJECT_PATH,
        "manifest_path": MANIFEST_PATH,
        "manifest_exists": bool(MANIFEST_PATH and os.path.exists(MANIFEST_PATH)),
        "catalog_path": CATALOG_PATH,
        "catalog_exists": bool(CATALOG_PATH and os.path.exists(CATALOG_PATH)),
        "data_model_path": DATA_MODEL_PATH,
        "data_model_exists": bool(DATA_MODEL_PATH and os.path.exists(DATA_MODEL_PATH)),
        "canvas_layout_path": CANVAS_LAYOUT_PATH,
        "canvas_layout_exists": bool(
            CANVAS_LAYOUT_PATH and os.path.exists(CANVAS_LAYOUT_PATH)
        ),
        "frontend_build_dir": FRONTEND_BUILD_DIR,
        "model_paths_configured": DBT_MODEL_PATHS,
        "model_paths_resolved": model_dirs,
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
