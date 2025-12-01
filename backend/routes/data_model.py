"""Routes for data model CRUD operations."""

from fastapi import APIRouter, HTTPException
import yaml
import os

from config import DATA_MODEL_PATH
from models.schemas import DataModelUpdate

router = APIRouter(prefix="/api", tags=["data-model"])


@router.get("/data-model")
async def get_data_model():
    """Return the current data model."""
    if not os.path.exists(DATA_MODEL_PATH):
        return {"version": 0.1, "entities": [], "relationships": []}

    try:
        with open(DATA_MODEL_PATH, "r") as f:
            data = yaml.safe_load(f) or {}

        if not data.get("entities"):
            data["entities"] = []
        if not data.get("relationships"):
            data["relationships"] = []

        return data
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error reading data model: {str(e)}"
        )


@router.post("/data-model")
async def save_data_model(data: DataModelUpdate):
    """Save the data model."""
    try:
        content = data.dict()  # Pydantic v1 (required by dbt-core==1.10)
        print(f"Saving data model to: {DATA_MODEL_PATH}")
        with open(DATA_MODEL_PATH, "w") as f:
            yaml.dump(content, f, default_flow_style=False, sort_keys=False)
            f.flush()
            os.fsync(f.fileno())
        return {"status": "success"}
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Error saving data model: {str(e)}"
        )
