from pathlib import Path

from trellis_datamodel.utils.structured_data import load_yaml_or_json


def test_loads_json_shaped_yaml_with_json_semantics(tmp_path: Path) -> None:
    path = tmp_path / "data.yml"
    path.write_text('{"entities": [{"id": "customer"}]}\n')

    assert load_yaml_or_json(path) == {"entities": [{"id": "customer"}]}


def test_loads_regular_yaml(tmp_path: Path) -> None:
    path = tmp_path / "data.yml"
    path.write_text("entities:\n  - id: customer\n")

    assert load_yaml_or_json(path) == {"entities": [{"id": "customer"}]}
