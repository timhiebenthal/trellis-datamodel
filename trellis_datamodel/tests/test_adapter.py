"""Tests for adapter factory."""

from trellis_datamodel.adapters import get_adapter
from trellis_datamodel.adapters.bruin import BruinAdapter


def test_get_adapter_bruin(monkeypatch):
    """Test that get_adapter() returns BruinAdapter when framework is bruin."""
    import trellis_datamodel.config as cfg

    monkeypatch.setattr(cfg, "FRAMEWORK", "bruin")
    monkeypatch.setattr(cfg, "BRUIN_PIPELINE_PATH", "/tmp/bruin_pipeline")
    monkeypatch.setattr(cfg, "BRUIN_ASSET_PATHS", [])
    monkeypatch.setattr(cfg, "DATA_MODEL_PATH", "/tmp/data_model.yml")

    adapter = get_adapter()

    assert isinstance(adapter, BruinAdapter)
    assert adapter.pipeline_path == "/tmp/bruin_pipeline"
    assert adapter.asset_paths == []
    assert adapter.data_model_path == "/tmp/data_model.yml"
