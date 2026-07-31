import pytest


def test_entity_typeddict_uses_generic_model_ref():
    from trellis_datamodel.adapters.base import Entity

    hints = Entity.__annotations__
    assert "model_ref" in hints
    assert "dbt_model" not in hints


def test_get_adapter_raises_not_implemented_for_bruin(monkeypatch):
    from trellis_datamodel import config as cfg
    from trellis_datamodel.adapters import get_adapter

    monkeypatch.setattr(cfg, "FRAMEWORK", "bruin")

    with pytest.raises(NotImplementedError, match="Bruin adapter not yet implemented"):
        get_adapter()


def test_get_adapter_still_returns_dbt_core_adapter_for_dbt_core(monkeypatch):
    from trellis_datamodel import config as cfg
    from trellis_datamodel.adapters import DbtCoreAdapter, get_adapter

    monkeypatch.setattr(cfg, "FRAMEWORK", "dbt-core")
    monkeypatch.setattr(cfg, "MANIFEST_PATH", "/tmp/manifest.json")
    monkeypatch.setattr(cfg, "CATALOG_PATH", "/tmp/catalog.json")
    monkeypatch.setattr(cfg, "DBT_PROJECT_PATH", "/tmp/dbt_project")
    monkeypatch.setattr(cfg, "DATA_MODEL_PATH", "/tmp/data_model.yml")
    monkeypatch.setattr(cfg, "DBT_MODEL_PATHS", ["models"])

    adapter = get_adapter()

    assert isinstance(adapter, DbtCoreAdapter)
