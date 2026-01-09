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
    monkeypatch.setattr(cfg, "EXPOSURES_ENABLED", False)
    monkeypatch.setattr(cfg, "EXPOSURES_DEFAULT_LAYOUT", "dashboards-as-rows")


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


def test_exposures_defaults_to_disabled(monkeypatch, tmp_path, capsys):
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

    assert cfg.EXPOSURES_ENABLED is False
    assert cfg.EXPOSURES_DEFAULT_LAYOUT == "dashboards-as-rows"
    assert "exposures" not in captured.out


def test_exposures_nested_config(monkeypatch, tmp_path):
    _prepare_config(monkeypatch)
    config_path = _write_config(
        tmp_path,
        """
        dbt_project_path: .
        exposures:
          enabled: true
          default_layout: entities-as-rows
        """,
    )

    cfg.load_config(str(config_path))

    assert cfg.EXPOSURES_ENABLED is True
    assert cfg.EXPOSURES_DEFAULT_LAYOUT == "entities-as-rows"


def test_exposures_invalid_layout_fallback(monkeypatch, tmp_path, capsys):
    _prepare_config(monkeypatch)
    config_path = _write_config(
        tmp_path,
        """
        dbt_project_path: .
        exposures:
          enabled: true
          default_layout: invalid-layout
        """,
    )

    cfg.load_config(str(config_path))
    captured = capsys.readouterr()

    assert cfg.EXPOSURES_ENABLED is True
    assert cfg.EXPOSURES_DEFAULT_LAYOUT == "dashboards-as-rows"
    assert "default_layout" in captured.out and "must be" in captured.out


def test_bus_matrix_disabled_by_default_entity_model(monkeypatch, tmp_path):
    """Bus Matrix off by default when modeling_style is entity_model (or unset)."""
    _prepare_config(monkeypatch)
    config_path = _write_config(
        tmp_path,
        """
        dbt_project_path: .
        """,
    )

    cfg.load_config(str(config_path))

    assert cfg.MODELING_STYLE == "entity_model"
    assert cfg.Bus_MATRIX_ENABLED is False


def test_bus_matrix_enabled_with_dimensional_model(monkeypatch, tmp_path):
    """Bus Matrix auto-on when modeling_style is dimensional_model."""
    _prepare_config(monkeypatch)
    config_path = _write_config(
        tmp_path,
        """
        dbt_project_path: .
        modeling_style: dimensional_model
        """,
    )

    cfg.load_config(str(config_path))

    assert cfg.MODELING_STYLE == "dimensional_model"
    assert cfg.Bus_MATRIX_ENABLED is True


def test_bus_matrix_can_disable_in_dimensional_model(monkeypatch, tmp_path):
    """Explicit bus_matrix.enabled: false can disable in dimensional mode."""
    _prepare_config(monkeypatch)
    config_path = _write_config(
        tmp_path,
        """
        dbt_project_path: .
        modeling_style: dimensional_model
        bus_matrix:
          enabled: false
        """,
    )

    cfg.load_config(str(config_path))

    assert cfg.MODELING_STYLE == "dimensional_model"
    assert cfg.Bus_MATRIX_ENABLED is False


def test_bus_matrix_ignore_enable_when_entity_model(monkeypatch, tmp_path):
    """bus_matrix.enabled: true is ignored when modeling_style is entity_model."""
    _prepare_config(monkeypatch)
    config_path = _write_config(
        tmp_path,
        """
        dbt_project_path: .
        modeling_style: entity_model
        bus_matrix:
          enabled: true
        """,
    )

    cfg.load_config(str(config_path))

    assert cfg.MODELING_STYLE == "entity_model"
    assert cfg.Bus_MATRIX_ENABLED is False
