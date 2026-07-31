"""Golden characterization test for data_model.yml round-tripping.

Locks current load/save behavior for `dbt_demo/data_model.yml` before the
planned `dbt_model` -> `model_ref` / `dbt_tags` -> `framework_tags` rename
(see specs/2026-07-31-generalize-transformation-adapter/). This test must
keep passing across that rename: `_normalize_entity` below is the single
place allowed to know both the old and new key literals.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import pytest

from trellis_datamodel import config as cfg
from trellis_datamodel.routes.data_model import load_data_model_raw, save_data_model_raw

REPO_ROOT = Path(__file__).resolve().parents[2]
DBT_DEMO_DATA_MODEL = REPO_ROOT / "dbt_demo" / "data_model.yml"


def _normalize_entity(entity: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize an entity dict to a rename-agnostic semantic shape.

    This is the ONE place in this test file allowed to reference the raw
    key literals (`model_ref`/`dbt_model`, `framework_tags`/`dbt_tags`).
    Everything else in this file must assert only on the normalized form.
    """
    return {
        "model_binding": entity.get("model_ref") or entity.get("dbt_model"),
        "framework_tags": entity.get("framework_tags") or entity.get("dbt_tags"),
        "ui_tags": entity.get("ui_tags"),
        "additional_models": entity.get("additional_models"),
        "drafted_fields": entity.get("drafted_fields"),
        "entity_type": entity.get("entity_type"),
        "description": entity.get("description"),
    }


def test_dbt_demo_data_model_loads_and_roundtrips_semantically(monkeypatch, tmp_path):
    # dbt_demo/ is gitignored (local-only sample project) and is not present
    # in a fresh CI checkout; skip rather than fail when it's absent, matching
    # the convention in test_demo_origin_fixtures.py.
    if not DBT_DEMO_DATA_MODEL.exists():
        pytest.skip(f"dbt_demo fixture not present at {DBT_DEMO_DATA_MODEL}")

    # Load the original fixture through the real load path.
    monkeypatch.setattr(cfg, "DATA_MODEL_PATH", str(DBT_DEMO_DATA_MODEL))
    original_model = load_data_model_raw()

    original_entities = original_model.get("entities") or []
    assert original_entities, "expected at least one entity in dbt_demo/data_model.yml"

    original_by_id = {
        entity["id"]: _normalize_entity(entity) for entity in original_entities
    }

    # Save to a temp path via the real save path, then reload through the
    # real load path again.
    temp_path = tmp_path / "data_model.yml"
    monkeypatch.setattr(cfg, "DATA_MODEL_PATH", str(temp_path))
    save_data_model_raw(original_model)

    assert os.path.exists(temp_path)

    reloaded_model = load_data_model_raw()
    reloaded_entities = reloaded_model.get("entities") or []

    reloaded_by_id = {
        entity["id"]: _normalize_entity(entity) for entity in reloaded_entities
    }

    assert set(reloaded_by_id.keys()) == set(original_by_id.keys())

    for entity_id, original_normalized in original_by_id.items():
        assert reloaded_by_id[entity_id] == original_normalized, (
            f"entity {entity_id!r} changed semantically after round-trip"
        )
