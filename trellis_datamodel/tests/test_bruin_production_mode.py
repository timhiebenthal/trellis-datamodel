"""
Schema routes against a Bruin project configured the way a real user has it.

Test mode pre-sets `DBT_PROJECT_PATH`, which hid that every schema route
rejected a Bruin project for lacking a dbt project path. Here the dbt keys are
blanked after the app starts, matching a production Bruin trellis.yml that
never mentions dbt.
"""

import os
import sys

import pytest
import yaml
from starlette.testclient import TestClient

DBT_ERROR = "dbt_project_path is not configured. Please set it in trellis.yml"


def _config_module():
    return sys.modules["trellis_datamodel.config"]


@pytest.fixture
def bruin_production_app(bruin_pipeline_copy, tmp_path, monkeypatch):
    """The real app on a Bruin pipeline, with no dbt settings at all."""
    data_model_path = str(tmp_path / "data_model.yml")
    with open(data_model_path, "w") as f:
        yaml.dump(
            {
                "version": 0.1,
                "entities": [
                    {"id": "customer", "label": "Customer", "model_ref": "core.dim__customer"},
                    {"id": "order", "label": "Order", "model_ref": "core.fct__order"},
                    {"id": "region", "label": "Region"},
                ],
                "relationships": [
                    {
                        "source": "order",
                        "target": "customer",
                        "type": "many_to_one",
                        "source_field": "customer_id",
                        "target_field": "customer_id",
                    }
                ],
            },
            f,
        )

    config = _config_module()
    monkeypatch.setattr(config, "FRAMEWORK", "bruin")
    monkeypatch.setattr(config, "BRUIN_PIPELINE_PATH", bruin_pipeline_copy)
    monkeypatch.setattr(config, "BRUIN_ASSET_PATHS", [])
    monkeypatch.setattr(config, "BRUIN_DEFAULT_ASSET_TYPE", "duckdb.sql")
    monkeypatch.setattr(config, "DATA_MODEL_PATH", data_model_path)
    monkeypatch.setattr(config, "CANVAS_LAYOUT_PATH", str(tmp_path / "canvas_layout.yml"))

    from trellis_datamodel.server import app

    with TestClient(app) as client:
        # A Bruin trellis.yml has no dbt keys; blank them once the app is up so
        # nothing in test-mode startup can put them back.
        monkeypatch.setattr(config, "DBT_PROJECT_PATH", "")
        monkeypatch.setattr(config, "MANIFEST_PATH", "")
        monkeypatch.setattr(config, "CATALOG_PATH", "")
        yield client


def _assert_not_rejected_for_dbt(response):
    assert "dbt_project_path" not in response.text
    assert response.status_code == 200, response.text


class TestBruinSchemaRoutesWithoutDbtProjectPath:
    def test_get_model_schema(self, bruin_production_app):
        response = bruin_production_app.get("/api/models/dim__customer/schema")

        _assert_not_rejected_for_dbt(response)
        assert [c["name"] for c in response.json()["columns"]] == [
            "customer_id",
            "customer_name",
        ]

    def test_post_model_schema(self, bruin_production_app, bruin_pipeline_copy):
        response = bruin_production_app.post(
            "/api/models/dim__customer/schema",
            json={
                "columns": [
                    {"name": "customer_id", "data_type": "varchar"},
                    {"name": "segment", "data_type": "varchar", "description": "Segment"},
                ],
                "description": "Pushed from Trellis",
            },
        )

        _assert_not_rejected_for_dbt(response)
        asset = os.path.join(bruin_pipeline_copy, "assets", "02_core", "dim__customer.sql")
        with open(asset) as f:
            content = f.read()
        assert "Pushed from Trellis" in content
        assert "segment" in content

    def test_infer_relationships(self, bruin_production_app):
        response = bruin_production_app.get("/api/infer-relationships")

        _assert_not_rejected_for_dbt(response)
        pairs = {(r["source"], r["target"]) for r in response.json()["relationships"]}
        # dbt and canvas convention: the referenced asset is the source.
        assert ("customer", "order") in pairs

    def test_sync_tests(self, bruin_production_app, bruin_pipeline_copy):
        response = bruin_production_app.post("/api/sync-tests")

        _assert_not_rejected_for_dbt(response)
        files = response.json()["files"]
        assert all(f.startswith(bruin_pipeline_copy) for f in files)
        # The fixture already holds the relationship's key, so there is nothing
        # to rewrite, and the hand-written key to the unbound dim__product
        # asset must survive the push.
        order_asset = os.path.join(
            bruin_pipeline_copy, "assets", "02_core", "fct__order.sql"
        )
        with open(order_asset) as f:
            assert "dim__product" in f.read()

    def test_post_schema_scaffolds_an_asset(self, bruin_production_app, bruin_pipeline_copy):
        response = bruin_production_app.post(
            "/api/schema",
            json={
                "entity_id": "region",
                "model_name": "dim__region",
                "fields": [
                    {"name": "region_id", "datatype": "varchar", "description": "Region key"}
                ],
                "description": "Sales regions",
            },
        )

        _assert_not_rejected_for_dbt(response)
        file_path = response.json()["file_path"]
        assert file_path.startswith(bruin_pipeline_copy)
        with open(file_path) as f:
            assert "region_id" in f.read()


