"""Tests for catalog resolution and unresolved bindings on the metric tree."""

from pathlib import Path

import pytest
import yaml

import trellis_datamodel.config as cfg
from trellis_datamodel.models.metric import (
    MetricBinding,
    MetricEntry,
    MetricTreeUpdate,
)
from trellis_datamodel.services import metric_tree as metric_tree_service
from trellis_datamodel.services.metric_tree import (
    load_metric_tree,
    resolve_catalog,
    save_metric_tree,
)
from trellis_datamodel.utils.structured_data import load_yaml_or_json

SEMANTIC_MODEL_FIXTURE = (
    Path(__file__).parent / "fixtures" / "metric_tree" / "semantic_model.yml"
)

# The models the fake framework reports: one backs the fixture's `fct__order`
# dataset, the other backs an entity that carries no metrics.
FIXTURE_MODELS = [
    {
        "unique_id": "model.shop.fct_order",
        "name": "fct__order",
        "schema": "main",
        "table": "fct__order",
        "columns": [],
        "description": None,
        "materialization": "table",
        "file_path": "models/3_core/fct__order.sql",
        "tags": [],
    },
    {
        "unique_id": "model.shop.dim_customer",
        "name": "dim_customer",
        "schema": "main",
        "table": "dim_customer",
        "columns": [],
        "description": None,
        "materialization": "table",
        "file_path": "models/3_core/dim_customer.sql",
        "tags": [],
    },
]

# `fct__web_session` has an entity with a matching id but no `model_ref`, so it
# must stay unbindable: only entities actually bound to a model participate.
FIXTURE_ENTITIES = [
    {"id": "fct__order", "label": "Order fact", "model_ref": "model.shop.fct_order"},
    {"id": "dim_customer", "label": "Customer", "model_ref": "model.shop.dim_customer"},
    {"id": "fct__web_session", "label": "Web session, unbound"},
    {"id": "fct__orphan", "label": "Orphan", "model_ref": "model.shop.missing"},
]


@pytest.fixture
def catalog_docs(monkeypatch, tmp_path):
    """Point every path the catalog reads at tmp_path plus the shared fixture."""
    semantic_model = tmp_path / "semantic_model.yml"
    semantic_model.write_text(SEMANTIC_MODEL_FIXTURE.read_text())

    data_model = tmp_path / "data_model.yml"
    data_model.write_text(
        yaml.safe_dump(
            {"version": 0.1, "entities": FIXTURE_ENTITIES, "relationships": []}
        )
    )

    monkeypatch.setattr(
        cfg, "OSSIE_CONFIG", cfg.OssieConfig(file=str(semantic_model))
    )
    monkeypatch.setattr(cfg, "DATA_MODEL_PATH", str(data_model))
    monkeypatch.setattr(
        cfg,
        "METRICS_CONFIG",
        cfg.MetricsConfig(
            enabled=True,
            file=str(tmp_path / "metric_tree.yml"),
        ),
    )
    monkeypatch.setattr(metric_tree_service, "get_models", lambda: FIXTURE_MODELS)

    return {
        "semantic_model": semantic_model,
        "data_model": data_model,
        "tree": Path(cfg.METRICS_CONFIG.file),
    }


def _catalog_by_name() -> dict[str, dict]:
    return {entry["name"]: entry for entry in resolve_catalog()}


