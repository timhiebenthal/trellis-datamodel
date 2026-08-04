"""Tests for @bruin block rewriter utility."""

import os
import re

import pytest
import yaml

from trellis_datamodel.utils.bruin_parser import parse_bruin_block
from trellis_datamodel.utils.bruin_rewriter import (
    rewrite_bruin_block,
    write_bruin_asset,
)


def _extract_bruin_block(content: str) -> str:
    """Helper to extract YAML content from the first @bruin block."""
    m = re.search(r"/\*\s*@bruin\s*\n(.*?)\n\s*@bruin\s*\*/", content, re.DOTALL)
    if m:
        return m.group(1)
    m = re.search(r'"""\s*@bruin\s*\n(.*?)\n\s*@bruin\s*"""', content, re.DOTALL)
    if m:
        return m.group(1)
    raise ValueError("No @bruin block found")


def _parsed_block(content: str) -> dict:
    """Parse the @bruin block's YAML into a plain dict."""
    return yaml.safe_load(_extract_bruin_block(content))


class TestRewriteSQLBruinBlock:
    """Test rewriting @bruin blocks in SQL files."""

    def test_rewrite_sql_bruin_block_description(self, tmp_path):
        """Rewrite description in a SQL @bruin block."""
        sql_content = """/* @bruin
name: core.dim__game
columns:
  - name: game_id
    type: varchar
    description: "Game ID"
  - name: game_name
    type: varchar
    description: "Game name"
@bruin */
SELECT * FROM games;
"""
        file_path = tmp_path / "dim__game.sql"
        file_path.write_text(sql_content)

        result = rewrite_bruin_block(
            str(file_path),
            updates={"description": "Updated description for games"},
        )

        assert result == file_path
        updated = file_path.read_text()

        # The SQL code outside the block must be unchanged
        assert "SELECT * FROM games;" in updated

        block = _parsed_block(updated)
        assert block["name"] == "core.dim__game"
        assert block["description"] == "Updated description for games"
        assert [c["name"] for c in block["columns"]] == ["game_id", "game_name"]
        assert "/* @bruin" in updated
        assert "@bruin */" in updated


class TestRewritePythonBruinBlock:
    """Test rewriting @bruin blocks in Python files."""

    def test_rewrite_python_bruin_block(self, tmp_path):
        """Rewrite description in a Python @bruin block."""
        py_content = '''"""@bruin
name: core.dim__game
columns:
  - name: game_id
    type: varchar
    description: "Game ID"
@bruin"""
import pandas as pd

df = pd.read_sql("SELECT * FROM games", con=conn)
'''
        file_path = tmp_path / "dim__game.py"
        file_path.write_text(py_content)

        result = rewrite_bruin_block(
            str(file_path),
            updates={"description": "Updated Python model"},
        )

        assert result == file_path
        updated = file_path.read_text()

        assert "import pandas as pd" in updated
        assert 'df = pd.read_sql("SELECT * FROM games", con=conn)' in updated

        block = _parsed_block(updated)
        assert block["description"] == "Updated Python model"
        assert block["name"] == "core.dim__game"

        assert '"""@bruin' in updated
        assert '@bruin"""' in updated


class TestRewritePreservesSurroundingCode:
    """Test that surrounding code is preserved byte-identically."""

    def test_rewrite_preserves_surrounding_code(self, tmp_path):
        """Verify code outside the @bruin block is byte-identical afterwards."""
        sql_body = """WITH base AS (
    SELECT * FROM games
)
SELECT game_id, game_name
FROM base
WHERE game_id IS NOT NULL;
"""
        sql_content = (
            "/* @bruin\n"
            "name: core.dim__game\n"
            "columns:\n"
            "  - name: game_id\n"
            "    type: varchar\n"
            '    description: "Game ID"\n'
            "@bruin */\n" + sql_body
        )
        file_path = tmp_path / "dim__game.sql"
        file_path.write_text(sql_content)

        rewrite_bruin_block(
            str(file_path), updates={"description": "Updated description"}
        )

        updated = file_path.read_text()
        # Everything from the first SQL line onward is untouched, byte for byte.
        assert updated.endswith(sql_body)


