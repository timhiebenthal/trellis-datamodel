from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import yaml
import os

app = FastAPI()

# CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# dbt-ontology/config.yaml
CONFIG_PATH = os.path.abspath(os.path.join(BASE_DIR, "../config.yaml"))

# Default values
MANIFEST_PATH = ""
CATALOG_PATH = ""
ONTOLOGY_PATH = os.path.abspath(os.path.join(BASE_DIR, "../ontology.yaml"))
DBT_PROJECT_PATH = ""
DBT_MODEL_PATHS = ["3-entity"]


def load_config():
    global MANIFEST_PATH, ONTOLOGY_PATH, DBT_MODEL_PATHS, CATALOG_PATH, DBT_PROJECT_PATH
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                config = yaml.safe_load(f) or {}

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
                # Fallback or error? Plan said "Require dbt_project_path"
                # But for now let's just leave it empty and let status check fail
                DBT_PROJECT_PATH = ""

            # 2. Resolve Manifest
            if "dbt_manifest_path" in config:
                p = config["dbt_manifest_path"]
                if not os.path.isabs(p) and DBT_PROJECT_PATH:
                    MANIFEST_PATH = os.path.abspath(os.path.join(DBT_PROJECT_PATH, p))
                elif os.path.isabs(p):
                    MANIFEST_PATH = p
                else:
                     # Fallback for legacy or missing project path (though we said no backwards compat, safe to keep simple)
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
                # Resolve relative path from dbt-ontology/ (config location)
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
print(f"Looking for ontology at: {ONTOLOGY_PATH}")
print(f"Filtering models by paths: {DBT_MODEL_PATHS}")


@app.get("/api/config-status")
async def get_config_status():
    config_present = os.path.exists(CONFIG_PATH)
    manifest_exists = os.path.exists(MANIFEST_PATH) if MANIFEST_PATH else False
    catalog_exists = os.path.exists(CATALOG_PATH) if CATALOG_PATH else False
    ontology_exists = os.path.exists(ONTOLOGY_PATH) if ONTOLOGY_PATH else False
    
    error = None
    if not config_present:
        error = "Config file not found."
    elif not DBT_PROJECT_PATH:
        error = "dbt_project_path not set in config."
    elif not manifest_exists:
        error = f"Manifest not found at {MANIFEST_PATH}"

    return {
        "config_present": config_present,
        "dbt_project_path": DBT_PROJECT_PATH,
        "manifest_path": MANIFEST_PATH,
        "catalog_path": CATALOG_PATH,
        "manifest_exists": manifest_exists,
        "catalog_exists": catalog_exists,
        "ontology_exists": ontology_exists,
        "error": error
    }


def load_catalog():
    if not os.path.exists(CATALOG_PATH):
        return None
    try:
        with open(CATALOG_PATH, "r") as f:
            return json.load(f)
    except Exception as exc:
        print(f"Warning: failed to read catalog at {CATALOG_PATH}: {exc}")
        return None


@app.get("/api/manifest")
async def get_manifest():
    if not os.path.exists(MANIFEST_PATH):
        raise HTTPException(
            status_code=404, detail=f"Manifest not found at {MANIFEST_PATH}"
        )

    try:
        with open(MANIFEST_PATH, "r") as f:
            data = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading manifest: {str(e)}")

    catalog = load_catalog()
    catalog_nodes = (catalog or {}).get("nodes", {})

    models = []
    for key, node in data.get("nodes", {}).items():
        if node.get("resource_type") == "model":
            # Filter by path
            original_path = node.get("original_file_path", "")

            # If DBT_MODEL_PATHS is set, require at least one match
            if DBT_MODEL_PATHS:
                match = False
                for pattern in DBT_MODEL_PATHS:
                    if pattern in original_path:
                        match = True
                        break
                if not match:
                    continue

            def catalog_columns():
                unique_id = node.get("unique_id")
                catalog_node = catalog_nodes.get(unique_id)
                if not catalog_node:
                    return None
                cols = []
                for col in catalog_node.get("columns", {}).values():
                    cols.append(
                        {
                            "name": col.get("name"),
                            "type": col.get("type") or col.get("data_type"),
                        }
                    )
                return cols

            columns = catalog_columns()
            if not columns:
                columns = []
                for col_name, col_data in node.get("columns", {}).items():
                    columns.append({"name": col_name, "type": col_data.get("type")})

            # Extract materialization from config (defaults to "view" if not specified)
            config = node.get("config", {})
            materialized = config.get("materialized", "view")

            models.append(
                {
                    "unique_id": node.get(
                        "unique_id"
                    ),  # e.g. "model.elmo.entity_booking"
                    "name": node.get("name"),
                    "schema": node.get("schema"),
                    "table": node.get("alias", node.get("name")),
                    "columns": columns,
                    "description": node.get("description"),
                    "materialization": materialized,
                }
            )

    models.sort(key=lambda x: x["name"])
    return {"models": models}


@app.get("/api/ontology")
async def get_ontology():
    if not os.path.exists(ONTOLOGY_PATH):
        return {"version": 0.1, "entities": [], "relationships": []}

    try:
        with open(ONTOLOGY_PATH, "r") as f:
            data = yaml.safe_load(f) or {}

        if not data.get("entities"):
            data["entities"] = []
        if not data.get("relationships"):
            data["relationships"] = []

        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading ontology: {str(e)}")


class OntologyUpdate(BaseModel):
    version: float = 0.1
    entities: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]


@app.post("/api/ontology")
async def save_ontology(data: OntologyUpdate):
    try:
        content = data.model_dump()
        with open(ONTOLOGY_PATH, "w") as f:
            yaml.dump(content, f, default_flow_style=False, sort_keys=False)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving ontology: {str(e)}")


# Mount static files (Frontend)
# Must be after API routes
FRONTEND_BUILD_DIR = os.path.abspath(os.path.join(BASE_DIR, "../frontend/build"))

if os.path.exists(FRONTEND_BUILD_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_BUILD_DIR, html=True), name="static")
else:
    print(
        f"Warning: Frontend build not found at {FRONTEND_BUILD_DIR}. Run 'npm run build' in frontend/"
    )

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