class TestResolveCatalog:
    """One entry per metric in the Ossie document, classified for the sidebar."""

    def test_missing_semantic_model_yields_an_empty_catalog(
        self, catalog_docs, monkeypatch, tmp_path
    ):
        monkeypatch.setattr(
            cfg,
            "OSSIE_CONFIG",
            cfg.OssieConfig(file=str(tmp_path / "absent.yml")),
        )

        assert resolve_catalog() == []

    def test_semantic_model_without_metrics_yields_an_empty_catalog(
        self, catalog_docs, monkeypatch
    ):
        catalog_docs["semantic_model"].write_text(
            "version: 0.2.0.dev0\nname: no_metrics\ndatasets: []\n"
        )

        assert resolve_catalog() == []

    def test_dataset_scoped_metric_on_a_mapped_dataset_is_bindable(self, catalog_docs):
        entry = _catalog_by_name()["revenue"]

        assert entry["bindable"] is True
        assert entry["dataset"] == "fct__order"
        assert entry["entity_id"] == "fct__order"
        assert "reason" not in entry

    def test_document_level_metric_is_read_only_with_a_scope_reason(self, catalog_docs):
        entry = _catalog_by_name()["gross_margin"]

        assert entry["bindable"] is False
        assert entry["dataset"] is None
        assert entry["entity_id"] is None
        assert "document" in entry["reason"]
        assert "cross-dataset" in entry["reason"]

    def test_unmapped_dataset_is_read_only_with_the_dataset_named(self, catalog_docs):
        entry = _catalog_by_name()["sessions"]

        assert entry["bindable"] is False
        assert entry["dataset"] == "fct__web_session"
        assert entry["entity_id"] is None
        assert "fct__web_session" in entry["reason"]

    def test_catalog_is_sorted_by_dataset_then_name(self, catalog_docs):
        assert [entry["name"] for entry in resolve_catalog()] == [
            "gross_margin",
            "order_count",
            "revenue",
            "sessions",
        ]


class TestUnresolvedOnLoad:
    """A saved reference that no longer resolves is flagged, never dropped."""

    def _tree(self, *metrics: MetricEntry) -> MetricTreeUpdate:
        return MetricTreeUpdate(version=0.1, metrics=list(metrics), influences=[])

    def test_bound_metric_definition_present_is_resolved(self, catalog_docs):
        save_metric_tree(
            self._tree(
                MetricEntry(
                    id="revenue",
                    label="Revenue",
                    binding=MetricBinding(dataset="fct__order", name="revenue"),
                )
            )
        )

        reloaded = load_metric_tree(cfg.METRICS_CONFIG.file)

        assert reloaded.metrics[0].unresolved is False

    def test_bound_metric_whose_definition_vanished_is_unresolved(self, catalog_docs):
        save_metric_tree(
            self._tree(
                MetricEntry(
                    id="archived_revenue",
                    label="Archived revenue",
                    binding=MetricBinding(
                        dataset="fct__order", name="archived_revenue"
                    ),
                )
            )
        )

        reloaded = load_metric_tree(cfg.METRICS_CONFIG.file)

        assert reloaded.metrics[0].unresolved is True

    def test_draft_with_a_deleted_dataset_ref_is_unresolved(self, catalog_docs):
        save_metric_tree(
            self._tree(
                MetricEntry(
                    id="orphan_draft",
                    label="Orphan draft",
                    expression="sum(amount) from removed",
                    dataset_ref="removed_entity",
                )
            )
        )

        reloaded = load_metric_tree(cfg.METRICS_CONFIG.file)

        assert reloaded.metrics[0].unresolved is True

    def test_a_bound_metric_survives_a_vanished_definition(self, catalog_docs):
        save_metric_tree(
            self._tree(
                MetricEntry(
                    id="archived_revenue",
                    label="Archived revenue",
                    binding=MetricBinding(
                        dataset="fct__order", name="archived_revenue"
                    ),
                )
            )
        )

        saved = load_yaml_or_json(str(catalog_docs["tree"]))["metrics"][0]

        assert saved["binding"] == {
            "dataset": "fct__order",
            "name": "archived_revenue",
        }
        assert "unresolved" not in saved


