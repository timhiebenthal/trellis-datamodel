"""Tests for @bruin block parser utility."""

import os
import logging

from trellis_datamodel.utils.bruin_parser import (
    parse_bruin_block,
    scan_pipeline_assets,
)


class TestParseBruinBlock:
    """Tests for parse_bruin_block()."""

    def test_parse_sql_bruin_block(self, tmp_path):
        """Parse a valid SQL @bruin block and verify all fields."""
        sql_content = """/* @bruin
name: core.dim__game
connection: nba_duckdb
type: duckdb.sql
depends:
  - prep.prep__game
materialization:
  type: table
  strategy: create+replace
columns:
  - name: game_id
    type: varchar
    description: "Unique identifier for the NBA game"
    primary_key: true
@bruin */
"""
        file_path = tmp_path / "dim__game.sql"
        file_path.write_text(sql_content)

        asset = parse_bruin_block(str(file_path))
        assert asset is not None
        assert asset.name == "core.dim__game"
        assert asset.connection == "nba_duckdb"
        assert asset.type == "duckdb.sql"
        assert asset.depends == ["prep.prep__game"]
        assert asset.materialization == {"type": "table", "strategy": "create+replace"}
        assert len(asset.columns) == 1
        assert asset.columns[0]["name"] == "game_id"
        assert asset.columns[0]["type"] == "varchar"
        assert asset.columns[0]["description"] == "Unique identifier for the NBA game"
        assert asset.columns[0]["primary_key"] is True
        assert asset.file_path == str(file_path)

    def test_parse_python_bruin_block(self, tmp_path):
        """Parse a valid Python @bruin block with minimal fields."""
        py_content = '''"""@bruin
name: raw.raw_games
connection: nba_duckdb
@bruin"""
'''
        file_path = tmp_path / "raw_games.py"
        file_path.write_text(py_content)

        asset = parse_bruin_block(str(file_path))
        assert asset is not None
        assert asset.name == "raw.raw_games"
        assert asset.connection == "nba_duckdb"
        # Defaults for fields not present
        assert asset.type == ""
        assert asset.depends == []
        assert asset.materialization == {}
        assert asset.columns == []
        assert asset.description == ""
        assert asset.tags == []
        assert asset.custom_checks == []
        assert asset.file_path == str(file_path)

    def test_parse_malformed_bruin_block(self, tmp_path, caplog):
        """Malformed YAML inside @bruin block returns None and logs warning."""
        sql_content = """/* @bruin
name: core.dim__game
invalid_yaml: [unclosed
@bruin */
"""
        file_path = tmp_path / "broken.sql"
        file_path.write_text(sql_content)

        caplog.set_level(logging.WARNING)
        asset = parse_bruin_block(str(file_path))
        assert asset is None
        assert "malformed" in caplog.text.lower() or "warning" in caplog.text.lower()

    def test_parse_no_bruin_block(self, tmp_path):
        """File without @bruin block returns None."""
        file_path = tmp_path / "no_block.sql"
        file_path.write_text("SELECT 1 AS id;\n")

        assert parse_bruin_block(str(file_path)) is None

    def test_parse_unsupported_extension(self, tmp_path):
        """Unsupported file extension returns None."""
        file_path = tmp_path / "notes.txt"
        file_path.write_text("some content")

        assert parse_bruin_block(str(file_path)) is None


