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
    # #region agent log
    import json

    log_path = "/home/tim_ubuntu/git_repos/trellis-datamodel/.cursor/debug.log"
    log_entry = json.dumps(
        {
            "id": "log_lineage_entry_A",
            "timestamp": 0,
            "location": "lineage.py:33",
            "message": "Lineage endpoint called",
            "data": {
                "LINEAGE_ENABLED": cfg.LINEAGE_ENABLED,
                "MANIFEST_PATH": cfg.MANIFEST_PATH,
                "model_id": model_id,
                "hypothesisId": "B",
            },
            "sessionId": "debug-session",
            "runId": "run1",
        }
    )
    with open(log_path, "a") as f:
        f.write(log_entry + "\n")
    # #endregion

    # Check if lineage is enabled
    if not cfg.LINEAGE_ENABLED:
        # #region agent log
        log_entry = json.dumps(
            {
                "id": "log_lineage_disabled_B",
                "timestamp": 0,
                "location": "lineage.py:47",
                "message": "Lineage disabled, raising error",
                "data": {"LINEAGE_ENABLED": cfg.LINEAGE_ENABLED, "hypothesisId": "B"},
                "sessionId": "debug-session",
                "runId": "run1",
            }
        )
        with open(log_path, "a") as f:
            f.write(log_entry + "\n")
        # #endregion
        raise FeatureDisabledError(
            "Lineage is disabled. Set lineage.enabled: true in trellis.yml to enable."
        )

    # Validate manifest path exists
    manifest_path = validate_manifest_path()

    # region agent log
    log_entry = json.dumps(
        {
            "id": "log_lineage_manifest_path_C",
            "timestamp": 0,
            "location": "lineage.py:50",
            "message": "Manifest path validated",
            "data": {"manifest_path": manifest_path, "hypothesisId": "A,C"},
            "sessionId": "debug-session",
            "runId": "run1",
        }
    )
    with open(log_path, "a") as f:
        f.write(log_entry + "\n")
    # endregion

    # Extract lineage
    lineage_data = extract_upstream_lineage(
        manifest_path=manifest_path,
        catalog_path=cfg.CATALOG_PATH,
        model_unique_id=model_id,
    )

    return lineage_data