class TestResolvedExpressionOnLoad:
    """A bound entry carries the definition's expression, read-only."""

    def _tree(self, *metrics: MetricEntry) -> MetricTreeUpdate:
        return MetricTreeUpdate(version=0.1, metrics=list(metrics), influences=[])

    def test_bound_metric_carries_the_semantic_model_expression(self, catalog_docs):
        save_metric_tree(
            self._tree(
                MetricEntry(
                    id="revenue",
                    label="Revenue",
                    binding=MetricBinding(dataset="fct__order", name="revenue"),
                )
            )
        )

        reloaded = load_metric_tree(cfg.METRICS_CONFIG.file)

        assert reloaded.metrics[0].resolved_expression == "sum(amount)"

    def test_a_draft_carries_no_resolved_expression(self, catalog_docs):
        save_metric_tree(
            self._tree(
                MetricEntry(
                    id="revenue",
                    label="Revenue",
                    expression="sum(amount) from fct__order",
                    dataset_ref="fct__order",
                )
            )
        )

        reloaded = load_metric_tree(cfg.METRICS_CONFIG.file)

        assert reloaded.metrics[0].resolved_expression is None

    def test_an_unresolved_binding_carries_no_resolved_expression(self, catalog_docs):
        save_metric_tree(
            self._tree(
                MetricEntry(
                    id="archived_revenue",
                    label="Archived revenue",
                    binding=MetricBinding(
                        dataset="fct__order", name="archived_revenue"
                    ),
                )
            )
        )

        reloaded = load_metric_tree(cfg.METRICS_CONFIG.file)

        assert reloaded.metrics[0].unresolved is True
        assert reloaded.metrics[0].resolved_expression is None

    def test_a_definition_with_another_expression_shape_is_left_without_one(
        self, catalog_docs
    ):
        catalog_docs["semantic_model"].write_text(
            yaml.safe_dump(
                {
                    "version": "0.2.0.dev0",
                    "datasets": [
                        {
                            "name": "fct__order",
                            "metrics": [
                                {"name": "revenue", "expression": "sum(amount)"}
                            ],
                        }
                    ],
                }
            )
        )
        save_metric_tree(
            self._tree(
                MetricEntry(
                    id="revenue",
                    label="Revenue",
                    binding=MetricBinding(dataset="fct__order", name="revenue"),
                )
            )
        )

        reloaded = load_metric_tree(cfg.METRICS_CONFIG.file)

        assert reloaded.metrics[0].unresolved is False
        assert reloaded.metrics[0].resolved_expression is None


