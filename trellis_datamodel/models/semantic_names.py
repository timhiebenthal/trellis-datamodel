"""Names a model takes in exported semantic models."""

from typing import Any, Mapping


def semantic_dataset_name(model: Mapping[str, Any]) -> str:
    """The semantic-model dataset name for a model: its short name, version-suffixed.

    Two versions of one dbt model are two physical tables. Sharing one dataset
    name would make every relationship keyed by that name ambiguous.
    """
    name = (model.get("name") or model.get("unique_id") or "").strip()
    version = model.get("version")
    if version is not None:
        name = f"{name}_v{version}"
    return name
