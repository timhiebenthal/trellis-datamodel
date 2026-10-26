"""Tests for the metric tree document: load, validate, save, layout split."""

import os
import textwrap
from pathlib import Path

import pytest

import trellis_datamodel.config as cfg
from trellis_datamodel.exceptions import ValidationError
from trellis_datamodel.models.metric import (
    Influence,
    MetricBinding,
    MetricEntry,
    MetricTreeFile,
    MetricTreeUpdate,
    Position,
)
from trellis_datamodel.services.metric_tree import (
    load_metric_layout,
    load_metric_tree,
    merge_layout,
    save_metric_tree,
    split_metric_layout,
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
            layout_file=str(tmp_path / "metric_layout.yml"),
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
    load_metric_layout(str(metrics_paths / "metric_layout.yml"))

    assert not os.path.exists(metrics_paths / "metric_tree.yml")
    assert not os.path.exists(metrics_paths / "metric_layout.yml")


def test_missing_layout_returns_empty_map(metrics_paths):
    assert load_metric_layout(str(metrics_paths / "metric_layout.yml")) == {}


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
    first_layout = (metrics_paths / "metric_layout.yml").read_bytes()

    save_metric_tree(tree)

    assert (metrics_paths / "metric_tree.yml").read_bytes() == first_tree
    assert (metrics_paths / "metric_layout.yml").read_bytes() == first_layout


def test_save_twice_with_positions_is_byte_identical(metrics_paths):
    tree = _tree(
        _draft("revenue", position=Position(x=120.5, y=-40.0)),
        _draft("order_count", position=Position(x=0, y=0)),
    )

    save_metric_tree(tree)
    first_tree = (metrics_paths / "metric_tree.yml").read_bytes()
    first_layout = (metrics_paths / "metric_layout.yml").read_bytes()

    save_metric_tree(
        _tree(
            _draft("order_count", position=Position(x=0, y=0)),
            _draft("revenue", position=Position(x=120.5, y=-40.0)),
        )
    )

    assert (metrics_paths / "metric_tree.yml").read_bytes() == first_tree
    assert (metrics_paths / "metric_layout.yml").read_bytes() == first_layout


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


def test_merge_layout_sets_positions_by_id(metrics_paths):
    (metrics_paths / "metric_layout.yml").write_text(
        textwrap.dedent(
            """\
            revenue:
              position:
                x: 10
                y: 20
              width: 240
              panel_height: 180
              collapsed: true
            """
        )
    )
    save_metric_tree(_tree(_draft("revenue"), _draft("order_count")))

    tree = load_metric_tree(str(metrics_paths / "metric_tree.yml"))
    assert all(metric.position is None for metric in tree.metrics)

    merged = merge_layout(tree)

    revenue = next(metric for metric in merged.metrics if metric.id == "revenue")
    order_count = next(metric for metric in merged.metrics if metric.id == "order_count")
    assert revenue.position == Position(x=10, y=20)
    assert order_count.position is None


def test_merge_layout_ignores_layout_for_absent_metrics(metrics_paths):
    (metrics_paths / "metric_layout.yml").write_text(
        textwrap.dedent(
            """\
            gone_metric:
              position:
                x: 1
                y: 2
            """
        )
    )
    save_metric_tree(_tree(_draft("revenue")))

    tree = merge_layout(load_metric_tree(str(metrics_paths / "metric_tree.yml")))

    assert [metric.id for metric in tree.metrics] == ["revenue"]
    assert tree.metrics[0].position is None


def test_save_writes_positions_to_layout_not_tree(metrics_paths):
    save_metric_tree(_tree(_draft("revenue", position=Position(x=12.5, y=40))))

    tree_text = (metrics_paths / "metric_tree.yml").read_text()
    layout = load_metric_layout(str(metrics_paths / "metric_layout.yml"))

    assert "position" not in tree_text
    assert layout["revenue"]["position"] == {"x": 12.5, "y": 40}


def test_save_drops_layout_for_removed_metric(metrics_paths):
    (metrics_paths / "metric_layout.yml").write_text(
        textwrap.dedent(
            """\
            gone_metric:
              position:
                x: 1
                y: 2
            revenue:
              position:
                x: 3
                y: 4
            """
        )
    )

    save_metric_tree(_tree(_draft("revenue")))

    layout = load_metric_layout(str(metrics_paths / "metric_layout.yml"))
    assert "gone_metric" not in layout
    assert layout["revenue"]["position"] == {"x": 3, "y": 4}


def test_save_preserves_layout_extras_for_surviving_metric(metrics_paths):
    (metrics_paths / "metric_layout.yml").write_text(
        textwrap.dedent(
            """\
            revenue:
              width: 240
              panel_height: 180
              collapsed: true
            """
        )
    )

    save_metric_tree(_tree(_draft("revenue")))

    layout = load_metric_layout(str(metrics_paths / "metric_layout.yml"))
    assert layout["revenue"] == {
        "width": 240,
        "panel_height": 180,
        "collapsed": True,
    }


def test_split_metric_layout_strips_position():
    entries, layout = split_metric_layout(
        [_draft("revenue", position=Position(x=1, y=2))]
    )

    assert entries[0].position is None
    assert entries[0].expression == "sum(revenue) from fct__order"
    assert layout == {"revenue": {"position": {"x": 1, "y": 2}}}


def test_split_metric_layout_drops_repeated_layout_keys():
    entries, layout = split_metric_layout([_draft("revenue"), _draft("order_count")])

    assert [entry.id for entry in entries] == ["revenue", "order_count"]
    assert layout == {}
