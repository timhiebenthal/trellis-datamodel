"""
Configuration loading for Trellis Data.
Centralizes all path resolution logic.

For testing, set environment variable DATAMODEL_TEST_DIR to a temp directory path.
This will override all paths to use that directory.
"""

import os
import yaml
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

# Check for test mode - allows overriding config via environment
_TEST_DIR = os.environ.get("DATAMODEL_TEST_DIR", "")


@dataclass
class GuidanceConfig:
    """Configuration for entity creation guidance features."""
    entity_wizard_enabled: bool = True
    push_warning_enabled: bool = True
    min_description_length: int = 10
    disabled_guidance: list[str] = field(default_factory=list)


@dataclass
class DimensionalModelingConfig:
    """Configuration for dimensional modeling features."""
    enabled: bool = False
    dimension_prefixes: list[str] = field(default_factory=lambda: ["dim_", "d_"])
    fact_prefixes: list[str] = field(default_factory=lambda: ["fct_", "fact_"])


# Global configuration objects (set by load_config)
GUIDANCE_CONFIG: GuidanceConfig = GuidanceConfig()
DIMENSIONAL_MODELING_CONFIG: DimensionalModelingConfig = DimensionalModelingConfig()

if _TEST_DIR:
    # Test mode: use temp directory paths
    CONFIG_PATH = os.path.join(_TEST_DIR, "config.yml")
    FRAMEWORK: str = os.environ.get("DATAMODEL_FRAMEWORK", "dbt-core")
    MANIFEST_PATH: str = os.environ.get(
        "DATAMODEL_MANIFEST_PATH", os.path.join(_TEST_DIR, "manifest.json")
    )
    CATALOG_PATH: str = os.environ.get(
        "DATAMODEL_CATALOG_PATH", os.path.join(_TEST_DIR, "catalog.json")
    )
    DATA_MODEL_PATH: str = os.environ.get(
        "DATAMODEL_DATA_MODEL_PATH", os.path.join(_TEST_DIR, "data_model.yml")
    )
    CANVAS_LAYOUT_PATH: str = os.environ.get(
        "DATAMODEL_CANVAS_LAYOUT_PATH", os.path.join(_TEST_DIR, "canvas_layout.yml")
    )
    CANVAS_LAYOUT_VERSION_CONTROL: bool = (
        os.environ.get("DATAMODEL_CANVAS_LAYOUT_VERSION_CONTROL", "true").lower()
        == "true"
    )
    DBT_PROJECT_PATH: str = _TEST_DIR
    DBT_MODEL_PATHS: list[str] = ["3_core"]
    FRONTEND_BUILD_DIR: str = os.path.join(_TEST_DIR, "frontend/build")
    DBT_COMPANY_DUMMY_PATH: str = os.path.join(_TEST_DIR, "dbt_company_dummy")
    LINEAGE_LAYERS: list[str] = []
    LINEAGE_ENABLED: bool = False
    EXPOSURES_ENABLED: bool = False
    EXPOSURES_DEFAULT_LAYOUT: str = "dashboards-as-rows"
    MODELING_STYLE: str = "entity_model"
    Bus_MATRIX_ENABLED: bool = False
    GUIDANCE_CONFIG: GuidanceConfig = GuidanceConfig()
    DIMENSIONAL_MODELING_CONFIG: DimensionalModelingConfig = DimensionalModelingConfig()
else:
    # Production mode: will be set by load_config()
    CONFIG_PATH: str = ""
    FRAMEWORK: str = "dbt-core"
    MANIFEST_PATH: str = ""
    CATALOG_PATH: str = ""
    DATA_MODEL_PATH: str = ""
    CANVAS_LAYOUT_PATH: str = ""
    CANVAS_LAYOUT_VERSION_CONTROL: bool = True
    DBT_PROJECT_PATH: str = ""
    DBT_MODEL_PATHS: list[str] = []
    FRONTEND_BUILD_DIR: str = ""
    DBT_COMPANY_DUMMY_PATH: str = ""
    LINEAGE_LAYERS: list[str] = []
    LINEAGE_ENABLED: bool = False
    EXPOSURES_ENABLED: bool = False
    EXPOSURES_DEFAULT_LAYOUT: str = "dashboards-as-rows"
    MODELING_STYLE: str = "entity_model"
    Bus_MATRIX_ENABLED: bool = False
    DIMENSIONAL_MODELING_CONFIG: DimensionalModelingConfig = DimensionalModelingConfig()


