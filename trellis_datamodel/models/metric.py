"""Pydantic models for the metric tree document."""

from pydantic import BaseModel, Field


class MetricBinding(BaseModel):
    """Reference to a dataset-scoped metric defined in semantic_model.yml."""

    dataset: str = Field(..., description="Dataset name the bound metric lives under")
    name: str = Field(..., description="Metric name within that dataset")


class Position(BaseModel):
    """Canvas position for a metric node. Wire/layout only, never persisted to metric_tree.yml."""

    x: float = Field(..., description="Horizontal canvas position")
    y: float = Field(..., description="Vertical canvas position")


class MetricEntry(BaseModel):
    """A metric on the canvas: authored in Trellis (draft) or bound to the semantic model."""

    id: str = Field(..., description="Unique metric ID within the tree")
    label: str = Field(..., description="Display label")
    description: str | None = Field(
        None, description="Optional description; drafts only"
    )
    expression: str | None = Field(
        None, description="Draft metric expression; never set on a bound metric"
    )
    dataset_ref: str | None = Field(
        None, description="Entity ID from data_model.yml; drafts only"
    )
    binding: MetricBinding | None = Field(
        None, description="Bound metric reference; never set on a draft"
    )
    position: Position | None = Field(
        None, description="Canvas position supplied by the client, split into metric_layout.yml"
    )
    # Read-only resolution state for the API, attached at load time. Never
    # authored by a client and never written: `save_metric_tree` excludes it
    # from the document it dumps.
    unresolved: bool | None = Field(
        None,
        description="True when the binding or dataset_ref no longer resolves; read only",
    )


class Influence(BaseModel):
    """A directed claim: `effect` moves when its `drivers` move."""

    effect: str = Field(..., description="Metric ID that moves")
    drivers: list[str] = Field(
        default_factory=list, description="Metric IDs that move the effect"
    )


class MetricTreeFile(BaseModel):
    """YAML file structure for metric_tree.yml."""

    version: float = 0.1
    metrics: list[MetricEntry] = Field(default_factory=list)
    influences: list[Influence] = Field(default_factory=list)


class MetricTreeUpdate(MetricTreeFile):
    """POST /api/metric-tree payload; identical shape, positions allowed per metric."""
