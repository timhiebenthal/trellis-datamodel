"""
API-level tests with framework: bruin.

Everything else tests the adapter in isolation. This drives the real ASGI app
against a Bruin pipeline, which is what actually proves no route or service
carries a dbt assumption — the whole point of the adapter generalization.
"""

import os

import pytest
import yaml
from starlette.testclient import TestClient

from trellis_datamodel import config as cfg


@pytest.fixture
def bruin_app(bruin_pipeline_copy, tmp_path, monkeypatch):
    """The real app, configured for Bruin rather than dbt."""
    data_model_path = str(tmp_path / "data_model.yml")
    with open(data_model_path, "w") as f:
        yaml.dump(
            {
                "version": 0.1,
                "entities": [
                    {
                        "id": "customer",
                        "label": "Customer",
                        "model_ref": "core.dim__customer",
                    },
                    {
                        "id": "order",
                        "label": "Order",
                        "model_ref": "core.fct__order",
                    },
                    {"id": "region", "label": "Region"},
                ],
                "relationships": [],
            },
            f,
        )

    config_module = __import__("sys").modules["trellis_datamodel.config"]
    monkeypatch.setattr(config_module, "FRAMEWORK", "bruin")
    monkeypatch.setattr(config_module, "BRUIN_PIPELINE_PATH", bruin_pipeline_copy)
    monkeypatch.setattr(config_module, "BRUIN_ASSET_PATHS", [])
    monkeypatch.setattr(config_module, "BRUIN_DEFAULT_ASSET_TYPE", "duckdb.sql")
    monkeypatch.setattr(config_module, "DATA_MODEL_PATH", data_model_path)
    monkeypatch.setattr(config_module, "CANVAS_LAYOUT_PATH", str(tmp_path / "canvas_layout.yml"))
    monkeypatch.setattr(config_module, "LINEAGE_ENABLED", True)
    monkeypatch.setattr(config_module, "LINEAGE_LAYERS", [])
    monkeypatch.setattr(config_module, "EXPOSURES_ENABLED", True)

    from trellis_datamodel.server import app

    with TestClient(app) as client:
        yield client


class TestManifestEndpoint:
    def test_returns_bruin_assets_as_models(self, bruin_app):
        response = bruin_app.get("/api/manifest")

        assert response.status_code == 200
        names = [m["name"] for m in response.json()["models"]]
        assert "dim__customer" in names
        assert "fct__order" in names

    def test_models_carry_columns_and_schema(self, bruin_app):
        models = {m["name"]: m for m in bruin_app.get("/api/manifest").json()["models"]}

        dim = models["dim__customer"]
        assert dim["unique_id"] == "core.dim__customer"
        assert dim["schema"] == "core"
        assert [c["name"] for c in dim["columns"]] == [
            "customer_id",
            "customer_name",
        ]


class TestConfigStatusEndpoint:
    def test_reports_the_pipeline_not_a_dbt_project(self, bruin_app, bruin_pipeline_copy):
        data = bruin_app.get("/api/config-status").json()

        assert data["framework"] == "bruin"
        assert data["project_path"] == bruin_pipeline_copy
        assert data["artifacts_present"] is True
        assert data["error"] is None

    def test_does_not_emit_dbt_artifact_keys(self, bruin_app):
        """A Bruin project has no manifest.json to report on."""
        data = bruin_app.get("/api/config-status").json()

        assert "manifest_path" not in data
        assert "catalog_path" not in data
        assert "dbt_project_path" not in data

    def test_reports_bruin_artifacts(self, bruin_app):
        artifacts = bruin_app.get("/api/config-status").json()["artifacts"]

        assert artifacts["pipeline"]["exists"] is True
        assert artifacts["assets"]["exists"] is True

    def test_missing_pipeline_reports_an_error(self, bruin_app, monkeypatch, tmp_path):
        import sys

        monkeypatch.setattr(
            sys.modules["trellis_datamodel.config"],
            "BRUIN_PIPELINE_PATH",
            str(tmp_path / "nope"),
        )

        data = bruin_app.get("/api/config-status").json()

        assert data["artifacts_present"] is False
        assert "Pipeline not found" in data["error"]


