import logging

from trellis_datamodel.utils.structured_data import load_data_model_file


def test_unset_or_missing_path_returns_empty(tmp_path):
    assert load_data_model_file(None) == {}
    assert load_data_model_file(tmp_path / "missing.yml") == {}


def test_empty_file_returns_empty(tmp_path):
    path = tmp_path / "data_model.yml"
    path.write_text("")
    assert load_data_model_file(path) == {}


def test_loads_yaml_content(tmp_path):
    path = tmp_path / "data_model.yml"
    path.write_text("entities:\n  - id: customer\n")
    assert load_data_model_file(str(path)) == {"entities": [{"id": "customer"}]}


def test_unparseable_file_returns_empty_and_logs_warning(tmp_path, caplog):
    path = tmp_path / "data_model.yml"
    path.write_text("entities: [unclosed\n")
    with caplog.at_level(logging.WARNING):
        assert load_data_model_file(path) == {}
    assert "Could not load data model" in caplog.text
