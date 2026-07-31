"""Route for dbt reconciliation."""

from fastapi import APIRouter

from trellis_datamodel.services.reconciliation import reconcile_framework
from trellis_datamodel.routes.data_model import _add_legacy_key_aliases

router = APIRouter(prefix="/api", tags=["reconciliation"])


@router.post("/reconcile")
@router.post("/reconcile-dbt", include_in_schema=False)  # TODO(sprint-6): remove after frontend migration
async def reconcile_dbt_endpoint():
    """Reconcile dbt manifest columns into data_model.yml with provenance tags.

    Reads the current manifest, merges materialized columns (source='dbt')
    into each bound entity's drafted_fields, and writes back only if changed.
    Non-destructive: entities whose model is absent from the manifest are
    left untouched (handles partial dbt compiles).
    """
    data_model, changed = reconcile_framework()
    return {
        "status": "success",
        "changed": changed,
        "data_model": _add_legacy_key_aliases(data_model),
    }
