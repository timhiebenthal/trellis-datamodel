"""Tests for YamlHandler utility class."""

import os
import pytest
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from trellis_datamodel.utils.yaml_handler import YamlHandler


class TestYamlHandlerFileOperations:
    """Test file I/O operations."""

    def test_load_nonexistent_file(self, temp_dir):
        handler = YamlHandler()
        result = handler.load_file(os.path.join(temp_dir, "missing.yml"))
        assert result is None

    def test_load_and_save_file(self, temp_dir):
        handler = YamlHandler()
        file_path = os.path.join(temp_dir, "test.yml")

        # Save data
        data = {"version": 2, "models": [{"name": "test_model"}]}
        handler.save_file(file_path, data)

        # Load data back
        loaded = handler.load_file(file_path)
        assert loaded is not None
        assert loaded["version"] == 2
        assert loaded["models"][0]["name"] == "test_model"

    def test_save_creates_directories(self, temp_dir):
        handler = YamlHandler()
        nested_path = os.path.join(temp_dir, "nested", "deep", "test.yml")
        data = {"version": 2}
        handler.save_file(nested_path, data)
        assert os.path.exists(nested_path)


class TestYamlHandlerModelOperations:
    """Test model-level operations."""

    def test_find_model_returns_none_for_empty_data(self):
        handler = YamlHandler()
        assert handler.find_model({}, "test") is None
        assert handler.find_model({"models": []}, "test") is None

    def test_find_model_returns_match(self):
        handler = YamlHandler()
        data = {"models": [{"name": "users"}, {"name": "orders"}]}
        result = handler.find_model(data, "users")
        assert result is not None
        assert result["name"] == "users"

    def test_ensure_model_creates_new(self):
        handler = YamlHandler()
        data = {}
        model = handler.ensure_model(data, "new_model")

        assert "version" in data
        assert data["version"] == 2
        assert model["name"] == "new_model"
        # Tags are not auto-created; update_model_tags handles them when needed
        assert "tags" not in model

    def test_ensure_model_returns_existing(self):
        handler = YamlHandler()
        existing = CommentedMap({"name": "existing", "description": "test"})
        data = {"version": 2, "models": CommentedSeq([existing])}

        model = handler.ensure_model(data, "existing")
        assert model["description"] == "test"
        assert len(data["models"]) == 1

    def test_update_model_description(self):
        handler = YamlHandler()
        model = CommentedMap({"name": "test"})
        handler.update_model_description(model, "New description")
        assert model["description"] == "New description"

    def test_update_model_description_skips_none(self):
        handler = YamlHandler()
        model = CommentedMap({"name": "test"})
        handler.update_model_description(model, None)
        assert "description" not in model

    def test_update_model_tags(self):
        handler = YamlHandler()
        model = CommentedMap({"name": "test", "tags": []})
        handler.update_model_tags(model, ["core", "pii"])
        assert model["tags"] == ["core", "pii"]

    def test_update_model_tags_uses_config_as_default(self):
        handler = YamlHandler()
        model = CommentedMap({"name": "test"})
        handler.update_model_tags(model, ["core", "pii"])
        # Should use config.tags as default when no tags exist
        assert "tags" not in model
        assert model["config"]["tags"] == ["core", "pii"]

    def test_update_model_tags_preserves_config_location(self):
        handler = YamlHandler()
        model = CommentedMap({"name": "test", "config": {"tags": ["old"]}})
        handler.update_model_tags(model, ["new"])
        # Should update in config.tags (original location)
        assert model["config"]["tags"] == ["new"]
        assert "tags" not in model


