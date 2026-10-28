import logging
from pathlib import Path

import pytest
import yaml

from trellis_datamodel.utils.structured_data import (
    load_yaml_file,
    load_yaml_or_json,
    save_yaml_file,
    try_load_yaml_file,
)


def test_loads_json_shaped_yaml_with_json_semantics(tmp_path: Path) -> None:
    path = tmp_path / "data.yml"
    path.write_text('{"entities": [{"id": "customer"}]}\n')

    assert load_yaml_or_json(path) == {"entities": [{"id": "customer"}]}


def test_loads_regular_yaml(tmp_path: Path) -> None:
    path = tmp_path / "data.yml"
    path.write_text("entities:\n  - id: customer\n")

    assert load_yaml_or_json(path) == {"entities": [{"id": "customer"}]}


class TestLoadYamlFile:
    def test_missing_or_unset_path_returns_default(self, tmp_path: Path) -> None:
        assert load_yaml_file(tmp_path / "missing.yml", {}) == {}
        assert load_yaml_file("", {"x": 1}) == {"x": 1}
        assert load_yaml_file(None) is None

    def test_empty_file_returns_default(self, tmp_path: Path) -> None:
        path = tmp_path / "empty.yml"
        path.write_text("")

        assert load_yaml_file(path, {}) == {}

    def test_malformed_yaml_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.yml"
        path.write_text("entities: [unclosed")

        with pytest.raises(yaml.YAMLError):
            load_yaml_file(path, {})

    def test_unreadable_path_raises(self, tmp_path: Path) -> None:
        with pytest.raises(OSError):
            load_yaml_file(tmp_path, {})


class TestTryLoadYamlFile:
    def test_malformed_yaml_warns_and_returns_default(self, tmp_path: Path, caplog) -> None:
        path = tmp_path / "bad.yml"
        path.write_text("entities: [unclosed")

        with caplog.at_level(logging.WARNING):
            assert try_load_yaml_file(path, {}) == {}
        assert str(path) in caplog.text

    def test_loads_valid_file(self, tmp_path: Path) -> None:
        path = tmp_path / "data.yml"
        path.write_text("entities: []\n")

        assert try_load_yaml_file(path, {}) == {"entities": []}


def test_save_yaml_file_writes_block_style_in_key_order(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "data.yml"

    save_yaml_file(path, {"zeta": [1, 2], "alpha": {"b": 1}})

    assert path.read_text() == "zeta:\n- 1\n- 2\nalpha:\n  b: 1\n"
