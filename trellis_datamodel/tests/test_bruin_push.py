"""
Bruin Push (`sync_relationships`) writes more than foreign keys.

For every bound asset it also pushes the entity description, the drafted
columns (a type only where the asset declares none), each drafted column's
origin (asset-level `meta`, one string entry per column) and the entity's
`ui_tags` (removing only tags Trellis itself pushed before).
"""

import os
import re

import pytest
import yaml

from trellis_datamodel import config as cfg
from trellis_datamodel.adapters.bruin import BruinAdapter
from trellis_datamodel.services.reconciliation import reconcile_framework

ORIGIN = [{"System": "CRM"}, {"Table": "customers"}]
CUSTOMER_REF = "core.dim__customer"


def _block(path):
    with open(path) as f:
        content = f.read()
    match = re.search(r"/\*\s*@bruin\s*\n(.*?)\n\s*@bruin\s*\*/", content, re.S)
    return yaml.safe_load(match.group(1))


def _columns(path):
    return {c["name"]: c for c in _block(path)["columns"]}


@pytest.fixture
def data_model_path(tmp_path):
    path = tmp_path / "data_model.yml"
    path.write_text(yaml.safe_dump({"entities": [], "relationships": []}))
    return str(path)


@pytest.fixture
def adapter(bruin_pipeline_copy, data_model_path):
    return BruinAdapter(
        pipeline_path=bruin_pipeline_copy,
        data_model_path=data_model_path,
        asset_paths=[],
    )


@pytest.fixture
def customer_path(bruin_pipeline_copy):
    return os.path.join(bruin_pipeline_copy, "assets", "02_core", "dim__customer.sql")


def _customer(**extra):
    return {"id": "customer", "label": "Customer", "model_ref": CUSTOMER_REF, **extra}


def _add_asset_meta(path, meta_yaml):
    """Hand-write an asset-level `meta` block, as a Bruin user would."""
    with open(path) as f:
        content = f.read()
    content = content.replace("columns:\n", f"meta:\n{meta_yaml}columns:\n", 1)
    with open(path, "w") as f:
        f.write(content)


class TestTags:
    def test_trellis_tag_lands_on_the_asset(self, adapter, customer_path):
        customer = _customer(ui_tags=["pii"])

        adapter.sync_relationships([customer], [])

        assert _block(customer_path)["tags"] == ["core", "entity", "pii"]
        assert customer["pushed_tags"] == ["pii"]

    def test_tag_hand_added_to_the_asset_survives(self, adapter, customer_path):
        customer = _customer(ui_tags=["pii"])
        adapter.sync_relationships([customer], [])
        with open(customer_path) as f:
            content = f.read()
        with open(customer_path, "w") as f:
            f.write(content.replace("  - pii\n", "  - pii\n  - hourly\n", 1))

        customer["ui_tags"] = []
        adapter.sync_relationships([customer], [])

        assert _block(customer_path)["tags"] == ["core", "entity", "hourly"]

    def test_ui_tag_the_asset_already_carries_is_not_recorded_as_pushed(
        self, adapter, customer_path
    ):
        customer = _customer(ui_tags=["core", "pii"])

        adapter.sync_relationships([customer], [])
        assert customer["pushed_tags"] == ["pii"]

        customer["ui_tags"] = []
        adapter.sync_relationships([customer], [])
        assert _block(customer_path)["tags"] == ["core", "entity"]

    def test_no_ui_tags_changes_nothing(self, adapter, customer_path):
        before = open(customer_path).read()
        customer = _customer(pushed_tags=["entity"])

        updated = adapter.sync_relationships([customer], [])

        assert updated == []
        assert open(customer_path).read() == before
        assert customer["pushed_tags"] == ["entity"]

    def test_empty_ui_tags_removes_only_previously_pushed_tags(
        self, adapter, customer_path
    ):
        customer = _customer(ui_tags=[], pushed_tags=["entity"])

        adapter.sync_relationships([customer], [])

        assert _block(customer_path)["tags"] == ["core"]
        assert customer["pushed_tags"] == []


class TestDescription:
    def test_entity_description_is_pushed(self, adapter, customer_path):
        adapter.sync_relationships([_customer(description="Every customer.")], [])

        assert _block(customer_path)["description"] == "Every customer."

    def test_asset_description_kept_without_an_entity_description(
        self, adapter, customer_path
    ):
        adapter.sync_relationships([_customer(drafted_fields=[])], [])

        assert _block(customer_path)["description"] == "One row per customer."


