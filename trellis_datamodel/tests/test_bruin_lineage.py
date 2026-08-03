"""
Tests for BruinAdapter's lineage and source-system extraction.

Bruin has no manifest, so lineage is derived from each asset's `depends:` list.
An asset with no upstreams, or an ingestr asset, is where data enters the
pipeline and plays the role a dbt source plays.
"""

import pytest

from trellis_datamodel.adapters.bruin import BruinAdapter
from trellis_datamodel.exceptions import NotFoundError


@pytest.fixture
def adapter(bruin_pipeline, tmp_path):
    return BruinAdapter(
        pipeline_path=bruin_pipeline,
        data_model_path=str(tmp_path / "data_model.yml"),
        asset_paths=[],
    )


def _nodes_by_id(graph):
    return {n["unique_id"]: n for n in graph["nodes"]}


class TestGetLineage:
    def test_walks_upstream_to_the_ingestion_point(self, adapter):
        graph = adapter.get_lineage("core.dim__customer")

        assert set(_nodes_by_id(graph)) == {
            "core.dim__customer",
            "prep.prep__customers",
            "raw.raw__customers",
        }

    def test_edges_point_upstream_to_downstream(self, adapter):
        graph = adapter.get_lineage("core.dim__customer")

        assert {
            "source": "prep.prep__customers",
            "target": "core.dim__customer",
        } in graph["edges"]
        assert {
            "source": "raw.raw__customers",
            "target": "prep.prep__customers",
        } in graph["edges"]

    def test_accepts_short_name(self, adapter):
        """Entity bindings hold either spelling."""
        graph = adapter.get_lineage("dim__customer")

        assert "core.dim__customer" in _nodes_by_id(graph)

    def test_multiple_upstreams_are_all_followed(self, adapter):
        """fct__order depends on both a prep asset and a dimension."""
        graph = adapter.get_lineage("core.fct__order")

        assert set(_nodes_by_id(graph)) == {
            "core.fct__order",
            "prep.prep__orders",
            "raw.raw__orders",
            "core.dim__customer",
            "prep.prep__customers",
            "raw.raw__customers",
        }

    def test_mapping_form_depends_is_followed(self, adapter):
        """prep__orders declares its upstream as a mapping, not a bare string."""
        graph = adapter.get_lineage("prep.prep__orders")

        assert "raw.raw__orders" in _nodes_by_id(graph)

    def test_ingestr_asset_is_a_source(self, adapter):
        node = _nodes_by_id(adapter.get_lineage("prep.prep__orders"))[
            "raw.raw__orders"
        ]

        assert node["is_source"] is True
        assert node["resource_type"] == "source"
        assert node["source_name"] == "postgres_prod"

    def test_asset_without_upstreams_is_a_source(self, adapter):
        """A root asset is where data enters, whatever its type."""
        node = _nodes_by_id(adapter.get_lineage("core.dim__customer"))[
            "raw.raw__customers"
        ]

        assert node["is_source"] is True
        assert node["source_name"] == "crm_api"

    def test_transform_assets_are_not_sources(self, adapter):
        node = _nodes_by_id(adapter.get_lineage("core.dim__customer"))[
            "prep.prep__customers"
        ]

        assert node["is_source"] is False
        assert node["resource_type"] == "model"
        assert node["source_name"] is None

    def test_folder_carries_the_lineage_layer(self, adapter):
        nodes = _nodes_by_id(adapter.get_lineage("core.dim__customer"))

        assert nodes["core.dim__customer"]["folder"] == "02_core"
        assert nodes["prep.prep__customers"]["folder"] == "01_prep"
        assert nodes["raw.raw__customers"]["folder"] == "00_ingest"

    def test_nodes_carry_their_file_path(self, adapter):
        node = _nodes_by_id(adapter.get_lineage("core.dim__customer"))[
            "core.dim__customer"
        ]

        assert node["file_path"].endswith("dim__customer.sql")

    def test_root_only_graph_has_no_edges(self, adapter):
        graph = adapter.get_lineage("raw.raw__customers")

        assert [n["unique_id"] for n in graph["nodes"]] == ["raw.raw__customers"]
        assert graph["edges"] == []

    def test_unknown_asset_raises_not_found(self, adapter):
        with pytest.raises(NotFoundError, match="not found in pipeline"):
            adapter.get_lineage("core.nope")

    def test_unknown_asset_names_near_misses(self, adapter):
        with pytest.raises(NotFoundError, match="Found similar assets"):
            adapter.get_lineage("other.dim__customer")

    def test_sees_upstreams_outside_configured_asset_paths(
        self, bruin_pipeline, tmp_path
    ):
        """Filtering the model list must not truncate the lineage graph."""
        adapter = BruinAdapter(
            pipeline_path=bruin_pipeline,
            data_model_path=str(tmp_path / "data_model.yml"),
            asset_paths=["02_core"],
        )

        graph = adapter.get_lineage("core.dim__customer")

        assert "prep.prep__customers" in _nodes_by_id(graph)
        assert "raw.raw__customers" in _nodes_by_id(graph)

    def test_dangling_dependency_is_kept_in_the_graph(self, tmp_path):
        """A `depends` entry naming a missing asset must not be dropped."""
        assets = tmp_path / "pipeline" / "assets" / "core"
        assets.mkdir(parents=True)
        (assets / "a.sql").write_text(
            "/* @bruin\nname: core.a\ndepends:\n  - prep.missing\n@bruin */\n"
        )

        adapter = BruinAdapter(
            pipeline_path=str(tmp_path / "pipeline"),
            data_model_path="",
            asset_paths=[],
        )

        nodes = _nodes_by_id(adapter.get_lineage("core.a"))
        assert "prep.missing" in nodes
        assert nodes["prep.missing"]["folder"] is None

    def test_short_name_dependency_resolves_to_one_node(self, tmp_path):
        """A `depends: [dim__x]` entry must not appear as a second node."""
        assets = tmp_path / "pipeline" / "assets" / "core"
        assets.mkdir(parents=True)
        (assets / "dim__x.sql").write_text("/* @bruin\nname: core.dim__x\n@bruin */\n")
        (assets / "fct__y.sql").write_text(
            "/* @bruin\nname: core.fct__y\ndepends:\n  - dim__x\n@bruin */\n"
        )

        adapter = BruinAdapter(
            pipeline_path=str(tmp_path / "pipeline"),
            data_model_path="",
            asset_paths=[],
        )

        nodes = _nodes_by_id(adapter.get_lineage("core.fct__y"))
        assert set(nodes) == {"core.fct__y", "core.dim__x"}

    def test_cyclic_depends_terminates(self, tmp_path):
        """A malformed pipeline must not hang the request."""
        assets = tmp_path / "pipeline" / "assets" / "core"
        assets.mkdir(parents=True)
        (assets / "a.sql").write_text(
            "/* @bruin\nname: core.a\ndepends:\n  - core.b\n@bruin */\n"
        )
        (assets / "b.sql").write_text(
            "/* @bruin\nname: core.b\ndepends:\n  - core.a\n@bruin */\n"
        )

        adapter = BruinAdapter(
            pipeline_path=str(tmp_path / "pipeline"),
            data_model_path="",
            asset_paths=[],
        )

        assert set(_nodes_by_id(adapter.get_lineage("core.a"))) == {"core.a", "core.b"}


