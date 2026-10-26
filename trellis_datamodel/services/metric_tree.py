"""Metric tree document: load, validate, save, and layout split.

`metric_tree.yml` holds metric definitions and influence edges; node positions
live beside it in `metric_layout.yml`, keyed by metric id, mirroring the
`data_model.yml` / `canvas_layout.yml` split.

The catalog is resolved the way the exporter names datasets: entity
`model_ref` -> model short name -> the `name` on an Ossie dataset.
"""

import logging
from pathlib import Path
from typing import Any

from trellis_datamodel import config as cfg
from trellis_datamodel.exceptions import ValidationError
from trellis_datamodel.models.entity_keys import get_model_ref
from trellis_datamodel.models.metric import (
    Influence,
    MetricBinding,
    MetricEntry,
    MetricTreeFile,
    MetricTreeUpdate,
    Position,
)
from trellis_datamodel.services.manifest import get_models
from trellis_datamodel.utils.yaml_handler import YamlHandler

logger = logging.getLogger(__name__)

# Layout keys owned by the canvas, preserved across saves for surviving metrics.
_LAYOUT_EXTRA_KEYS = ("width", "panel_height", "collapsed")

# Ossie's default document name, beside data_model.yml.
DEFAULT_OSSIE_FILENAME = "semantic_model.yml"

_DOCUMENT_SCOPE_REASON = (
    "document-level metric: cross-dataset scope, so it has no single entity"
)


def load_metric_tree(path: str) -> MetricTreeFile:
    """Load metric_tree.yml, returning the empty document when the file is missing."""
    data = YamlHandler().load_file(path)
    if not data:
        return MetricTreeFile(version=0.1, metrics=[], influences=[])
    return _annotate_unresolved(MetricTreeFile.model_validate(data))


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


def _ossie_path() -> Path:
    """The configured Ossie document, or the default beside data_model.yml."""
    configured = (cfg.OSSIE_CONFIG.file or "").strip()
    if configured:
        return Path(configured)
    data_model_path = (getattr(cfg, "DATA_MODEL_PATH", "") or "").strip()
    if data_model_path:
        return Path(data_model_path).parent / DEFAULT_OSSIE_FILENAME
    return Path(DEFAULT_OSSIE_FILENAME)


def _ossie_document() -> dict[str, Any]:
    """The Ossie document as a plain mapping; an empty one when unreadable."""
    document = YamlHandler().load_file(str(_ossie_path()))
    return document if isinstance(document, dict) else {}


def _entries(value: Any) -> list[dict[str, Any]]:
    """List-shaped YAML entries, ignoring anything hand-edited into another shape."""
    return [entry for entry in value or [] if isinstance(entry, dict)]


def _data_model_entities() -> list[dict[str, Any]]:
    """Entities in data_model.yml; empty when the file has not been written yet."""
    data_model_path = (getattr(cfg, "DATA_MODEL_PATH", "") or "").strip()
    if not data_model_path:
        return []
    data = YamlHandler().load_file(data_model_path)
    return _entries(data.get("entities")) if isinstance(data, dict) else []


def _entity_ids() -> set[str]:
    return {
        str(entity.get("id") or "").strip()
        for entity in _data_model_entities()
        if str(entity.get("id") or "").strip()
    }


def _model_dataset_names() -> dict[str, str]:
    """`unique_id -> dataset name`, using the exporter's naming rule.

    A model list the framework cannot report leaves every dataset unmatched
    rather than failing the catalog.
    """
    try:
        models = get_models()
    except Exception as exc:  # noqa: BLE001 - the catalog is best-effort
        logger.debug("Catalog resolution could not read models: %s", exc)
        return {}

    names: dict[str, str] = {}
    for model in models:
        unique_id = str(model.get("unique_id") or "").strip()
        if unique_id:
            names[unique_id] = str(model.get("name") or unique_id).strip()
    return names


def _dataset_to_entity(
    entities: list[dict[str, Any]], model_names: dict[str, str]
) -> dict[str, str]:
    """`dataset name -> entity id`, only for entities actually bound to a model."""
    mapping: dict[str, str] = {}
    for entity in sorted(entities, key=lambda entry: str(entry.get("id") or "")):
        entity_id = str(entity.get("id") or "").strip()
        model_ref = get_model_ref(entity)
        if not entity_id or not model_ref:
            continue
        dataset_name = model_names.get(model_ref)
        if dataset_name and dataset_name not in mapping:
            mapping[dataset_name] = entity_id
    return mapping


def _binding_key(binding: MetricBinding) -> tuple[str, str]:
    return (binding.dataset.strip(), binding.name.strip())


def _bound_references(document: dict[str, Any]) -> set[tuple[str, str]]:
    """Every `(dataset, metric name)` pair the Ossie document currently defines."""
    references: set[tuple[str, str]] = set()
    for dataset in _entries(document.get("datasets")):
        dataset_name = str(dataset.get("name") or "").strip()
        if not dataset_name:
            continue
        for metric in _entries(dataset.get("metrics")):
            metric_name = str(metric.get("name") or "").strip()
            if metric_name:
                references.add((dataset_name, metric_name))
    return references


