"""
Tests for BruinAdapter's model and schema surface.

Read paths run against the committed fixture pipeline; write paths run against
a per-test copy of it so the fixture stays pristine. Lineage, relationships,
and scaffolding have their own files.
"""

import os

import pytest
import yaml

from trellis_datamodel.adapters.bruin import BruinAdapter
from trellis_datamodel.utils.bruin_parser import parse_bruin_block


@pytest.fixture
def adapter(bruin_pipeline, tmp_path):
    """Read-only adapter over the fixture pipeline, all asset paths."""
    return BruinAdapter(
        pipeline_path=bruin_pipeline,
        data_model_path=str(tmp_path / "data_model.yml"),
        asset_paths=[],
    )


@pytest.fixture
def writable_adapter(bruin_pipeline_copy, tmp_path):
    """Adapter over a writable copy, for anything that rewrites assets."""
    return BruinAdapter(
        pipeline_path=bruin_pipeline_copy,
        data_model_path=str(tmp_path / "data_model.yml"),
        asset_paths=[],
    )


class TestGetModels:
    def test_returns_every_parseable_asset(self, adapter):
        names = [m["name"] for m in adapter.get_models()]

        assert names == [
            "dim__customer",
            "dim__product",
            "fct__order",
            "prep__customers",
            "prep__orders",
            "raw__customers",
            "raw__orders",
        ]

    def test_splits_dotted_name_into_schema_and_table(self, adapter):
        models = {m["name"]: m for m in adapter.get_models()}

        assert models["dim__customer"]["unique_id"] == "core.dim__customer"
        assert models["dim__customer"]["schema"] == "core"
        assert models["dim__customer"]["table"] == "dim__customer"

    def test_undotted_name_has_empty_schema(self, tmp_path):
        assets = tmp_path / "pipeline" / "assets"
        assets.mkdir(parents=True)
        (assets / "flat.sql").write_text("/* @bruin\nname: flat\n@bruin */\n")

        adapter = BruinAdapter(
            pipeline_path=str(tmp_path / "pipeline"),
            data_model_path="",
            asset_paths=[],
        )

        model = adapter.get_models()[0]
        assert model["schema"] == ""
        assert model["name"] == "flat"

    def test_carries_columns_description_and_tags(self, adapter):
        models = {m["name"]: m for m in adapter.get_models()}
        dim = models["dim__customer"]

        assert dim["description"] == "One row per customer."
        assert dim["tags"] == ["core", "entity"]
        assert [c["name"] for c in dim["columns"]] == ["customer_id", "customer_name"]
        assert dim["columns"][0]["type"] == "varchar"

    def test_materialization_from_block(self, adapter):
        models = {m["name"]: m for m in adapter.get_models()}

        assert models["dim__customer"]["materialization"] == "table"
        assert models["prep__customers"]["materialization"] == "view"
        # No materialization declared at all.
        assert models["raw__customers"]["materialization"] == ""

    def test_respects_asset_paths_filter(self, bruin_pipeline, tmp_path):
        adapter = BruinAdapter(
            pipeline_path=bruin_pipeline,
            data_model_path=str(tmp_path / "data_model.yml"),
            asset_paths=["02_core"],
        )

        assert [m["name"] for m in adapter.get_models()] == [
            "dim__customer",
            "dim__product",
            "fct__order",
        ]

    def test_missing_pipeline_yields_no_models(self, tmp_path):
        adapter = BruinAdapter(
            pipeline_path=str(tmp_path / "nope"),
            data_model_path="",
            asset_paths=[],
        )

        assert adapter.get_models() == []