def _customer_asset(pipeline):
    return os.path.join(pipeline, "assets", "02_core", "dim__customer.sql")


def _asset_tags(pipeline):
    with open(_customer_asset(pipeline)) as f:
        content = f.read()
    block = content.split("/* @bruin\n", 1)[1].split("\n@bruin */", 1)[0]
    return yaml.safe_load(block).get("tags")


def _autosave_customer(client, ui_tags):
    """Save with the payload shape auto-save.ts sends for a bound entity:
    model_ref + ui_tags (omitted once emptied), never pushed_tags."""
    customer = {"id": "customer", "label": "Customer", "model_ref": "core.dim__customer"}
    if ui_tags:
        customer["ui_tags"] = ui_tags
    response = client.post(
        "/api/data-model",
        json={
            "version": 0.1,
            "entities": [
                customer,
                {"id": "order", "label": "Order", "model_ref": "core.fct__order"},
            ],
            "relationships": [],
        },
    )
    assert response.status_code == 200, response.text


def _push(client):
    response = client.post("/api/sync-tests")
    _assert_not_rejected_for_dbt(response)


def _pushed_tags(data_model_path):
    with open(data_model_path) as f:
        entities = yaml.safe_load(f)["entities"]
    return next(e for e in entities if e["id"] == "customer").get("pushed_tags")


class TestBruinTagPushThroughRoutes:
    @pytest.fixture
    def data_model_path(self):
        return _config_module().DATA_MODEL_PATH

    def test_push_records_pushed_tags_in_the_data_model(
        self, bruin_production_app, bruin_pipeline_copy, data_model_path
    ):
        _autosave_customer(bruin_production_app, ["core", "pii"])
        _push(bruin_production_app)

        assert _asset_tags(bruin_pipeline_copy) == ["core", "entity", "pii"]
        # `core` was already on the asset: Bruin's tag, not Trellis's.
        assert _pushed_tags(data_model_path) == ["pii"]

    def test_removed_trellis_tag_leaves_the_asset_on_next_push(
        self, bruin_production_app, bruin_pipeline_copy
    ):
        _autosave_customer(bruin_production_app, ["pii", "gdpr"])
        _push(bruin_production_app)
        _autosave_customer(bruin_production_app, ["gdpr"])
        _push(bruin_production_app)

        assert _asset_tags(bruin_pipeline_copy) == ["core", "entity", "gdpr"]

    def test_removing_the_last_trellis_tag_removes_it_from_the_asset(
        self, bruin_production_app, bruin_pipeline_copy, data_model_path
    ):
        _autosave_customer(bruin_production_app, ["pii"])
        _push(bruin_production_app)
        _autosave_customer(bruin_production_app, [])
        _push(bruin_production_app)

        assert _asset_tags(bruin_pipeline_copy) == ["core", "entity"]
        assert _pushed_tags(data_model_path) == []


class TestBruinSchemaRoutesWithoutPipelinePath:
    def test_reports_the_bruin_setting_not_the_dbt_one(
        self, bruin_production_app, monkeypatch
    ):
        monkeypatch.setattr(_config_module(), "BRUIN_PIPELINE_PATH", "")

        response = bruin_production_app.get("/api/models/dim__customer/schema")

        assert response.status_code == 400
        assert "bruin_pipeline_path" in response.json()["detail"]
        assert "dbt_project_path" not in response.text


SCHEMA_ROUTE_CALLS = [
    ("get", "/api/models/users/schema", None),
    ("post", "/api/models/users/schema", {"columns": [{"name": "id"}]}),
    ("get", "/api/infer-relationships", None),
    ("post", "/api/sync-tests", None),
    (
        "post",
        "/api/schema",
        {"entity_id": "users", "model_name": "users", "fields": [{"name": "id"}]},
    ),
]


class TestDbtSchemaRoutesKeepTheirErrors:
    @pytest.mark.parametrize("method,url,body", SCHEMA_ROUTE_CALLS)
    def test_missing_dbt_project_path(self, test_client, monkeypatch, method, url, body):
        monkeypatch.setattr(_config_module(), "DBT_PROJECT_PATH", "")

        response = getattr(test_client, method)(url, **({"json": body} if body else {}))

        assert response.status_code == 400
        assert response.json() == {"detail": DBT_ERROR, "error": "configuration_error"}

    @pytest.mark.parametrize("method,url,body", SCHEMA_ROUTE_CALLS)
    def test_nonexistent_dbt_project_path(
        self, test_client, monkeypatch, tmp_path, method, url, body
    ):
        missing = str(tmp_path / "no_such_project")
        monkeypatch.setattr(_config_module(), "DBT_PROJECT_PATH", missing)

        response = getattr(test_client, method)(url, **({"json": body} if body else {}))

        assert response.status_code == 400
        assert response.json()["detail"] == f"dbt_project_path does not exist: {missing}"
