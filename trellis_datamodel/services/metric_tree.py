"""Metric tree document: load, validate, and save.

`metric_tree.yml` holds metric definitions and influence edges; node positions
are computed deterministically on the frontend from the tree hierarchy.

The catalog is resolved the way the exporter names datasets: entity
`model_ref` -> model short name -> the `name` on an Ossie dataset.
"""

import logging
from pathlib import Path
from typing import Any

from trellis_datamodel import config as cfg
from trellis_datamodel.adapters.base import semantic_dataset_name
from trellis_datamodel.exceptions import ValidationError
from trellis_datamodel.models.entity_keys import get_model_ref
from trellis_datamodel.models.metric import (
    Influence,
    MetricBinding,
    MetricEntry,
    MetricTreeFile,
    MetricTreeUpdate,
)
from trellis_datamodel.services.manifest import get_models
from trellis_datamodel.utils.yaml_handler import YamlHandler

logger = logging.getLogger(__name__)

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
            names[unique_id] = semantic_dataset_name(model)
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


def resolve_datasets() -> list[str]:
    """Names of the datasets a push writes to semantic_model.yml, sorted.

    These are the datasets a draft can attach to: one per entity bound to a
    model, named by the exporter's rule.
    """
    return sorted(
        _dataset_to_entity(_data_model_entities(), _model_dataset_names())
    )


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


def _expression_text(metric: dict[str, Any]) -> str | None:
    """The dialect expression the exporter writes, or None for another shape."""
    expression = metric.get("expression")
    dialects = expression.get("dialects") if isinstance(expression, dict) else None
    if not isinstance(dialects, list):
        return None
    for dialect in dialects:
        if not isinstance(dialect, dict):
            continue
        text = dialect.get("expression")
        if isinstance(text, str) and text.strip():
            return text
    return None


def _bound_expressions(document: dict[str, Any]) -> dict[tuple[str, str], str]:
    """`(dataset, metric name) -> expression`, keyed like `_bound_references`."""
    expressions: dict[tuple[str, str], str] = {}
    for dataset in _entries(document.get("datasets")):
        dataset_name = str(dataset.get("name") or "").strip()
        if not dataset_name:
            continue
        for metric in _entries(dataset.get("metrics")):
            metric_name = str(metric.get("name") or "").strip()
            if not metric_name:
                continue
            text = _expression_text(metric)
            if text is not None:
                expressions.setdefault((dataset_name, metric_name), text)
    return expressions


def _is_unresolved(
    metric: MetricEntry,
    references: set[tuple[str, str]],
    datasets: set[str],
) -> bool:
    """Whether this entry's outside reference is broken; mirrors the save warnings."""
    if metric.binding is not None:
        return _binding_key(metric.binding) not in references
    dataset_ref = (metric.dataset_ref or "").strip()
    return bool(dataset_ref) and dataset_ref not in datasets


def _annotate_unresolved(tree: MetricTreeFile) -> MetricTreeFile:
    """Flag entries whose reference no longer resolves; never drops one.

    Also carries the bound definition's expression for display, so the detail
    panel can show it without the client reading semantic_model.yml.
    """
    document = _ossie_document()
    references = _bound_references(document)
    expressions = _bound_expressions(document)
    datasets = set(resolve_datasets())
    for metric in tree.metrics:
        metric.unresolved = _is_unresolved(metric, references, datasets)
        metric.resolved_expression = (
            expressions.get(_binding_key(metric.binding))
            if metric.binding is not None and not metric.unresolved
            else None
        )
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


def _save_warnings(tree: MetricTreeUpdate) -> list[str]:
    """Warnings for references that no longer resolve; the entries are kept.

    Both cases are outside Trellis' control - a definition deleted from
    semantic_model.yml, a dataset whose entity or model went away - so they
    warn and badge rather than rejecting the save or dropping the entry.
    """
    references = _bound_references(_ossie_document())
    datasets = set(resolve_datasets())

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
        if dataset_ref and dataset_ref not in datasets:
            warnings.append(
                f'metric "{metric.id}" dataset_ref "{dataset_ref}" does not match '
                "any dataset exported to semantic_model.yml"
            )
    return warnings


def save_metric_tree(tree: MetricTreeUpdate) -> list[str]:
    """Validate, sort and write metric_tree.yml. Returns warnings."""
    validate_metric_tree(tree)
    warnings = _save_warnings(tree)

    entries = sorted(tree.metrics, key=lambda m: m.id)
    influences = [
        Influence(effect=influence.effect, drivers=sorted(set(influence.drivers)))
        for influence in sorted(tree.influences, key=lambda i: i.effect)
    ]

    document = {
        "version": tree.version,
        # `unresolved` and `resolved_expression` are wire state: the file carries
        # definitions and references, not verdicts or copies.
        "metrics": [
            entry.model_dump(
                exclude_none=True, exclude={"unresolved", "resolved_expression"}
            )
            for entry in entries
        ],
        "influences": [
            influence.model_dump(exclude_none=True) for influence in influences
        ],
    }

    handler = YamlHandler()
    handler.save_file(cfg.METRICS_CONFIG.file, document)

    return warnings
