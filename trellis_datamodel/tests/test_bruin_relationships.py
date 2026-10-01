"""
Tests for BruinAdapter relationship inference and sync.

Bruin declares references natively as `columns[].foreign_key: {table, column}`,
so relationships round-trip: inference reads them and sync writes them.

Sync prunes like dbt: a foreign_key is removed only from a column that is an
end of a payload relationship but no longer holds that relationship's key.
Foreign keys on any other column, including hand-written ones, are kept.
"""

import os
import re

import pytest
import yaml

from trellis_datamodel.adapters.bruin import BruinAdapter
from trellis_datamodel.services.fk_placement import place_foreign_key


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
        assert ("customer", "order") in pairs
        assert ("product", "order") in pairs

    def test_carries_the_joining_fields(self, adapter):
        relationship = next(
            r
            for r in adapter.infer_relationships()
            if (r["source"], r["target"]) == ("customer", "order")
        )

        assert relationship["source_field"] == "customer_id"
        assert relationship["target_field"] == "customer_id"
        assert relationship["source_model_name"] == "dim__customer"
        assert relationship["target_model_name"] == "fct__order"

    def test_resolves_a_dotted_foreign_key_target(self, adapter):
        """fct__order references core.dim__customer by its full name."""
        assert any(
            r["source"] == "customer" for r in adapter.infer_relationships()
        )

    def test_resolves_a_short_name_foreign_key_target(self, adapter):
        """fct__order references dim__product by its short name."""
        assert any(r["source"] == "product" for r in adapter.infer_relationships())

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
        assert ("dim__customer", "fct__order") in pairs

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
                    "type": "one_to_many",
                    "source": "customer",
                    "target": "order",
                    "source_field": "customer_id",
                    "target_field": "amount",
                }
            ],
        )

        assert updated
        columns = _columns(self._fct_path(writable_adapter))
        assert columns["amount"]["foreign_key"] == {
            "table": "core.dim__customer",
            "column": "customer_id",
        }

    def test_one_to_many_places_fk_on_target_asset(self, writable_adapter):
        writable_adapter.sync_relationships(
            entities=DATA_MODEL["entities"],
            relationships=[
                {
                    "type": "one_to_many",
                    "source": "customer",
                    "target": "order",
                    "source_field": "customer_id",
                    "target_field": "amount",
                }
            ],
        )

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
                    "type": "one_to_many",
                    "source": "product",
                    "target": "order",
                    "source_field": "product_id",
                    "target_field": "amount",
                }
            ],
        )

        columns = _columns(self._fct_path(writable_adapter))
        assert columns["amount"]["foreign_key"]["table"] == "core.dim__product"

    def test_does_not_prune_foreign_keys_when_the_payload_has_no_relationships(
        self, writable_adapter
    ):
        """Like dbt: a column in no payload relationship is not managed."""
        writable_adapter.sync_relationships(
            entities=DATA_MODEL["entities"], relationships=[]
        )

        columns = _columns(self._fct_path(writable_adapter))
        assert columns["customer_id"]["foreign_key"] == {
            "table": "core.dim__customer",
            "column": "customer_id",
        }
        assert columns["product_id"]["foreign_key"] == {
            "table": "dim__product",
            "column": "product_id",
        }

    def test_does_not_prune_a_foreign_key_whose_relationship_left_the_payload(
        self, writable_adapter
    ):
        writable_adapter.sync_relationships(
            entities=DATA_MODEL["entities"],
            relationships=[
                {
                    "type": "one_to_many",
                    "source": "customer",
                    "target": "order",
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
        # Not in the payload, so not managed: kept exactly as written.
        assert columns["product_id"]["foreign_key"] == {
            "table": "dim__product",
            "column": "product_id",
        }

    def test_keeps_a_hand_written_foreign_key_to_an_unbound_asset(
        self, writable_adapter
    ):
        """dim__product has no entity, so Trellis never created its key."""
        entities = [e for e in DATA_MODEL["entities"] if e["id"] != "product"]

        writable_adapter.sync_relationships(
            entities=entities,
            relationships=[
                {
                    "type": "one_to_many",
                    "source": "customer",
                    "target": "order",
                    "source_field": "customer_id",
                    "target_field": "customer_id",
                }
            ],
        )

        assert _columns(self._fct_path(writable_adapter))["product_id"][
            "foreign_key"
        ] == {"table": "dim__product", "column": "product_id"}

    def test_keeps_a_foreign_key_to_a_bound_asset_outside_the_payload(
        self, writable_adapter
    ):
        """customer_id -> core.dim__customer is in no payload relationship."""
        writable_adapter.sync_relationships(
            entities=DATA_MODEL["entities"],
            relationships=[
                {
                    "type": "one_to_many",
                    "source": "product",
                    "target": "order",
                    "source_field": "product_id",
                    "target_field": "product_id",
                }
            ],
        )

        assert _columns(self._fct_path(writable_adapter))["customer_id"][
            "foreign_key"
        ] == {"table": "core.dim__customer", "column": "customer_id"}

    def test_keeps_the_fk_column_of_a_relationship_naming_an_unbound_entity(
        self, writable_adapter
    ):
        """The placement still claims product_id, so it is not stale.

        Bruin cannot write a reference to an asset no entity is bound to, but
        the key already there is the one the relationship describes.
        """
        entities = [e for e in DATA_MODEL["entities"] if e["id"] != "product"]

        writable_adapter.sync_relationships(
            entities=entities,
            relationships=[
                {
                    "type": "one_to_many",
                    "source": "product",
                    "target": "order",
                    "source_field": "product_id",
                    "target_field": "product_id",
                }
            ],
        )

        assert _columns(self._fct_path(writable_adapter))["product_id"][
            "foreign_key"
        ] == {"table": "dim__product", "column": "product_id"}

    def test_prunes_a_stale_foreign_key_on_a_managed_column(self, writable_adapter):
        """many_to_one moves the key to dim__customer; the old one goes."""
        writable_adapter.sync_relationships(
            entities=DATA_MODEL["entities"],
            relationships=[
                {
                    "type": "many_to_one",
                    "source": "customer",
                    "target": "order",
                    "source_field": "customer_id",
                    "target_field": "customer_id",
                }
            ],
        )

        dim_path = writable_adapter._find_asset("core.dim__customer").file_path
        assert _columns(dim_path)["customer_id"]["foreign_key"] == {
            "table": "core.fct__order",
            "column": "customer_id",
        }
        fct_columns = _columns(self._fct_path(writable_adapter))
        assert "foreign_key" not in fct_columns["customer_id"]
        # Unrelated to the payload, so it stays.
        assert fct_columns["product_id"]["foreign_key"]["table"] == "dim__product"

    def test_round_trips_through_inference(self, writable_adapter):
        """What sync writes, inference must read back."""
        writable_adapter.sync_relationships(
            entities=DATA_MODEL["entities"],
            relationships=[
                {
                    "type": "one_to_many",
                    "source": "customer",
                    "target": "order",
                    "source_field": "customer_id",
                    "target_field": "customer_id",
                }
            ],
        )

        # product_id's key is outside the payload, so it is kept and read back too.
        inferred = [
            r
            for r in writable_adapter.infer_relationships()
            if "customer" in (r["source"], r["target"])
        ]

        assert len(inferred) == 1
        assert (inferred[0]["source"], inferred[0]["target"]) == ("customer", "order")
        assert inferred[0]["source_field"] == "customer_id"
        assert inferred[0]["target_field"] == "customer_id"

    def test_adds_a_column_the_asset_does_not_declare(self, writable_adapter):
        """A relationship on an undocumented column must not be lost."""
        writable_adapter.sync_relationships(
            entities=DATA_MODEL["entities"],
            relationships=[
                {
                    "type": "one_to_many",
                    "source": "customer",
                    "target": "order",
                    "source_field": "customer_id",
                    "target_field": "undocumented_id",
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
                    "type": "one_to_many",
                    "source": "customer",
                    "target": "order",
                    "source_field": "customer_id",
                    "target_field": "customer_id",
                },
                {
                    "type": "one_to_many",
                    "source": "product",
                    "target": "order",
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
                    "type": "one_to_many",
                    "source": "not_an_entity",
                    "target": "order",
                    "source_field": "id",
                    "target_field": "amount",
                },
                {
                    "type": "one_to_many",
                    "source": "customer",
                    "target": "order",
                    "source_field": "customer_id",
                    "target_field": "customer_id",
                },
                {
                    "type": "one_to_many",
                    "source": "product",
                    "target": "order",
                    "source_field": "product_id",
                    "target_field": "product_id",
                },
            ],
        )

        # Only the unresolvable one was dropped, so nothing else changed.
        assert updated == []
        assert "foreign_key" not in _columns(self._fct_path(writable_adapter))["amount"]

    def test_push_then_pull_returns_the_same_single_edge(self, writable_adapter):
        """A canvas edge customer -> order must come back as itself, once."""
        edge = {
            "type": "one_to_many",
            "source": "customer",
            "target": "order",
            "source_field": "customer_id",
            "target_field": "customer_id",
        }
        writable_adapter.sync_relationships(
            entities=DATA_MODEL["entities"], relationships=[edge]
        )

        dim_path = writable_adapter._find_asset("core.dim__customer").file_path
        assert "foreign_key" not in _columns(dim_path)["customer_id"]
        assert _columns(self._fct_path(writable_adapter))["customer_id"][
            "foreign_key"
        ] == {"table": "core.dim__customer", "column": "customer_id"}

        # product_id's key is outside the payload, so it is kept; leave it out.
        inferred = writable_adapter.infer_relationships()
        assert [
            (r["source"], r["target"], r["source_field"], r["target_field"])
            for r in inferred
            if "customer" in (r["source"], r["target"])
        ] == [("customer", "order", "customer_id", "customer_id")]


# The asset each entity in DATA_MODEL is bound to, by its declared name.
_ASSET_OF = {"customer": "core.dim__customer", "order": "core.fct__order"}


@pytest.mark.parametrize(
    "rel_type",
    [
        "one_to_many",
        "one_to_zero_or_many",
        "zero_or_one_to_many",
        "zero_or_many_to_many",
        "many_to_one",
        "many_to_many",
        "zero_or_many_to_one",
        "one_to_one",
        "unknown_type",
        "",
    ],
)
def test_push_places_fk_where_the_shared_rule_says(writable_adapter, rel_type):
    """Bruin push follows `place_foreign_key`, exactly like dbt."""
    writable_adapter.sync_relationships(
        entities=DATA_MODEL["entities"],
        relationships=[
            {
                "type": rel_type,
                "source": "customer",
                "target": "order",
                "source_field": "src_key",
                "target_field": "tgt_key",
            }
        ],
    )

    placement = place_foreign_key(
        rel_type, "customer", "src_key", "order", "tgt_key"
    )
    fk_path = writable_adapter._find_asset(_ASSET_OF[placement.fk_entity]).file_path
    ref_path = writable_adapter._find_asset(_ASSET_OF[placement.ref_entity]).file_path

    assert _columns(fk_path)[placement.fk_field]["foreign_key"] == {
        "table": _ASSET_OF[placement.ref_entity],
        "column": placement.ref_field,
    }
    assert placement.ref_field not in _columns(ref_path)


def test_infer_emits_the_dbt_convention(tmp_path):
    """source = referenced asset, target = FK holder, fields to match."""
    assets = tmp_path / "pipeline" / "assets" / "core"
    assets.mkdir(parents=True)
    (assets / "a.sql").write_text(
        "/* @bruin\n"
        "name: core.a\n"
        "columns:\n"
        "  - name: b_id\n"
        "    foreign_key:\n"
        "      table: core.b\n"
        "      column: id\n"
        "@bruin */\n"
    )
    (assets / "b.sql").write_text(
        "/* @bruin\nname: core.b\ncolumns:\n  - name: id\n@bruin */\n"
    )
    adapter = BruinAdapter(
        pipeline_path=str(tmp_path / "pipeline"),
        data_model_path="",
        asset_paths=[],
    )

    assert adapter.infer_relationships(include_unbound=True) == [
        {
            "source": "b",
            "target": "a",
            "label": "",
            "type": "one_to_many",
            "source_field": "id",
            "target_field": "b_id",
            "source_model_name": "b",
            "source_model_version": None,
            "target_model_name": "a",
            "target_model_version": None,
        }
    ]


def test_removing_trellis_tag_removes_it_from_the_bruin_block_on_next_push(
    writable_adapter,
):
    """Mirror of the dbt end-to-end: push ui_tags, drop one, push again."""
    customer = {
        "id": "customer",
        "label": "Customer",
        "model_ref": "core.dim__customer",
        "ui_tags": ["pii"],
    }
    asset_path = writable_adapter._find_asset("core.dim__customer").file_path

    writable_adapter.sync_relationships([customer], [])
    assert _block(asset_path)["tags"] == ["core", "entity", "pii"]

    customer["ui_tags"] = []
    writable_adapter.sync_relationships([customer], [])
    assert _block(asset_path)["tags"] == ["core", "entity"]
