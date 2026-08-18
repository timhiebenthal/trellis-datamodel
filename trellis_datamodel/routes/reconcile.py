"""Route for dbt reconciliation."""

from fastapi import APIRouter

from trellis_datamodel.services.reconciliation import reconcile_framework

router = APIRouter(prefix="/api", tags=["reconciliation"])


@router.post("/reconcile")
def reconcile_framework_endpoint():
    """Reconcile dbt manifest columns into data_model.yml with provenance tags.

    Reads the current manifest, merges materialized columns (source='dbt')
    into each bound entity's drafted_fields, and writes back only if changed.
    Non-destructive: entities whose model is absent from the manifest are
    left untouched (handles partial dbt compiles).
    """
    _, changed = reconcile_framework()
    return {
        "status": "success",
        "changed": changed,
    }
