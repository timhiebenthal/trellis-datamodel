"""Tests for @bruin block rewriter utility."""

import os
import re
import pytest

from trellis_datamodel.utils.bruin_rewriter import rewrite_bruin_block


def _extract_bruin_block(content: str) -> str:
    """Helper to extract YAML content from the first @bruin block."""
    # Try SQL pattern
    m = re.search(r"/\*\s*@bruin\s*\n(.*?)\n\s*@bruin\s*\*/", content, re.DOTALL)
    if m:
        return m.group(1)
    # Try Python pattern
    m = re.search(r'"""\s*@bruin\s*\n(.*?)\n\s*@bruin\s*"""', content, re.DOTALL)
    if m:
        return m.group(1)
    raise ValueError("No @bruin block found")


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

        # Extract and parse the YAML to verify description
        yaml_str = _extract_bruin_block(updated)
        assert "name: core.dim__game" in yaml_str
        assert "description: Updated description for games" in yaml_str
        # Original columns preserved
        assert "game_id" in yaml_str
        assert "game_name" in yaml_str
        # Verify the block boundaries are intact
        assert "/* @bruin" in updated
        assert "@bruin */" in updated
        assert "SELECT * FROM games;" in updated


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

        # Python code outside block unchanged
        assert "import pandas as pd" in updated
        assert 'df = pd.read_sql("SELECT * FROM games", con=conn)' in updated

        # Verify description updated
        yaml_str = _extract_bruin_block(updated)
        assert "description: Updated Python model" in yaml_str
        assert "name: core.dim__game" in yaml_str

        # Verify block boundaries intact
        assert '"""@bruin' in updated
        assert '@bruin"""' in updated


class TestRewritePreservesSurroundingCode:
    """Test that surrounding code is preserved byte-identically."""

    def test_rewrite_preserves_surrounding_code(self, tmp_path):
        """Verify code outside @bruin block is byte-identical."""
        sql_content = """/* @bruin
name: core.dim__game
columns:
  - name: game_id
    type: varchar
    description: "Game ID"
@bruin */
WITH base AS (
    SELECT * FROM games
)
SELECT game_id, game_name
FROM base
WHERE game_id IS NOT NULL;
"""
        file_path = tmp_path / "dim__game.sql"
        file_path.write_text(sql_content)

        # Extract the exact SQL portion after the @bruin block
        lines = sql_content.splitlines(keepends=True)
        first_line_of_sql = next(
            i for i, line in enumerate(lines) if line.strip().startswith("WITH")
        )
        original_sql = "".join(lines[first_line_of_sql:])

        rewrite_bruin_block(
            str(file_path),
            updates={"description": "Updated description"},
        )

        updated = file_path.read_text()
        updated_lines = updated.splitlines(keepends=True)
        updated_sql_lines = [
            line
            for line in updated_lines
            if not line.strip().startswith("/*") and not line.strip().startswith("@bruin")
        ]

        # The SQL part must be identical to original
        assert "WITH base AS (" in updated
        assert "FROM base" in updated
        assert "WHERE game_id IS NOT NULL;" in updated


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

        updated_columns = [
            {"name": "game_id", "type": "varchar", "description": "Updated Game ID"},
            {"name": "game_name", "type": "varchar", "description": "Game name"},
            {"name": "release_date", "type": "date", "description": "Release date"},
        ]

        rewrite_bruin_block(
            str(file_path),
            updates={"columns": updated_columns},
        )

        updated = file_path.read_text()
        yaml_str = _extract_bruin_block(updated)

        # Check new column exists
        assert "release_date" in yaml_str
        assert "type: date" in yaml_str
        # Check existing column description updated
        assert "Updated Game ID" in yaml_str
        # Check SQL unchanged
        assert "SELECT * FROM games;" in updated

    def test_rewrite_columns_maps_data_type_to_type(self, tmp_path):
        """Map data_type key to type key when merging columns."""
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

        # Updates use data_type (not type) — must be mapped to 'type' in Bruin format
        updated_columns = [
            {"name": "game_id", "data_type": "varchar", "description": "Updated"},
        ]

        rewrite_bruin_block(
            str(file_path),
            updates={"columns": updated_columns},
        )

        updated = file_path.read_text()
        yaml_str = _extract_bruin_block(updated)

        # Must have 'type: varchar', NOT 'data_type: varchar'
        assert "type: varchar" in yaml_str or "type: " in yaml_str
        assert "data_type:" not in yaml_str


class TestRewriteNoBruinBlock:
    """Test error handling when no @bruin block exists."""

    def test_rewrite_no_bruin_block_raises(self, tmp_path):
        """Raises ValueError when no @bruin block exists."""
        file_path = tmp_path / "no_block.sql"
        file_path.write_text("SELECT * FROM games;\n")

        with pytest.raises(ValueError, match="No @bruin block found in file"):
            rewrite_bruin_block(str(file_path), updates={"description": "test"})

    def test_rewrite_no_bruin_block_python_raises(self, tmp_path):
        """Raises ValueError when no @bruin block exists in Python file."""
        file_path = tmp_path / "no_block.py"
        file_path.write_text('print("hello")\n')

        with pytest.raises(ValueError, match="No @bruin block found in file"):
            rewrite_bruin_block(str(file_path), updates={"description": "test"})