class TestDependsNormalization:
    """`depends:` accepts plain asset names and full mappings (Bruin's Upstream)."""

    def test_depends_plain_strings(self, tmp_path):
        file_path = tmp_path / "a.sql"
        file_path.write_text(
            "/* @bruin\nname: core.a\ndepends:\n  - prep.b\n  - prep.c\n@bruin */\n"
        )

        asset = parse_bruin_block(str(file_path))
        assert asset.depends == ["prep.b", "prep.c"]

    def test_depends_mapping_form(self, tmp_path):
        """A mapping upstream contributes its `value`, not the whole dict."""
        file_path = tmp_path / "a.sql"
        file_path.write_text(
            "/* @bruin\n"
            "name: core.a\n"
            "depends:\n"
            "  - value: prep.b\n"
            "    type: asset\n"
            "    mode: symbolic\n"
            "@bruin */\n"
        )

        asset = parse_bruin_block(str(file_path))
        assert asset.depends == ["prep.b"]

    def test_depends_mixed_forms(self, tmp_path):
        file_path = tmp_path / "a.sql"
        file_path.write_text(
            "/* @bruin\n"
            "name: core.a\n"
            "depends:\n"
            "  - prep.b\n"
            "  - value: prep.c\n"
            "    type: asset\n"
            "@bruin */\n"
        )

        asset = parse_bruin_block(str(file_path))
        assert asset.depends == ["prep.b", "prep.c"]

    def test_depends_raw_is_preserved(self, tmp_path):
        """The unnormalized form survives so a rewrite can round-trip it."""
        file_path = tmp_path / "a.sql"
        file_path.write_text(
            "/* @bruin\n"
            "name: core.a\n"
            "depends:\n"
            "  - value: prep.b\n"
            "    type: asset\n"
            "@bruin */\n"
        )

        asset = parse_bruin_block(str(file_path))
        assert asset.depends_raw == [{"value": "prep.b", "type": "asset"}]

    def test_depends_mapping_without_value_is_skipped(self, tmp_path):
        """An upstream with no resolvable asset name is dropped, not crashed on."""
        file_path = tmp_path / "a.sql"
        file_path.write_text(
            "/* @bruin\n"
            "name: core.a\n"
            "depends:\n"
            "  - uri: postgres://somewhere\n"
            "  - prep.b\n"
            "@bruin */\n"
        )

        asset = parse_bruin_block(str(file_path))
        assert asset.depends == ["prep.b"]


class TestParseParameters:
    """`parameters:` carries the ingestr source identity."""

    def test_parse_ingestr_parameters(self, tmp_path):
        file_path = tmp_path / "raw.sql"
        file_path.write_text(
            "/* @bruin\n"
            "name: raw.orders\n"
            "type: ingestr\n"
            "parameters:\n"
            "  source_connection: postgres_prod\n"
            "  source_table: public.orders\n"
            "@bruin */\n"
        )

        asset = parse_bruin_block(str(file_path))
        assert asset.type == "ingestr"
        assert asset.parameters["source_connection"] == "postgres_prod"
        assert asset.parameters["source_table"] == "public.orders"

    def test_parameters_default_empty(self, tmp_path):
        file_path = tmp_path / "a.sql"
        file_path.write_text("/* @bruin\nname: core.a\n@bruin */\n")

        assert parse_bruin_block(str(file_path)).parameters == {}


