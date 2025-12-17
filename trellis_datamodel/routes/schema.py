"""Routes for schema sync operations."""

from fastapi import APIRouter, HTTPException
import yaml
import os

from trellis_datamodel import config as cfg
from trellis_datamodel.models.schemas import DbtSchemaRequest, ModelSchemaRequest
from trellis_datamodel.adapters import get_adapter

router = APIRouter(prefix="/api", tags=["schema"])


@router.post("/dbt-schema")
async def save_dbt_schema(request: DbtSchemaRequest):
    """Generate and save a schema YAML file for the drafted fields."""
    try:
        if not cfg.DBT_PROJECT_PATH:
            raise HTTPException(
                status_code=400,
                detail="dbt_project_path is not configured. Please set it in config.yml",
            )

        adapter = get_adapter()
        output_path = adapter.save_dbt_schema(
            entity_id=request.entity_id,
            model_name=request.model_name,
            fields=request.fields,
            description=request.description,
            tags=request.tags,
        )

        return {
            "status": "success",
            "file_path": str(output_path),
            "message": f"Schema saved to {output_path}",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving schema: {str(e)}")


@router.post("/sync-dbt-tests")
async def sync_dbt_tests():
    """Sync relationship tests from data model to schema files."""
    try:
        if not cfg.DBT_PROJECT_PATH:
            raise HTTPException(
                status_code=400,
                detail="dbt_project_path is not configured. Please set it in config.yml",
            )

        if not cfg.DATA_MODEL_PATH or not os.path.exists(cfg.DATA_MODEL_PATH):
            raise HTTPException(status_code=404, detail="Data model file not found")

        with open(cfg.DATA_MODEL_PATH, "r") as f:
            data_model = yaml.safe_load(f) or {}

        entities = data_model.get("entities", [])
        relationships = data_model.get("relationships", [])

        adapter = get_adapter()
        updated_files = adapter.sync_relationships(entities, relationships)

        return {
            "status": "success",
            "message": f"Updated {len(updated_files)} file(s)",
            "files": [str(f) for f in updated_files],
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error syncing tests: {str(e)}")


@router.get("/models/{model_name}/schema")
async def get_model_schema(model_name: str, version: int | None = None):
    """Get the schema for a specific model from its YAML file."""
    try:
        if not cfg.DBT_PROJECT_PATH:
            raise HTTPException(
                status_code=400,
                detail="dbt_project_path is not configured. Please set it in config.yml",
            )

        adapter = get_adapter()
        schema = adapter.get_model_schema(model_name, version=version)

        return {
            "model_name": schema.get("model_name", model_name),
            "description": schema.get("description", ""),
            "columns": schema.get("columns", []),
            "tags": schema.get("tags", []),
            "file_path": schema.get("file_path", ""),
        }

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Error reading model schema: {str(e)}"
        )


@router.post("/models/{model_name}/schema")
async def update_model_schema(model_name: str, request: ModelSchemaRequest):
    """Update the schema for a specific model in its YAML file."""
    try:
        if not cfg.DBT_PROJECT_PATH:
            raise HTTPException(
                status_code=400,
                detail="dbt_project_path is not configured. Please set it in config.yml",
            )

        adapter = get_adapter()
        output_path = adapter.save_model_schema(
            model_name=model_name,
            columns=request.columns,
            description=request.description,
            tags=request.tags,
            version=request.version,
        )

        return {
            "status": "success",
            "message": f"Schema updated for model '{model_name}'",
            "file_path": str(output_path),
        }

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Error updating model schema: {str(e)}"
        )


@router.get("/infer-relationships")
async def infer_relationships(include_unbound: bool = False):
    """Scan schema files and infer entity relationships from relationship tests."""
    try:
        if not cfg.DBT_PROJECT_PATH:
            raise HTTPException(
                status_code=400,
                detail="dbt_project_path is not configured. Please set it in config.yml",
            )

        adapter = get_adapter()
        relationships = adapter.infer_relationships(include_unbound=include_unbound)

        return {"relationships": relationships}

    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Error inferring relationships: {str(e)}"
        )