def find_config_file(config_override: Optional[str] = None) -> Optional[str]:
    """
    Find config file in order of priority:
    1. CLI override (--config)
    2. TRELLIS_CONFIG_PATH environment variable
    3. trellis.yml in current directory
    4. config.yml in current directory (fallback)

    Returns:
        Path to config file or None if not found
    """
    if config_override:
        if os.path.exists(config_override):
            return os.path.abspath(config_override)
        return None

    # Check for TRELLIS_CONFIG_PATH environment variable (used in tests)
    env_config = os.environ.get("TRELLIS_CONFIG_PATH")
    if env_config and os.path.exists(env_config):
        return os.path.abspath(env_config)

    cwd = os.getcwd()

    # Try trellis.yml first
    trellis_yml = os.path.join(cwd, "trellis.yml")
    if os.path.exists(trellis_yml):
        return os.path.abspath(trellis_yml)

    # Fallback to config.yml
    config_yml = os.path.join(cwd, "config.yml")
    if os.path.exists(config_yml):
        return os.path.abspath(config_yml)

    return None


def load_config(config_path: Optional[str] = None) -> None:
    """Load and resolve all paths from config file."""
    global FRAMEWORK, MANIFEST_PATH, DATA_MODEL_PATH, DBT_MODEL_PATHS, CATALOG_PATH, DBT_PROJECT_PATH, CANVAS_LAYOUT_PATH, CANVAS_LAYOUT_VERSION_CONTROL, CONFIG_PATH, FRONTEND_BUILD_DIR, DBT_COMPANY_DUMMY_PATH, LINEAGE_LAYERS, GUIDANCE_CONFIG, LINEAGE_ENABLED, EXPOSURES_ENABLED, EXPOSURES_DEFAULT_LAYOUT, MODELING_STYLE, Bus_MATRIX_ENABLED, DIMENSIONAL_MODELING_CONFIG

    # Skip loading config file in test mode (paths already set via environment)
    # Unless TRELLIS_CONFIG_PATH is explicitly set (for test configs)
    if os.environ.get("DATAMODEL_TEST_DIR") and not os.environ.get("TRELLIS_CONFIG_PATH"):
        return

    # Find config file
    if config_path:
        CONFIG_PATH = config_path
    else:
        found_config = find_config_file()
        if not found_config:
            # No config found - use defaults
            CONFIG_PATH = ""
            return
        CONFIG_PATH = found_config

    if not os.path.exists(CONFIG_PATH):
        return

    try:
        with open(CONFIG_PATH, "r") as f:
            config = yaml.safe_load(f) or {}

        # 0. Get framework (defaults to dbt-core)
        FRAMEWORK = config.get("framework", "dbt-core")

        # 1. Get dbt_project_path (Required for resolving other paths)
        if "dbt_project_path" in config:
            p = config["dbt_project_path"]
            if not os.path.isabs(p):
                # Resolve relative to config file location
                DBT_PROJECT_PATH = os.path.abspath(
                    os.path.join(os.path.dirname(CONFIG_PATH), p)
                )
            else:
                DBT_PROJECT_PATH = p
        else:
            DBT_PROJECT_PATH = ""

        # 2. Resolve Manifest
        if "dbt_manifest_path" in config:
            p = config["dbt_manifest_path"]
            if not os.path.isabs(p) and DBT_PROJECT_PATH:
                MANIFEST_PATH = os.path.abspath(os.path.join(DBT_PROJECT_PATH, p))
            elif os.path.isabs(p):
                MANIFEST_PATH = p
            else:
                MANIFEST_PATH = os.path.abspath(
                    os.path.join(os.path.dirname(CONFIG_PATH), p)
                )

        # 3. Resolve Catalog
        if "dbt_catalog_path" in config:
            p = config["dbt_catalog_path"]
            if not os.path.isabs(p) and DBT_PROJECT_PATH:
                CATALOG_PATH = os.path.abspath(os.path.join(DBT_PROJECT_PATH, p))
            elif os.path.isabs(p):
                CATALOG_PATH = p
            else:
                CATALOG_PATH = os.path.abspath(
                    os.path.join(os.path.dirname(CONFIG_PATH), p)
                )

        # 4. Resolve Data Model (env var takes precedence)
        if (
            "DATAMODEL_DATA_MODEL_PATH" not in os.environ
            and "data_model_file" in config
        ):
            p = config["data_model_file"]
            if not os.path.isabs(p):
                base_path = DBT_PROJECT_PATH or os.path.dirname(CONFIG_PATH)
                DATA_MODEL_PATH = os.path.abspath(os.path.join(base_path, p))
            else:
                DATA_MODEL_PATH = p

        # 5. Model path filters
        if "dbt_model_paths" in config:
            DBT_MODEL_PATHS = config["dbt_model_paths"]

        # 6. Resolve Canvas Layout (defaults to canvas_layout.yml next to data model)
        if "canvas_layout_file" in config:
            p = config["canvas_layout_file"]
            if not os.path.isabs(p):
                base_path = DBT_PROJECT_PATH or os.path.dirname(CONFIG_PATH)
                CANVAS_LAYOUT_PATH = os.path.abspath(os.path.join(base_path, p))
            else:
                CANVAS_LAYOUT_PATH = p
        else:
            # Default: canvas_layout.yml next to data_model.yml
            if DATA_MODEL_PATH:
                data_model_dir = os.path.dirname(DATA_MODEL_PATH)
                CANVAS_LAYOUT_PATH = os.path.abspath(
                    os.path.join(data_model_dir, "canvas_layout.yml")
                )
            else:
                CANVAS_LAYOUT_PATH = os.path.abspath(
                    os.path.join(os.path.dirname(CONFIG_PATH), "canvas_layout.yml")
                )

        # 7. Canvas layout version control setting
        if "canvas_layout_version_control" in config:
            CANVAS_LAYOUT_VERSION_CONTROL = config["canvas_layout_version_control"]

        # 8. Frontend build directory
        fe_env = os.environ.get("DATAMODEL_FRONTEND_BUILD_DIR")
        if fe_env:
            FRONTEND_BUILD_DIR = fe_env
        elif "frontend_build_dir" in config:
            p = config["frontend_build_dir"]
            if not os.path.isabs(p):
                FRONTEND_BUILD_DIR = os.path.abspath(
                    os.path.join(os.path.dirname(CONFIG_PATH), p)
                )
            else:
                FRONTEND_BUILD_DIR = p
        else:
            # Default: frontend/build next to config file (repo root)
            FRONTEND_BUILD_DIR = os.path.abspath(
                os.path.join(os.path.dirname(CONFIG_PATH), "frontend", "build")
            )

        # 9. Resolve dbt company dummy path (only if explicitly configured)
        # If not configured, leave empty so CLI can use smart fallback logic
        if "dbt_company_dummy_path" in config:
            p = config["dbt_company_dummy_path"]
            if not os.path.isabs(p):
                DBT_COMPANY_DUMMY_PATH = os.path.abspath(
                    os.path.join(os.path.dirname(CONFIG_PATH), p)
                )
            else:
                DBT_COMPANY_DUMMY_PATH = p
        # Note: No default set here - CLI handles fallback to cwd/dbt_company_dummy

        # 10. Load lineage configuration (nested structure, with legacy fallback)
        LINEAGE_ENABLED = False
        LINEAGE_LAYERS = []

        lineage_config = config.get("lineage")
        if isinstance(lineage_config, dict):
            LINEAGE_ENABLED = bool(lineage_config.get("enabled", False))
            lineage_layers = lineage_config.get("layers", [])
            if isinstance(lineage_layers, list):
                LINEAGE_LAYERS = lineage_layers
            elif lineage_layers is not None:
                print("Warning: 'lineage.layers' must be a list. Ignoring provided value.")

        legacy_lineage_present = "lineage_layers" in config
        if lineage_config and legacy_lineage_present:
            print(
                "Warning: 'lineage_layers' at top level is deprecated and ignored when 'lineage' section is present. "
                "Use 'lineage.enabled' and 'lineage.layers' instead."
            )
        elif not lineage_config and legacy_lineage_present:
            print(
                "Warning: 'lineage_layers' at top level is deprecated. Use nested 'lineage.enabled' and 'lineage.layers' instead."
            )
            legacy_layers = config["lineage_layers"]
            if isinstance(legacy_layers, list):
                LINEAGE_LAYERS = legacy_layers
            else:
                print("Warning: 'lineage_layers' must be a list. Ignoring provided value.")

        # 11. Load guidance configuration (new: entity_creation_guidance, legacy: guidance)
        guidance_section = config.get("entity_creation_guidance")
        legacy_guidance_section = config.get("guidance")
        if guidance_section is None and legacy_guidance_section is not None:
            print(
                "Warning: 'guidance' is deprecated. Use 'entity_creation_guidance' with 'wizard.enabled'."
            )
            guidance_section = legacy_guidance_section

        if isinstance(guidance_section, dict):
            entity_wizard_enabled = guidance_section.get("enabled")
            if entity_wizard_enabled is None:
                entity_wizard_enabled = guidance_section.get("entity_wizard_enabled", True)
            wizard_section = guidance_section.get("wizard") or guidance_section.get(
                "entity_wizard"
            )
            if isinstance(wizard_section, dict):
                entity_wizard_enabled = wizard_section.get(
                    "enabled", entity_wizard_enabled
                )
            GUIDANCE_CONFIG = GuidanceConfig(
                entity_wizard_enabled=bool(entity_wizard_enabled),
                push_warning_enabled=guidance_section.get("push_warning_enabled", True),
                min_description_length=guidance_section.get("min_description_length", 10),
                disabled_guidance=guidance_section.get("disabled_guidance", [])
                if isinstance(guidance_section.get("disabled_guidance"), list)
                else [],
            )
        else:
            # Use defaults if guidance section is missing or invalid
            GUIDANCE_CONFIG = GuidanceConfig()

        # 12. Load exposures configuration
        EXPOSURES_ENABLED = False
        EXPOSURES_DEFAULT_LAYOUT = "dashboards-as-rows"

        exposures_config = config.get("exposures")
        if isinstance(exposures_config, dict):
            EXPOSURES_ENABLED = bool(exposures_config.get("enabled", False))
            default_layout = exposures_config.get("default_layout", "dashboards-as-rows")
            if default_layout in ["dashboards-as-rows", "entities-as-rows"]:
                EXPOSURES_DEFAULT_LAYOUT = default_layout
            else:
                print("Warning: 'exposures.default_layout' must be 'dashboards-as-rows' or 'entities-as-rows'. Using default 'dashboards-as-rows'.")

        # 13. Load modeling style configuration
        MODELING_STYLE = config.get("modeling_style", "entity_model")
        if MODELING_STYLE not in ["dimensional_model", "entity_model"]:
            print(f"Warning: 'modeling_style' must be 'dimensional_model' or 'entity_model'. Using default 'entity_model'.")
            MODELING_STYLE = "entity_model"

        # 14. Load bus matrix configuration (disabled for explicit entity_model, enabled otherwise)
        # Bus matrix is specific to dimensional modeling (Kimball methodology)
        # If modeling_style is explicitly set to "entity_model" in config, disable Bus Matrix
        # Otherwise, enable it by default (for backward compatibility and dimensional_model)
        modeling_style_in_config = "modeling_style" in config
        if modeling_style_in_config and MODELING_STYLE == "entity_model":
            Bus_MATRIX_ENABLED = False
        else:
            # Enable for dimensional_model or when not explicitly set
            Bus_MATRIX_ENABLED = True
            bus_matrix_config = config.get("bus_matrix")
            if isinstance(bus_matrix_config, dict):
                Bus_MATRIX_ENABLED = bool(bus_matrix_config.get("enabled", True))

        # 15. Load dimensional modeling configuration
        DIMENSIONAL_MODELING_CONFIG = DimensionalModelingConfig()
        dimensional_config = config.get("dimensional_modeling")
        if isinstance(dimensional_config, dict):
            DIMENSIONAL_MODELING_CONFIG.enabled = MODELING_STYLE == "dimensional_model"
            inference_patterns = dimensional_config.get("inference_patterns")
            if isinstance(inference_patterns, dict):
                dimension_prefixes = inference_patterns.get("dimension_prefixes")
                if isinstance(dimension_prefixes, list):
                    DIMENSIONAL_MODELING_CONFIG.dimension_prefixes = dimension_prefixes
                fact_prefixes = inference_patterns.get("fact_prefixes")
                if isinstance(fact_prefixes, list):
                    DIMENSIONAL_MODELING_CONFIG.fact_prefixes = fact_prefixes

    except Exception as e:
        print(f"Error loading config: {e}")


