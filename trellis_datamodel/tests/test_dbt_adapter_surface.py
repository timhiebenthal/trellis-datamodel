"""
Tests for DbtCoreAdapter's lineage, exposure, and project-status methods.

These are the four methods that let routes and services stop reading dbt
artifacts themselves. They are tested directly here, rather than only through
the endpoints that consume them, so a shape regression points at the adapter
instead of surfacing as a confusing route failure.
"""

import json
import os

import pytest
import yaml

from trellis_datamodel.adapters.dbt_core import DbtCoreAdapter
from trellis_datamodel.exceptions import FileOperationError, NotFoundError


MANIFEST = {
    "nodes": {
        "model.proj.dim__customer": {
            "unique_id": "model.proj.dim__customer",
            "resource_type": "model",
            "name": "dim__customer",
            "original_file_path": "models/3_core/dim__customer.sql",
            "depends_on": {"nodes": ["model.proj.stg__customer"]},
        },
        "model.proj.stg__customer": {
            "unique_id": "model.proj.stg__customer",
            "resource_type": "model",
            "name": "stg__customer",
            "original_file_path": "models/1_clean/stg__customer.sql",
            "depends_on": {"nodes": ["source.proj.crm.customers"]},
        },
        "model.proj.standalone": {
            "unique_id": "model.proj.standalone",
            "resource_type": "model",
            "name": "standalone",
            "original_file_path": "models/standalone.sql",
            "depends_on": {"nodes": []},
        },
    },
    "sources": {
        "source.proj.crm.customers": {
            "unique_id": "source.proj.crm.customers",
            "resource_type": "source",
            "name": "customers",
            "source_name": "crm",
            "original_file_path": "models/sources.yml",
        }
    },
}


@pytest.fixture
def adapter(tmp_path):
    """A DbtCoreAdapter over a manifest written into a temp project."""
    project = tmp_path / "dbt_project"
    (project / "models").mkdir(parents=True)
    manifest_path = project / "target" / "manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(json.dumps(MANIFEST))

    return DbtCoreAdapter(
        manifest_path=str(manifest_path),
        catalog_path=str(project / "target" / "catalog.json"),
        project_path=str(project),
        data_model_path=str(tmp_path / "data_model.yml"),
        model_paths=["3_core"],
    )


class TestGetLineage:
    def test_walks_upstream_to_sources(self, adapter):
        graph = adapter.get_lineage("model.proj.dim__customer")

        assert {n["unique_id"] for n in graph["nodes"]} == {
            "model.proj.dim__customer",
            "model.proj.stg__customer",
            "source.proj.crm.customers",
        }
        assert graph["edges"] == [
            {"source": "model.proj.stg__customer", "target": "model.proj.dim__customer"},
            {"source": "source.proj.crm.customers", "target": "model.proj.stg__customer"},
        ]

    def test_marks_sources_and_carries_source_name(self, adapter):
        nodes = {
            n["unique_id"]: n
            for n in adapter.get_lineage("model.proj.dim__customer")["nodes"]
        }

        source = nodes["source.proj.crm.customers"]
        assert source["is_source"] is True
        assert source["resource_type"] == "source"
        assert source["source_name"] == "crm"

        model = nodes["model.proj.stg__customer"]
        assert model["is_source"] is False
        assert model["source_name"] is None
        assert model["name"] == "stg__customer"

    def test_carries_folder_for_layer_assignment(self, adapter):
        nodes = {
            n["unique_id"]: n
            for n in adapter.get_lineage("model.proj.dim__customer")["nodes"]
        }

        assert nodes["model.proj.dim__customer"]["folder"] == "3_core"
        assert nodes["model.proj.stg__customer"]["folder"] == "1_clean"

    def test_top_level_model_has_no_folder(self, adapter):
        """`models/standalone.sql` has no layer folder — not the filename."""
        nodes = adapter.get_lineage("model.proj.standalone")["nodes"]

        assert nodes[0]["folder"] is None

    def test_root_only_graph_has_no_edges(self, adapter):
        graph = adapter.get_lineage("model.proj.standalone")

        assert [n["unique_id"] for n in graph["nodes"]] == ["model.proj.standalone"]
        assert graph["edges"] == []

    def test_unknown_model_raises_not_found(self, adapter):
        with pytest.raises(NotFoundError, match="not found in manifest"):
            adapter.get_lineage("model.proj.nope")

    def test_unknown_model_names_near_misses(self, adapter):
        """A version/project mismatch is the common case; name the candidates."""
        with pytest.raises(NotFoundError, match="Found similar models"):
            adapter.get_lineage("model.other_project.dim__customer")

    def test_missing_manifest_raises_file_operation_error(self, adapter):
        os.remove(adapter.manifest_path)

        with pytest.raises(FileOperationError, match="Manifest not found"):
            adapter.get_lineage("model.proj.dim__customer")


class TestGetSourceSystemsForModel:
    def test_returns_source_names(self, adapter):
        assert adapter.get_source_systems_for_model("model.proj.dim__customer") == [
            "crm"
        ]

    def test_model_without_sources_returns_empty(self, adapter):
        assert adapter.get_source_systems_for_model("model.proj.standalone") == []

    def test_unknown_model_returns_empty_rather_than_raising(self, adapter):
        """This backs optional display; it must never break the response."""
        assert adapter.get_source_systems_for_model("model.proj.nope") == []

    def test_missing_manifest_returns_empty(self, adapter):
        os.remove(adapter.manifest_path)

        assert adapter.get_source_systems_for_model("model.proj.dim__customer") == []


