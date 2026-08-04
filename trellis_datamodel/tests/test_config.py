"""Tests for configuration loading."""

import importlib
import os
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
    monkeypatch.setattr(cfg, "ENTITY_MODELING_CONFIG", cfg.EntityModelingConfig())
    monkeypatch.setattr(cfg, "BRUIN_PIPELINE_PATH", "")
    monkeypatch.setattr(cfg, "BRUIN_ASSET_PATHS", [])
    monkeypatch.setattr(cfg, "BRUIN_DEFAULT_ASSET_TYPE", "duckdb.sql")


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


def test_inference_patterns_string_format(monkeypatch, tmp_path):
    """Test that inference patterns support string format (converted to list)."""
    _prepare_config(monkeypatch)
    config_path = _write_config(
        tmp_path,
        """
        dbt_project_path: .
        modeling_style: dimensional_model
        dimensional_modeling:
          inference_patterns:
            dimension_prefix: "d_"
            fact_prefix: "f_"
        """,
    )

    cfg.load_config(str(config_path))

    assert isinstance(cfg.DIMENSIONAL_MODELING_CONFIG.dimension_prefix, list)
    assert cfg.DIMENSIONAL_MODELING_CONFIG.dimension_prefix == ["d_"]
    assert isinstance(cfg.DIMENSIONAL_MODELING_CONFIG.fact_prefix, list)
    assert cfg.DIMENSIONAL_MODELING_CONFIG.fact_prefix == ["f_"]


def test_inference_patterns_list_format(monkeypatch, tmp_path):
    """Test that inference patterns preserve list format."""
    _prepare_config(monkeypatch)
    config_path = _write_config(
        tmp_path,
        """
        dbt_project_path: .
        modeling_style: dimensional_model
        dimensional_modeling:
          inference_patterns:
            dimension_prefix: ["dim_", "d_"]
            fact_prefix: ["fct_", "fact_"]
        """,
    )

    cfg.load_config(str(config_path))

    assert isinstance(cfg.DIMENSIONAL_MODELING_CONFIG.dimension_prefix, list)
    assert cfg.DIMENSIONAL_MODELING_CONFIG.dimension_prefix == ["dim_", "d_"]
    assert isinstance(cfg.DIMENSIONAL_MODELING_CONFIG.fact_prefix, list)
    assert cfg.DIMENSIONAL_MODELING_CONFIG.fact_prefix == ["fct_", "fact_"]


def test_inference_patterns_mixed_string_list(monkeypatch, tmp_path):
    """Test that mixing string and list formats works."""
    _prepare_config(monkeypatch)
    config_path = _write_config(
        tmp_path,
        """
        dbt_project_path: .
        modeling_style: dimensional_model
        dimensional_modeling:
          inference_patterns:
            dimension_prefix: "d_"
            fact_prefix: ["fct_", "fact_"]
        """,
    )

    cfg.load_config(str(config_path))

    assert isinstance(cfg.DIMENSIONAL_MODELING_CONFIG.dimension_prefix, list)
    assert cfg.DIMENSIONAL_MODELING_CONFIG.dimension_prefix == ["d_"]
    assert isinstance(cfg.DIMENSIONAL_MODELING_CONFIG.fact_prefix, list)
    assert cfg.DIMENSIONAL_MODELING_CONFIG.fact_prefix == ["fct_", "fact_"]


def test_inference_patterns_defaults_when_missing(monkeypatch, tmp_path):
    """Test that defaults are used when inference_patterns is missing."""
    _prepare_config(monkeypatch)
    config_path = _write_config(
        tmp_path,
        """
        dbt_project_path: .
        modeling_style: dimensional_model
        """,
    )

    cfg.load_config(str(config_path))

    assert isinstance(cfg.DIMENSIONAL_MODELING_CONFIG.dimension_prefix, list)
    assert cfg.DIMENSIONAL_MODELING_CONFIG.dimension_prefix == ["dim_", "d_"]
    assert isinstance(cfg.DIMENSIONAL_MODELING_CONFIG.fact_prefix, list)
    assert cfg.DIMENSIONAL_MODELING_CONFIG.fact_prefix == ["fct_", "fact_"]