class TestRewriteColumns:
    """Test column rewriting in @bruin blocks."""

    def test_rewrite_columns(self, tmp_path):
        """Add a new column and modify an existing one."""
        sql_content = """/* @bruin
name: core.dim__game
columns:
  - name: game_id
    type: varchar
    description: "Game ID"
  - name: game_name
    type: varchar
    description: "Game name"
@bruin */
SELECT * FROM games;
"""
        file_path = tmp_path / "dim__game.sql"
        file_path.write_text(sql_content)

        rewrite_bruin_block(
            str(file_path),
            updates={
                "columns": [
                    {
                        "name": "game_id",
                        "type": "varchar",
                        "description": "Updated Game ID",
                    },
                    {
                        "name": "game_name",
                        "type": "varchar",
                        "description": "Game name",
                    },
                    {
                        "name": "release_date",
                        "type": "date",
                        "description": "Release date",
                    },
                ]
            },
        )

        updated = file_path.read_text()
        block = _parsed_block(updated)
        columns = {c["name"]: c for c in block["columns"]}

        assert set(columns) == {"game_id", "game_name", "release_date"}
        assert columns["release_date"]["type"] == "date"
        assert columns["game_id"]["description"] == "Updated Game ID"
        assert "SELECT * FROM games;" in updated

    def test_rewrite_columns_maps_data_type_to_type(self, tmp_path):
        """`data_type` from Trellis is written as Bruin's `type`."""
        sql_content = """/* @bruin
name: core.dim__game
columns:
  - name: game_id
    type: varchar
    description: "Game ID"
@bruin */
SELECT * FROM games;
"""
        file_path = tmp_path / "dim__game.sql"
        file_path.write_text(sql_content)

        rewrite_bruin_block(
            str(file_path),
            updates={
                "columns": [
                    {
                        "name": "game_id",
                        "data_type": "varchar",
                        "description": "Updated",
                    }
                ]
            },
        )

        updated = file_path.read_text()
        block = _parsed_block(updated)
        assert block["columns"][0]["type"] == "varchar"
        assert "data_type" not in block["columns"][0]


class TestRewritePreservesColumnMetadata:
    """Bruin column metadata Trellis does not own must survive a rewrite."""

    FIXTURE = """/* @bruin
name: core.fct__order
columns:
  - name: order_id
    type: varchar
    description: "Order ID"
    primary_key: true
    nullable: false
    checks:
      - name: unique
      - name: not_null
  - name: customer_id
    type: varchar
    description: "Customer"
    foreign_key:
      table: core.dim__customer
      column: customer_id
@bruin */
SELECT * FROM orders;
"""

    def test_description_only_update_keeps_column_metadata(self, tmp_path):
        """Updating the model description must not strip column-level keys."""
        file_path = tmp_path / "fct__order.sql"
        file_path.write_text(self.FIXTURE)

        rewrite_bruin_block(str(file_path), updates={"description": "Orders"})

        columns = {
            c["name"]: c for c in _parsed_block(file_path.read_text())["columns"]
        }
        assert columns["order_id"]["primary_key"] is True
        assert columns["order_id"]["nullable"] is False
        assert columns["order_id"]["checks"] == [{"name": "unique"}, {"name": "not_null"}]
        assert columns["customer_id"]["foreign_key"] == {
            "table": "core.dim__customer",
            "column": "customer_id",
        }

    def test_column_update_round_trips_foreign_key(self, tmp_path):
        """A caller may write foreign_key/primary_key/checks through the rewriter."""
        file_path = tmp_path / "fct__order.sql"
        file_path.write_text(self.FIXTURE)

        rewrite_bruin_block(
            str(file_path),
            updates={
                "columns": [
                    {
                        "name": "order_id",
                        "data_type": "varchar",
                        "primary_key": True,
                        "checks": [{"name": "unique"}],
                    },
                    {
                        "name": "customer_id",
                        "data_type": "varchar",
                        "foreign_key": {
                            "table": "core.dim__customer",
                            "column": "customer_id",
                        },
                    },
                ]
            },
        )

        # Re-parse through the real parser, not just the YAML, so the round trip
        # is proven end to end.
        asset = parse_bruin_block(str(file_path))
        columns = {c["name"]: c for c in asset.columns}
        assert columns["order_id"]["primary_key"] is True
        assert columns["order_id"]["checks"] == [{"name": "unique"}]
        assert columns["customer_id"]["foreign_key"] == {
            "table": "core.dim__customer",
            "column": "customer_id",
        }

    def test_foreign_key_can_be_removed(self, tmp_path):
        """Omitting foreign_key on a rewritten column prunes it (stale FK cleanup)."""
        file_path = tmp_path / "fct__order.sql"
        file_path.write_text(self.FIXTURE)

        rewrite_bruin_block(
            str(file_path),
            updates={
                "columns": [
                    {"name": "order_id", "data_type": "varchar"},
                    {"name": "customer_id", "data_type": "varchar"},
                ]
            },
        )

        columns = {
            c["name"]: c for c in _parsed_block(file_path.read_text())["columns"]
        }
        assert "foreign_key" not in columns["customer_id"]


