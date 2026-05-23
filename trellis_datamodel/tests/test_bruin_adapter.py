"""Tests for BruinAdapter (TransformationAdapter protocol)."""

import os
import re
import pytest

from trellis_datamodel.adapters.bruin import BruinAdapter


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _extract_bruin_block(content: str) -> str:
    """Helper to extract YAML content from the first @bruin block."""
    m = re.search(
        r"/\*\s*@bruin\s*\n(.*?)\n\s*@bruin\s*\*/", content, re.DOTALL
    )
    if m:
        return m.group(1)
    m = re.search(
        r'"""\s*@bruin\s*\n(.*?)\n\s*@bruin\s*"""', content, re.DOTALL
    )
    if m:
        return m.group(1)
    raise ValueError("No @bruin block found")


def _create_pipeline(tmp_path, name="pipeline"):
    """Create a minimal Bruin pipeline structure under tmp_path and return
    the pipeline root."""
    pipeline = tmp_path / name
    return pipeline


def _write_sql_asset(assets_dir, filename, name, columns=None, description=None,
                     materialization=None, tags=None, depends=None, sql_body=None):
    """Write a SQL asset with a @bruin block."""
    cols_yaml = ""
    if columns:
        for c in columns:
            cols_yaml += (
                f"  - name: {c['name']}\n"
                f"    type: {c.get('type', 'varchar')}\n"
            )
            if c.get("description"):
                cols_yaml += f'    description: "{c["description"]}"\n'

    mat_yaml = ""
    if materialization:
        mat_yaml = f"materialization:\n  type: {materialization}\n"

    tags_yaml = ""
    if tags:
        tags_yaml = "tags:\n"
        for t in tags:
            tags_yaml += f"  - {t}\n"

    depends_yaml = ""
    if depends:
        depends_yaml = "depends:\n"
        for d in depends:
            depends_yaml += f"  - {d}\n"

    desc_yaml = ""
    if description:
        desc_yaml = f'description: "{description}"\n'

    body = sql_body or "SELECT 1;"

    content = (
        f"/* @bruin\n"
        f"name: {name}\n"
        f"type: pg.sql\n"
        f"{depends_yaml}"
        f"{mat_yaml}"
        f"columns:\n{cols_yaml}"
        f"{tags_yaml}"
        f"{desc_yaml}"
        f"@bruin */\n"
        f"{body}\n"
    )
    assets_dir.mkdir(parents=True, exist_ok=True)
    path = assets_dir / filename
    path.write_text(content)
    return path


