"""Metric tree document: load, validate, save, and layout split.

`metric_tree.yml` holds metric definitions and influence edges; node positions
live beside it in `metric_layout.yml`, keyed by metric id, mirroring the
`data_model.yml` / `canvas_layout.yml` split.
"""

from typing import Any

from trellis_datamodel import config as cfg
from trellis_datamodel.exceptions import ValidationError
from trellis_datamodel.models.metric import (
    Influence,
    MetricEntry,
    MetricTreeFile,
    MetricTreeUpdate,
    Position,
)
from trellis_datamodel.utils.yaml_handler import YamlHandler

# Layout keys owned by the canvas, preserved across saves for surviving metrics.
_LAYOUT_EXTRA_KEYS = ("width", "panel_height", "collapsed")


def load_metric_tree(path: str) -> MetricTreeFile:
    """Load metric_tree.yml, returning the empty document when the file is missing."""
    data = YamlHandler().load_file(path)
    if not data:
        return MetricTreeFile(version=0.1, metrics=[], influences=[])
    return MetricTreeFile.model_validate(data)


def load_metric_layout(path: str) -> dict[str, dict]:
    """Load metric_layout.yml as `{metric_id: {...}}`, empty when the file is missing."""
    data = YamlHandler().load_file(path)
    if not data:
        return {}
    return {
        str(metric_id): dict(entry)
        for metric_id, entry in data.items()
        if isinstance(entry, dict)
    }


def merge_layout(tree: MetricTreeFile) -> MetricTreeFile:
    """Attach persisted positions to `tree` by metric id; unmatched layout entries are ignored."""
    layout = load_metric_layout(cfg.METRICS_CONFIG.layout_file)
    for metric in tree.metrics:
        entry = layout.get(metric.id)
        if not entry or "position" not in entry:
            continue
        metric.position = Position.model_validate(entry["position"])
    return tree


def _validate_metric_shape(metric: MetricEntry) -> None:
    """Reject a metric that mixes the draft and bound shapes."""
    if metric.binding is not None:
        if (metric.expression or "").strip():
            raise ValidationError(
                f"Metric '{metric.id}' is bound to "
                f"'{metric.binding.dataset}.{metric.binding.name}' and must not carry an expression"
            )
        return

    if not (metric.expression or "").strip():
        raise ValidationError(f"Metric '{metric.id}' must define an expression")


def validate_metric_tree(tree: MetricTreeFile | MetricTreeUpdate) -> None:
    """Validate graph integrity, raising ValidationError with the offending metric id."""
    metric_ids: set[str] = set()
    for metric in tree.metrics:
        if metric.id in metric_ids:
            raise ValidationError(f"Duplicate metric id '{metric.id}'")
        metric_ids.add(metric.id)
        _validate_metric_shape(metric)

    for influence in tree.influences:
        if influence.effect not in metric_ids:
            raise ValidationError(
                f"Influence effect '{influence.effect}' is not a metric in the tree"
            )
        for driver in influence.drivers:
            if driver == influence.effect:
                raise ValidationError(
                    f"Metric '{driver}' cannot be its own driver"
                )
            if driver not in metric_ids:
                raise ValidationError(
                    f"Influence driver '{driver}' for effect '{influence.effect}' "
                    "is not a metric in the tree"
                )


def split_metric_layout(
    metrics: list[MetricEntry],
) -> tuple[list[MetricEntry], dict[str, dict]]:
    """Split positions out of `metrics`, carrying over layout keys for surviving ids."""
    existing = load_metric_layout(cfg.METRICS_CONFIG.layout_file)

    entries: list[MetricEntry] = []
    layout: dict[str, dict] = {}
    for metric in metrics:
        entries.append(metric.model_copy(update={"position": None}))

        entry_layout: dict[str, Any] = {}
        previous = existing.get(metric.id, {})
        if metric.position is not None:
            entry_layout["position"] = {
                "x": metric.position.x,
                "y": metric.position.y,
            }
        elif "position" in previous:
            # An omitted position is "no opinion", not "unset": a payload that
            # only edits a label must not reset where the node was drawn.
            entry_layout["position"] = previous["position"]
        for key in _LAYOUT_EXTRA_KEYS:
            if key in previous:
                entry_layout[key] = previous[key]
        if entry_layout:
            layout[metric.id] = entry_layout

    return entries, layout


def save_metric_tree(tree: MetricTreeUpdate) -> list[str]:
    """Validate, sort and write metric_tree.yml plus metric_layout.yml. Returns warnings."""
    validate_metric_tree(tree)

    entries, layout = split_metric_layout(sorted(tree.metrics, key=lambda m: m.id))
    influences = [
        Influence(effect=influence.effect, drivers=sorted(set(influence.drivers)))
        for influence in sorted(tree.influences, key=lambda i: i.effect)
    ]

    document = {
        "version": tree.version,
        "metrics": [entry.model_dump(exclude_none=True) for entry in entries],
        "influences": [
            influence.model_dump(exclude_none=True) for influence in influences
        ],
    }

    handler = YamlHandler()
    handler.save_file(cfg.METRICS_CONFIG.file, document)
    handler.save_file(cfg.METRICS_CONFIG.layout_file, layout)

    # Warnings (unresolvable references) are added in the catalog task.
    return []