# ===== Entity Modeling Configuration Tests (Stream D) =====


def test_entity_prefix_empty_list_default(monkeypatch, tmp_path):
    """Test empty prefix list (default behavior)."""
    _prepare_config(monkeypatch)
    config_path = _write_config(
        tmp_path,
        """
        dbt_project_path: .
        modeling_style: entity_model
        """,
    )

    cfg.load_config(str(config_path))

    assert cfg.ENTITY_MODELING_CONFIG.enabled is True
    assert isinstance(cfg.ENTITY_MODELING_CONFIG.entity_prefix, list)
    assert cfg.ENTITY_MODELING_CONFIG.entity_prefix == []


def test_entity_prefix_single_string(monkeypatch, tmp_path):
    """Test single string prefix configuration."""
    _prepare_config(monkeypatch)
    config_path = _write_config(
        tmp_path,
        """
        dbt_project_path: .
        modeling_style: entity_model
        entity_modeling:
          inference_patterns:
            prefix: "tbl_"
        """,
    )

    cfg.load_config(str(config_path))

    assert cfg.ENTITY_MODELING_CONFIG.enabled is True
    assert isinstance(cfg.ENTITY_MODELING_CONFIG.entity_prefix, list)
    assert cfg.ENTITY_MODELING_CONFIG.entity_prefix == ["tbl_"]


def test_entity_prefix_list_of_prefixes(monkeypatch, tmp_path):
    """Test list of prefixes configuration."""
    _prepare_config(monkeypatch)
    config_path = _write_config(
        tmp_path,
        """
        dbt_project_path: .
        modeling_style: entity_model
        entity_modeling:
          inference_patterns:
            prefix: ["tbl_", "entity_", "t_"]
        """,
    )

    cfg.load_config(str(config_path))

    assert cfg.ENTITY_MODELING_CONFIG.enabled is True
    assert isinstance(cfg.ENTITY_MODELING_CONFIG.entity_prefix, list)
    assert cfg.ENTITY_MODELING_CONFIG.entity_prefix == ["tbl_", "entity_", "t_"]


def test_entity_modeling_enabled_when_entity_model(monkeypatch, tmp_path):
    """Test config loads correctly when modeling_style = entity_model."""
    _prepare_config(monkeypatch)
    config_path = _write_config(
        tmp_path,
        """
        dbt_project_path: .
        modeling_style: entity_model
        entity_modeling:
          inference_patterns:
            prefix: "tbl_"
        """,
    )

    cfg.load_config(str(config_path))

    assert cfg.MODELING_STYLE == "entity_model"
    assert cfg.ENTITY_MODELING_CONFIG.enabled is True
    assert cfg.ENTITY_MODELING_CONFIG.entity_prefix == ["tbl_"]


def test_entity_modeling_disabled_when_dimensional_model(monkeypatch, tmp_path):
    """Test config disabled when modeling_style = dimensional_model."""
    _prepare_config(monkeypatch)
    config_path = _write_config(
        tmp_path,
        """
        dbt_project_path: .
        modeling_style: dimensional_model
        entity_modeling:
          inference_patterns:
            prefix: "tbl_"
        """,
    )

    cfg.load_config(str(config_path))

    assert cfg.MODELING_STYLE == "dimensional_model"
    assert cfg.ENTITY_MODELING_CONFIG.enabled is False
    assert cfg.ENTITY_MODELING_CONFIG.entity_prefix == []