def _write_py_asset(assets_dir, filename, name, columns=None, description=None,
                    tags=None, depends=None):
    """Write a Python asset with a @bruin block."""
    cols_yaml = ""
    if columns:
        for c in columns:
            cols_yaml += (
                f"  - name: {c['name']}\n"
                f"    type: {c.get('type', 'varchar')}\n"
            )

    tags_yaml = ""
    if tags:
        tags_yaml = "tags:\n"
        for t in tags:
            tags_yaml += f"  - {t}\n"

    depends_yaml = ""
    if depends:
        depends_yaml = "depends:\n"
        for d in depends:
            depends_yaml += f"  - {d}\n"

    desc_yaml = ""
    if description:
        desc_yaml = f'description: "{description}"\n'

    content = (
        f'"""@bruin\n'
        f"name: {name}\n"
        f"type: pg.python\n"
        f"{depends_yaml}"
        f"{cols_yaml}"
        f"{tags_yaml}"
        f"{desc_yaml}"
        f'@bruin"""\n'
        f"import pandas as pd\n"
        f"df = pd.read_sql('SELECT 1', con=conn)\n"
    )
    assets_dir.mkdir(parents=True, exist_ok=True)
    path = assets_dir / filename
    path.write_text(content)
    return path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBruinGetModels:
    """get_models() tests."""

    def test_bruin_get_models(self, tmp_path):
        """Scan pipeline assets and return 2 ModelInfo entries."""
        pipeline = _create_pipeline(tmp_path, "pipeline")

        # SQL asset with columns, materialization, tags, description
        _write_sql_asset(
            pipeline / "assets" / "01_clean",
            "clean__games.sql",
            name="core.clean__games",
            columns=[
                {"name": "game_id", "type": "varchar", "description": "Game ID"},
                {"name": "game_name", "type": "varchar", "description": "Game name"},
            ],
            description="Cleaned games data",
            materialization="table",
            tags=["clean"],
            depends=["raw__teams"],
        )

        # Python asset with no columns, no materialization
        _write_py_asset(
            pipeline / "assets" / "00_ingest",
            "raw__teams.py",
            name="core.raw__teams",
        )

        adapter = BruinAdapter(
            pipeline_path=str(pipeline),
            data_model_path="",
            asset_paths=[],
        )

        models = adapter.get_models()
        assert len(models) == 2

        # Find the SQL model
        sql_model = next(m for m in models if m["name"] == "clean__games")
        assert sql_model["unique_id"] == "core.clean__games"
        assert sql_model["schema"] == "core"
        assert sql_model["table"] == "clean__games"
        assert sql_model["version"] is None
        assert sql_model["description"] == "Cleaned games data"
        assert sql_model["materialization"] == "table"
        assert sql_model["tags"] == ["clean"]
        assert len(sql_model["columns"]) == 2
        assert sql_model["columns"][0]["name"] == "game_id"
        assert sql_model["columns"][0]["type"] == "varchar"
        assert sql_model["columns"][1]["name"] == "game_name"
        assert sql_model["columns"][1]["type"] == "varchar"
        assert "clean__games.sql" in sql_model["file_path"]

        # Find the Python model
        py_model = next(m for m in models if m["name"] == "raw__teams")
        assert py_model["unique_id"] == "core.raw__teams"
        assert py_model["schema"] == "core"
        assert py_model["table"] == "raw__teams"
        assert py_model["version"] is None
        assert py_model["description"] is None
        assert py_model["materialization"] == ""
        assert py_model["columns"] == []
        assert py_model["tags"] == []
        assert "raw__teams.py" in py_model["file_path"]

    def test_bruin_get_models_filtered(self, tmp_path):
        """With asset_paths filter, only matching assets are returned."""
        pipeline = _create_pipeline(tmp_path, "pipeline")

        _write_sql_asset(
            pipeline / "assets" / "01_clean",
            "clean__games.sql",
            name="core.clean__games",
            columns=[{"name": "game_id", "type": "varchar"}],
        )
        _write_py_asset(
            pipeline / "assets" / "00_ingest",
            "raw__teams.py",
            name="core.raw__teams",
        )

        adapter = BruinAdapter(
            pipeline_path=str(pipeline),
            data_model_path="",
            asset_paths=["01_clean"],
        )

        models = adapter.get_models()
        assert len(models) == 1
        assert models[0]["name"] == "clean__games"

    def test_bruin_adapter_empty_pipeline(self, tmp_path):
        """Empty assets/ directory returns empty list (no error)."""
        pipeline = _create_pipeline(tmp_path, "pipeline")
        # Create empty assets/ dir
        assets_dir = pipeline / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)

        adapter = BruinAdapter(
            pipeline_path=str(pipeline),
            data_model_path="",
            asset_paths=[],
        )

        models = adapter.get_models()
        assert models == []

    def test_bruin_adapter_mixed_valid_invalid(self, tmp_path):
        """One valid SQL asset, one malformed @bruin block -> returns 1 model."""
        pipeline = _create_pipeline(tmp_path, "pipeline")

        # Valid SQL asset with proper @bruin block
        _write_sql_asset(
            pipeline / "assets" / "01_clean",
            "valid.sql",
            name="core.valid_model",
            columns=[{"name": "id", "type": "int"}],
            description="Valid model",
        )

        # File with malformed @bruin block (invalid YAML — unclosed bracket)
        bad_file = pipeline / "assets" / "01_clean" / "bad.sql"
        bad_file.parent.mkdir(parents=True, exist_ok=True)
        bad_file.write_text(
            "/* @bruin\n"
            "name: bad_model\n"
            "type: pg.sql\n"
            "tags: [unclosed_list\n"
            "@bruin */\n"
            "SELECT 1;\n"
        )

        adapter = BruinAdapter(
            pipeline_path=str(pipeline),
            data_model_path="",
            asset_paths=[],
        )

        models = adapter.get_models()
        assert len(models) == 1
        assert models[0]["name"] == "valid_model"

    def test_bruin_materialization_mapping(self, tmp_path):
        """Materialization mapping: type=view, missing key handled."""
        pipeline = _create_pipeline(tmp_path, "pipeline")

        # Asset with materialization.type = "view"
        _write_sql_asset(
            pipeline / "assets" / "01_clean",
            "view_model.sql",
            name="core.view_model",
            columns=[{"name": "id", "type": "int"}],
            materialization="view",
        )

        # Asset without materialization key
        _write_sql_asset(
            pipeline / "assets" / "02_mart",
            "table_model.sql",
            name="core.table_model",
            columns=[{"name": "id", "type": "int"}],
            # no materialization
        )

        adapter = BruinAdapter(
            pipeline_path=str(pipeline),
            data_model_path="",
            asset_paths=[],
        )

        models = adapter.get_models()
        assert len(models) == 2

        view_m = next(m for m in models if m["name"] == "view_model")
        assert view_m["materialization"] == "view"

        table_m = next(m for m in models if m["name"] == "table_model")
        assert table_m["materialization"] == ""

    def test_bruin_name_without_schema_prefix(self, tmp_path):
        """Asset name without a dot -> schema='', name=full_name."""
        pipeline = _create_pipeline(tmp_path, "pipeline")

        _write_sql_asset(
            pipeline / "assets" / "01_clean",
            "simple_model.sql",
            name="simple_model",
            columns=[{"name": "id", "type": "int"}],
        )

        adapter = BruinAdapter(
            pipeline_path=str(pipeline),
            data_model_path="",
            asset_paths=[],
        )

        models = adapter.get_models()
        assert len(models) == 1
        m = models[0]
        assert m["unique_id"] == "simple_model"
        assert m["name"] == "simple_model"
        assert m["schema"] == ""
        assert m["table"] == "simple_model"