class TestGetModelSchema:
    def test_by_short_name(self, adapter):
        schema = adapter.get_model_schema("dim__customer")

        assert schema["model_name"] == "dim__customer"
        assert schema["description"] == "One row per customer."
        assert schema["tags"] == ["core", "entity"]

    def test_by_fully_qualified_name(self, adapter):
        """An entity binding may hold either spelling."""
        schema = adapter.get_model_schema("core.dim__customer")

        assert schema["model_name"] == "dim__customer"

    def test_columns_use_protocol_spelling(self, adapter):
        columns = {c["name"]: c for c in adapter.get_model_schema("dim__customer")["columns"]}

        # Bruin's `type` is surfaced as the protocol's `data_type`.
        assert columns["customer_id"]["data_type"] == "varchar"
        assert columns["customer_id"]["description"] == "Surrogate key for the customer."

    def test_checks_surface_as_data_tests(self, adapter):
        columns = {c["name"]: c for c in adapter.get_model_schema("dim__customer")["columns"]}

        assert columns["customer_id"]["data_tests"] == [
            {"name": "unique"},
            {"name": "not_null"},
        ]

    def test_bruin_owned_metadata_is_surfaced(self, adapter):
        """primary_key and foreign_key must survive a read so a save can keep them."""
        dim = {c["name"]: c for c in adapter.get_model_schema("dim__customer")["columns"]}
        fct = {c["name"]: c for c in adapter.get_model_schema("fct__order")["columns"]}

        assert dim["customer_id"]["primary_key"] is True
        assert fct["customer_id"]["foreign_key"] == {
            "table": "core.dim__customer",
            "column": "customer_id",
        }

    def test_unknown_model_raises(self, adapter):
        with pytest.raises(ValueError, match="not found in pipeline assets"):
            adapter.get_model_schema("nope")

    def test_version_argument_is_accepted_and_ignored(self, adapter):
        """Bruin has no model versioning; the protocol still passes a version."""
        assert adapter.get_model_schema("dim__customer", version=2)["model_name"] == (
            "dim__customer"
        )

    def test_finds_asset_outside_configured_asset_paths(
        self, bruin_pipeline, tmp_path
    ):
        """A binding may point at an asset the path filter excludes."""
        adapter = BruinAdapter(
            pipeline_path=bruin_pipeline,
            data_model_path=str(tmp_path / "data_model.yml"),
            asset_paths=["02_core"],
        )

        assert adapter.get_model_schema("prep__customers")["model_name"] == (
            "prep__customers"
        )


