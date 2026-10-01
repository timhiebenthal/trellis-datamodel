"""Origin pushed to dbt must survive the next reconcile (real adapter path)."""

import json

import yaml

from trellis_datamodel import config as cfg
from trellis_datamodel.adapters.dbt_core import DbtCoreAdapter
from trellis_datamodel.services.reconciliation import reconcile_framework

ORIGIN = [{"System": "CRM"}, {"Table": "customers"}]


def test_pushed_origin_survives_reconcile(tmp_path, monkeypatch):
    project = tmp_path / "dbt_project"
    (project / "models" / "3_core").mkdir(parents=True)
    manifest_path = project / "target" / "manifest.json"
    manifest_path.parent.mkdir(parents=True)
    data_model_path = tmp_path / "data_model.yml"

    entity = {
        "id": "customer",
        "label": "Customer",
        "model_ref": "model.proj.customer",
        "drafted_fields": [
            {"name": "id", "datatype": "int", "source": "draft"},
            {
                "name": "email",
                "datatype": "text",
                "source": "draft",
                "description": "Email address",
                "origin": ORIGIN,
            },
        ],
    }
    data_model_path.write_text(yaml.safe_dump({"entities": [entity]}))

    adapter = DbtCoreAdapter(
        manifest_path=str(manifest_path),
        catalog_path=str(project / "target" / "catalog.json"),
        project_path=str(project),
        data_model_path=str(data_model_path),
        model_paths=["3_core"],
    )

    # 1. Real push: writes schema.yml
    yml_path = adapter.save_schema_file(
        "customer", "customer", entity["drafted_fields"]
    )
    schema = yaml.safe_load(open(yml_path))
    email_col = next(
        c for c in schema["models"][0]["columns"] if c["name"] == "email"
    )
    assert email_col["meta"]["origin"] == ORIGIN  # origin is in meta
    assert "Origin" not in (email_col.get("description") or "")

    # 2. "dbt parse": manifest columns mirror schema.yml incl. meta
    manifest_cols = {
        c["name"]: {k: v for k, v in c.items() if k != "name"}
        | {"name": c["name"]}
        for c in schema["models"][0]["columns"]
    }
    manifest = {
        "nodes": {
            "model.proj.customer": {
                "unique_id": "model.proj.customer",
                "resource_type": "model",
                "name": "customer",
                "schema": "public",
                "original_file_path": "models/3_core/customer.sql",
                "config": {"materialized": "table"},
                "columns": manifest_cols,
                "tags": [],
            }
        },
        "sources": {},
    }
    manifest_path.write_text(json.dumps(manifest))

    # Adapter read side does carry origin
    cols = {c["name"]: c for c in adapter.get_models()[0]["columns"]}
    assert cols["email"]["origin"] == ORIGIN

    # 3. Reconcile as the /api/reconcile route does
    import trellis_datamodel.adapters as adapters_module

    monkeypatch.setattr(adapters_module, "get_adapter", lambda: adapter)
    monkeypatch.setattr(cfg, "DATA_MODEL_PATH", str(data_model_path))
    reconciled, _ = reconcile_framework()

    email = next(
        f for f in reconciled["entities"][0]["drafted_fields"] if f["name"] == "email"
    )
    assert email.get("origin") == ORIGIN