class TestBruinGetModelSchema:
    """get_model_schema() tests."""

    def test_bruin_get_model_schema(self, tmp_path):
        """Return ModelSchema for an existing model."""
        pipeline = _create_pipeline(tmp_path, "pipeline")

        _write_sql_asset(
            pipeline / "assets" / "01_clean",
            "clean__games.sql",
            name="core.clean__games",
            columns=[
                {"name": "game_id", "type": "varchar", "description": "Game ID"},
                {"name": "game_name", "type": "varchar", "description": "Game name"},
            ],
            description="Cleaned games data",
            tags=["clean"],
        )

        adapter = BruinAdapter(
            pipeline_path=str(pipeline),
            data_model_path="",
            asset_paths=[],
        )

        schema = adapter.get_model_schema("clean__games")

        assert schema["model_name"] == "clean__games"
        assert schema["description"] == "Cleaned games data"
        assert len(schema["columns"]) == 2

        # Verify Bruin 'type' maps to ColumnSchema.data_type
        assert schema["columns"][0]["name"] == "game_id"
        assert schema["columns"][0]["data_type"] == "varchar"
        assert schema["columns"][0]["description"] == "Game ID"

        assert schema["columns"][1]["name"] == "game_name"
        assert schema["columns"][1]["data_type"] == "varchar"
        assert schema["columns"][1]["description"] == "Game name"

        assert schema["tags"] == ["clean"]
        assert "clean__games.sql" in schema["file_path"]

    def test_bruin_get_model_schema_not_found(self, tmp_path):
        """Non-existent model raises ValueError."""
        pipeline = _create_pipeline(tmp_path, "pipeline")
        adapter = BruinAdapter(
            pipeline_path=str(pipeline),
            data_model_path="",
            asset_paths=[],
        )

        with pytest.raises(ValueError, match="not found"):
            adapter.get_model_schema("nonexistent")

    def test_bruin_get_model_schema_full_name(self, tmp_path):
        """get_model_schema also accepts the full dotted name."""
        pipeline = _create_pipeline(tmp_path, "pipeline")

        _write_sql_asset(
            pipeline / "assets" / "01_clean",
            "clean__games.sql",
            name="core.clean__games",
            columns=[{"name": "game_id", "type": "varchar"}],
            description="Games",
        )

        adapter = BruinAdapter(
            pipeline_path=str(pipeline),
            data_model_path="",
            asset_paths=[],
        )

        # Try full name
        schema = adapter.get_model_schema("core.clean__games")
        assert schema["model_name"] == "clean__games"
        assert schema["description"] == "Games"


