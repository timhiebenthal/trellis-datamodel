"""
Tests for BruinAdapter.save_schema_file — pushing drafted fields to Bruin.

Bruin has no sidecar schema file, so "save the schema" means editing the asset's
@bruin block. When the entity has no asset yet, one is scaffolded with a
deliberately non-runnable placeholder body: Trellis cannot know the query.
"""

import os
import re

import pytest
import yaml

from trellis_datamodel.adapters.bruin import BruinAdapter
from trellis_datamodel.utils.bruin_parser import parse_bruin_block


FIELDS = [
    {"name": "region_id", "data_type": "varchar", "description": "Region key"},
    {"name": "region_name", "data_type": "varchar", "description": "Region name"},
]


def _block(path):
    with open(path) as f:
        content = f.read()
    match = re.search(r"/\*\s*@bruin\s*\n(.*?)\n\s*@bruin\s*\*/", str(content), re.S)
    return yaml.safe_load(match.group(1))


@pytest.fixture
def data_model_path(tmp_path):
    path = str(tmp_path / "data_model.yml")
    with open(path, "w") as f:
        yaml.dump(
            {
                "entities": [
                    {
                        "id": "region",
                        "label": "Region",
                        "description": "Sales region.",
                    },
                    {
                        "id": "customer",
                        "label": "Customer",
                        "model_ref": "core.dim__customer",
                    },
                ]
            },
            f,
        )
    return path


@pytest.fixture
def adapter(bruin_pipeline_copy, data_model_path):
    return BruinAdapter(
        pipeline_path=bruin_pipeline_copy,
        data_model_path=data_model_path,
        asset_paths=[],
    )


class TestScaffoldingANewAsset:
    def test_creates_the_asset_file(self, adapter):
        path = adapter.save_schema_file(
            entity_id="region", model_name="core.dim__region", fields=FIELDS
        )

        assert os.path.exists(path)
        assert str(path).endswith("dim__region.sql")

    def test_block_declares_name_and_type(self, adapter):
        path = adapter.save_schema_file(
            entity_id="region", model_name="core.dim__region", fields=FIELDS
        )

        block = _block(path)
        assert block["name"] == "core.dim__region"
        assert block["type"] == "duckdb.sql"

    def test_asset_type_comes_from_config(self, bruin_pipeline_copy, data_model_path):
        """The type is platform-specific, so it cannot be guessed."""
        adapter = BruinAdapter(
            pipeline_path=bruin_pipeline_copy,
            data_model_path=data_model_path,
            asset_paths=[],
            default_asset_type="bq.sql",
        )

        path = adapter.save_schema_file(
            entity_id="region", model_name="core.dim__region", fields=FIELDS
        )

        assert _block(path)["type"] == "bq.sql"

    def test_drafted_fields_become_columns(self, adapter):
        path = adapter.save_schema_file(
            entity_id="region", model_name="core.dim__region", fields=FIELDS
        )

        columns = {c["name"]: c for c in _block(path)["columns"]}
        assert set(columns) == {"region_id", "region_name"}
        assert columns["region_id"]["type"] == "varchar"
        assert columns["region_id"]["description"] == "Region key"

    def test_description_falls_back_to_the_entity(self, adapter):
        path = adapter.save_schema_file(
            entity_id="region", model_name="core.dim__region", fields=FIELDS
        )

        assert _block(path)["description"] == "Sales region."

    def test_explicit_description_wins(self, adapter):
        path = adapter.save_schema_file(
            entity_id="region",
            model_name="core.dim__region",
            fields=FIELDS,
            description="Explicit",
        )

        assert _block(path)["description"] == "Explicit"

    def test_tags_are_written(self, adapter):
        path = adapter.save_schema_file(
            entity_id="region",
            model_name="core.dim__region",
            fields=FIELDS,
            tags=["core"],
        )

        assert _block(path)["tags"] == ["core"]

    def test_body_is_an_obvious_placeholder(self, adapter):
        """The user has to write the query; make that unmistakable."""
        path = adapter.save_schema_file(
            entity_id="region", model_name="core.dim__region", fields=FIELDS
        )

        with open(path) as f:
            body = f.read()

        assert "TODO" in body
        assert "core.dim__region" in body
        # Never silently produce something that looks like a finished model.
        assert "placeholder" in body.lower()

    def test_scaffolded_asset_is_parseable(self, adapter):
        """A scaffold Trellis cannot read back would be worse than none."""
        path = adapter.save_schema_file(
            entity_id="region", model_name="core.dim__region", fields=FIELDS
        )

        asset = parse_bruin_block(str(path))
        assert asset is not None
        assert asset.name == "core.dim__region"
        assert [c["name"] for c in asset.columns] == ["region_id", "region_name"]

    def test_scaffolded_asset_appears_in_get_models(self, adapter):
        adapter.save_schema_file(
            entity_id="region", model_name="core.dim__region", fields=FIELDS
        )

        assert "dim__region" in [m["name"] for m in adapter.get_models()]

    def test_lands_in_the_first_configured_asset_path(
        self, bruin_pipeline_copy, data_model_path
    ):
        """Otherwise the scaffold would sit where Trellis is not looking."""
        adapter = BruinAdapter(
            pipeline_path=bruin_pipeline_copy,
            data_model_path=data_model_path,
            asset_paths=["02_core", "01_prep"],
        )

        path = adapter.save_schema_file(
            entity_id="region", model_name="core.dim__region", fields=FIELDS
        )

        assert os.path.join("assets", "02_core", "dim__region.sql") in str(path)
        assert "dim__region" in [m["name"] for m in adapter.get_models()]

    def test_lands_directly_under_assets_when_unfiltered(self, adapter):
        path = adapter.save_schema_file(
            entity_id="region", model_name="core.dim__region", fields=FIELDS
        )

        assert str(path).endswith(os.path.join("assets", "dim__region.sql"))

    def test_short_model_name_scaffolds_too(self, adapter):
        path = adapter.save_schema_file(
            entity_id="region", model_name="dim__region", fields=FIELDS
        )

        assert _block(path)["name"] == "dim__region"

    def test_fields_without_a_name_are_skipped(self, adapter):
        path = adapter.save_schema_file(
            entity_id="region",
            model_name="core.dim__region",
            fields=[{"data_type": "varchar"}, FIELDS[0]],
        )

        assert [c["name"] for c in _block(path)["columns"]] == ["region_id"]