class TestScanPipelineAssets:
    """Tests for scan_pipeline_assets()."""

    def _create_asset_file(
        self, base_dir: str, subdir: str, filename: str, content: str
    ):
        """Helper to create an asset file within the pipeline assets directory."""
        full_dir = os.path.join(base_dir, "assets", subdir)
        os.makedirs(full_dir, exist_ok=True)
        file_path = os.path.join(full_dir, filename)
        with open(file_path, "w") as f:
            f.write(content)
        return file_path

    def test_scan_all_assets(self, tmp_path):
        """Scan with empty asset_paths returns all assets sorted by name."""
        pipeline_dir = str(tmp_path / "pipeline")

        self._create_asset_file(
            pipeline_dir,
            "01_clean",
            "clean__games.sql",
            "/* @bruin\nname: clean.clean__games\nconnection: nba_duckdb\n@bruin */\n",
        )
        self._create_asset_file(
            pipeline_dir,
            "00_ingest",
            "raw__teams.py",
            '"""@bruin\nname: raw.raw__teams\nconnection: nba_duckdb\n@bruin"""\n',
        )

        assets = scan_pipeline_assets(pipeline_dir, [])
        assert [a.name for a in assets] == ["clean.clean__games", "raw.raw__teams"]

    def test_scan_filtered_assets(self, tmp_path):
        """Scan with asset_paths filters by subdirectory."""
        pipeline_dir = str(tmp_path / "pipeline")

        self._create_asset_file(
            pipeline_dir,
            "01_clean",
            "clean__games.sql",
            "/* @bruin\nname: clean.clean__games\nconnection: nba_duckdb\n@bruin */\n",
        )
        self._create_asset_file(
            pipeline_dir,
            "00_ingest",
            "raw__teams.py",
            '"""@bruin\nname: raw.raw__teams\nconnection: nba_duckdb\n@bruin"""\n',
        )

        assets = scan_pipeline_assets(pipeline_dir, ["01_clean"])
        assert [a.name for a in assets] == ["clean.clean__games"]

    def test_scan_skip_non_asset_files(self, tmp_path):
        """Non .sql/.py files under assets are skipped."""
        pipeline_dir = str(tmp_path / "pipeline")

        self._create_asset_file(
            pipeline_dir,
            "01_clean",
            "clean__games.sql",
            "/* @bruin\nname: clean.clean__games\nconnection: nba_duckdb\n@bruin */\n",
        )
        self._create_asset_file(pipeline_dir, "00_ingest", "notes.txt", "not an asset")

        assets = scan_pipeline_assets(pipeline_dir, [])
        assert [a.name for a in assets] == ["clean.clean__games"]

    def test_scan_continues_on_parse_error(self, tmp_path, caplog):
        """One unparseable file does not stop the rest of the scan."""
        pipeline_dir = str(tmp_path / "pipeline")

        self._create_asset_file(
            pipeline_dir,
            "01_clean",
            "clean__games.sql",
            "/* @bruin\nname: clean.clean__games\nconnection: nba_duckdb\n@bruin */\n",
        )
        self._create_asset_file(
            pipeline_dir,
            "00_ingest",
            "broken.py",
            '"""@bruin\ninvalid_yaml: [unclosed\n@bruin"""\n',
        )

        caplog.set_level(logging.WARNING)
        assets = scan_pipeline_assets(pipeline_dir, [])
        assert [a.name for a in assets] == ["clean.clean__games"]

    def test_scan_missing_assets_dir(self, tmp_path):
        """A pipeline path with no assets/ directory yields nothing."""
        assert scan_pipeline_assets(str(tmp_path / "nope"), []) == []


class TestScanFixturePipeline:
    """The committed fixture pipeline is the shared baseline for adapter tests."""

    def test_scans_every_valid_asset(self, bruin_pipeline):
        assets = scan_pipeline_assets(bruin_pipeline, [])
        assert [a.name for a in assets] == [
            "core.dim__customer",
            "core.dim__product",
            "core.fct__order",
            "prep.prep__customers",
            "prep.prep__orders",
            "raw.raw__customers",
            "raw.raw__orders",
        ]

    def test_malformed_asset_is_skipped_not_fatal(self, bruin_pipeline):
        names = [a.name for a in scan_pipeline_assets(bruin_pipeline, [])]
        assert "core.broken__asset" not in names

    def test_asset_paths_filter(self, bruin_pipeline):
        assets = scan_pipeline_assets(bruin_pipeline, ["02_core"])
        assert [a.name for a in assets] == [
            "core.dim__customer",
            "core.dim__product",
            "core.fct__order",
        ]

    def test_python_asset_is_parsed(self, bruin_pipeline):
        assets = {a.name: a for a in scan_pipeline_assets(bruin_pipeline, [])}
        raw_customers = assets["raw.raw__customers"]
        assert raw_customers.type == "python"
        assert raw_customers.file_path.endswith(".py")

    def test_foreign_key_survives_parsing(self, bruin_pipeline):
        assets = {a.name: a for a in scan_pipeline_assets(bruin_pipeline, [])}
        columns = {c["name"]: c for c in assets["core.fct__order"].columns}
        assert columns["customer_id"]["foreign_key"] == {
            "table": "core.dim__customer",
            "column": "customer_id",
        }

    def test_mapping_depends_normalized(self, bruin_pipeline):
        assets = {a.name: a for a in scan_pipeline_assets(bruin_pipeline, [])}
        assert assets["prep.prep__orders"].depends == ["raw.raw__orders"]