class TestGetSourceSystemsForModel:
    def test_returns_the_source_connection(self, adapter):
        assert adapter.get_source_systems_for_model("core.dim__customer") == [
            "crm_api"
        ]

    def test_collects_every_source_upstream(self, adapter):
        assert adapter.get_source_systems_for_model("core.fct__order") == [
            "crm_api",
            "postgres_prod",
        ]

    def test_source_asset_reports_itself(self, adapter):
        assert adapter.get_source_systems_for_model("raw.raw__orders") == [
            "postgres_prod"
        ]

    def test_unknown_asset_returns_empty_rather_than_raising(self, adapter):
        """This backs optional display; it must never break the response."""
        assert adapter.get_source_systems_for_model("core.nope") == []

    def test_missing_pipeline_returns_empty(self, tmp_path):
        adapter = BruinAdapter(
            pipeline_path=str(tmp_path / "nope"),
            data_model_path="",
            asset_paths=[],
        )

        assert adapter.get_source_systems_for_model("core.dim__customer") == []


class TestLineageServiceIntegration:
    """The lineage service must layer a Bruin graph exactly as it does dbt's."""

    def test_transforms_bruin_graph_into_levels(self, adapter, monkeypatch):
        from trellis_datamodel.services import lineage as lineage_service

        monkeypatch.setattr(lineage_service, "get_adapter", lambda: adapter)
        monkeypatch.setattr(lineage_service.cfg, "LINEAGE_LAYERS", [])

        result = lineage_service.extract_upstream_lineage("core.dim__customer")

        levels = {n["id"]: n["level"] for n in result["nodes"]}
        assert levels["core.dim__customer"] == 0
        assert levels["prep.prep__customers"] == 1
        assert levels["raw.raw__customers"] == 2
        assert result["metadata"]["total_nodes"] == 3

    def test_assigns_configured_layers_from_asset_folders(self, adapter, monkeypatch):
        from trellis_datamodel.services import lineage as lineage_service

        monkeypatch.setattr(lineage_service, "get_adapter", lambda: adapter)
        monkeypatch.setattr(
            lineage_service.cfg, "LINEAGE_LAYERS", ["00_ingest", "01_prep", "02_core"]
        )

        result = lineage_service.extract_upstream_lineage("core.dim__customer")

        layers = {n["id"]: n["layer"] for n in result["nodes"]}
        assert layers["core.dim__customer"] == "02_core"
        assert layers["prep.prep__customers"] == "01_prep"
        # Sources always get the "sources" layer, whatever folder they live in.
        assert layers["raw.raw__customers"] == "sources"

    def test_unconfigured_folder_falls_back_to_unassigned(self, adapter, monkeypatch):
        from trellis_datamodel.services import lineage as lineage_service

        monkeypatch.setattr(lineage_service, "get_adapter", lambda: adapter)
        monkeypatch.setattr(lineage_service.cfg, "LINEAGE_LAYERS", ["02_core"])

        result = lineage_service.extract_upstream_lineage("core.dim__customer")

        layers = {n["id"]: n["layer"] for n in result["nodes"]}
        assert layers["core.dim__customer"] == "02_core"
        assert layers["prep.prep__customers"] == "unassigned"

    def test_source_name_is_exposed_to_the_frontend(self, adapter, monkeypatch):
        from trellis_datamodel.services import lineage as lineage_service

        monkeypatch.setattr(lineage_service, "get_adapter", lambda: adapter)
        monkeypatch.setattr(lineage_service.cfg, "LINEAGE_LAYERS", [])

        result = lineage_service.extract_upstream_lineage("core.dim__customer")

        source = next(n for n in result["nodes"] if n["isSource"])
        assert source["sourceName"] == "crm_api"