class TestMergingIntoAnExistingAsset:
    def test_does_not_scaffold_when_the_asset_exists(self, adapter):
        path = adapter.save_schema_file(
            entity_id="customer",
            model_name="core.dim__customer",
            fields=[{"name": "segment", "data_type": "varchar"}],
        )

        assert str(path).endswith(os.path.join("02_core", "dim__customer.sql"))

    def test_merges_the_new_column(self, adapter):
        path = adapter.save_schema_file(
            entity_id="customer",
            model_name="core.dim__customer",
            fields=[
                {"name": "customer_id", "data_type": "varchar"},
                {"name": "segment", "data_type": "varchar"},
            ],
        )

        columns = {c["name"]: c for c in _block(path)["columns"]}
        assert "segment" in columns

    def test_keeps_bruin_owned_column_metadata(self, adapter):
        path = adapter.save_schema_file(
            entity_id="customer",
            model_name="core.dim__customer",
            fields=[{"name": "customer_id", "data_type": "varchar"}],
        )

        columns = {c["name"]: c for c in _block(path)["columns"]}
        assert columns["customer_id"]["primary_key"] is True
        assert columns["customer_id"]["checks"] == [
            {"name": "unique"},
            {"name": "not_null"},
        ]

    def test_does_not_touch_the_sql_body(self, adapter):
        path = adapter.save_schema_file(
            entity_id="customer",
            model_name="core.dim__customer",
            fields=[{"name": "segment", "data_type": "varchar"}],
        )

        with open(path) as f:
            assert "FROM prep.prep__customers;" in f.read()

    def test_matches_an_existing_asset_by_short_name(self, adapter):
        path = adapter.save_schema_file(
            entity_id="customer",
            model_name="dim__customer",
            fields=[{"name": "segment", "data_type": "varchar"}],
        )

        # Merged into the existing asset rather than scaffolding a duplicate.
        assert str(path).endswith(os.path.join("02_core", "dim__customer.sql"))

    def test_tags_are_unioned_on_merge(self, adapter):
        path = adapter.save_schema_file(
            entity_id="customer",
            model_name="core.dim__customer",
            fields=[],
            tags=["reviewed"],
        )

        assert _block(path)["tags"] == ["core", "entity", "reviewed"]


class TestScaffoldingSafety:
    def test_never_overwrites_an_existing_file(self, adapter):
        """A name collision with an asset that has no @bruin block must not clobber it."""
        assets_dir = os.path.join(adapter.pipeline_path, "assets")
        colliding = os.path.join(assets_dir, "dim__region.sql")
        os.makedirs(assets_dir, exist_ok=True)
        with open(colliding, "w") as f:
            f.write("SELECT 'precious hand-written SQL';\n")

        with pytest.raises(FileExistsError):
            adapter.save_schema_file(
                entity_id="region", model_name="core.dim__region", fields=FIELDS
            )

        with open(colliding) as f:
            assert "precious hand-written SQL" in f.read()