class TestDraftedColumns:
    def test_drafted_field_missing_from_the_asset_is_added(
        self, adapter, customer_path
    ):
        field = {
            "name": "segment",
            "datatype": "text",
            "description": "Marketing segment.",
            "source": "draft",
        }

        adapter.sync_relationships([_customer(drafted_fields=[field])], [])

        assert _columns(customer_path)["segment"] == {
            "name": "segment",
            "type": "text",
            "description": "Marketing segment.",
        }

    def test_declared_type_is_never_overwritten(self, adapter, customer_path):
        field = {"name": "customer_name", "datatype": "int", "source": "draft"}

        adapter.sync_relationships([_customer(drafted_fields=[field])], [])

        assert _columns(customer_path)["customer_name"]["type"] == "varchar"

    def test_missing_type_is_filled_from_the_physical_type(
        self, adapter, customer_path
    ):
        with open(customer_path) as f:
            content = f.read()
        with open(customer_path, "w") as f:
            f.write(
                content.replace(
                    "  - name: customer_name\n    type: varchar\n",
                    "  - name: customer_name\n",
                )
            )
        field = {
            "name": "customer_name",
            "datatype": "text",
            "physical_datatype": "varchar(255)",
            "source": "dbt",
        }

        adapter.sync_relationships([_customer(drafted_fields=[field])], [])

        assert _columns(customer_path)["customer_name"]["type"] == "varchar(255)"

    def test_unknown_datatype_is_not_written(self, adapter, customer_path):
        field = {"name": "blob", "datatype": "unknown", "source": "draft"}

        adapter.sync_relationships([_customer(drafted_fields=[field])], [])

        assert _columns(customer_path)["blob"] == {"name": "blob"}

    def test_asset_column_not_drafted_is_kept(self, adapter, customer_path):
        field = {"name": "customer_id", "datatype": "text", "source": "dbt"}

        adapter.sync_relationships([_customer(drafted_fields=[field])], [])

        columns = _columns(customer_path)
        assert list(columns) == ["customer_id", "customer_name"]
        # Bruin-owned keys on the existing column survive too.
        assert columns["customer_id"]["primary_key"] is True
        assert columns["customer_id"]["checks"] == [
            {"name": "unique"},
            {"name": "not_null"},
        ]

    def test_column_description_is_pushed(self, adapter, customer_path):
        field = {
            "name": "customer_name",
            "datatype": "text",
            "description": "Legal name.",
            "source": "dbt",
        }

        adapter.sync_relationships([_customer(drafted_fields=[field])], [])

        assert _columns(customer_path)["customer_name"]["description"] == "Legal name."

    def test_second_identical_push_writes_nothing(self, adapter, customer_path):
        customer = _customer(
            description="Every customer.",
            ui_tags=["pii"],
            drafted_fields=[
                {"name": "segment", "datatype": "text", "description": "Segment."},
                {"name": "customer_name", "datatype": "text", "origin": ORIGIN},
            ],
        )
        assert adapter.sync_relationships([customer], []) != []
        after_first = open(customer_path).read()

        assert adapter.sync_relationships([customer], []) == []
        assert open(customer_path).read() == after_first


class TestOrigin:
    def test_origin_is_one_string_entry_per_column_in_asset_meta(
        self, adapter, customer_path
    ):
        field = {"name": "customer_name", "datatype": "text", "origin": ORIGIN}

        adapter.sync_relationships([_customer(drafted_fields=[field])], [])

        meta = _block(customer_path)["meta"]
        assert meta == {"origin.customer_name": "System: CRM | Table: customers"}
        assert isinstance(meta["origin.customer_name"], str)
        assert "meta" not in _columns(customer_path)["customer_name"]

    def test_pushed_origin_survives_reconcile(
        self, adapter, customer_path, data_model_path, monkeypatch
    ):
        """Mirror of test_origin_roundtrip.py for Bruin: push, read, reconcile."""
        entity = _customer(
            drafted_fields=[
                {"name": "customer_id", "datatype": "text", "source": "draft"},
                {
                    "name": "customer_name",
                    "datatype": "text",
                    "source": "draft",
                    "description": "Display name of the customer.",
                    "origin": ORIGIN,
                },
            ]
        )
        with open(data_model_path, "w") as f:
            yaml.safe_dump({"entities": [entity], "relationships": []}, f)

        adapter.sync_relationships([entity], [])

        model = next(m for m in adapter.get_models() if m["unique_id"] == CUSTOMER_REF)
        cols = {c["name"]: c for c in model["columns"]}
        assert cols["customer_name"]["origin"] == ORIGIN
        assert "origin" not in cols["customer_id"]

        import trellis_datamodel.adapters as adapters_module

        monkeypatch.setattr(adapters_module, "get_adapter", lambda: adapter)
        monkeypatch.setattr(cfg, "DATA_MODEL_PATH", data_model_path)
        reconciled, _ = reconcile_framework()

        fields = {f["name"]: f for f in reconciled["entities"][0]["drafted_fields"]}
        assert fields["customer_name"].get("origin") == ORIGIN

    def test_clearing_origin_removes_only_that_key(self, adapter, customer_path):
        _add_asset_meta(
            customer_path,
            "  owner_team: growth  # set by hand\n"
            "  origin.customer_name: 'System: CRM'\n",
        )
        field = {"name": "customer_name", "datatype": "text", "origin": []}

        adapter.sync_relationships([_customer(drafted_fields=[field])], [])

        assert _block(customer_path)["meta"] == {"owner_team": "growth"}
        assert "# set by hand" in open(customer_path).read()

    def test_origin_of_a_column_not_drafted_is_left_alone(
        self, adapter, customer_path
    ):
        _add_asset_meta(customer_path, "  origin.customer_id: 'System: ERP'\n")
        field = {"name": "customer_name", "datatype": "text", "origin": ORIGIN}

        adapter.sync_relationships([_customer(drafted_fields=[field])], [])

        assert _block(customer_path)["meta"] == {
            "origin.customer_id": "System: ERP",
            "origin.customer_name": "System: CRM | Table: customers",
        }
