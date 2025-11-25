import os
import yaml
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.abspath(os.path.join(BASE_DIR, "../config.yml"))

# Default values
MANIFEST_PATH = ""
CATALOG_PATH = ""
ONTOLOGY_PATH = os.path.abspath(os.path.join(BASE_DIR, "../ontology.yml"))
DBT_PROJECT_PATH = ""
DBT_MODEL_PATHS = ["3-entity"]

def load_config():
    global MANIFEST_PATH, ONTOLOGY_PATH, DBT_MODEL_PATHS, CATALOG_PATH, DBT_PROJECT_PATH
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                config = yaml.safe_load(f) or {}
            
            print(f"Config loaded: {config}")

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

            # 4. Resolve Ontology
            if "ontology_file" in config:
                p = config["ontology_file"]
                if not os.path.isabs(p):
                    ONTOLOGY_PATH = os.path.abspath(
                        os.path.join(os.path.dirname(CONFIG_PATH), p)
                    )
                else:
                    ONTOLOGY_PATH = p

            if "dbt_model_paths" in config:
                DBT_MODEL_PATHS = config["dbt_model_paths"]

        except Exception as e:
            print(f"Error loading config: {e}")

load_config()

print(f"Using Config: {CONFIG_PATH}")
print(f"dbt Project Path: {DBT_PROJECT_PATH}")
print(f"Looking for manifest at: {MANIFEST_PATH}")
print(f"Looking for catalog at: {CATALOG_PATH}")
