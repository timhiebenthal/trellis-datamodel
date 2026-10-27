"""Tests for /api/metric-tree and the `metrics_enabled` config-info flag."""

import os
from pathlib import Path

import pytest
import yaml

import trellis_datamodel.config as cfg
from trellis_datamodel.utils.structured_data import load_yaml_or_json


@pytest.fixture
def metrics_paths(monkeypatch, tmp_path):
    """Point the metric tree file path at a throwaway directory, feature on."""
    config = cfg.MetricsConfig(
        enabled=True,
        file=str(tmp_path / "metric_tree.yml"),
    )
    monkeypatch.setattr(cfg, "METRICS_CONFIG", config)
    return config


@pytest.fixture
def disabled_metrics(monkeypatch, tmp_path):
    """Point the metric tree file path at a throwaway directory, feature off."""
    config = cfg.MetricsConfig(
        enabled=False,
        file=str(tmp_path / "metric_tree.yml"),
    )
    monkeypatch.setattr(cfg, "METRICS_CONFIG", config)
    return config


def _payload() -> dict:
    """A valid two-metric, one-influence document."""
    return {
        "version": 0.1,
        "metrics": [
            {
                "id": "revenue",
                "label": "Revenue",
                "description": "Booked revenue for the period.",
                "expression": "sum(amount) from fct__order",
                "dataset_ref": "fct__order",
            },
            {
                "id": "avg_price",
                "label": "Average price",
                "description": "Mean order value.",
                "expression": "avg(price) from fct__order",
                "dataset_ref": "fct__order",
            },
        ],
        "influences": [{"effect": "revenue", "drivers": ["avg_price"]}],
    }


class TestDisabledGate:
    """The feature flag answers 404 and touches no file."""

    def test_get_returns_404_naming_the_config_key(
        self, test_client, disabled_metrics
    ):
        response = test_client.get("/api/metric-tree")

        assert response.status_code == 404
        assert "metrics.enabled" in response.json()["detail"]
        assert not os.path.exists(disabled_metrics.file)

    def test_post_returns_404_naming_the_config_key(
        self, test_client, disabled_metrics
    ):
        response = test_client.post("/api/metric-tree", json=_payload())

        assert response.status_code == 404
        assert "metrics.enabled" in response.json()["detail"]
        assert not os.path.exists(disabled_metrics.file)


class TestGetMetricTree:
    """GET returns the document."""

    def test_returns_empty_document_when_no_file(self, test_client, metrics_paths):
        response = test_client.get("/api/metric-tree")

        assert response.status_code == 200
        assert response.json() == {
            "version": 0.1,
            "metrics": [],
            "influences": [],
            "catalog": [],
        }
        assert not os.path.exists(metrics_paths.file)

    def test_returns_saved_document(
        self, test_client, metrics_paths
    ):
        payload = _payload()
        assert test_client.post("/api/metric-tree", json=payload).status_code == 200

        body = test_client.get("/api/metric-tree").json()

        assert [metric["id"] for metric in body["metrics"]] == ["avg_price", "revenue"]
        assert body["influences"] == [{"effect": "revenue", "drivers": ["avg_price"]}]
        assert body["catalog"] == []


class TestPostMetricTree:
    """POST validates and writes metric_tree.yml."""

    def test_round_trip_writes_tree_file(
        self, test_client, metrics_paths, temp_data_model_path
    ):
        Path(temp_data_model_path).write_text(
            yaml.safe_dump(
                {
                    "version": 0.1,
                    "entities": [{"id": "fct__order", "label": "Order fact"}],
                    "relationships": [],
                }
            )
        )

        response = test_client.post("/api/metric-tree", json=_payload())

        assert response.status_code == 200
        assert response.json() == {"status": "success", "warnings": []}
        assert os.path.exists(metrics_paths.file)

        tree = load_yaml_or_json(metrics_paths.file)
        assert tree["version"] == 0.1
        assert [metric["id"] for metric in tree["metrics"]] == ["avg_price", "revenue"]
        assert tree["influences"] == [{"effect": "revenue", "drivers": ["avg_price"]}]
        assert tree["metrics"][1]["expression"] == "sum(amount) from fct__order"

    def test_duplicate_id_returns_422_naming_the_id(self, test_client, metrics_paths):
        payload = _payload()
        payload["metrics"].append(dict(payload["metrics"][0]))

        response = test_client.post("/api/metric-tree", json=payload)

        assert response.status_code == 422
        assert "revenue" in response.json()["detail"]
        assert not os.path.exists(metrics_paths.file)


class TestConfigInfoFlag:
    """`metrics_enabled` publishes the flag the frontend gates the nav entry on."""

    def test_metrics_enabled_is_false(self, test_client, disabled_metrics):
        body = test_client.get("/api/config-info").json()

        assert body["metrics_enabled"] is False

    def test_metrics_enabled_is_true(self, test_client, metrics_paths):
        body = test_client.get("/api/config-info").json()

        assert body["metrics_enabled"] is True
