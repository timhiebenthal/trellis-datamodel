"""Route for dbt reconciliation."""

from fastapi import APIRouter

from trellis_datamodel.services.reconciliation import reconcile_dbt
from trellis_datamodel.routes.data_model import _add_legacy_key_aliases

router = APIRouter(prefix="/api", tags=["reconciliation"])


@router.post("/reconcile-dbt")
async def reconcile_dbt_endpoint():
    """Reconcile dbt manifest columns into data_model.yml with provenance tags.

    Reads the current manifest, merges materialized columns (source='dbt')
    into each bound entity's drafted_fields, and writes back only if changed.
    Non-destructive: entities whose model is absent from the manifest are
    left untouched (handles partial dbt compiles).
    """
    data_model, changed = reconcile_dbt()
    return {
        "status": "success",
        "changed": changed,
        "data_model": _add_legacy_key_aliases(data_model),
    }