class TestRewriteTags:
    def test_rewrite_tags(self, tmp_path):
        file_path = tmp_path / "a.sql"
        file_path.write_text(
            "/* @bruin\nname: core.a\ntags:\n  - old\n@bruin */\nSELECT 1;\n"
        )

        rewrite_bruin_block(str(file_path), updates={"tags": ["core", "entity"]})

        assert _parsed_block(file_path.read_text())["tags"] == ["core", "entity"]


class TestRewriteNoBruinBlock:
    """Test error handling when no @bruin block exists."""

    def test_rewrite_no_bruin_block_raises(self, tmp_path):
        file_path = tmp_path / "no_block.sql"
        file_path.write_text("SELECT * FROM games;\n")

        with pytest.raises(ValueError, match="No @bruin block found in file"):
            rewrite_bruin_block(str(file_path), updates={"description": "test"})

    def test_rewrite_no_bruin_block_python_raises(self, tmp_path):
        file_path = tmp_path / "no_block.py"
        file_path.write_text('print("hello")\n')

        with pytest.raises(ValueError, match="No @bruin block found in file"):
            rewrite_bruin_block(str(file_path), updates={"description": "test"})


class TestWriteBruinAsset:
    """write_bruin_asset() scaffolds an asset file that does not exist yet."""

    def test_creates_file_with_valid_block(self, tmp_path):
        file_path = os.path.join(str(tmp_path), "core", "dim__new.sql")

        result = write_bruin_asset(
            file_path,
            asset={"name": "core.dim__new", "type": "duckdb.sql"},
            sql_body="-- TODO: implement core.dim__new\n",
        )

        assert str(result) == file_path
        content = open(file_path).read()
        block = _parsed_block(content)
        assert block["name"] == "core.dim__new"
        assert block["type"] == "duckdb.sql"
        assert content.rstrip().endswith("-- TODO: implement core.dim__new")

    def test_created_file_is_parseable(self, tmp_path):
        """The scaffold must survive a round trip through the real parser."""
        file_path = os.path.join(str(tmp_path), "dim__new.sql")

        write_bruin_asset(
            file_path,
            asset={
                "name": "core.dim__new",
                "type": "duckdb.sql",
                "columns": [{"name": "id", "type": "varchar"}],
            },
            sql_body="-- TODO\n",
        )

        asset = parse_bruin_block(file_path)
        assert asset is not None
        assert asset.name == "core.dim__new"
        assert asset.columns == [{"name": "id", "type": "varchar"}]

    def test_python_asset_uses_docstring_delimiters(self, tmp_path):
        file_path = os.path.join(str(tmp_path), "raw__new.py")

        write_bruin_asset(
            file_path,
            asset={"name": "raw.raw__new", "type": "python"},
            sql_body="# TODO: implement\n",
        )

        content = open(file_path).read()
        assert content.startswith('"""@bruin')
        assert '@bruin"""' in content
        assert parse_bruin_block(file_path).name == "raw.raw__new"

    def test_refuses_to_clobber_existing_file(self, tmp_path):
        file_path = os.path.join(str(tmp_path), "dim__existing.sql")
        with open(file_path, "w") as f:
            f.write("SELECT 1;\n")

        with pytest.raises(FileExistsError):
            write_bruin_asset(
                file_path, asset={"name": "core.x"}, sql_body="-- TODO\n"
            )