class TestYamlHandlerColumnOperations:
    """Test column-level operations."""

    def test_find_column_returns_none_for_missing(self):
        handler = YamlHandler()
        model = CommentedMap({"name": "test", "columns": []})
        assert handler.find_column(model, "missing") is None

    def test_find_column_returns_match(self):
        handler = YamlHandler()
        model = CommentedMap(
            {"name": "test", "columns": [{"name": "id"}, {"name": "name"}]}
        )
        result = handler.find_column(model, "id")
        assert result is not None
        assert result["name"] == "id"

    def test_ensure_column_creates_new(self):
        handler = YamlHandler()
        model = CommentedMap({"name": "test"})
        col = handler.ensure_column(model, "new_col")

        assert "columns" in model
        assert col["name"] == "new_col"

    def test_ensure_column_returns_existing(self):
        handler = YamlHandler()
        model = CommentedMap(
            {
                "name": "test",
                "columns": CommentedSeq(
                    [CommentedMap({"name": "existing", "data_type": "int"})]
                ),
            }
        )
        col = handler.ensure_column(model, "existing")
        assert col["data_type"] == "int"
        assert len(model["columns"]) == 1

    def test_update_column(self):
        handler = YamlHandler()
        col = CommentedMap({"name": "test"})
        handler.update_column(col, data_type="text", description="A test column")

        assert col["data_type"] == "text"
        assert col["description"] == "A test column"

    def test_update_column_skips_none(self):
        handler = YamlHandler()
        col = CommentedMap({"name": "test"})
        handler.update_column(col, data_type=None, description=None)
        assert "data_type" not in col
        assert "description" not in col

    def test_update_columns_batch(self):
        handler = YamlHandler()
        model = CommentedMap({"name": "test"})
        columns_data = [
            {"name": "id", "data_type": "int"},
            {"name": "name", "data_type": "text", "description": "User name"},
        ]
        handler.update_columns_batch(model, columns_data)

        assert len(model["columns"]) == 2
        assert model["columns"][0]["data_type"] == "int"
        assert model["columns"][1]["description"] == "User name"

    def test_get_columns(self):
        handler = YamlHandler()
        model = CommentedMap(
            {
                "name": "test",
                "columns": [
                    {"name": "id", "data_type": "int", "description": "Primary key"},
                    {"name": "name", "data_type": "text"},
                ],
            }
        )
        cols = handler.get_columns(model)
        assert len(cols) == 2
        assert cols[0]["name"] == "id"
        assert cols[0]["description"] == "Primary key"


class TestYamlHandlerRelationshipTests:
    """Test relationship test operations."""

    def test_add_relationship_test(self):
        handler = YamlHandler()
        col = CommentedMap({"name": "user_id"})
        handler.add_relationship_test(col, "users", "id")

        assert "data_tests" in col
        assert len(col["data_tests"]) == 1
        rel = col["data_tests"][0]["relationships"]
        assert rel["arguments"]["to"] == "ref('users')"
        assert rel["arguments"]["field"] == "id"

    def test_add_relationship_test_replaces_existing(self):
        handler = YamlHandler()
        col = CommentedMap(
            {
                "name": "user_id",
                "data_tests": CommentedSeq(
                    [
                        CommentedMap(
                            {"relationships": {"to": "ref('old')", "field": "old_id"}}
                        ),
                        CommentedMap({"not_null": {}}),
                    ]
                ),
            }
        )
        handler.add_relationship_test(col, "new_model", "new_id")

        # Should replace relationship but keep other tests
        assert len(col["data_tests"]) == 2
        rel_test = next(t for t in col["data_tests"] if "relationships" in t)
        assert rel_test["relationships"]["arguments"]["to"] == "ref('new_model')"


class TestYamlIndentation:
    """Test YAML indentation formatting (regression test for issue #19)."""

    def test_models_list_indentation(self, temp_dir):
        """Test that models list items are properly indented under the models key."""
        handler = YamlHandler()
        file_path = os.path.join(temp_dir, "test_indentation.yml")

        # Create data with a plain Python list (simulates real usage in dbt_core.py)
        data = {"version": 2, "models": [{"name": "test_model", "description": "Test"}]}
        handler.save_file(file_path, data)

        # Read the raw file text
        with open(file_path, "r") as f:
            content = f.read()

        # Assert proper indentation: models list items should be indented 2 spaces
        # Expected format:
        # models:
        #   - name: test_model
        assert (
            "models:\n  - name:" in content
        ), f"Expected proper indentation, got:\n{content}"

    def test_ensure_model_normalizes_plain_list(self, temp_dir):
        """Test that ensure_model normalizes plain Python lists to CommentedSeq."""
        handler = YamlHandler()
        file_path = os.path.join(temp_dir, "test_normalize.yml")

        # Start with a plain Python list
        data = {"version": 2, "models": []}

        # Call ensure_model which should normalize the list
        handler.ensure_model(data, "new_model")

        # Verify it's now a CommentedSeq
        assert isinstance(data["models"], CommentedSeq)

        # Save and verify indentation
        handler.save_file(file_path, data)

        with open(file_path, "r") as f:
            content = f.read()

        assert (
            "models:\n  - name:" in content
        ), f"Expected proper indentation after normalization, got:\n{content}"


