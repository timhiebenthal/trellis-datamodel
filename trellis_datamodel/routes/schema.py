"""Routes for schema sync operations."""

from fastapi import APIRouter

from trellis_datamodel.models.schemas import (
    DbtSchemaRequest,
    FileOperationResponse,
    ModelSchemaRequest,
    ModelSchemaResponse,
    RelationshipsResponse,
    SyncTestsResponse,
)
from trellis_datamodel.services.schema import (
    get_model_schema,
    infer_relationships,
    save_dbt_schema,
    sync_dbt_tests,
    update_model_schema,
)

router = APIRouter(prefix="/api", tags=["schema"])


@router.post("/dbt-schema", response_model=FileOperationResponse)
async def save_dbt_schema_endpoint(request: DbtSchemaRequest):
    """Generate and save a schema YAML file for the drafted fields."""
    output_path = save_dbt_schema(
        entity_id=request.entity_id,
        model_name=request.model_name,
        fields=request.fields,
        description=request.description,
        tags=request.tags,
    )

    return FileOperationResponse(
        file_path=str(output_path),
        message=f"Schema saved to {output_path}",
    )


@router.post("/sync-dbt-tests", response_model=SyncTestsResponse)
async def sync_dbt_tests_endpoint():
    """Sync relationship tests from data model to schema files."""
    updated_files = sync_dbt_tests()

    return SyncTestsResponse(
        message=f"Updated {len(updated_files)} file(s)",
        files=[str(f) for f in updated_files],
    )


@router.get("/models/{model_name}/schema", response_model=ModelSchemaResponse)
async def get_model_schema_endpoint(model_name: str, version: int | None = None):
    """Get the schema for a specific model from its YAML file."""
    schema = get_model_schema(model_name, version=version)
    return ModelSchemaResponse(**schema)


@router.post("/models/{model_name}/schema", response_model=FileOperationResponse)
async def update_model_schema_endpoint(
    model_name: str, request: ModelSchemaRequest
):
    """Update the schema for a specific model in its YAML file."""
    output_path = update_model_schema(
        model_name=model_name,
        columns=request.columns,
        description=request.description,
        tags=request.tags,
        version=request.version,
    )

    return FileOperationResponse(
        file_path=str(output_path),
        message=f"Schema updated for model '{model_name}'",
    )


@router.get("/infer-relationships", response_model=RelationshipsResponse)
async def infer_relationships_endpoint(include_unbound: bool = False):
    """Scan schema files and infer entity relationships from relationship tests."""
    relationships = infer_relationships(include_unbound=include_unbound)
    return RelationshipsResponse(relationships=relationships)