class TestBruinSaveModelSchema:
    """save_model_schema() tests."""

    def test_bruin_save_model_schema(self, tmp_path):
        """Update description and columns, verify file is rewritten."""
        pipeline = _create_pipeline(tmp_path, "pipeline")

        path = _write_sql_asset(
            pipeline / "assets" / "01_clean",
            "clean__games.sql",
            name="core.clean__games",
            columns=[
                {"name": "game_id", "type": "varchar", "description": "Game ID"},
            ],
            description="Cleaned games data",
            tags=["clean"],
            sql_body="SELECT game_id, game_name FROM raw_teams;",
        )

        adapter = BruinAdapter(
            pipeline_path=str(pipeline),
            data_model_path="",
            asset_paths=[],
        )

        updated_columns = [
            {"name": "game_id", "data_type": "varchar", "description": "Updated"},
            {"name": "game_name", "data_type": "varchar", "description": "Game name"},
        ]

        result = adapter.save_model_schema(
            "clean__games",
            columns=updated_columns,
            description="New desc",
        )

        assert result == path

        # Re-read file and verify
        updated = path.read_text()

        # SQL code unchanged
        assert "SELECT game_id, game_name FROM raw_teams;" in updated

        # Extract and verify @bruin block
        yaml_str = _extract_bruin_block(updated)
        # The YAML serializer may quote string values with spaces
        assert "New desc" in yaml_str

        # data_type should be written as 'type' in the bruin block
        assert "type: varchar" in yaml_str
        assert "data_type:" not in yaml_str

        # Both columns should be present
        assert "game_id" in yaml_str
        assert "game_name" in yaml_str
        assert "Updated" in yaml_str

    def test_bruin_save_model_schema_not_found(self, tmp_path):
        """Save on non-existent model raises ValueError."""
        pipeline = _create_pipeline(tmp_path, "pipeline")
        adapter = BruinAdapter(
            pipeline_path=str(pipeline),
            data_model_path="",
            asset_paths=[],
        )

        with pytest.raises(ValueError, match="not found"):
            adapter.save_model_schema(
                "nonexistent",
                columns=[{"name": "id", "data_type": "int"}],
            )


class TestBruinRelationships:
    """infer_relationships() and sync_relationships() tests."""

    def test_bruin_infer_relationships(self, tmp_path):
        """infer_relationships returns empty list."""
        pipeline = _create_pipeline(tmp_path, "pipeline")
        adapter = BruinAdapter(
            pipeline_path=str(pipeline),
            data_model_path="",
            asset_paths=[],
        )
        result = adapter.infer_relationships()
        assert result == []

    def test_bruin_sync_relationships(self, tmp_path):
        """sync_relationships returns empty list."""
        pipeline = _create_pipeline(tmp_path, "pipeline")
        adapter = BruinAdapter(
            pipeline_path=str(pipeline),
            data_model_path="",
            asset_paths=[],
        )
        result = adapter.sync_relationships(entities=[], relationships=[])
        assert result == []
