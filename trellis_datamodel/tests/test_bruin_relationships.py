"""
Tests for BruinAdapter relationship inference and sync.

Bruin declares references natively as `columns[].foreign_key: {table, column}`,
so relationships round-trip: inference reads them, sync writes them, and a
relationship deleted in Trellis has its foreign_key pruned.
"""

import os
import re

import pytest
import yaml

from trellis_datamodel.adapters.bruin import BruinAdapter


DATA_MODEL = {
    "entities": [
        {
            "id": "customer",
            "label": "Customer",
            "model_ref": "core.dim__customer",
        },
        {
            "id": "product",
            "label": "Product",
            # Bound by short name, to prove both spellings resolve.
            "model_ref": "dim__product",
        },
        {
            "id": "order",
            "label": "Order",
            "model_ref": "core.fct__order",
        },
    ],
    "relationships": [],
}


def _write_data_model(path, data_model):
    with open(path, "w") as f:
        yaml.dump(data_model, f)


def _block(path):
    with open(path) as f:
        content = f.read()
    match = re.search(r"/\*\s*@bruin\s*\n(.*?)\n\s*@bruin\s*\*/", content, re.S)
    return yaml.safe_load(match.group(1))


def _columns(path):
    return {c["name"]: c for c in _block(path)["columns"]}


@pytest.fixture
def data_model_path(tmp_path):
    path = str(tmp_path / "data_model.yml")
    _write_data_model(path, DATA_MODEL)
    return path


@pytest.fixture
def adapter(bruin_pipeline, data_model_path):
    return BruinAdapter(
        pipeline_path=bruin_pipeline,
        data_model_path=data_model_path,
        asset_paths=[],
    )


@pytest.fixture
def writable_adapter(bruin_pipeline_copy, data_model_path):
    return BruinAdapter(
        pipeline_path=bruin_pipeline_copy,
        data_model_path=data_model_path,
        asset_paths=[],
    )


class TestInferRelationships:
    def test_reads_foreign_keys_as_relationships(self, adapter):
        relationships = adapter.infer_relationships()

        pairs = {(r["source"], r["target"]) for r in relationships}
        assert ("order", "customer") in pairs
        assert ("order", "product") in pairs

    def test_carries_the_joining_fields(self, adapter):
        relationship = next(
            r
            for r in adapter.infer_relationships()
            if (r["source"], r["target"]) == ("order", "customer")
        )

        assert relationship["source_field"] == "customer_id"
        assert relationship["target_field"] == "customer_id"
        assert relationship["source_model_name"] == "fct__order"
        assert relationship["target_model_name"] == "dim__customer"

    def test_resolves_a_dotted_foreign_key_target(self, adapter):
        """fct__order references core.dim__customer by its full name."""
        assert any(
            r["target"] == "customer" for r in adapter.infer_relationships()
        )

    def test_resolves_a_short_name_foreign_key_target(self, adapter):
        """fct__order references dim__product by its short name."""
        assert any(r["target"] == "product" for r in adapter.infer_relationships())

    def test_unbound_entities_excluded_by_default(self, bruin_pipeline, tmp_path):
        """With nothing bound, there is nothing to infer."""
        path = str(tmp_path / "data_model.yml")
        _write_data_model(path, {"entities": [], "relationships": []})
        adapter = BruinAdapter(
            pipeline_path=bruin_pipeline, data_model_path=path, asset_paths=[]
        )

        assert adapter.infer_relationships() == []

    def test_include_unbound_falls_back_to_asset_names(
        self, bruin_pipeline, tmp_path
    ):
        """Right after a bind, before the data model is persisted."""
        path = str(tmp_path / "data_model.yml")
        _write_data_model(path, {"entities": [], "relationships": []})
        adapter = BruinAdapter(
            pipeline_path=bruin_pipeline, data_model_path=path, asset_paths=[]
        )

        pairs = {
            (r["source"], r["target"])
            for r in adapter.infer_relationships(include_unbound=True)
        }
        assert ("fct__order", "dim__customer") in pairs

    def test_incomplete_foreign_key_is_skipped(self, tmp_path):
        """A foreign_key missing its column cannot be resolved."""
        assets = tmp_path / "pipeline" / "assets" / "core"
        assets.mkdir(parents=True)
        (assets / "a.sql").write_text(
            "/* @bruin\n"
            "name: core.a\n"
            "columns:\n"
            "  - name: b_id\n"
            "    foreign_key:\n"
            "      table: core.b\n"
            "@bruin */\n"
        )
        (assets / "b.sql").write_text("/* @bruin\nname: core.b\n@bruin */\n")

        adapter = BruinAdapter(
            pipeline_path=str(tmp_path / "pipeline"),
            data_model_path="",
            asset_paths=[],
        )

        assert adapter.infer_relationships(include_unbound=True) == []

    def test_foreign_key_to_unknown_asset_is_skipped(self, tmp_path):
        assets = tmp_path / "pipeline" / "assets" / "core"
        assets.mkdir(parents=True)
        (assets / "a.sql").write_text(
            "/* @bruin\n"
            "name: core.a\n"
            "columns:\n"
            "  - name: b_id\n"
            "    foreign_key:\n"
            "      table: core.missing\n"
            "      column: id\n"
            "@bruin */\n"
        )

        adapter = BruinAdapter(
            pipeline_path=str(tmp_path / "pipeline"),
            data_model_path="",
            asset_paths=[],
        )

        assert adapter.infer_relationships(include_unbound=True) == []

    def test_sees_assets_outside_configured_paths(self, bruin_pipeline, data_model_path):
        """A filtered model list must not hide a relationship target."""
        adapter = BruinAdapter(
            pipeline_path=bruin_pipeline,
            data_model_path=data_model_path,
            asset_paths=["02_core"],
        )

        assert len(adapter.infer_relationships()) == 2


