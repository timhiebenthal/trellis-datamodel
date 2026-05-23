"""Tests for path validation utilities."""

import os

import pytest

from trellis_datamodel.exceptions import ConfigurationError
from trellis_datamodel.utils.path_validation import validate_pipeline_path


def test_validate_pipeline_path_valid(monkeypatch, tmp_path):
    """Test that validate_pipeline_path returns path when valid."""
    import trellis_datamodel.config as cfg

    pipeline_dir = tmp_path / "pipeline"
    pipeline_dir.mkdir()

    monkeypatch.setattr(cfg, "BRUIN_PIPELINE_PATH", str(pipeline_dir))

    result = validate_pipeline_path()

    assert result == str(pipeline_dir)


def test_validate_pipeline_path_missing(monkeypatch):
    """Test that validate_pipeline_path raises ConfigurationError when path missing."""
    import trellis_datamodel.config as cfg

    monkeypatch.setattr(cfg, "BRUIN_PIPELINE_PATH", "/nonexistent/path/12345")

    with pytest.raises(ConfigurationError):
        validate_pipeline_path()


def test_validate_pipeline_path_not_configured(monkeypatch):
    """Test that validate_pipeline_path raises ConfigurationError when empty."""
    import trellis_datamodel.config as cfg

    monkeypatch.setattr(cfg, "BRUIN_PIPELINE_PATH", "")

    with pytest.raises(ConfigurationError):
        validate_pipeline_path()
