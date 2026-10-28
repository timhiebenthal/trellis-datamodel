"""Behaviour tests for GET /api/exposures: exposure metadata and entity usage.

The adapter reads a real manifest.json and the service reads a real
data_model.yml, both written into the shared test directory.
"""

import json
import sys

import pytest
import yaml

import trellis_datamodel.config  # noqa: F401  (ensure loaded)


class _Cfg:
    """Always the live config module: CLI tests re-import it mid-session."""

    def __getattr__(self, name):
        return getattr(sys.modules["trellis_datamodel.config"], name)


cfg = _Cfg()


def _model(name: str, depends_on: list[str] | None = None) -> dict:
    return {
        "unique_id": f"model.shop.{name}",
        "resource_type": "model",
        "name": name,
        "original_file_path": f"models/{name}.sql",
        "depends_on": {"nodes": depends_on or []},
    }


def _write_manifest(nodes: dict, exposures: dict, sources: dict | None = None):
    with open(cfg.MANIFEST_PATH, "w") as f:
        json.dump({"nodes": nodes, "sources": sources or {}, "exposures": exposures}, f)


def _write_data_model(entities: list[dict]):
    with open(cfg.DATA_MODEL_PATH, "w") as f:
        yaml.safe_dump({"version": 0.1, "entities": entities}, f)


def _exposure(name: str, depends_on: list[str], **extra) -> dict:
    return {"name": name, "depends_on": {"nodes": depends_on}, **extra}


@pytest.fixture
def exposures_client(test_client, monkeypatch):
    monkeypatch.setattr(sys.modules["trellis_datamodel.config"], "EXPOSURES_ENABLED", True)
    return test_client


def _get(client) -> dict:
    response = client.get("/api/exposures")
    assert response.status_code == 200
    return response.json()


def test_exposure_marks_entity_bound_to_an_upstream_model_as_used(exposures_client):
    _write_manifest(
        nodes={
            "model.shop.stg_orders": _model("stg_orders"),
            "model.shop.mart_sales": _model("mart_sales", ["model.shop.stg_orders"]),
        },
        exposures={
            "exposure.shop.sales_dash": _exposure(
                "sales_dash", ["model.shop.mart_sales"]
            )
        },
    )
    _write_data_model([{"id": "orders", "dbt_model": "model.shop.stg_orders"}])

    assert _get(exposures_client)["entityUsage"] == {"orders": ["sales_dash"]}


def test_exposure_marks_entity_bound_directly_to_the_exposed_model(exposures_client):
    _write_manifest(
        nodes={"model.shop.mart_sales": _model("mart_sales")},
        exposures={
            "exposure.shop.sales_dash": _exposure(
                "sales_dash", ["model.shop.mart_sales"]
            )
        },
    )
    _write_data_model([{"id": "sales", "model_ref": "model.shop.mart_sales"}])

    assert _get(exposures_client)["entityUsage"] == {"sales": ["sales_dash"]}


def test_exposure_marks_entity_that_lists_an_upstream_model_in_additional_models(
    exposures_client,
):
    _write_manifest(
        nodes={
            "model.shop.stg_orders": _model("stg_orders"),
            "model.shop.mart_sales": _model("mart_sales", ["model.shop.stg_orders"]),
        },
        exposures={
            "exposure.shop.sales_dash": _exposure(
                "sales_dash", ["model.shop.mart_sales"]
            )
        },
    )
    _write_data_model(
        [
            {
                "id": "sales",
                "dbt_model": "model.shop.unrelated",
                "additional_models": ["model.shop.stg_orders"],
            }
        ]
    )

    assert _get(exposures_client)["entityUsage"] == {"sales": ["sales_dash"]}


def test_entity_not_upstream_of_any_exposure_is_absent_from_usage(exposures_client):
    _write_manifest(
        nodes={
            "model.shop.stg_orders": _model("stg_orders"),
            "model.shop.stg_customers": _model("stg_customers"),
            "model.shop.mart_sales": _model("mart_sales", ["model.shop.stg_orders"]),
        },
        exposures={
            "exposure.shop.sales_dash": _exposure(
                "sales_dash", ["model.shop.mart_sales"]
            )
        },
    )
    _write_data_model(
        [
            {"id": "orders", "dbt_model": "model.shop.stg_orders"},
            {"id": "customers", "dbt_model": "model.shop.stg_customers"},
        ]
    )

    assert _get(exposures_client)["entityUsage"] == {"orders": ["sales_dash"]}


def test_entity_used_by_two_exposures_lists_both_in_declaration_order(
    exposures_client,
):
    _write_manifest(
        nodes={"model.shop.stg_orders": _model("stg_orders")},
        exposures={
            "exposure.shop.a_dash": _exposure("a_dash", ["model.shop.stg_orders"]),
            "exposure.shop.b_dash": _exposure("b_dash", ["model.shop.stg_orders"]),
        },
    )
    _write_data_model([{"id": "orders", "dbt_model": "model.shop.stg_orders"}])

    assert _get(exposures_client)["entityUsage"] == {"orders": ["a_dash", "b_dash"]}


def test_exposure_reaching_an_entity_through_two_paths_is_listed_once(
    exposures_client,
):
    _write_manifest(
        nodes={
            "model.shop.stg_orders": _model("stg_orders"),
            "model.shop.mart_a": _model("mart_a", ["model.shop.stg_orders"]),
            "model.shop.mart_b": _model("mart_b", ["model.shop.stg_orders"]),
        },
        exposures={
            "exposure.shop.dash": _exposure(
                "dash", ["model.shop.mart_a", "model.shop.mart_b"]
            )
        },
    )
    _write_data_model([{"id": "orders", "dbt_model": "model.shop.stg_orders"}])

    assert _get(exposures_client)["entityUsage"] == {"orders": ["dash"]}


