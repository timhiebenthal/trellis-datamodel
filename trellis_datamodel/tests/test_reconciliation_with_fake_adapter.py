"""
Proves TransformationAdapter is a real abstraction: reconciliation works
against a FakeAdapter test double exactly as it does against DbtCoreAdapter,
driven solely by the adapter's get_models() output.
"""

import yaml

from trellis_datamodel.services.reconciliation import reconcile_framework


def test_reconcile_framework_uses_fake_adapter_get_models(
    monkeypatch, temp_data_model_path, fake_adapter
):
    """reconcile_framework() should reconcile using only get_models() from
    whatever adapter get_adapter() returns — here, a FakeAdapter, not dbt."""
    data_model = {
        "entities": [
            {
                "id": "users",
                "label": "Users",
                "model_ref": "model.project.users",
                "drafted_fields": [
                    {"name": "id", "datatype": "int", "source": "draft"},
                ],
            }
        ]
    }
    with open(temp_data_model_path, "w") as f:
        yaml.safe_dump(data_model, f)

    fake_adapter.models = [
        {
            "unique_id": "model.project.users",
            "name": "users",
            "version": None,
            "schema": "public",
            "table": "users",
            "columns": [
                {"name": "id", "type": "integer", "description": "Primary key"},
                {"name": "email", "type": "varchar", "description": "Email address"},
            ],
            "description": "Users table",
            "materialization": "table",
            "file_path": "models/3_core/users.sql",
            "tags": ["core"],
        }
    ]

    import trellis_datamodel.adapters as adapters_module

    monkeypatch.setattr(adapters_module, "get_adapter", lambda: fake_adapter)

    reconciled, changed = reconcile_framework()

    assert changed is True
    fields = reconciled["entities"][0]["drafted_fields"]
    names = [f["name"] for f in fields]
    assert names == ["id", "email"]

    email_field = next(f for f in fields if f["name"] == "email")
    assert email_field["datatype"] == "text"
    assert email_field["source"] == "dbt"
    assert email_field["description"] == "Email address"

    assert reconciled["entities"][0]["framework_tags"] == ["core"]