class TestSaveWarnings:
    """Unresolvable references warn; the entry is always kept."""

    def _tree(self, *metrics: MetricEntry) -> MetricTreeUpdate:
        return MetricTreeUpdate(version=0.1, metrics=list(metrics), influences=[])

    def test_no_warning_when_every_reference_resolves(self, catalog_docs):
        warnings = save_metric_tree(
            self._tree(
                MetricEntry(
                    id="revenue",
                    label="Revenue",
                    binding=MetricBinding(dataset="fct__order", name="revenue"),
                ),
                MetricEntry(
                    id="draft",
                    label="Draft",
                    expression="sum(amount) from fct__order",
                    dataset_ref="fct__order",
                ),
            )
        )

        assert warnings == []

    def test_warns_and_keeps_a_binding_whose_definition_vanished(self, catalog_docs):
        warnings = save_metric_tree(
            self._tree(
                MetricEntry(
                    id="archived_revenue",
                    label="Archived revenue",
                    binding=MetricBinding(
                        dataset="fct__order", name="archived_revenue"
                    ),
                )
            )
        )

        assert len(warnings) == 1
        assert "archived_revenue" in warnings[0]
        assert "fct__order.archived_revenue" in warnings[0]
        assert "semantic_model.yml" in warnings[0]

        saved = load_yaml_or_json(str(catalog_docs["tree"]))["metrics"]
        assert [metric["id"] for metric in saved] == ["archived_revenue"]

    def test_warns_on_an_unresolvable_dataset_ref_and_keeps_the_entry(
        self, catalog_docs
    ):
        warnings = save_metric_tree(
            self._tree(
                MetricEntry(
                    id="orphan_draft",
                    label="Orphan draft",
                    expression="sum(amount) from removed",
                    dataset_ref="removed_entity",
                )
            )
        )

        assert len(warnings) == 1
        assert "orphan_draft" in warnings[0]
        assert "removed_entity" in warnings[0]
        assert "data_model.yml" in warnings[0]

        saved = load_yaml_or_json(str(catalog_docs["tree"]))["metrics"]
        assert [metric["id"] for metric in saved] == ["orphan_draft"]
        assert saved[0]["dataset_ref"] == "removed_entity"

    def test_a_draft_without_a_dataset_ref_never_warns(self, catalog_docs):
        warnings = save_metric_tree(
            self._tree(
                MetricEntry(
                    id="document_metric",
                    label="Document metric",
                    expression="gross_profit / net_revenue",
                )
            )
        )

        assert warnings == []

    def test_client_supplied_unresolved_is_never_written(self, catalog_docs):
        """`unresolved` is wire state; a round-tripped payload must not persist it."""
        warnings = save_metric_tree(
            MetricTreeUpdate.model_validate(
                {
                    "version": 0.1,
                    "metrics": [
                        {
                            "id": "revenue",
                            "label": "Revenue",
                            "binding": {
                                "dataset": "fct__order",
                                "name": "revenue",
                            },
                            "unresolved": True,
                        }
                    ],
                    "influences": [],
                }
            )
        )

        assert warnings == []
        saved = load_yaml_or_json(str(catalog_docs["tree"]))["metrics"][0]
        assert "unresolved" not in saved

    def test_client_supplied_resolved_expression_is_never_written(self, catalog_docs):
        """`resolved_expression` is wire state; a round-tripped payload must not persist it."""
        warnings = save_metric_tree(
            MetricTreeUpdate.model_validate(
                {
                    "version": 0.1,
                    "metrics": [
                        {
                            "id": "revenue",
                            "label": "Revenue",
                            "binding": {
                                "dataset": "fct__order",
                                "name": "revenue",
                            },
                            "resolved_expression": "sum(amount)",
                        }
                    ],
                    "influences": [],
                }
            )
        )

        assert warnings == []
        saved = load_yaml_or_json(str(catalog_docs["tree"]))["metrics"][0]
        assert "resolved_expression" not in saved


class TestGetCatalogRoute:
    """GET /api/metric-tree publishes catalog flags and the unresolved state."""

    def test_get_returns_bindable_flags_and_unresolved_metrics(
        self, test_client, catalog_docs
    ):
        assert (
            test_client.post(
                "/api/metric-tree",
                json={
                    "version": 0.1,
                    "metrics": [
                        {
                            "id": "revenue",
                            "label": "Revenue",
                            "binding": {"dataset": "fct__order", "name": "revenue"},
                        },
                        {
                            "id": "archived_revenue",
                            "label": "Archived revenue",
                            "binding": {
                                "dataset": "fct__order",
                                "name": "archived_revenue",
                            },
                        },
                        {
                            "id": "orphan_draft",
                            "label": "Orphan draft",
                            "expression": "sum(amount) from removed",
                            "dataset_ref": "removed_entity",
                        },
                    ],
                    "influences": [],
                },
            ).status_code
            == 200
        )

        body = test_client.get("/api/metric-tree").json()

        assert {
            entry["name"]: entry["bindable"] for entry in body["catalog"]
        } == {
            "gross_margin": False,
            "order_count": True,
            "revenue": True,
            "sessions": False,
        }
        assert {
            metric["id"]: metric["unresolved"] for metric in body["metrics"]
        } == {
            "archived_revenue": True,
            "orphan_draft": True,
            "revenue": False,
        }

    def test_get_publishes_the_bound_expression(self, test_client, catalog_docs):
        assert (
            test_client.post(
                "/api/metric-tree",
                json={
                    "version": 0.1,
                    "metrics": [
                        {
                            "id": "revenue",
                            "label": "Revenue",
                            "binding": {"dataset": "fct__order", "name": "revenue"},
                        }
                    ],
                    "influences": [],
                },
            ).status_code
            == 200
        )

        body = test_client.get("/api/metric-tree").json()

        assert body["metrics"][0]["resolved_expression"] == "sum(amount)"