def test_source_upstream_of_an_exposure_marks_no_entity(exposures_client):
    _write_manifest(
        nodes={
            "model.shop.stg_orders": _model(
                "stg_orders", ["source.shop.raw.orders"]
            ),
        },
        sources={
            "source.shop.raw.orders": {
                "unique_id": "source.shop.raw.orders",
                "name": "orders",
                "source_name": "raw",
            }
        },
        exposures={
            "exposure.shop.dash": _exposure("dash", ["model.shop.stg_orders"])
        },
    )
    _write_data_model([{"id": "raw_orders", "dbt_model": "source.shop.raw.orders"}])

    assert _get(exposures_client)["entityUsage"] == {}


def test_exposure_depending_on_a_model_missing_from_the_manifest_still_marks_its_entity(
    exposures_client,
):
    _write_manifest(
        nodes={"model.shop.other": _model("other")},
        exposures={
            "exposure.shop.dash": _exposure("dash", ["model.shop.renamed_away"])
        },
    )
    _write_data_model([{"id": "legacy", "dbt_model": "model.shop.renamed_away"}])

    assert _get(exposures_client)["entityUsage"] == {"legacy": ["dash"]}


def test_exposure_metadata_is_returned_with_owner_when_present(exposures_client):
    _write_manifest(
        nodes={"model.shop.mart_sales": _model("mart_sales")},
        exposures={
            "exposure.shop.sales_dash": _exposure(
                "sales_dash",
                ["model.shop.mart_sales"],
                label="Sales Dashboard",
                type="dashboard",
                description="Weekly sales",
                owner={"name": "Ada", "email": "ada@example.com"},
            )
        },
    )

    assert _get(exposures_client)["exposures"] == [
        {
            "name": "sales_dash",
            "label": "Sales Dashboard",
            "type": "dashboard",
            "description": "Weekly sales",
            "owner": {"name": "Ada"},
        }
    ]


def test_exposure_without_an_owner_has_no_owner_key(exposures_client):
    _write_manifest(
        nodes={"model.shop.mart_sales": _model("mart_sales")},
        exposures={
            "exposure.shop.sales_dash": _exposure(
                "sales_dash", ["model.shop.mart_sales"], type="dashboard"
            )
        },
    )

    exposure = _get(exposures_client)["exposures"][0]

    assert "owner" not in exposure
    assert exposure["label"] is None


def test_exposure_without_a_name_is_skipped(exposures_client):
    _write_manifest(
        nodes={"model.shop.stg_orders": _model("stg_orders")},
        exposures={
            "exposure.shop.nameless": {"depends_on": {"nodes": ["model.shop.stg_orders"]}},
            "exposure.shop.dash": _exposure("dash", ["model.shop.stg_orders"]),
        },
    )
    _write_data_model([{"id": "orders", "dbt_model": "model.shop.stg_orders"}])

    body = _get(exposures_client)

    assert [e["name"] for e in body["exposures"]] == ["dash"]
    assert body["entityUsage"] == {"orders": ["dash"]}


def test_project_without_exposures_returns_empty_response(exposures_client):
    _write_manifest(nodes={"model.shop.stg_orders": _model("stg_orders")}, exposures={})
    _write_data_model([{"id": "orders", "dbt_model": "model.shop.stg_orders"}])

    assert _get(exposures_client) == {"exposures": [], "entityUsage": {}}


def test_unreadable_manifest_returns_empty_response(exposures_client):
    with open(cfg.MANIFEST_PATH, "w") as f:
        f.write("{not json")

    assert _get(exposures_client) == {"exposures": [], "entityUsage": {}}


def test_exposures_are_listed_with_empty_usage_when_no_data_model_exists(
    exposures_client,
):
    _write_manifest(
        nodes={"model.shop.stg_orders": _model("stg_orders")},
        exposures={"exposure.shop.dash": _exposure("dash", ["model.shop.stg_orders"])},
    )

    body = _get(exposures_client)

    assert [e["name"] for e in body["exposures"]] == ["dash"]
    assert body["entityUsage"] == {}


def test_exposures_are_listed_with_empty_usage_when_data_model_is_malformed(
    exposures_client,
):
    _write_manifest(
        nodes={"model.shop.stg_orders": _model("stg_orders")},
        exposures={"exposure.shop.dash": _exposure("dash", ["model.shop.stg_orders"])},
    )
    with open(cfg.DATA_MODEL_PATH, "w") as f:
        f.write("entities: [unclosed\n")

    body = _get(exposures_client)

    assert [e["name"] for e in body["exposures"]] == ["dash"]
    assert body["entityUsage"] == {}


def test_entity_without_an_id_is_never_reported_as_used(exposures_client):
    _write_manifest(
        nodes={"model.shop.stg_orders": _model("stg_orders")},
        exposures={"exposure.shop.dash": _exposure("dash", ["model.shop.stg_orders"])},
    )
    _write_data_model(
        [
            {"dbt_model": "model.shop.stg_orders"},
            {"id": "orders", "dbt_model": "model.shop.stg_orders"},
        ]
    )

    assert _get(exposures_client)["entityUsage"] == {"orders": ["dash"]}
