"""Routes for the metric tree document."""

from typing import Any

from fastapi import APIRouter, Body, HTTPException

from trellis_datamodel import config as cfg
from trellis_datamodel.models.metric import MetricTreeUpdate
from trellis_datamodel.services.metric_tree import (
    load_metric_tree,
    merge_layout,
    resolve_catalog,
    save_metric_tree,
)

router = APIRouter(prefix="/api", tags=["metric-tree"])


# Deliberately an HTTPException rather than FeatureDisabledError: the global
# handler maps that exception to 403 and other features depend on it, while
# SPEC.md requires 404 here. Do not "unify" the two.
def _ensure_metrics_enabled() -> None:
    """Reject requests with 404 when the metric tree feature is disabled."""
    if not cfg.METRICS_CONFIG.enabled:
        raise HTTPException(
            status_code=404,
            detail="Metric tree is disabled. Set metrics.enabled: true in trellis.yml.",
        )


def _build_catalog() -> list[dict[str, Any]]:
    """Return the bindable plus read-only metric catalog from semantic_model.yml."""
    return resolve_catalog()


@router.get("/metric-tree")
async def get_metric_tree():
    """
    Return the metric tree document with layout merged into each metric.

    Returns:
        Dictionary with version, metrics, influences, and catalog

    Raises:
        HTTPException: 404 if the metric tree feature is disabled
    """
    _ensure_metrics_enabled()

    tree = merge_layout(load_metric_tree(cfg.METRICS_CONFIG.file))

    return {
        "version": tree.version,
        "metrics": [metric.model_dump(exclude_none=True) for metric in tree.metrics],
        "influences": [
            influence.model_dump(exclude_none=True) for influence in tree.influences
        ],
        "catalog": _build_catalog(),
    }


@router.post("/metric-tree")
async def post_metric_tree(payload: MetricTreeUpdate = Body(...)):
    """
    Save the metric tree document, splitting metric positions into the layout file.

    Args:
        payload: MetricTreeUpdate with version, metrics and influences

    Returns:
        Dictionary with status and any warnings

    Raises:
        HTTPException: 404 if the metric tree feature is disabled
        ValidationError: If graph integrity is violated, mapped to 422 globally
    """
    _ensure_metrics_enabled()

    warnings = save_metric_tree(payload)

    return {"status": "success", "warnings": warnings}
