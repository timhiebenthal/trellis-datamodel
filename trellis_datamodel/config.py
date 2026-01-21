"""
Configuration loading for Trellis Data.
Centralizes all path resolution logic.

For testing, set environment variable DATAMODEL_TEST_DIR to a temp directory path.
This will override all paths to use that directory.
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)

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
    dimension_prefix: list[str] = field(default_factory=lambda: ["dim_", "d_"])
    fact_prefix: list[str] = field(default_factory=lambda: ["fct_", "fact_"])


@dataclass
class EntityModelingConfig:
    """Configuration for entity modeling features."""

    enabled: bool = False
    entity_prefix: list[str] = field(default_factory=list)


@dataclass
class SourceChipsConfig:
    """Configuration for source chip features."""

    enabled: bool = True
    source_sources: str = "both"  # Options: "manual", "lineage", "both"


# Global configuration objects (set by load_config)
GUIDANCE_CONFIG: GuidanceConfig = GuidanceConfig()
DIMENSIONAL_MODELING_CONFIG: DimensionalModelingConfig = DimensionalModelingConfig()
ENTITY_MODELING_CONFIG: EntityModelingConfig = EntityModelingConfig()
SOURCE_CHIPS_CONFIG: SourceChipsConfig = SourceChipsConfig()

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
    BUSINESS_EVENTS_ENABLED: bool = False
    BUSINESS_EVENTS_PATH: str = ""
    GUIDANCE_CONFIG: GuidanceConfig = GuidanceConfig()
    DIMENSIONAL_MODELING_CONFIG: DimensionalModelingConfig = DimensionalModelingConfig()
    ENTITY_MODELING_CONFIG: EntityModelingConfig = EntityModelingConfig()
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
    BUSINESS_EVENTS_ENABLED: bool = False
    BUSINESS_EVENTS_PATH: str = ""
    DIMENSIONAL_MODELING_CONFIG: DimensionalModelingConfig = DimensionalModelingConfig()
    ENTITY_MODELING_CONFIG: EntityModelingConfig = EntityModelingConfig()


def _load_yaml_config(path: str) -> dict[str, Any]:
    """Load YAML config, returning an empty dict on error."""
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning("Error loading config file %s: %s", path, e)
        return {}


def _resolve_config_path(config_path: Optional[str]) -> Optional[str]:
    """Pick explicit path or search for a config file."""
    if config_path:
        return config_path
    return find_config_file()


def _resolve_base_path(config_path: str) -> str:
    """Base directory for relative paths."""
    return os.path.dirname(config_path)


def _resolve_path(base_dir: str, candidate: str) -> str:
    """Resolve candidate path relative to base when not absolute."""
    if os.path.isabs(candidate):
        return candidate
    return os.path.abspath(os.path.join(base_dir, candidate))


def _resolve_project_path(config_path: str, config: dict[str, Any]) -> str:
    """Resolve dbt_project_path with config directory fallback."""
    project_path = config.get("dbt_project_path")
    if not project_path:
        return ""
    base_dir = _resolve_base_path(config_path)
    return _resolve_path(base_dir, project_path)


def _resolve_manifest_path(
    config_path: str, project_path: str, config: dict[str, Any]
) -> str:
    """Resolve manifest path relative to dbt project when available."""
    manifest_path = config.get("dbt_manifest_path")
    if not manifest_path:
        return ""
    base_dir = project_path or _resolve_base_path(config_path)
    return _resolve_path(base_dir, manifest_path)


def _resolve_catalog_path(
    config_path: str, project_path: str, config: dict[str, Any]
) -> str:
    """Resolve catalog path relative to dbt project when available."""
    catalog_path = config.get("dbt_catalog_path")
    if not catalog_path:
        return ""
    base_dir = project_path or _resolve_base_path(config_path)
    return _resolve_path(base_dir, catalog_path)


def _resolve_data_model_path(
    config_path: str, project_path: str, config: dict[str, Any], existing: str
) -> str:
    """Resolve data_model_file unless overridden by environment."""
    if "DATAMODEL_DATA_MODEL_PATH" in os.environ:
        return existing

    data_model_file = config.get("data_model_file")
    if not data_model_file:
        return existing

    base_dir = project_path or _resolve_base_path(config_path)
    return _resolve_path(base_dir, data_model_file)


def _resolve_canvas_layout_path(
    config_path: str, project_path: str, data_model_path: str, config: dict[str, Any]
) -> str:
    """Resolve canvas layout path with sensible defaults near data_model.yml."""
    layout_file = config.get("canvas_layout_file")
    if layout_file:
        base_dir = project_path or _resolve_base_path(config_path)
        return _resolve_path(base_dir, layout_file)

    if data_model_path:
        data_model_dir = os.path.dirname(data_model_path)
        return os.path.abspath(os.path.join(data_model_dir, "canvas_layout.yml"))

    return os.path.abspath(
        os.path.join(_resolve_base_path(config_path), "canvas_layout.yml")
    )


def _resolve_frontend_build_dir(config_path: str, config: dict[str, Any]) -> str:
    """
    Resolve frontend build directory.

    Environment variable DATAMODEL_FRONTEND_BUILD_DIR can override the default.
    Defaults to ./frontend/build relative to the config file base path.
    """
    env_dir = os.environ.get("DATAMODEL_FRONTEND_BUILD_DIR")
    if env_dir:
        return env_dir

    return os.path.abspath(
        os.path.join(_resolve_base_path(config_path), "frontend", "build")
    )


def _resolve_company_dummy_path(config_path: str, config: dict[str, Any]) -> str:
    """Resolve optional dbt_company_dummy_path."""
    dummy_path = config.get("dbt_company_dummy_path")
    if not dummy_path:
        return ""
    return _resolve_path(_resolve_base_path(config_path), dummy_path)


def _load_lineage_config(config: dict[str, Any]) -> tuple[bool, list[str]]:
    """Load lineage settings with legacy support."""
    enabled = False
    layers: list[str] = []

    lineage_config = config.get("lineage")
    if isinstance(lineage_config, dict):
        enabled = bool(lineage_config.get("enabled", False))
        lineage_layers = lineage_config.get("layers", [])
        if isinstance(lineage_layers, list):
            layers = lineage_layers
        elif lineage_layers is not None:
            logger.warning("'lineage.layers' must be a list. Ignoring provided value.")

    legacy_present = "lineage_layers" in config
    if lineage_config and legacy_present:
        msg = (
            "'lineage_layers' at top level is deprecated and ignored when 'lineage' "
            "section is present. Use 'lineage.enabled' and 'lineage.layers' instead."
        )
        print(msg)
        logger.warning(msg)
    elif not lineage_config and legacy_present:
        msg = (
            "'lineage_layers' at top level is deprecated. Use nested 'lineage.enabled' "
            "and 'lineage.layers' instead."
        )
        print(msg)
        logger.warning(msg)
        legacy_layers = config["lineage_layers"]
        if isinstance(legacy_layers, list):
            layers = legacy_layers
        else:
            logger.warning("'lineage_layers' must be a list. Ignoring provided value.")

    return enabled, layers


def _load_guidance_config(config: dict[str, Any]) -> GuidanceConfig:
    """Load entity creation guidance settings with legacy fallback."""
    guidance_section = config.get("entity_creation_guidance")
    legacy_guidance_section = config.get("guidance")
    if guidance_section is None and legacy_guidance_section is not None:
        logger.warning(
            "'guidance' is deprecated. Use 'entity_creation_guidance' with 'wizard.enabled'."
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
            entity_wizard_enabled = wizard_section.get("enabled", entity_wizard_enabled)
        return GuidanceConfig(
            entity_wizard_enabled=bool(entity_wizard_enabled),
            push_warning_enabled=guidance_section.get("push_warning_enabled", True),
            min_description_length=guidance_section.get("min_description_length", 10),
            disabled_guidance=(
                guidance_section.get("disabled_guidance", [])
                if isinstance(guidance_section.get("disabled_guidance"), list)
                else []
            ),
        )

    return GuidanceConfig()


def _load_exposures_config(config: dict[str, Any]) -> tuple[bool, str]:
    """Load exposures configuration with validation."""
    enabled = False
    default_layout = "dashboards-as-rows"

    exposures_config = config.get("exposures")
    if isinstance(exposures_config, dict):
        enabled = bool(exposures_config.get("enabled", False))
        layout = exposures_config.get("default_layout", default_layout)
        if layout in ["dashboards-as-rows", "entities-as-rows"]:
            default_layout = layout
        else:
            msg = (
                "'exposures.default_layout' must be 'dashboards-as-rows' or "
                "'entities-as-rows'. Using default 'dashboards-as-rows'."
            )
            print(msg)
            logger.warning(msg)

    return enabled, default_layout


def _load_business_events_config(config: dict[str, Any]) -> bool:
    """Load business events configuration."""
    enabled = False

    business_events_config = config.get("business_events")
    if isinstance(business_events_config, dict):
        enabled = bool(business_events_config.get("enabled", False))

    return enabled


def _resolve_business_events_path(
    config_path: str, data_model_path: str, config: dict[str, Any]
) -> str:
    """Resolve business events path, defaulting to same directory as data_model.yml."""
    business_events_config = config.get("business_events")
    if isinstance(business_events_config, dict):
        business_events_file = business_events_config.get("file")
        if business_events_file:
            base_dir = _resolve_base_path(config_path)
            return _resolve_path(base_dir, business_events_file)

    # Default: same directory as data_model.yml
    if data_model_path:
        data_model_dir = os.path.dirname(data_model_path)
        return os.path.abspath(os.path.join(data_model_dir, "business_events.yml"))

    return os.path.abspath(
        os.path.join(_resolve_base_path(config_path), "business_events.yml")
    )


def _load_modeling_style(config: dict[str, Any]) -> str:
    """Load modeling style with validation."""
    modeling_style = config.get("modeling_style", "entity_model")
    if modeling_style not in ["dimensional_model", "entity_model"]:
        logger.warning(
            "'modeling_style' must be 'dimensional_model' or 'entity_model'. "
            "Using default 'entity_model'."
        )
        return "entity_model"
    return modeling_style


def _resolve_bus_matrix_enabled(modeling_style: str, bus_matrix_config: Any) -> bool:
    """Derive Bus Matrix enablement from modeling style and optional override."""
    enabled = modeling_style == "dimensional_model"
    if isinstance(bus_matrix_config, dict) and modeling_style == "dimensional_model":
        enabled = bool(bus_matrix_config.get("enabled", True))
    return enabled


def _load_dimensional_modeling_config(
    modeling_style: str, config: dict[str, Any]
) -> DimensionalModelingConfig:
    """Load dimensional modeling config, enabling inference based on modeling_style."""
    dimensional_config = DimensionalModelingConfig()
    dimensional_config.enabled = modeling_style == "dimensional_model"

    config_section = config.get("dimensional_modeling")
    if not isinstance(config_section, dict):
        return dimensional_config

    inference_patterns = config_section.get("inference_patterns")
    if not isinstance(inference_patterns, dict):
        return dimensional_config

    dimension_prefix = inference_patterns.get("dimension_prefix")
    if isinstance(dimension_prefix, str):
        dimensional_config.dimension_prefix = [dimension_prefix]
    elif isinstance(dimension_prefix, list):
        dimensional_config.dimension_prefix = dimension_prefix

    fact_prefix = inference_patterns.get("fact_prefix")
    if isinstance(fact_prefix, str):
        dimensional_config.fact_prefix = [fact_prefix]
    elif isinstance(fact_prefix, list):
        dimensional_config.fact_prefix = fact_prefix

    return dimensional_config


def _load_entity_modeling_config(
    modeling_style: str, config: dict[str, Any]
) -> EntityModelingConfig:
    """Load entity modeling config, enabling prefix application based on modeling_style."""
    entity_config = EntityModelingConfig()
    entity_config.enabled = modeling_style == "entity_model"

    # Only load prefix config when entity modeling is enabled
    if not entity_config.enabled:
        return entity_config

    config_section = config.get("entity_modeling")
    if not isinstance(config_section, dict):
        return entity_config

    inference_patterns = config_section.get("inference_patterns")
    if not isinstance(inference_patterns, dict):
        return entity_config

    entity_prefix = inference_patterns.get("prefix")
    if isinstance(entity_prefix, str):
        entity_config.entity_prefix = [entity_prefix]
    elif isinstance(entity_prefix, list):
        entity_config.entity_prefix = entity_prefix

    return entity_config


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
    global FRAMEWORK, MANIFEST_PATH, DATA_MODEL_PATH, DBT_MODEL_PATHS, CATALOG_PATH, DBT_PROJECT_PATH, CANVAS_LAYOUT_PATH, CANVAS_LAYOUT_VERSION_CONTROL, CONFIG_PATH, FRONTEND_BUILD_DIR, DBT_COMPANY_DUMMY_PATH, LINEAGE_LAYERS, GUIDANCE_CONFIG, LINEAGE_ENABLED, EXPOSURES_ENABLED, EXPOSURES_DEFAULT_LAYOUT, MODELING_STYLE, Bus_MATRIX_ENABLED, BUSINESS_EVENTS_ENABLED, BUSINESS_EVENTS_PATH, DIMENSIONAL_MODELING_CONFIG, ENTITY_MODELING_CONFIG

    # Skip loading config file in test mode (paths already set via environment)
    # Unless TRELLIS_CONFIG_PATH is explicitly set (for test configs)
    if os.environ.get("DATAMODEL_TEST_DIR") and not os.environ.get(
        "TRELLIS_CONFIG_PATH"
    ):
        return

    CONFIG_PATH = _resolve_config_path(config_path) or ""
    if not CONFIG_PATH:
        return

    if not os.path.exists(CONFIG_PATH):
        return

    config = _load_yaml_config(CONFIG_PATH)

    # 0. Framework
    FRAMEWORK = config.get("framework", "dbt-core")

    # 1. Project path (required for other resolutions)
    DBT_PROJECT_PATH = _resolve_project_path(CONFIG_PATH, config)

    # 2. Manifest and catalog
    MANIFEST_PATH = _resolve_manifest_path(CONFIG_PATH, DBT_PROJECT_PATH, config)
    CATALOG_PATH = _resolve_catalog_path(CONFIG_PATH, DBT_PROJECT_PATH, config)

    # 3. Data model path (env can override)
    DATA_MODEL_PATH = _resolve_data_model_path(
        CONFIG_PATH, DBT_PROJECT_PATH, config, DATA_MODEL_PATH
    )

    # 4. Model path filters
    if "dbt_model_paths" in config:
        DBT_MODEL_PATHS = config["dbt_model_paths"]

    # 5. Canvas layout path
    CANVAS_LAYOUT_PATH = _resolve_canvas_layout_path(
        CONFIG_PATH, DBT_PROJECT_PATH, DATA_MODEL_PATH, config
    )

    # 6. Canvas layout version control
    if "canvas_layout_version_control" in config:
        CANVAS_LAYOUT_VERSION_CONTROL = config["canvas_layout_version_control"]

    # 7. Frontend build directory
    FRONTEND_BUILD_DIR = _resolve_frontend_build_dir(CONFIG_PATH, config)

    # 8. dbt company dummy path (optional)
    DBT_COMPANY_DUMMY_PATH = _resolve_company_dummy_path(CONFIG_PATH, config)

    # 9. Lineage configuration
    LINEAGE_ENABLED, LINEAGE_LAYERS = _load_lineage_config(config)

    # 10. Guidance configuration
    GUIDANCE_CONFIG = _load_guidance_config(config)

    # 11. Exposures configuration
    EXPOSURES_ENABLED, EXPOSURES_DEFAULT_LAYOUT = _load_exposures_config(config)

    # 12. Modeling style and bus matrix
    MODELING_STYLE = _load_modeling_style(config)
    Bus_MATRIX_ENABLED = _resolve_bus_matrix_enabled(
        MODELING_STYLE, config.get("bus_matrix")
    )

    # 13. Dimensional modeling configuration
    DIMENSIONAL_MODELING_CONFIG = _load_dimensional_modeling_config(
        MODELING_STYLE, config
    )

    # 14. Entity modeling configuration
    ENTITY_MODELING_CONFIG = _load_entity_modeling_config(MODELING_STYLE, config)

    # 15. Business events configuration
    BUSINESS_EVENTS_ENABLED = _load_business_events_config(config)
    BUSINESS_EVENTS_PATH = _resolve_business_events_path(
        CONFIG_PATH, DATA_MODEL_PATH, config
    )


def reload_config(config_path: Optional[str] = None) -> None:
    """
    Reload configuration from trellis.yml at runtime.
    
    This function reloads the config file and updates all global configuration
    variables. Should be called after config file changes to apply new settings
    without restarting the server.
    
    Args:
        config_path: Optional override path to config file. If None, uses
                    find_config_file() to locate trellis.yml.
    
    Raises:
        ConfigurationError: If config file cannot be found or loaded.
    """
    from trellis_datamodel.exceptions import ConfigurationError
    
    logger.info("Reloading configuration...")
    try:
        # Use provided path or find config file
        if not config_path:
            config_path = find_config_file()
        
        if not config_path:
            raise ConfigurationError(
                "No config file found. Please create trellis.yml in the current directory."
            )
        
        # Reload config (this updates all global variables)
        load_config(config_path)
        logger.info("Configuration reloaded successfully")
    except ConfigurationError:
        # Re-raise ConfigurationError as-is
        raise
    except Exception as e:
        logger.error(f"Failed to reload configuration: {e}")
        raise ConfigurationError(f"Failed to reload configuration: {e}") from e


def print_config() -> None:
    """Print current configuration for debugging."""
    logger.info("Using Config: %s", CONFIG_PATH)
    logger.info("Framework: %s", FRAMEWORK)
    logger.info("Project Path: %s", DBT_PROJECT_PATH)
    logger.info("Frontend build dir: %s", FRONTEND_BUILD_DIR)
    logger.info("Looking for manifest at: %s", MANIFEST_PATH)
    logger.info("Looking for catalog at: %s", CATALOG_PATH)
    logger.info("Looking for data model at: %s", DATA_MODEL_PATH)
    logger.info("Looking for canvas layout at: %s", CANVAS_LAYOUT_PATH)
    logger.info("Canvas layout version control: %s", CANVAS_LAYOUT_VERSION_CONTROL)
    logger.info("Filtering models by paths: %s", DBT_MODEL_PATHS)
    logger.info("Lineage enabled: %s", LINEAGE_ENABLED)
    if LINEAGE_LAYERS:
        logger.info("Lineage layers: %s", LINEAGE_LAYERS)
    logger.info("Exposures enabled: %s", EXPOSURES_ENABLED)
    if EXPOSURES_ENABLED:
        logger.info("Exposures default layout: %s", EXPOSURES_DEFAULT_LAYOUT)
    logger.info("Modeling style: %s", MODELING_STYLE)
    logger.info("Bus Matrix enabled: %s", Bus_MATRIX_ENABLED)
    if DIMENSIONAL_MODELING_CONFIG.enabled:
        logger.info(
            "Dimensional modeling enabled: %s", DIMENSIONAL_MODELING_CONFIG.enabled
        )
        logger.info(
            "Dimension prefixes: %s", DIMENSIONAL_MODELING_CONFIG.dimension_prefix
        )
        logger.info("Fact prefixes: %s", DIMENSIONAL_MODELING_CONFIG.fact_prefix)
    if ENTITY_MODELING_CONFIG.enabled:
        logger.info("Entity modeling enabled: %s", ENTITY_MODELING_CONFIG.enabled)
        logger.info("Entity prefixes: %s", ENTITY_MODELING_CONFIG.entity_prefix)
    if DBT_COMPANY_DUMMY_PATH:
        logger.info("dbt company dummy path: %s", DBT_COMPANY_DUMMY_PATH)
