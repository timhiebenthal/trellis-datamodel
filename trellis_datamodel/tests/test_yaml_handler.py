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