def _is_unresolved(
    metric: MetricEntry,
    references: set[tuple[str, str]],
    entity_ids: set[str],
) -> bool:
    """Why this entry's outside reference is broken; mirrors the save warnings."""
    if metric.binding is not None:
        return _binding_key(metric.binding) not in references
    dataset_ref = (metric.dataset_ref or "").strip()
    return bool(dataset_ref) and dataset_ref not in entity_ids


def _annotate_unresolved(tree: MetricTreeFile) -> MetricTreeFile:
    """Flag entries whose reference no longer resolves; never drops one."""
    references = _bound_references(_ossie_document())
    entity_ids = _entity_ids()
    for metric in tree.metrics:
        metric.unresolved = _is_unresolved(metric, references, entity_ids)
    return tree


def resolve_catalog() -> list[dict[str, Any]]:
    """Classify every metric in the Ossie document as bindable or read-only.

    Only dataset-scoped metrics whose dataset maps to an entity bound to a model
    are bindable. Document-level metrics and dataset-scoped metrics on an
    unmapped dataset are listed read-only, with the reason the sidebar shows.
    """
    document = _ossie_document()
    dataset_metrics: list[tuple[str, str]] = [
        (
            str(dataset.get("name") or "").strip(),
            str(metric.get("name") or "").strip(),
        )
        for dataset in _entries(document.get("datasets"))
        for metric in _entries(dataset.get("metrics"))
    ]
    root_metrics = [
        str(metric.get("name") or "").strip()
        for metric in _entries(document.get("metrics"))
    ]
    if not dataset_metrics and not root_metrics:
        return []

    dataset_to_entity = _dataset_to_entity(
        _data_model_entities(), _model_dataset_names()
    )

    catalog: list[dict[str, Any]] = []
    seen: set[tuple[str | None, str]] = set()

    for name in root_metrics:
        if not name or (None, name) in seen:
            continue
        seen.add((None, name))
        catalog.append(
            {
                "name": name,
                "dataset": None,
                "entity_id": None,
                "bindable": False,
                "reason": _DOCUMENT_SCOPE_REASON,
            }
        )

    for dataset_name, name in dataset_metrics:
        if not dataset_name or not name or (dataset_name, name) in seen:
            continue
        seen.add((dataset_name, name))
        entity_id = dataset_to_entity.get(dataset_name)
        if entity_id is None:
            catalog.append(
                {
                    "name": name,
                    "dataset": dataset_name,
                    "entity_id": None,
                    "bindable": False,
                    "reason": (
                        f'dataset "{dataset_name}" does not match any entity '
                        "bound to a model in data_model.yml"
                    ),
                }
            )
            continue
        catalog.append(
            {
                "name": name,
                "dataset": dataset_name,
                "entity_id": entity_id,
                "bindable": True,
            }
        )

    return sorted(catalog, key=lambda entry: (entry["dataset"] or "", entry["name"]))


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


def _save_warnings(tree: MetricTreeUpdate) -> list[str]:
    """Warnings for references that no longer resolve; the entries are kept.

    Both cases are outside Trellis' control - a definition deleted from
    semantic_model.yml, an entity deleted from data_model.yml - so they warn
    and badge rather than rejecting the save or dropping the entry.
    """
    references = _bound_references(_ossie_document())
    entity_ids = _entity_ids()

    warnings: list[str] = []
    for metric in sorted(tree.metrics, key=lambda entry: entry.id):
        if metric.binding is not None:
            dataset, name = _binding_key(metric.binding)
            if (dataset, name) not in references:
                warnings.append(
                    f'bound metric "{metric.id}" references "{dataset}.{name}", '
                    "which is not found in semantic_model.yml"
                )
            continue

        dataset_ref = (metric.dataset_ref or "").strip()
        if dataset_ref and dataset_ref not in entity_ids:
            warnings.append(
                f'metric "{metric.id}" dataset_ref "{dataset_ref}" does not match '
                "any entity in data_model.yml"
            )
    return warnings


def save_metric_tree(tree: MetricTreeUpdate) -> list[str]:
    """Validate, sort and write metric_tree.yml plus metric_layout.yml. Returns warnings."""
    validate_metric_tree(tree)
    warnings = _save_warnings(tree)

    entries, layout = split_metric_layout(sorted(tree.metrics, key=lambda m: m.id))
    influences = [
        Influence(effect=influence.effect, drivers=sorted(set(influence.drivers)))
        for influence in sorted(tree.influences, key=lambda i: i.effect)
    ]

    document = {
        "version": tree.version,
        # `unresolved` is wire state: the file carries definitions, not verdicts.
        "metrics": [
            entry.model_dump(exclude_none=True, exclude={"unresolved"})
            for entry in entries
        ],
        "influences": [
            influence.model_dump(exclude_none=True) for influence in influences
        ],
    }

    handler = YamlHandler()
    handler.save_file(cfg.METRICS_CONFIG.file, document)
    handler.save_file(cfg.METRICS_CONFIG.layout_file, layout)

    return warnings
