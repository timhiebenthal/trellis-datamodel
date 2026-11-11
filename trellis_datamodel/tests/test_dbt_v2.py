"""dbt v2 YAML compatibility and real artifact regression tests."""

import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest
from ruamel.yaml.comments import CommentedMap

from trellis_datamodel.utils.column_metadata import resolve_column_origin
from trellis_datamodel.utils.yaml_handler import YamlHandler

ORIGIN = [{"System": "CRM"}]


@pytest.mark.parametrize("writer", ["update_columns_batch", "merge_columns_non_destructive"])
def test_v2_column_metadata_merges_under_config(writer):
    handler = YamlHandler(dbt_v2=True)
    model = CommentedMap({"columns": [CommentedMap({
        "name": "id",
        "meta": {"legacy": True, "owner": "old"},
        "config": {"tags": ["pii"], "meta": {"owner": "analytics"}},
        "data_tests": ["not_null"],
    })]})
    getattr(handler, writer)(model, [{"name": "id", "meta": {"origin": ORIGIN}}])
    col = model["columns"][0]
    assert "meta" not in col
    assert col["config"] == {
        "tags": ["pii"],
        "meta": {"legacy": True, "owner": "analytics", "origin": ORIGIN},
    }
    assert col["data_tests"] == ["not_null"]


@pytest.mark.parametrize("writer", ["update_columns_batch", "merge_columns_non_destructive"])
def test_v1_column_metadata_keeps_legacy_location(writer):
    handler = YamlHandler()
    model = CommentedMap({"columns": [{"name": "id", "meta": {"owner": "analytics"}}]})
    getattr(handler, writer)(model, [{"name": "id", "meta": {"origin": ORIGIN}}])
    assert model["columns"][0]["meta"] == {"owner": "analytics", "origin": ORIGIN}


def test_config_origin_takes_precedence_over_legacy_meta():
    assert resolve_column_origin({
        "config": {"meta": {"origin": ORIGIN}},
        "meta": {"origin": [{"System": "old"}]},
    }) == ORIGIN


def test_schema_reader_returns_structured_origin():
    columns = YamlHandler().get_columns({"columns": [{
        "name": "id", "config": {"meta": {"origin": ORIGIN}},
    }]})
    assert columns[0]["origin"] == ORIGIN


def test_v2_model_tags_move_to_config():
    model = CommentedMap({"name": "orders", "tags": ["existing"]})
    YamlHandler(dbt_v2=True).merge_model_tags(model, ["new"])
    assert "tags" not in model
    assert model["config"]["tags"] == ["existing", "new"]


@pytest.fixture
def v2_project(tmp_path):
    from trellis_datamodel.adapters.dbt_core import DbtCoreAdapter

    source = Path(__file__).parent / "fixtures" / "dbt_v2"
    project = tmp_path / "project"
    shutil.copytree(source, project)
    (project / "target").mkdir()
    shutil.move(project / "manifest.json", project / "target" / "manifest.json")
    adapter = DbtCoreAdapter(
        manifest_path=str(project / "target" / "manifest.json"),
        catalog_path=str(project / "target" / "catalog.json"),
        project_path=str(project),
        data_model_path=str(tmp_path / "data_model.yml"),
        model_paths=[],
    )
    return project, adapter


def test_real_v2_artifact_reads(v2_project):
    project, adapter = v2_project
    models = {m["name"]: m for m in adapter.get_models()}
    assert set(models) == {"customers", "orders"}
    assert models["customers"]["columns"][0]["origin"] == ORIGIN
    assert models["customers"]["columns"][0]["type"] == "integer"
    assert models["customers"]["tags"] == ["dimension"]
    assert adapter.get_model_schema("customers")["columns"][0]["origin"] == ORIGIN
    relationships = adapter.infer_relationships(include_unbound=True)
    assert len(relationships) == 1
    assert relationships[0]["source"] == "customers"
    assert relationships[0]["source_field"] == "id"
    assert relationships[0]["target"] == "orders"
    assert relationships[0]["target_field"] == "customer_id"
    lineage = adapter.get_lineage("model.trellis_v2.orders")
    assert len(lineage["nodes"]) == 2
    assert len(lineage["edges"]) == 1


def test_v2_catalog_enrichment(v2_project):
    """Synthetic warehouse types exercise enrichment, not warehouse connectivity."""
    project, adapter = v2_project
    (project / "target" / "catalog.json").write_text(json.dumps({
        "metadata": {"dbt_version": "2.0.11"},
        "nodes": {"model.trellis_v2.customers": {"columns": {
            "ID": {"name": "ID", "type": "NUMBER", "comment": "Warehouse ID"},
        }}},
    }))
    column = adapter.get_models()[0]["columns"][0]
    assert column["name"] == "id"
    assert column["type"] == "NUMBER"
    assert column["origin"] == ORIGIN


