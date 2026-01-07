"""Tests for configuration loading."""

import textwrap
from pathlib import Path

import trellis_datamodel.config as cfg


def _prepare_config(monkeypatch):
    """Reset config globals and disable test-mode short-circuiting."""
    monkeypatch.setattr(cfg, "_TEST_DIR", "")
    monkeypatch.delenv("DATAMODEL_TEST_DIR", raising=False)
    monkeypatch.setattr(cfg, "CONFIG_PATH", "")
    monkeypatch.setattr(cfg, "DBT_PROJECT_PATH", "")
    monkeypatch.setattr(cfg, "LINEAGE_ENABLED", False)
    monkeypatch.setattr(cfg, "LINEAGE_LAYERS", [])


def _write_config(tmp_path: Path, contents: str) -> Path:
    path = tmp_path / "trellis.yml"
    path.write_text(textwrap.dedent(contents))
    return path


def test_lineage_defaults_to_disabled(monkeypatch, tmp_path, capsys):
    _prepare_config(monkeypatch)
    config_path = _write_config(
        tmp_path,
        """
        framework: dbt-core
        dbt_project_path: .
        """,
    )

    cfg.load_config(str(config_path))
    captured = capsys.readouterr()

    assert cfg.LINEAGE_ENABLED is False
    assert cfg.LINEAGE_LAYERS == []
    assert "lineage_layers" not in captured.out


def test_lineage_nested_config(monkeypatch, tmp_path):
    _prepare_config(monkeypatch)
    config_path = _write_config(
        tmp_path,
        """
        dbt_project_path: .
        lineage:
          enabled: true
          layers:
            - core
            - marts
        """,
    )

    cfg.load_config(str(config_path))

    assert cfg.LINEAGE_ENABLED is True
    assert cfg.LINEAGE_LAYERS == ["core", "marts"]


def test_lineage_legacy_layers_with_warning(monkeypatch, tmp_path, capsys):
    _prepare_config(monkeypatch)
    config_path = _write_config(
        tmp_path,
        """
        dbt_project_path: .
        lineage_layers:
          - legacy
        """,
    )

    cfg.load_config(str(config_path))
    captured = capsys.readouterr()

    assert cfg.LINEAGE_ENABLED is False
    assert cfg.LINEAGE_LAYERS == ["legacy"]
    assert "deprecated" in captured.out


def test_lineage_prefers_nested_over_legacy(monkeypatch, tmp_path, capsys):
    _prepare_config(monkeypatch)
    config_path = _write_config(
        tmp_path,
        """
        dbt_project_path: .
        lineage_layers:
          - legacy
        lineage:
          enabled: false
          layers:
            - nested
        """,
    )

    cfg.load_config(str(config_path))
    captured = capsys.readouterr()

    assert cfg.LINEAGE_ENABLED is False
    assert cfg.LINEAGE_LAYERS == ["nested"]
    assert "deprecated" in captured.out
