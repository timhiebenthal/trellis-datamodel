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


# Global guidance configuration (set by load_config)
GUIDANCE_CONFIG: GuidanceConfig = GuidanceConfig()

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
    GUIDANCE_CONFIG: GuidanceConfig = GuidanceConfig()
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


def find_config_file(config_override: Optional[str] = None) -> Optional[str]:
    """
    Find config file in order of priority:
    1. CLI override (--config)
    2. trellis.yml in current directory
    3. config.yml in current directory (fallback)

    Returns:
        Path to config file or None if not found
    """
    if config_override:
        if os.path.exists(config_override):
            return os.path.abspath(config_override)
        return None

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
    global FRAMEWORK, MANIFEST_PATH, DATA_MODEL_PATH, DBT_MODEL_PATHS, CATALOG_PATH, DBT_PROJECT_PATH, CANVAS_LAYOUT_PATH, CANVAS_LAYOUT_VERSION_CONTROL, CONFIG_PATH, FRONTEND_BUILD_DIR, DBT_COMPANY_DUMMY_PATH, LINEAGE_LAYERS, GUIDANCE_CONFIG

    # Skip loading config file in test mode (paths already set via environment)
    if _TEST_DIR:
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

        # 10. Load lineage layers configuration
        if "lineage_layers" in config:
            LINEAGE_LAYERS = config["lineage_layers"]
            if not isinstance(LINEAGE_LAYERS, list):
                LINEAGE_LAYERS = []
        else:
            LINEAGE_LAYERS = []

        # 11. Load guidance configuration
        if "guidance" in config:
            guidance_config = config["guidance"]
            GUIDANCE_CONFIG = GuidanceConfig(
                entity_wizard_enabled=guidance_config.get("entity_wizard_enabled", True),
                push_warning_enabled=guidance_config.get("push_warning_enabled", True),
                min_description_length=guidance_config.get("min_description_length", 10),
                disabled_guidance=guidance_config.get("disabled_guidance", [])
                if isinstance(guidance_config.get("disabled_guidance"), list)
                else [],
            )
        else:
            # Use defaults if guidance section is missing
            GUIDANCE_CONFIG = GuidanceConfig()

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
    if LINEAGE_LAYERS:
        print(f"Lineage layers: {LINEAGE_LAYERS}")
    if DBT_COMPANY_DUMMY_PATH:
        print(f"dbt company dummy path: {DBT_COMPANY_DUMMY_PATH}")
