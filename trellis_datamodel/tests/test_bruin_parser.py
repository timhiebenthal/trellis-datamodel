"""Tests for @bruin block parser utility."""

import os
import logging
import pytest

from trellis_datamodel.utils.bruin_parser import BruinAsset, parse_bruin_block, scan_pipeline_assets


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
        sql_content = """SELECT 1 AS id;
"""
        file_path = tmp_path / "no_block.sql"
        file_path.write_text(sql_content)

        asset = parse_bruin_block(str(file_path))
        assert asset is None

    def test_parse_unsupported_extension(self, tmp_path):
        """Unsupported file extension returns None."""
        file_path = tmp_path / "notes.txt"
        file_path.write_text("some content")

        asset = parse_bruin_block(str(file_path))
        assert asset is None


class TestScanPipelineAssets:
    """Tests for scan_pipeline_assets()."""

    def _create_asset_file(self, base_dir: str, subdir: str, filename: str, content: str):
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

        # Create asset files
        clean_sql = self._create_asset_file(
            pipeline_dir, "01_clean", "clean__games.sql",
            '/* @bruin\nname: clean.clean__games\nconnection: nba_duckdb\n@bruin */\n',
        )
        ingest_py = self._create_asset_file(
            pipeline_dir, "00_ingest", "raw__teams.py",
            '"""@bruin\nname: raw.raw__teams\nconnection: nba_duckdb\n@bruin"""\n',
        )

        assets = scan_pipeline_assets(pipeline_dir, [])
        assert len(assets) == 2
        # Sorted by name: clean.clean__games, raw.raw__teams
        assert assets[0].name == "clean.clean__games"
        assert assets[1].name == "raw.raw__teams"

    def test_scan_filtered_assets(self, tmp_path):
        """Scan with asset_paths filters by subdirectory."""
        pipeline_dir = str(tmp_path / "pipeline")

        self._create_asset_file(
            pipeline_dir, "01_clean", "clean__games.sql",
            '/* @bruin\nname: clean.clean__games\nconnection: nba_duckdb\n@bruin */\n',
        )
        self._create_asset_file(
            pipeline_dir, "00_ingest", "raw__teams.py",
            '"""@bruin\nname: raw.raw__teams\nconnection: nba_duckdb\n@bruin"""\n',
        )

        # Filter to only 01_clean
        assets = scan_pipeline_assets(pipeline_dir, ["01_clean"])
        assert len(assets) == 1
        assert assets[0].name == "clean.clean__games"

    def test_scan_skip_non_asset_files(self, tmp_path):
        """Non .sql/.py files under assets are skipped."""
        pipeline_dir = str(tmp_path / "pipeline")

        self._create_asset_file(
            pipeline_dir, "01_clean", "clean__games.sql",
            '/* @bruin\nname: clean.clean__games\nconnection: nba_duckdb\n@bruin */\n',
        )
        # Create a non-asset file (should be skipped)
        self._create_asset_file(
            pipeline_dir, "00_ingest", "notes.txt",
            "not an asset file",
        )

        assets = scan_pipeline_assets(pipeline_dir, [])
        assert len(assets) == 1
        assert assets[0].name == "clean.clean__games"

    def test_scan_continues_on_parse_error(self, tmp_path, caplog):
        """scan_pipeline_assets continues processing other files when one has a parse error."""
        pipeline_dir = str(tmp_path / "pipeline")

        # Valid asset
        self._create_asset_file(
            pipeline_dir, "01_clean", "clean__games.sql",
            '/* @bruin\nname: clean.clean__games\nconnection: nba_duckdb\n@bruin */\n',
        )
        # Malformed asset
        self._create_asset_file(
            pipeline_dir, "00_ingest", "broken.py",
            '"""@bruin\ninvalid_yaml: [unclosed\n@bruin"""\n',
        )

        caplog.set_level(logging.WARNING)
        assets = scan_pipeline_assets(pipeline_dir, [])
        assert len(assets) == 1
        assert assets[0].name == "clean.clean__games"