class TestSyncRelationships:
    def _fct_path(self, adapter):
        return os.path.join(
            adapter.pipeline_path, "assets", "02_core", "fct__order.sql"
        )

    def test_writes_a_new_foreign_key(self, writable_adapter):
        updated = writable_adapter.sync_relationships(
            entities=DATA_MODEL["entities"],
            relationships=[
                {
                    "source": "order",
                    "target": "customer",
                    "source_field": "amount",
                    "target_field": "customer_id",
                }
            ],
        )

        assert updated
        columns = _columns(self._fct_path(writable_adapter))
        assert columns["amount"]["foreign_key"] == {
            "table": "core.dim__customer",
            "column": "customer_id",
        }

    def test_writes_the_targets_own_name_spelling(self, writable_adapter):
        """dim__product is bound by short name but declares itself dotted."""
        writable_adapter.sync_relationships(
            entities=DATA_MODEL["entities"],
            relationships=[
                {
                    "source": "order",
                    "target": "product",
                    "source_field": "amount",
                    "target_field": "product_id",
                }
            ],
        )

        columns = _columns(self._fct_path(writable_adapter))
        assert columns["amount"]["foreign_key"]["table"] == "core.dim__product"

    def test_prunes_a_removed_relationship(self, writable_adapter):
        """Entity model wins: no relationship means no foreign_key."""
        writable_adapter.sync_relationships(
            entities=DATA_MODEL["entities"], relationships=[]
        )

        columns = _columns(self._fct_path(writable_adapter))
        assert "foreign_key" not in columns["customer_id"]
        assert "foreign_key" not in columns["product_id"]

    def test_keeps_a_relationship_that_still_exists(self, writable_adapter):
        writable_adapter.sync_relationships(
            entities=DATA_MODEL["entities"],
            relationships=[
                {
                    "source": "order",
                    "target": "customer",
                    "source_field": "customer_id",
                    "target_field": "customer_id",
                }
            ],
        )

        columns = _columns(self._fct_path(writable_adapter))
        assert columns["customer_id"]["foreign_key"] == {
            "table": "core.dim__customer",
            "column": "customer_id",
        }
        # The other one was not in the payload, so it goes.
        assert "foreign_key" not in columns["product_id"]

    def test_round_trips_through_inference(self, writable_adapter):
        """What sync writes, inference must read back."""
        writable_adapter.sync_relationships(
            entities=DATA_MODEL["entities"],
            relationships=[
                {
                    "source": "order",
                    "target": "customer",
                    "source_field": "customer_id",
                    "target_field": "customer_id",
                }
            ],
        )

        inferred = writable_adapter.infer_relationships()

        assert len(inferred) == 1
        assert (inferred[0]["source"], inferred[0]["target"]) == ("order", "customer")
        assert inferred[0]["source_field"] == "customer_id"

    def test_adds_a_column_the_asset_does_not_declare(self, writable_adapter):
        """A relationship on an undocumented column must not be lost."""
        writable_adapter.sync_relationships(
            entities=DATA_MODEL["entities"],
            relationships=[
                {
                    "source": "order",
                    "target": "customer",
                    "source_field": "undocumented_id",
                    "target_field": "customer_id",
                }
            ],
        )

        columns = _columns(self._fct_path(writable_adapter))
        assert columns["undocumented_id"]["foreign_key"]["table"] == (
            "core.dim__customer"
        )

    def test_preserves_other_column_metadata(self, writable_adapter):
        writable_adapter.sync_relationships(
            entities=DATA_MODEL["entities"], relationships=[]
        )

        columns = _columns(self._fct_path(writable_adapter))
        assert columns["order_id"]["primary_key"] is True
        assert columns["amount"]["type"] == "double"
        assert columns["amount"]["description"] == "Order amount in EUR."

    def test_preserves_the_sql_body(self, writable_adapter):
        writable_adapter.sync_relationships(
            entities=DATA_MODEL["entities"], relationships=[]
        )

        with open(self._fct_path(writable_adapter)) as f:
            assert "FROM prep.prep__orders;" in f.read()

    def test_untouched_when_nothing_changes(self, writable_adapter):
        """A no-op sync must not rewrite files.

        Note product_id's foreign_key is written by hand as `dim__product` while
        sync would produce `core.dim__product`. Those name the same asset, so
        this must not count as a change — otherwise every sync would put a
        spurious diff in the user's pipeline.
        """
        updated = writable_adapter.sync_relationships(
            entities=DATA_MODEL["entities"],
            relationships=[
                {
                    "source": "order",
                    "target": "customer",
                    "source_field": "customer_id",
                    "target_field": "customer_id",
                },
                {
                    "source": "order",
                    "target": "product",
                    "source_field": "product_id",
                    "target_field": "product_id",
                },
            ],
        )

        assert updated == []

    def test_never_touches_an_unbound_asset(self, writable_adapter, tmp_path):
        """An asset Trellis knows nothing about is left alone."""
        path = str(tmp_path / "partial_model.yml")
        _write_data_model(
            path,
            {"entities": [{"id": "order", "model_ref": "core.fct__order"}]},
        )
        writable_adapter.data_model_path = path

        before = open(
            os.path.join(
                writable_adapter.pipeline_path,
                "assets",
                "02_core",
                "dim__customer.sql",
            )
        ).read()

        writable_adapter.sync_relationships(
            entities=[{"id": "order", "model_ref": "core.fct__order"}],
            relationships=[],
        )

        after = open(
            os.path.join(
                writable_adapter.pipeline_path,
                "assets",
                "02_core",
                "dim__customer.sql",
            )
        ).read()
        assert before == after

    def test_relationship_naming_an_unbound_entity_is_skipped(self, writable_adapter):
        updated = writable_adapter.sync_relationships(
            entities=DATA_MODEL["entities"],
            relationships=[
                {
                    "source": "order",
                    "target": "not_an_entity",
                    "source_field": "amount",
                    "target_field": "id",
                },
                {
                    "source": "order",
                    "target": "customer",
                    "source_field": "customer_id",
                    "target_field": "customer_id",
                },
                {
                    "source": "order",
                    "target": "product",
                    "source_field": "product_id",
                    "target_field": "product_id",
                },
            ],
        )

        # Only the unresolvable one was dropped, so nothing else changed.
        assert updated == []
        assert "foreign_key" not in _columns(self._fct_path(writable_adapter))["amount"]