class TestTagHandling:
    """Test tag handling improvements (issue #20)."""

    def test_update_model_tags_skips_empty_tags(self):
        """Test that empty tags arrays are not written to YAML (Point 1)."""
        handler = YamlHandler()
        model = CommentedMap({"name": "test"})

        # Update with empty tags - should not create tags key
        handler.update_model_tags(model, [])

        assert "tags" not in model
        assert "config" not in model

    def test_update_model_tags_removes_existing_empty_tags(self):
        """Test that existing tags are removed when updated to empty (Point 1)."""
        handler = YamlHandler()
        model = CommentedMap({"name": "test", "tags": ["old_tag"]})

        # Update with empty tags - should remove existing tags
        handler.update_model_tags(model, [])

        assert "tags" not in model

    def test_update_model_tags_removes_config_tags_when_empty(self):
        """Test that config.tags are removed when updated to empty (Point 1)."""
        handler = YamlHandler()
        model = CommentedMap(
            {
                "name": "test",
                "config": CommentedMap({"tags": ["old_tag"], "materialized": "table"}),
            }
        )

        # Update with empty tags - should remove config.tags but keep config
        handler.update_model_tags(model, [])

        assert "tags" not in model["config"]
        assert model["config"]["materialized"] == "table"

    def test_update_version_tags_skips_empty_tags(self):
        """Test that empty tags arrays are not written for versions (Point 1)."""
        handler = YamlHandler()
        version = CommentedMap({"v": 2})

        # Update with empty tags - should not create config
        handler.update_version_tags(version, [])

        assert "config" not in version

    def test_update_version_tags_removes_existing_empty_tags(self):
        """Test that existing version tags are removed when updated to empty (Point 1)."""
        handler = YamlHandler()
        version = CommentedMap({"v": 2, "config": CommentedMap({"tags": ["old_tag"]})})

        # Update with empty tags - should remove config.tags
        handler.update_version_tags(version, [])

        assert "tags" not in version["config"]

    def test_config_placement_after_description(self, temp_dir):
        """Test that config block is placed after description (Point 2)."""
        handler = YamlHandler()
        file_path = os.path.join(temp_dir, "test_config_placement.yml")

        # Create model with name and description, then add tags
        model = CommentedMap()
        model["name"] = "test_model"
        model["description"] = "A test model"

        handler.update_model_tags(model, ["core"])

        # Save and check order
        data = {"version": 2, "models": [model]}
        handler.save_file(file_path, data)

        with open(file_path, "r") as f:
            content = f.read()

        # Config should appear after description
        desc_pos = content.find("description:")
        config_pos = content.find("config:")

        assert desc_pos > 0, "Description should be present"
        assert config_pos > 0, "Config should be present"
        assert config_pos > desc_pos, "Config should appear after description"

    def test_config_placement_before_columns(self, temp_dir):
        """Test that config block is placed before columns (Point 2)."""
        handler = YamlHandler()
        file_path = os.path.join(temp_dir, "test_config_before_columns.yml")

        # Create model with name, description, and columns
        model = CommentedMap()
        model["name"] = "test_model"
        model["description"] = "A test model"
        model["columns"] = CommentedSeq([CommentedMap({"name": "id"})])

        # Add tags - should insert config before columns
        handler.update_model_tags(model, ["core"])

        # Save and check order
        data = {"version": 2, "models": [model]}
        handler.save_file(file_path, data)

        with open(file_path, "r") as f:
            content = f.read()

        # Config should appear before columns
        config_pos = content.find("config:")
        columns_pos = content.find("columns:")

        assert config_pos > 0, "Config should be present"
        assert columns_pos > 0, "Columns should be present"
        assert config_pos < columns_pos, "Config should appear before columns"

    def test_config_placement_after_name_when_no_description(self, temp_dir):
        """Test that config is placed after name when description is missing (Point 2)."""
        handler = YamlHandler()
        file_path = os.path.join(temp_dir, "test_config_after_name.yml")

        # Create model with only name
        model = CommentedMap()
        model["name"] = "test_model"

        handler.update_model_tags(model, ["core"])

        # Save and check order
        data = {"version": 2, "models": [model]}
        handler.save_file(file_path, data)

        with open(file_path, "r") as f:
            content = f.read()

        # Config should appear after name
        name_pos = content.find("name:")
        config_pos = content.find("config:")

        assert name_pos > 0, "Name should be present"
        assert config_pos > 0, "Config should be present"
        assert config_pos > name_pos, "Config should appear after name"

    def test_version_config_placement(self, temp_dir):
        """Test that config block in versions is placed correctly (Point 2)."""
        handler = YamlHandler()
        file_path = os.path.join(temp_dir, "test_version_config.yml")

        # Create version with description
        version = CommentedMap()
        version["v"] = 2
        version["description"] = "Version 2"

        handler.update_version_tags(version, ["core"])

        # Save and check order
        model = CommentedMap()
        model["name"] = "test_model"
        model["versions"] = CommentedSeq([version])
        data = {"version": 2, "models": [model]}
        handler.save_file(file_path, data)

        with open(file_path, "r") as f:
            content = f.read()

        # In the version block, config should appear after description
        lines = content.split("\n")
        v_line = next(i for i, line in enumerate(lines) if "v:" in line)
        desc_line = next(
            i for i, line in enumerate(lines) if i > v_line and "description:" in line
        )
        config_line = next(
            i for i, line in enumerate(lines) if i > v_line and "config:" in line
        )

        assert (
            config_line > desc_line
        ), "Config should appear after description in version block"
