"""Regression guards for demo-project origin fixture shapes."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DBT_DEMO = REPO_ROOT / "dbt_demo"


def test_demo_data_model_origins_are_structured_lists():
    """dbt_demo/data_model.yml origins are fully migrated to structured lists."""
    if not DBT_DEMO.exists():
        return

    data_model_path = DBT_DEMO / "data_model.yml"
    with open(data_model_path, "r") as f:
        data_model = yaml.safe_load(f)

    all_origins = [
        field.get("origin")
        for entity in data_model.get("entities", [])
        for field in entity.get("drafted_fields") or []
        if field.get("origin") is not None
    ]
    assert all_origins, "expected at least one origin entry in dbt_demo"
    legacy = [o for o in all_origins if isinstance(o, str)]
    assert not legacy, f"expected no legacy string origins, found: {legacy}"
    for origin in all_origins:
        assert isinstance(origin, list), f"origin should be a list, got: {type(origin)}"
        for entry in origin:
            assert isinstance(entry, dict), f"each origin entry should be a dict, got: {type(entry)}"


def test_demo_schema_has_meta_origin():
    """dbt_demo schema.yml has at least one column with a structured meta.origin list."""
    if not DBT_DEMO.exists():
        return

    schema_path = DBT_DEMO / "models" / "3-entity" / "dim__lead.yml"
    with open(schema_path, "r") as f:
        schema = yaml.safe_load(f)

    lead_model = next(m for m in schema["models"] if m["name"] == "dim__lead")
    cols_with_origin = [
        c for c in lead_model["columns"]
        if isinstance(c.get("meta", {}).get("origin"), list)
    ]
    assert cols_with_origin, "expected at least one column with meta.origin list in dim__lead.yml"
    for col in cols_with_origin:
        for entry in col["meta"]["origin"]:
            assert isinstance(entry, dict), f"each origin entry should be a dict, got: {entry}"