class TestConfigInfoEndpoint:
    def test_advertises_bruin_capabilities(self, bruin_app):
        capabilities = bruin_app.get("/api/config-info").json()["capabilities"]

        assert capabilities["lineage"] is True
        assert capabilities["relationships"] is True
        assert capabilities["exposures"] is False
        assert capabilities["column_lineage"] is False

    def test_reports_resolved_asset_dirs(self, bruin_app, bruin_pipeline_copy):
        data = bruin_app.get("/api/config-info").json()

        assert data["model_paths_resolved"] == [
            os.path.abspath(os.path.join(bruin_pipeline_copy, "assets"))
        ]


class TestLineageEndpoint:
    def test_returns_lineage_for_a_bruin_asset(self, bruin_app):
        response = bruin_app.get("/api/lineage/core.dim__customer")

        assert response.status_code == 200
        data = response.json()
        ids = {n["id"] for n in data["nodes"]}
        assert ids == {
            "core.dim__customer",
            "prep.prep__customers",
            "raw.raw__customers",
        }

    def test_levels_are_computed(self, bruin_app):
        nodes = {
            n["id"]: n
            for n in bruin_app.get("/api/lineage/core.dim__customer").json()["nodes"]
        }

        assert nodes["core.dim__customer"]["level"] == 0
        assert nodes["raw.raw__customers"]["level"] == 2

    def test_source_is_flagged_with_its_system(self, bruin_app):
        nodes = {
            n["id"]: n
            for n in bruin_app.get("/api/lineage/core.dim__customer").json()["nodes"]
        }

        assert nodes["raw.raw__customers"]["isSource"] is True
        assert nodes["raw.raw__customers"]["sourceName"] == "crm_api"

    def test_unknown_asset_returns_404(self, bruin_app):
        assert bruin_app.get("/api/lineage/core.nope").status_code == 404


class TestExposuresEndpoint:
    def test_returns_empty_rather_than_failing(self, bruin_app):
        """Bruin has no exposures; the endpoint must still answer cleanly."""
        response = bruin_app.get("/api/exposures")

        assert response.status_code == 200
        assert response.json() == {"exposures": [], "entityUsage": {}}


class TestDataModelEndpoint:
    def test_returns_entities_with_lineage_derived_sources(self, bruin_app):
        response = bruin_app.get("/api/data-model")

        assert response.status_code == 200
        entities = {e["id"]: e for e in response.json()["entities"]}
        assert entities["customer"]["source_system"] == ["crm_api"]

    def test_collects_every_source_upstream_of_an_entity(self, bruin_app):
        entities = {
            e["id"]: e for e in bruin_app.get("/api/data-model").json()["entities"]
        }

        assert sorted(entities["order"]["source_system"]) == [
            "crm_api",
            "postgres_prod",
        ]

    def test_unbound_entity_has_no_sources(self, bruin_app):
        entities = {
            e["id"]: e for e in bruin_app.get("/api/data-model").json()["entities"]
        }

        assert not entities["region"].get("source_system")


class TestSchemaEndpoints:
    def test_reads_a_model_schema(self, bruin_app):
        response = bruin_app.get("/api/models/dim__customer/schema")

        assert response.status_code == 200
        data = response.json()
        assert data["model_name"] == "dim__customer"
        assert [c["name"] for c in data["columns"]] == [
            "customer_id",
            "customer_name",
        ]

    def test_updates_a_model_schema(self, bruin_app, bruin_pipeline_copy):
        response = bruin_app.post(
            "/api/models/dim__customer/schema",
            json={
                "columns": [
                    {"name": "customer_id", "data_type": "varchar"},
                    {
                        "name": "segment",
                        "data_type": "varchar",
                        "description": "Segment",
                    },
                ],
                "description": "Updated via API",
            },
        )

        assert response.status_code == 200

        asset_path = os.path.join(
            bruin_pipeline_copy, "assets", "02_core", "dim__customer.sql"
        )
        with open(asset_path) as f:
            content = f.read()
        assert "Updated via API" in content
        assert "segment" in content
        # The SQL body is untouched.
        assert "FROM prep.prep__customers;" in content

    def test_infers_relationships_from_foreign_keys(self, bruin_app):
        response = bruin_app.get("/api/infer-relationships")

        assert response.status_code == 200
        pairs = {
            (r["source"], r["target"]) for r in response.json()["relationships"]
        }
        assert ("order", "customer") in pairs