@pytest.mark.parametrize("writer", ["save_model_schema", "save_schema_file", "sync_relationships"])
@pytest.mark.parametrize("dbt_version", ["2.0.11", "1.9.8"])
def test_adapter_writers_choose_syntax_from_dbt_version(v2_project, writer, dbt_version):
    project, adapter = v2_project
    manifest_path = project / "target" / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    # v1 and v2 can share schema v12; it cannot determine YAML syntax.
    manifest["metadata"]["dbt_version"] = dbt_version
    manifest_path.write_text(json.dumps(manifest))
    if writer == "save_model_schema":
        adapter.save_model_schema("customers", [
            {"name": "id", "meta": {"origin": ORIGIN}},
            {"name": "new_id", "meta": {"origin": ORIGIN}},
        ])
    else:
        fields = [
            {"name": "id", "datatype": "integer", "origin": ORIGIN},
            {"name": "new_id", "datatype": "integer", "origin": ORIGIN},
        ]
        if writer == "save_schema_file":
            adapter.save_schema_file("customers", "customers", fields)
        else:
            adapter.sync_relationships([
                {
                    "id": "customers", "model_ref": "model.trellis_v2.customers",
                    "drafted_fields": fields,
                },
                {
                    "id": "orders", "model_ref": "model.trellis_v2.orders",
                    "drafted_fields": [{"name": "customer_id", "datatype": "integer"}],
                },
            ], [{
                "source": "customers", "source_field": "id",
                "target": "orders", "target_field": "customer_id", "type": "one_to_many",
            }])
    data = adapter.yaml_handler.load_file(str(project / "models" / "schema.yml"))
    column = data["models"][0]["columns"][0]
    # Existing nested metadata remains nested even for v1.
    assert column["config"]["meta"]["origin"] == ORIGIN
    assert "meta" not in column

    # A new column proves version selection independently of existing YAML.
    new_column = data["models"][0]["columns"][1]
    if dbt_version.startswith("2."):
        assert new_column["config"]["meta"]["origin"] == ORIGIN
        assert "meta" not in new_column
    else:
        assert new_column["meta"]["origin"] == ORIGIN

    # Opt in to validating Trellis output with an independently installed v2.
    binary = os.environ.get("DBT_V2_BIN")
    if binary and dbt_version.startswith("2."):
        (project / "profiles.yml").write_text(
            "trellis_v2:\n  target: dev\n  outputs:\n    dev:\n"
            "      type: snowflake\n      account: example\n      user: example\n"
            "      password: example\n      database: example\n"
            "      warehouse: example\n      schema: public\n"
        )
        result = subprocess.run([
            binary, "parse", "--project-dir", str(project), "--profiles-dir", str(project),
            "--no-manage-state",
        ], capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, result.stdout + result.stderr
        parsed = json.loads(manifest_path.read_text())
        assert parsed["metadata"]["dbt_version"].startswith("2.")
        assert parsed["nodes"]["model.trellis_v2.customers"]["columns"]["new_id"]["meta"]["origin"] == ORIGIN
        assert len(adapter.infer_relationships(include_unbound=True)) == 1


@pytest.mark.parametrize("writer", ["update_columns_batch", "merge_columns_non_destructive"])
@pytest.mark.parametrize("nested", [True, False])
def test_metadata_comments_survive_push(writer, nested, tmp_path):
    path = tmp_path / "schema.yml"
    path.write_text("""models:
  - name: customers
    columns:
      - name: id
        config:
          meta:
            owner: analytics  # keep the owner comment
""")
    if not nested:
        path.write_text(path.read_text().replace(
            "        config:\n          meta:\n            owner:",
            "        meta:\n          owner:",
        ))
    handler = YamlHandler(dbt_v2=True)
    data = handler.load_file(str(path))
    getattr(handler, writer)(data["models"][0], [{"name": "id", "meta": {"origin": ORIGIN}}])
    handler.save_file(str(path), data)
    assert "# keep the owner comment" in path.read_text()


def test_v2_versioned_schema_metadata(v2_project):
    project, adapter = v2_project
    path = project / "models" / "schema.yml"
    data = adapter.yaml_handler.load_file(str(path))
    model = data["models"][0]
    model["latest_version"] = 1
    model["versions"] = [{"v": 1}]
    adapter.yaml_handler.save_file(str(path), data)
    adapter.save_model_schema("customers", [
        {"name": "id", "meta": {"origin": ORIGIN}},
    ], version=1, tags=["dimension"])
    data = adapter.yaml_handler.load_file(str(path))
    version = data["models"][0]["versions"][0]
    assert version["columns"][0]["config"]["meta"]["origin"] == ORIGIN
    assert version["config"]["tags"] == ["dimension"]
    assert adapter.get_model_schema("customers", version=1)["columns"][0]["origin"] == ORIGIN
