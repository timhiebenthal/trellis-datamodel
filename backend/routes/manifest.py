"""Routes for dbt manifest and catalog operations."""
from fastapi import APIRouter, HTTPException
import json
import os

from config import (
    CONFIG_PATH,
    MANIFEST_PATH,
    CATALOG_PATH,
    DATA_MODEL_PATH,
    DBT_PROJECT_PATH,
    DBT_MODEL_PATHS,
)

router = APIRouter(prefix="/api", tags=["manifest"])


def load_catalog():
    """Load catalog.json if it exists."""
    if not os.path.exists(CATALOG_PATH):
        return None
    try:
        with open(CATALOG_PATH, "r") as f:
            return json.load(f)
    except Exception as exc:
        print(f"Warning: failed to read catalog at {CATALOG_PATH}: {exc}")
        return None


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
    """Return parsed dbt models from manifest.json."""
    if not os.path.exists(MANIFEST_PATH):
        raise HTTPException(
            status_code=404, detail=f"Manifest not found at {MANIFEST_PATH}"
        )

    try:
        with open(MANIFEST_PATH, "r") as f:
            data = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading manifest: {str(e)}")

    catalog = load_catalog()
    catalog_nodes = (catalog or {}).get("nodes", {})

    models = []
    for key, node in data.get("nodes", {}).items():
        if node.get("resource_type") == "model":
            # Filter by path
            original_path = node.get("original_file_path", "")

            # If DBT_MODEL_PATHS is set, require at least one match
            if DBT_MODEL_PATHS:
                match = False
                for pattern in DBT_MODEL_PATHS:
                    if pattern in original_path:
                        match = True
                        break
                if not match:
                    continue

            def catalog_columns():
                unique_id = node.get("unique_id")
                catalog_node = catalog_nodes.get(unique_id)
                if not catalog_node:
                    return None
                cols = []
                for col in catalog_node.get("columns", {}).values():
                    cols.append(
                        {
                            "name": col.get("name"),
                            "type": col.get("type") or col.get("data_type"),
                        }
                    )
                return cols

            columns = catalog_columns()
            if not columns:
                columns = []
                for col_name, col_data in node.get("columns", {}).items():
                    columns.append({"name": col_name, "type": col_data.get("type")})

            # Extract materialization from config (defaults to "view" if not specified)
            config = node.get("config", {})
            materialized = config.get("materialized", "view")

            models.append(
                {
                    "unique_id": node.get("unique_id"),
                    "name": node.get("name"),
                    "schema": node.get("schema"),
                    "table": node.get("alias", node.get("name")),
                    "columns": columns,
                    "description": node.get("description"),
                    "materialization": materialized,
                    "file_path": original_path,
                    "tags": node.get("tags", []),
                }
            )

    models.sort(key=lambda x: x["name"])
    return {"models": models}

