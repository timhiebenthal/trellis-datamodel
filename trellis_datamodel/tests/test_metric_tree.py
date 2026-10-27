"""Tests for the metric tree document: load, validate, save."""

import os

import pytest

import trellis_datamodel.config as cfg
from trellis_datamodel.exceptions import ValidationError
from trellis_datamodel.models.metric import (
    Influence,
    MetricBinding,
    MetricEntry,
    MetricTreeFile,
    MetricTreeUpdate,
)
from trellis_datamodel.services.metric_tree import (
    load_metric_tree,
    save_metric_tree,
    validate_metric_tree,
)


@pytest.fixture
def metrics_paths(monkeypatch, tmp_path):
    """Point cfg.METRICS_CONFIG at a throwaway directory."""
    monkeypatch.setattr(
        cfg,
        "METRICS_CONFIG",
        cfg.MetricsConfig(
            enabled=True,
            file=str(tmp_path / "metric_tree.yml"),
        ),
    )
    return tmp_path


def _draft(metric_id: str, **overrides) -> MetricEntry:
    fields = {
        "id": metric_id,
        "label": metric_id.replace("_", " ").title(),
        "description": f"{metric_id} description",
        "expression": f"sum({metric_id}) from fct__order",
        "dataset_ref": "fct__order",
    }
    fields.update(overrides)
    return MetricEntry(**fields)


def _bound(metric_id: str) -> MetricEntry:
    return MetricEntry(
        id=metric_id,
        label=metric_id.replace("_", " ").title(),
        binding=MetricBinding(dataset="fct__order", name=metric_id),
    )


def _tree(*metrics: MetricEntry, influences=None) -> MetricTreeUpdate:
    return MetricTreeUpdate(
        version=0.1,
        metrics=list(metrics),
        influences=list(influences or []),
    )


def test_missing_file_returns_empty_document(metrics_paths):
    tree = load_metric_tree(str(metrics_paths / "metric_tree.yml"))

    assert isinstance(tree, MetricTreeFile)
    assert tree.version == 0.1
    assert tree.metrics == []
    assert tree.influences == []


def test_load_missing_file_writes_nothing(metrics_paths):
    load_metric_tree(str(metrics_paths / "metric_tree.yml"))

    assert not os.path.exists(metrics_paths / "metric_tree.yml")


def test_save_then_load_round_trip(metrics_paths):
    save_metric_tree(
        _tree(
            _draft("revenue"),
            _bound("avg_price"),
            influences=[Influence(effect="revenue", drivers=["avg_price"])],
        )
    )

    tree = load_metric_tree(str(metrics_paths / "metric_tree.yml"))

    assert [metric.id for metric in tree.metrics] == ["avg_price", "revenue"]
    revenue = next(metric for metric in tree.metrics if metric.id == "revenue")
    avg_price = next(metric for metric in tree.metrics if metric.id == "avg_price")
    assert revenue.description == "revenue description"
    assert revenue.expression == "sum(revenue) from fct__order"
    assert revenue.dataset_ref == "fct__order"
    assert revenue.binding is None
    assert avg_price.expression is None
    assert avg_price.binding == MetricBinding(dataset="fct__order", name="avg_price")
    assert tree.influences == [Influence(effect="revenue", drivers=["avg_price"])]


def test_save_sorts_metrics_influences_and_drivers(metrics_paths):
    save_metric_tree(
        _tree(
            _draft("revenue"),
            _draft("order_count"),
            _draft("avg_price"),
            _bound("basket_size"),
            influences=[
                Influence(effect="revenue", drivers=["order_count", "avg_price", "avg_price"]),
                Influence(effect="basket_size", drivers=["order_count"]),
            ],
        )
    )

    tree = load_metric_tree(str(metrics_paths / "metric_tree.yml"))

    assert [metric.id for metric in tree.metrics] == [
        "avg_price",
        "basket_size",
        "order_count",
        "revenue",
    ]
    assert [influence.effect for influence in tree.influences] == [
        "basket_size",
        "revenue",
    ]
    assert tree.influences[1].drivers == ["avg_price", "order_count"]


def test_save_twice_is_byte_identical(metrics_paths):
    tree = _tree(
        _draft("revenue"),
        _draft("order_count"),
        _bound("avg_price"),
        influences=[
            Influence(effect="revenue", drivers=["order_count", "avg_price"]),
        ],
    )

    save_metric_tree(tree)
    first_tree = (metrics_paths / "metric_tree.yml").read_bytes()

    save_metric_tree(tree)

    assert (metrics_paths / "metric_tree.yml").read_bytes() == first_tree


def test_validate_accepts_valid_tree():
    validate_metric_tree(
        _tree(
            _draft("revenue"),
            _bound("avg_price"),
            influences=[Influence(effect="revenue", drivers=["avg_price"])],
        )
    )


def test_validate_rejects_duplicate_metric_ids():
    with pytest.raises(ValidationError) as exc_info:
        validate_metric_tree(_tree(_draft("revenue"), _draft("revenue")))

    assert "revenue" in str(exc_info.value)


def test_validate_rejects_unknown_effect():
    with pytest.raises(ValidationError) as exc_info:
        validate_metric_tree(
            _tree(
                _draft("revenue"),
                influences=[Influence(effect="margin", drivers=["revenue"])],
            )
        )

    assert "margin" in str(exc_info.value)


def test_validate_rejects_unknown_driver():
    with pytest.raises(ValidationError) as exc_info:
        validate_metric_tree(
            _tree(
                _draft("revenue"),
                influences=[Influence(effect="revenue", drivers=["ghost_metric"])],
            )
        )

    assert "ghost_metric" in str(exc_info.value)


def test_validate_rejects_self_driver():
    with pytest.raises(ValidationError) as exc_info:
        validate_metric_tree(
            _tree(
                _draft("revenue"),
                influences=[Influence(effect="revenue", drivers=["revenue"])],
            )
        )

    assert "revenue" in str(exc_info.value)


def test_validate_rejects_bound_metric_with_expression():
    with pytest.raises(ValidationError) as exc_info:
        validate_metric_tree(
            _tree(
                MetricEntry(
                    id="avg_price",
                    label="Average price",
                    binding=MetricBinding(dataset="fct__order", name="avg_price"),
                    expression="avg(price)",
                )
            )
        )

    assert "avg_price" in str(exc_info.value)


@pytest.mark.parametrize("expression", [None, "", "   "])
def test_validate_rejects_draft_without_expression(expression):
    with pytest.raises(ValidationError) as exc_info:
        validate_metric_tree(_tree(_draft("revenue", expression=expression)))

    assert "revenue" in str(exc_info.value)