class TestSaveModelSchema:
    def _block(self, path):
        with open(path) as f:
            content = f.read()
        import re

        match = re.search(r"/\*\s*@bruin\s*\n(.*?)\n\s*@bruin\s*\*/", content, re.S)
        return yaml.safe_load(match.group(1))

    def test_updates_description(self, writable_adapter):
        path = writable_adapter.save_model_schema(
            "dim__customer", columns=[], description="Updated description"
        )

        assert self._block(path)["description"] == "Updated description"

    def test_preserves_sql_body(self, writable_adapter):
        path = writable_adapter.save_model_schema(
            "dim__customer", columns=[], description="Updated"
        )

        with open(path) as f:
            assert "FROM prep.prep__customers;" in f.read()

    def test_adds_a_column(self, writable_adapter):
        path = writable_adapter.save_model_schema(
            "dim__customer",
            columns=[
                {"name": "customer_id", "data_type": "varchar"},
                {"name": "customer_name", "data_type": "varchar"},
                {"name": "segment", "data_type": "varchar", "description": "Segment"},
            ],
        )

        columns = {c["name"]: c for c in self._block(path)["columns"]}
        assert set(columns) == {"customer_id", "customer_name", "segment"}
        assert columns["segment"]["type"] == "varchar"

    def test_keeps_bruin_metadata_trellis_does_not_send(self, writable_adapter):
        """A schema push must not strip primary_key/checks it never knew about."""
        path = writable_adapter.save_model_schema(
            "dim__customer",
            columns=[
                {"name": "customer_id", "data_type": "varchar"},
                {"name": "customer_name", "data_type": "varchar"},
            ],
        )

        columns = {c["name"]: c for c in self._block(path)["columns"]}
        assert columns["customer_id"]["primary_key"] is True
        assert columns["customer_id"]["checks"] == [
            {"name": "unique"},
            {"name": "not_null"},
        ]

    def test_keeps_foreign_key_on_unrelated_schema_push(self, writable_adapter):
        path = writable_adapter.save_model_schema(
            "fct__order",
            columns=[
                {"name": "order_id", "data_type": "varchar"},
                {"name": "customer_id", "data_type": "varchar"},
            ],
        )

        columns = {c["name"]: c for c in self._block(path)["columns"]}
        assert columns["customer_id"]["foreign_key"] == {
            "table": "core.dim__customer",
            "column": "customer_id",
        }

    def test_data_tests_are_written_as_checks(self, writable_adapter):
        path = writable_adapter.save_model_schema(
            "dim__customer",
            columns=[
                {
                    "name": "customer_name",
                    "data_type": "varchar",
                    "data_tests": [{"name": "not_null"}],
                }
            ],
        )

        columns = {c["name"]: c for c in self._block(path)["columns"]}
        assert columns["customer_name"]["checks"] == [{"name": "not_null"}]

    def test_tags_are_unioned_not_replaced(self, writable_adapter):
        """Incoming tags are Trellis additions, matching the dbt adapter."""
        path = writable_adapter.save_model_schema(
            "dim__customer", columns=[], tags=["reviewed"]
        )

        assert self._block(path)["tags"] == ["core", "entity", "reviewed"]

    def test_tags_are_not_duplicated(self, writable_adapter):
        path = writable_adapter.save_model_schema(
            "dim__customer", columns=[], tags=["core"]
        )

        assert self._block(path)["tags"] == ["core", "entity"]

    def test_round_trips_through_the_parser(self, writable_adapter):
        """The write must produce something the reader still understands."""
        path = writable_adapter.save_model_schema(
            "dim__customer", columns=[], description="Round trip"
        )

        asset = parse_bruin_block(str(path))
        assert asset is not None
        assert asset.name == "core.dim__customer"
        assert asset.description == "Round trip"
        assert asset.depends == ["prep.prep__customers"]

    def test_python_asset_is_writable(self, writable_adapter):
        """Bruin's Python assets use docstring delimiters, not SQL comments."""
        path = writable_adapter.save_model_schema(
            "raw__customers", columns=[], description="Now documented"
        )

        asset = parse_bruin_block(str(path))
        assert asset.description == "Now documented"
        with open(path) as f:
            assert "import pandas as pd" in f.read()


class TestGetModelDirs:
    def test_unfiltered_returns_assets_root(self, adapter, bruin_pipeline):
        assert adapter.get_model_dirs() == [
            os.path.abspath(os.path.join(bruin_pipeline, "assets"))
        ]

    def test_filtered_returns_each_configured_path(self, bruin_pipeline):
        adapter = BruinAdapter(
            pipeline_path=bruin_pipeline,
            data_model_path="",
            asset_paths=["01_prep", "02_core"],
        )

        assets = os.path.join(bruin_pipeline, "assets")
        assert adapter.get_model_dirs() == [
            os.path.abspath(os.path.join(assets, "01_prep")),
            os.path.abspath(os.path.join(assets, "02_core")),
        ]

    def test_duplicate_paths_are_collapsed(self, bruin_pipeline):
        adapter = BruinAdapter(
            pipeline_path=bruin_pipeline,
            data_model_path="",
            asset_paths=["02_core", "02_core"],
        )

        assert len(adapter.get_model_dirs()) == 1