def test_framework_enum_lists_only_implemented_frameworks():
    """The enum advertises what Trellis can actually do.

    A framework value only becomes selectable once its adapter exists, so a user
    cannot configure a framework that has no working implementation behind it.
    Adding a value here without an adapter is the failure this test exists to
    catch — extend it in the same commit that lands the adapter, never before.
    """
    from trellis_datamodel.adapters import get_adapter
    from trellis_datamodel.models.schemas import FrameworkEnum

    assert [f.value for f in FrameworkEnum] == ["dbt-core", "bruin"]

    # Every listed framework must be constructible by the factory, which is the
    # substance behind the claim above.
    for framework in FrameworkEnum:
        cfg_module = importlib.import_module("trellis_datamodel.config")
        original = cfg_module.FRAMEWORK
        try:
            cfg_module.FRAMEWORK = framework.value
            assert get_adapter() is not None
        finally:
            cfg_module.FRAMEWORK = original


def test_load_config_resolves_bruin_pipeline_path(monkeypatch, tmp_path):
    """Bruin framework config resolves pipeline path and asset paths."""
    _prepare_config(monkeypatch)
    config_path = _write_config(
        tmp_path,
        """
        framework: bruin
        bruin_pipeline_path: ./pipeline
        bruin_asset_paths:
          - assets
        """,
    )

    cfg.load_config(str(config_path))

    assert cfg.FRAMEWORK == "bruin"
    assert os.path.isabs(cfg.BRUIN_PIPELINE_PATH)
    assert cfg.BRUIN_PIPELINE_PATH == os.path.abspath(tmp_path / "pipeline")
    assert cfg.BRUIN_ASSET_PATHS == ["assets"]


def test_bruin_pipeline_path_resolved_regardless_of_framework(monkeypatch, tmp_path):
    """Resolution is unconditional so config reporting does not depend on load order."""
    _prepare_config(monkeypatch)
    config_path = _write_config(
        tmp_path,
        """
        framework: dbt-core
        bruin_pipeline_path: ./pipeline
        """,
    )

    cfg.load_config(str(config_path))

    assert cfg.BRUIN_PIPELINE_PATH == os.path.abspath(tmp_path / "pipeline")


def test_bruin_default_asset_type_is_configurable(monkeypatch, tmp_path):
    """Scaffolding needs an asset type, and it is platform-specific."""
    _prepare_config(monkeypatch)
    config_path = _write_config(
        tmp_path,
        """
        framework: bruin
        bruin_pipeline_path: ./pipeline
        bruin_default_asset_type: bq.sql
        """,
    )

    cfg.load_config(str(config_path))

    assert cfg.BRUIN_DEFAULT_ASSET_TYPE == "bq.sql"


def test_bruin_defaults_when_unset(monkeypatch, tmp_path):
    """A dbt project leaves the Bruin fields empty, not absent."""
    _prepare_config(monkeypatch)
    config_path = _write_config(tmp_path, "framework: dbt-core\n")

    cfg.load_config(str(config_path))

    assert cfg.BRUIN_PIPELINE_PATH == ""
    assert cfg.BRUIN_ASSET_PATHS == []
    assert cfg.BRUIN_DEFAULT_ASSET_TYPE == "duckdb.sql"


def test_repo_trellis_yml_loads(monkeypatch):
    """Loading this repo's real trellis.yml (dbt-based) resolves as expected."""
    _prepare_config(monkeypatch)
    repo_root = Path(__file__).resolve().parents[2]
    config_path = repo_root / "trellis.yml"

    cfg.load_config(str(config_path))

    assert cfg.FRAMEWORK == "dbt-core"
    assert cfg.DBT_PROJECT_PATH == os.path.abspath(repo_root / "dbt_demo")
    assert cfg.MODELING_STYLE == "dimensional_model"
    assert cfg.DIMENSIONAL_MODELING_CONFIG.dimension_prefix == ["dim__"]
    assert cfg.DIMENSIONAL_MODELING_CONFIG.fact_prefix == ["fact__"]
    assert cfg.EXPOSURES_ENABLED is True
    assert cfg.BUSINESS_EVENTS_ENABLED is True
