"""Routes for the metric tree document."""

from typing import Any

from fastapi import APIRouter, Body, Depends

from trellis_datamodel import config as cfg
from trellis_datamodel.models.metric import MetricTreeUpdate
from trellis_datamodel.routes.dependencies import require_feature
from trellis_datamodel.services.metric_tree import (
    load_metric_tree,
    resolve_catalog,
    resolve_datasets,
    save_metric_tree,
)

# The metric tree spec requires a disabled feature to look absent, so this
# guard answers 404 instead of the default 403.
router = APIRouter(
    prefix="/api",
    tags=["metric-tree"],
    dependencies=[
        Depends(
            require_feature(
                lambda: cfg.METRICS_CONFIG.enabled,
                "Metric tree is disabled. Set metrics.enabled: true in trellis.yml.",
                status_code=404,
            )
        )
    ],
)


def _build_catalog() -> list[dict[str, Any]]:
    """Return the bindable plus read-only metric catalog from semantic_model.yml."""
    return resolve_catalog()


@router.get("/metric-tree")
async def get_metric_tree():
    """
    Return the metric tree document.

    Returns:
        Dictionary with version, metrics, influences, catalog, and the datasets
        a draft can attach to

    Raises:
        FeatureDisabledError: 404 if the metric tree feature is disabled
    """
    tree = load_metric_tree(cfg.METRICS_CONFIG.file)

    return {
        "version": tree.version,
        "metrics": [metric.model_dump(exclude_none=True) for metric in tree.metrics],
        "influences": [
            influence.model_dump(exclude_none=True) for influence in tree.influences
        ],
        "catalog": _build_catalog(),
        "datasets": resolve_datasets(),
    }


@router.post("/metric-tree")
async def post_metric_tree(payload: MetricTreeUpdate = Body(...)):
    """
    Save the metric tree document.

    Args:
        payload: MetricTreeUpdate with version, metrics and influences

    Returns:
        Dictionary with status and any warnings

    Raises:
        FeatureDisabledError: 404 if the metric tree feature is disabled
        ValidationError: If graph integrity is violated, mapped to 422 globally
    """
    warnings = save_metric_tree(payload)

    return {"status": "success", "warnings": warnings}