class TestGetProjectStatus:
    def test_healthy_pipeline(self, adapter, bruin_pipeline):
        status = adapter.get_project_status()

        assert status["framework"] == "bruin"
        assert status["artifacts_present"] is True
        assert status["project_path"] == bruin_pipeline
        assert status["project_path_exists"] is True
        assert status["error"] is None

    def test_reports_pipeline_and_assets_artifacts(self, adapter):
        artifacts = adapter.get_project_status()["artifacts"]

        assert artifacts["pipeline"]["exists"] is True
        assert artifacts["pipeline"]["path"].endswith("pipeline.yml")
        assert artifacts["assets"]["exists"] is True

    def test_declares_bruin_capabilities(self, adapter):
        capabilities = adapter.get_project_status()["capabilities"]

        assert capabilities["lineage"] is True
        assert capabilities["relationships"] is True
        assert capabilities["scaffolding"] is True
        # Bruin has neither concept; the frontend gates on these, not on the
        # framework name.
        assert capabilities["exposures"] is False
        assert capabilities["column_lineage"] is False

    def test_unset_pipeline_path_is_an_error(self, tmp_path):
        adapter = BruinAdapter(
            pipeline_path="", data_model_path="", asset_paths=[]
        )

        status = adapter.get_project_status()
        assert status["artifacts_present"] is False
        assert "bruin_pipeline_path not set" in status["error"]

    def test_missing_pipeline_is_an_error(self, tmp_path):
        adapter = BruinAdapter(
            pipeline_path=str(tmp_path / "nope"), data_model_path="", asset_paths=[]
        )

        assert "Pipeline not found" in adapter.get_project_status()["error"]

    def test_missing_assets_dir_is_an_error(self, tmp_path):
        (tmp_path / "pipeline").mkdir()
        adapter = BruinAdapter(
            pipeline_path=str(tmp_path / "pipeline"),
            data_model_path="",
            asset_paths=[],
        )

        assert "No assets directory" in adapter.get_project_status()["error"]

    def test_empty_assets_dir_is_an_error(self, tmp_path):
        (tmp_path / "pipeline" / "assets").mkdir(parents=True)
        adapter = BruinAdapter(
            pipeline_path=str(tmp_path / "pipeline"),
            data_model_path="",
            asset_paths=[],
        )

        status = adapter.get_project_status()
        assert status["artifacts_present"] is False
        assert "No assets with an @bruin block" in status["error"]


class TestGetExposures:
    def test_bruin_has_no_exposures(self, adapter):
        """Empty, and capabilities say why — not an exception at the call site."""
        assert adapter.get_exposures() == []
        assert adapter.get_project_status()["capabilities"]["exposures"] is False


class TestInferEntityTypes:
    def test_returns_empty_when_dimensional_modeling_disabled(
        self, adapter, monkeypatch
    ):
        from trellis_datamodel import config as cfg

        monkeypatch.setattr(
            cfg.DIMENSIONAL_MODELING_CONFIG, "enabled", False, raising=False
        )

        assert adapter.infer_entity_types() == {}

    def test_classifies_by_configured_prefixes(self, adapter, monkeypatch):
        from trellis_datamodel import config as cfg
        from trellis_datamodel.adapters import entity_type_inference

        monkeypatch.setattr(cfg.DIMENSIONAL_MODELING_CONFIG, "enabled", True)
        monkeypatch.setattr(
            cfg.DIMENSIONAL_MODELING_CONFIG, "dimension_prefix", ["dim__"]
        )
        monkeypatch.setattr(cfg.DIMENSIONAL_MODELING_CONFIG, "fact_prefix", ["fct__"])
        entity_type_inference.reset_cache()

        types = adapter.infer_entity_types()

        assert types["dim__customer"] == "dimension"
        assert types["fct__order"] == "fact"
        assert types["prep__customers"] == "unclassified"

    def test_cache_is_namespaced_per_framework(self, adapter, monkeypatch):
        """dbt and Bruin adapters must not clobber each other's inference."""
        from trellis_datamodel import config as cfg
        from trellis_datamodel.adapters import entity_type_inference

        monkeypatch.setattr(cfg.DIMENSIONAL_MODELING_CONFIG, "enabled", True)
        monkeypatch.setattr(
            cfg.DIMENSIONAL_MODELING_CONFIG, "dimension_prefix", ["dim__"]
        )
        monkeypatch.setattr(cfg.DIMENSIONAL_MODELING_CONFIG, "fact_prefix", ["fct__"])
        entity_type_inference.reset_cache()

        adapter.infer_entity_types()
        entity_type_inference.reset_cache("dbt-core")

        # Clearing dbt's namespace must leave Bruin's entry intact.
        assert "bruin" in entity_type_inference._CACHES
