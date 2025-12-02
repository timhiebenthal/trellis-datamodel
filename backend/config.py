"""
Configuration loading for the Data Model UI backend.
Centralizes all path resolution logic.

For testing, set environment variable DATAMODEL_TEST_DIR to a temp directory path.
This will override all paths to use that directory.
"""

import os
import yaml

# Base directory (backend folder)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Check for test mode - allows overriding config via environment
_TEST_DIR = os.environ.get("DATAMODEL_TEST_DIR", "")

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
    DBT_PROJECT_PATH: str = _TEST_DIR
    DBT_MODEL_PATHS: list[str] = ["3_core"]
    FRONTEND_BUILD_DIR: str = os.path.join(_TEST_DIR, "frontend/build")
else:
    # Production mode: use config.yml
    CONFIG_PATH = os.path.abspath(os.path.join(BASE_DIR, "../config.yml"))
    FRAMEWORK: str = "dbt-core"
    MANIFEST_PATH: str = ""
    CATALOG_PATH: str = ""
    # Allow env var override for testing
    DATA_MODEL_PATH: str = os.environ.get(
        "DATAMODEL_DATA_MODEL_PATH",
        os.path.abspath(os.path.join(BASE_DIR, "../data_model.yml"))
    )
    DBT_PROJECT_PATH: str = ""
    DBT_MODEL_PATHS: list[str] = ["3-entity"]
    FRONTEND_BUILD_DIR: str = os.path.abspath(
        os.path.join(BASE_DIR, "../frontend/build")
    )


def load_config() -> None:
    """Load and resolve all paths from config.yml."""
    global FRAMEWORK, MANIFEST_PATH, DATA_MODEL_PATH, DBT_MODEL_PATHS, CATALOG_PATH, DBT_PROJECT_PATH

    # Skip loading config file in test mode (paths already set via environment)
    if _TEST_DIR:
        return

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
                MANIFEST_PATH = os.path.abspath(os.path.join(BASE_DIR, p))

        # 3. Resolve Catalog
        if "dbt_catalog_path" in config:
            p = config["dbt_catalog_path"]
            if not os.path.isabs(p) and DBT_PROJECT_PATH:
                CATALOG_PATH = os.path.abspath(os.path.join(DBT_PROJECT_PATH, p))
            elif os.path.isabs(p):
                CATALOG_PATH = p
            else:
                CATALOG_PATH = os.path.abspath(os.path.join(BASE_DIR, p))

        # 4. Resolve Data Model (env var takes precedence)
        if "DATAMODEL_DATA_MODEL_PATH" not in os.environ and "data_model_file" in config:
            p = config["data_model_file"]
            if not os.path.isabs(p):
                base_path = DBT_PROJECT_PATH or os.path.dirname(CONFIG_PATH)
                DATA_MODEL_PATH = os.path.abspath(os.path.join(base_path, p))
            else:
                DATA_MODEL_PATH = p

        # 5. Model path filters
        if "dbt_model_paths" in config:
            DBT_MODEL_PATHS = config["dbt_model_paths"]

    except Exception as e:
        print(f"Error loading config: {e}")


def print_config() -> None:
    """Print current configuration for debugging."""
    print(f"Using Config: {CONFIG_PATH}")
    print(f"Framework: {FRAMEWORK}")
    print(f"Project Path: {DBT_PROJECT_PATH}")
    print(f"Looking for manifest at: {MANIFEST_PATH}")
    print(f"Looking for catalog at: {CATALOG_PATH}")
    print(f"Looking for data model at: {DATA_MODEL_PATH}")
    print(f"Filtering models by paths: {DBT_MODEL_PATHS}")


# Load config on import
load_config()
