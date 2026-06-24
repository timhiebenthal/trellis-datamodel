"""Regression guards for demo-project origin fixture shapes."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DBT_DEMO = REPO_ROOT / "dbt_demo"


def test_demo_data_model_retains_legacy_string_origin():
    """dbt_demo/data_model.yml keeps pipe-string origins for silent migration."""
    if not DBT_DEMO.exists():
        return

    data_model_path = DBT_DEMO / "data_model.yml"
    with open(data_model_path, "r") as f:
        data_model = yaml.safe_load(f)

    legacy_origins = [
        field.get("origin")
        for entity in data_model.get("entities", [])
        for field in entity.get("drafted_fields") or []
        if isinstance(field.get("origin"), str) and field.get("origin")
    ]
    assert legacy_origins, "expected at least one legacy string origin in dbt_demo"


def test_demo_schema_has_hand_written_meta_origin():
    """dbt_demo schema.yml includes at least one column with meta.origin."""
    if not DBT_DEMO.exists():
        return

    schema_path = DBT_DEMO / "models" / "3-entity" / "dim__lead.yml"
    with open(schema_path, "r") as f:
        schema = yaml.safe_load(f)

    lead_model = next(m for m in schema["models"] if m["name"] == "dim__lead")
    lead_key = next(c for c in lead_model["columns"] if c["name"] == "lead_key")
    assert lead_key.get("meta", {}).get("origin") == [
        {"DH1": "CORE.T_DYN_LEAD.LEADKEY"},
        {"DH2": "SCD2_LEAD.LEADKEY"},
    ]