def print_config() -> None:
    """Print current configuration for debugging."""
    print(f"Using Config: {CONFIG_PATH}")
    print(f"Framework: {FRAMEWORK}")
    print(f"Project Path: {DBT_PROJECT_PATH}")
    print(f"Frontend build dir: {FRONTEND_BUILD_DIR}")
    print(f"Looking for manifest at: {MANIFEST_PATH}")
    print(f"Looking for catalog at: {CATALOG_PATH}")
    print(f"Looking for data model at: {DATA_MODEL_PATH}")
    print(f"Looking for canvas layout at: {CANVAS_LAYOUT_PATH}")
    print(f"Canvas layout version control: {CANVAS_LAYOUT_VERSION_CONTROL}")
    print(f"Filtering models by paths: {DBT_MODEL_PATHS}")
    print(f"Lineage enabled: {LINEAGE_ENABLED}")
    if LINEAGE_LAYERS:
        print(f"Lineage layers: {LINEAGE_LAYERS}")
    print(f"Exposures enabled: {EXPOSURES_ENABLED}")
    if EXPOSURES_ENABLED:
        print(f"Exposures default layout: {EXPOSURES_DEFAULT_LAYOUT}")
    print(f"Modeling style: {MODELING_STYLE}")
    print(f"Bus Matrix enabled: {Bus_MATRIX_ENABLED}")
    if DIMENSIONAL_MODELING_CONFIG.enabled:
        print(f"Dimensional modeling enabled: {DIMENSIONAL_MODELING_CONFIG.enabled}")
        print(f"Dimension prefixes: {DIMENSIONAL_MODELING_CONFIG.dimension_prefixes}")
        print(f"Fact prefixes: {DIMENSIONAL_MODELING_CONFIG.fact_prefixes}")
    if DBT_COMPANY_DUMMY_PATH:
        print(f"dbt company dummy path: {DBT_COMPANY_DUMMY_PATH}")