class TestGetExposures:
    def test_reads_exposures_from_manifest(self, adapter):
        manifest = dict(MANIFEST)
        manifest["exposures"] = {
            "exposure.proj.revenue": {
                "name": "revenue",
                "label": "Revenue Dashboard",
                "type": "dashboard",
                "url": "https://bi.example.com/revenue",
                "owner": {"name": "analytics", "email": "a@example.com"},
                "depends_on": {"nodes": ["model.proj.dim__customer"]},
            }
        }
        with open(adapter.manifest_path, "w") as f:
            json.dump(manifest, f)

        exposures = adapter.get_exposures()

        assert len(exposures) == 1
        assert exposures[0]["name"] == "revenue"
        assert exposures[0]["label"] == "Revenue Dashboard"
        assert exposures[0]["url"] == "https://bi.example.com/revenue"
        assert exposures[0]["owner"] == {"name": "analytics"}
        assert exposures[0]["depends_on"] == ["model.proj.dim__customer"]

    def test_falls_back_to_exposures_yml_at_project_root(self, adapter):
        """Uncompiled projects keep their exposures in a plain YAML file."""
        with open(os.path.join(adapter.project_path, "exposures.yml"), "w") as f:
            yaml.dump(
                {
                    "exposures": [
                        {
                            "name": "revenue",
                            "type": "dashboard",
                            "depends_on": ["ref('dim__customer')"],
                        }
                    ]
                },
                f,
            )

        exposures = adapter.get_exposures()

        assert exposures[0]["name"] == "revenue"
        # ref() strings are resolved so callers only ever see unique_ids.
        assert exposures[0]["depends_on"] == ["model.proj.dim__customer"]

    def test_falls_back_to_exposures_yml_under_models(self, adapter):
        with open(
            os.path.join(adapter.project_path, "models", "exposures.yml"), "w"
        ) as f:
            yaml.dump({"exposures": [{"name": "revenue", "type": "dashboard"}]}, f)

        assert adapter.get_exposures()[0]["name"] == "revenue"

    def test_unresolvable_ref_is_dropped_not_fatal(self, adapter):
        with open(os.path.join(adapter.project_path, "exposures.yml"), "w") as f:
            yaml.dump(
                {
                    "exposures": [
                        {
                            "name": "revenue",
                            "depends_on": ["ref('does_not_exist')"],
                        }
                    ]
                },
                f,
            )

        assert adapter.get_exposures()[0]["depends_on"] == []

    def test_versioned_ref_resolves_to_matching_version(self, adapter):
        manifest = json.loads(open(adapter.manifest_path).read())
        manifest["nodes"]["model.proj.dim__customer.v2"] = {
            "resource_type": "model",
            "name": "dim__customer",
            "version": 2,
            "original_file_path": "models/3_core/dim__customer.sql",
            "depends_on": {"nodes": []},
        }
        with open(adapter.manifest_path, "w") as f:
            json.dump(manifest, f)

        with open(os.path.join(adapter.project_path, "exposures.yml"), "w") as f:
            yaml.dump(
                {
                    "exposures": [
                        {"name": "revenue", "depends_on": ["ref('dim__customer', v=2)"]}
                    ]
                },
                f,
            )

        assert adapter.get_exposures()[0]["depends_on"] == [
            "model.proj.dim__customer.v2"
        ]

    def test_exposure_without_name_is_skipped(self, adapter):
        with open(os.path.join(adapter.project_path, "exposures.yml"), "w") as f:
            yaml.dump({"exposures": [{"type": "dashboard"}]}, f)

        assert adapter.get_exposures() == []

    def test_no_exposures_anywhere_returns_empty(self, adapter):
        assert adapter.get_exposures() == []


class TestGetProjectStatus:
    def test_reports_artifacts(self, adapter):
        status = adapter.get_project_status()

        assert status["framework"] == "dbt-core"
        assert status["artifacts_present"] is True
        assert status["artifacts"]["manifest"]["exists"] is True
        assert status["artifacts"]["manifest"]["path"] == adapter.manifest_path
        # No catalog was written, and that is not an error — it is optional.
        assert status["artifacts"]["catalog"]["exists"] is False
        assert status["error"] is None

    def test_reports_resolved_model_paths(self, adapter):
        status = adapter.get_project_status()

        assert status["model_paths_configured"] == ["3_core"]
        assert status["model_paths_resolved"] == [
            os.path.join(adapter.project_path, "models", "3_core")
        ]

    def test_missing_manifest_is_an_error(self, adapter):
        os.remove(adapter.manifest_path)

        status = adapter.get_project_status()

        assert status["artifacts_present"] is False
        assert "Manifest not found" in status["error"]

    def test_unset_project_path_is_an_error(self, adapter):
        adapter.project_path = ""

        assert "dbt_project_path not set" in adapter.get_project_status()["error"]

    def test_declares_full_dbt_capabilities(self, adapter):
        assert adapter.get_project_status()["capabilities"] == {
            "lineage": True,
            "column_lineage": True,
            "exposures": True,
            "relationships": True,
            "scaffolding": True,
        }
