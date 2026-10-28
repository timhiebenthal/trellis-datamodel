"""Routes for schema sync operations."""

from fastapi import APIRouter

from trellis_datamodel import config as cfg
from trellis_datamodel.observability import timed_phase
from trellis_datamodel.models.schemas import (
    FileOperationResponse,
    ModelSchemaRequest,
    ModelSchemaResponse,
    RelationshipsResponse,
    SyncTestsResponse,
)
from trellis_datamodel.services.schema import (
    get_model_schema,
    infer_relationships,
    save_model_schema_from_request,
    sync_framework_tests,
    update_model_schema,
)
from trellis_datamodel.utils.path_validation import validate_model_name

router = APIRouter(prefix="/api", tags=["schema"])


@router.post("/schema", response_model=FileOperationResponse)
async def save_model_schema_endpoint(request: ModelSchemaRequest):
    """Generate and save a schema YAML file for the drafted fields."""
    # The name becomes a file name when the model has no schema file yet.
    if request.model_name is not None:
        validate_model_name(request.model_name)
    output_path = save_model_schema_from_request(
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


@router.post("/sync-tests", response_model=SyncTestsResponse)
async def sync_framework_tests_endpoint():
    """Sync relationship tests from data model to schema files."""
    outcome = sync_framework_tests()

    # `files` also carries the Ossie document, which the message already names
    # separately; counting it here would report one more schema file than was
    # actually written.
    framework_file_count = len(outcome.files) - (1 if outcome.ossie_path else 0)
    message = f"Updated {framework_file_count} file(s)"
    if outcome.ossie_path is not None:
        message += f", wrote {outcome.ossie_path.name}"
    elif cfg.OSSIE_CONFIG.enabled:
        # Only explain the absence when the user asked for the export; a
        # disabled feature should not shape the message at all.
        message += "; no semantic model was written"

    if outcome.warnings:
        count = len(outcome.warnings)
        message += f", {count} warning" if count == 1 else f", {count} warnings"

    return SyncTestsResponse(
        message=message,
        files=[str(f) for f in outcome.files],
        warnings=outcome.warnings,
    )


@router.get("/models/{model_name}/schema", response_model=ModelSchemaResponse)
async def get_model_schema_endpoint(model_name: str, version: int | None = None):
    """Get the schema for a specific model from its YAML file."""
    with timed_phase("schema_read"):
        schema = get_model_schema(model_name, version=version)
    return ModelSchemaResponse(**schema)


@router.post("/models/{model_name}/schema", response_model=FileOperationResponse)
async def update_model_schema_endpoint(
    model_name: str, request: ModelSchemaRequest
):
    """Update the schema for a specific model in its YAML file."""
    validate_model_name(model_name)
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
    with timed_phase("relationship_scan"):
        relationships = infer_relationships(include_unbound=include_unbound)
    return RelationshipsResponse(relationships=relationships)
