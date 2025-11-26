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
# dbt-ontology/config.yml
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
                if not os.path.isabs(p):
                    base_path = DBT_PROJECT_PATH or os.path.dirname(CONFIG_PATH)
                    ONTOLOGY_PATH = os.path.abspath(os.path.join(base_path, p))
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
        "error": error,
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
                    "file_path": original_path,
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
        content = data.dict()  # Pydantic v1 (required by dbt-core==1.10)
        print(f"Saving ontology to: {ONTOLOGY_PATH}")
        with open(ONTOLOGY_PATH, "w") as f:
            yaml.dump(content, f, default_flow_style=False, sort_keys=False)
        return {"status": "success"}
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error saving ontology: {str(e)}")


class DbtSchemaRequest(BaseModel):
    entity_id: str
    model_name: str
    fields: List[Dict[str, str]]
    description: Optional[str] = None


@app.post("/api/dbt-schema")
async def save_dbt_schema(request: DbtSchemaRequest):
    """Generate and save a dbt schema YAML file for the drafted fields"""
    try:
        # Validate that DBT_PROJECT_PATH is set
        if not DBT_PROJECT_PATH:
            raise HTTPException(
                status_code=400,
                detail="dbt_project_path is not configured. Please set it in config.yml",
            )

        # Determine the models directory
        # Use the first path from dbt_model_paths if available, otherwise just "models"
        if DBT_MODEL_PATHS and len(DBT_MODEL_PATHS) > 0:
            models_subdir = DBT_MODEL_PATHS[0]
        else:
            models_subdir = "models"

        models_dir = os.path.abspath(
            os.path.join(DBT_PROJECT_PATH, "models", models_subdir)
        )

        # Create models directory if it doesn't exist
        os.makedirs(models_dir, exist_ok=True)

        # Load ontology to get relationships and description
        ontology_data = {}
        if ONTOLOGY_PATH and os.path.exists(ONTOLOGY_PATH):
            try:
                with open(ONTOLOGY_PATH, "r") as f:
                    ontology_data = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Warning: Could not load ontology: {e}")

        # Use description from request if available, otherwise fallback to ontology
        entity_description = request.description
        if not entity_description:
            entities = ontology_data.get("entities", [])
            for entity in entities:
                if entity.get("id") == request.entity_id:
                    entity_description = entity.get("description")
                    break

        # Build a map of field names to relationships for this entity
        # FK is on the "many" side: target for one_to_many, source for many_to_one
        # This matches the logic in sync_dbt_tests
        relationships = ontology_data.get("relationships", [])
        field_to_relationship = {}

        for rel in relationships:
            source_id = rel.get("source")
            target_id = rel.get("target")
            rel_type = rel.get("type", "one_to_many")
            source_field = rel.get("source_field")
            target_field = rel.get("target_field")

            if not source_field or not target_field:
                continue

            # FK is on the "many" side: target for one_to_many, source for many_to_one
            fk_on_target = rel_type == "one_to_many"

            fk_entity = target_id if fk_on_target else source_id
            fk_field = target_field if fk_on_target else source_field
            ref_entity = source_id if fk_on_target else target_id
            ref_field = source_field if fk_on_target else target_field

            # If this entity has the FK field, add it to the map
            if fk_entity == request.entity_id:
                field_to_relationship[fk_field] = {
                    "target_entity": ref_entity,
                    "target_field": ref_field,
                }

        # Generate YAML content with relationship tests
        columns = []
        for field in request.fields:
            column_dict = {
                "name": field["name"],
                "data_type": field["datatype"],
            }

            # Add description if available
            if field.get("description"):
                column_dict["description"] = field["description"]

            # Add relationship test if field has a relationship defined
            field_name = field["name"]
            if field_name in field_to_relationship:
                rel_info = field_to_relationship[field_name]
                column_dict["data_tests"] = [
                    {
                        "relationships": {
                            "to": f"ref('{rel_info['target_entity']}')",
                            "field": rel_info["target_field"],
                        }
                    }
                ]

            columns.append(column_dict)

        model_dict = {
            "name": request.model_name,
            "columns": columns,
        }

        # Add description if available
        if entity_description:
            model_dict["description"] = entity_description

        schema_content = {
            "version": 2,
            "models": [model_dict],
        }

        # Write to file (using .yml extension to match dbt convention)
        output_path = os.path.join(models_dir, f"{request.entity_id}.yml")

        # Log the path we're writing to
        print(f"Writing dbt schema to: {output_path}")
        print(f"Schema content: {schema_content}")

        with open(output_path, "w") as f:
            yaml.dump(schema_content, f, default_flow_style=False, sort_keys=False)

        print(f"Successfully wrote file to: {output_path}")

        return {
            "status": "success",
            "file_path": output_path,
            "message": f"Schema saved to {output_path}",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error saving dbt schema: {str(e)}"
        )


@app.post("/api/sync-dbt-tests")
async def sync_dbt_tests():
    """Sync relationship tests from ontology to dbt yml files"""
    try:
        if not DBT_PROJECT_PATH:
            raise HTTPException(
                status_code=400,
                detail="dbt_project_path is not configured. Please set it in config.yml",
            )

        # Load ontology
        if not ONTOLOGY_PATH or not os.path.exists(ONTOLOGY_PATH):
            raise HTTPException(status_code=404, detail="Ontology file not found")

        with open(ONTOLOGY_PATH, "r") as f:
            ontology = yaml.safe_load(f) or {}

        entities = ontology.get("entities", [])
        relationships = ontology.get("relationships", [])

        # Build entity lookup
        entity_map = {e["id"]: e for e in entities}

        # Group relationships by target entity (the one with the FK)
        # For one_to_many: source has PK, target has FK
        # For many_to_one: source has FK, target has PK
        fk_by_entity = {}  # entity_id -> list of {fk_field, ref_entity, ref_field}

        for rel in relationships:
            source_id = rel.get("source")
            target_id = rel.get("target")
            rel_type = rel.get("type", "one_to_many")
            source_field = rel.get("source_field")
            target_field = rel.get("target_field")

            if not source_field or not target_field:
                continue  # Skip relationships without field mappings

            # FK is on the "many" side: target for one_to_many, source otherwise
            fk_on_target = rel_type == "one_to_many"

            fk_entity = target_id if fk_on_target else source_id
            fk_field = target_field if fk_on_target else source_field
            ref_entity = source_id if fk_on_target else target_id
            ref_field = source_field if fk_on_target else target_field

            fk_by_entity.setdefault(fk_entity, []).append(
                {
                    "fk_field": fk_field,
                    "ref_entity": ref_entity,
                    "ref_field": ref_field,
                }
            )

        # Determine models directory
        if DBT_MODEL_PATHS and len(DBT_MODEL_PATHS) > 0:
            models_subdir = DBT_MODEL_PATHS[0]
        else:
            models_subdir = "models"

        models_dir = os.path.abspath(
            os.path.join(DBT_PROJECT_PATH, "models", models_subdir)
        )

        updated_files = []

        # Update yml files for entities with FK relationships
        for entity_id, fk_list in fk_by_entity.items():
            entity = entity_map.get(entity_id)
            if not entity:
                continue

            # Find or create yml file
            yml_path = os.path.join(models_dir, f"{entity_id}.yml")

            if os.path.exists(yml_path):
                # Load existing yml
                with open(yml_path, "r") as f:
                    schema = yaml.safe_load(f) or {"version": 2, "models": []}
            else:
                # Create new yml structure
                schema = {"version": 2, "models": []}

            # Find or create model entry
            models_list = schema.get("models", [])
            model_entry = None
            for m in models_list:
                if m.get("name") == entity_id or m.get("name") == entity.get("label"):
                    model_entry = m
                    break

            if not model_entry:
                model_entry = {"name": entity_id, "columns": []}
                models_list.append(model_entry)
                schema["models"] = models_list

            # Sync description if available in ontology
            if entity.get("description"):
                model_entry["description"] = entity.get("description")

            # Ensure columns list exists
            if "columns" not in model_entry:
                model_entry["columns"] = []

            # Add/update relationship tests for each FK
            for fk_info in fk_list:
                fk_field = fk_info["fk_field"]
                ref_entity = fk_info["ref_entity"]
                ref_field = fk_info["ref_field"]

                # Find or create column entry
                col_entry = None
                for col in model_entry["columns"]:
                    if col.get("name") == fk_field:
                        col_entry = col
                        break

                if not col_entry:
                    col_entry = {"name": fk_field, "data_type": "text"}
                    model_entry["columns"].append(col_entry)

                # Add/update relationship test
                rel_test = {
                    "relationships": {
                        "to": f"ref('{ref_entity}')",
                        "field": ref_field,
                    }
                }

                # Check if data_tests exists and update
                data_tests = col_entry.get("data_tests", [])

                # Remove any existing relationship test for this column
                data_tests = [t for t in data_tests if "relationships" not in t]
                data_tests.append(rel_test)
                col_entry["data_tests"] = data_tests

            # Write updated yml
            with open(yml_path, "w") as f:
                yaml.dump(schema, f, default_flow_style=False, sort_keys=False)

            updated_files.append(yml_path)

        return {
            "status": "success",
            "message": f"Updated {len(updated_files)} file(s)",
            "files": updated_files,
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Error syncing dbt tests: {str(e)}"
        )


@app.get("/api/infer-relationships")
async def infer_relationships():
    """Scan dbt yml files and infer entity relationships from relationship tests"""
    try:
        # Validate that DBT_PROJECT_PATH is set
        if not DBT_PROJECT_PATH:
            raise HTTPException(
                status_code=400,
                detail="dbt_project_path is not configured. Please set it in config.yml",
            )

        # Determine the models directory
        if DBT_MODEL_PATHS and len(DBT_MODEL_PATHS) > 0:
            models_subdir = DBT_MODEL_PATHS[0]
        else:
            models_subdir = "models"

        models_dir = os.path.abspath(
            os.path.join(DBT_PROJECT_PATH, "models", models_subdir)
        )

        if not os.path.exists(models_dir):
            return {"relationships": []}

        # Load ontology to map model names to entity IDs
        # Maps: model name (from dbt_model unique_id) -> entity id on canvas
        model_to_entity = {}
        if ONTOLOGY_PATH and os.path.exists(ONTOLOGY_PATH):
            try:
                with open(ONTOLOGY_PATH, "r") as f:
                    ontology_data = yaml.safe_load(f) or {}
                    entities = ontology_data.get("entities", [])
                    for entity in entities:
                        entity_id = entity.get("id")
                        dbt_model = entity.get("dbt_model")
                        if dbt_model:
                            # Extract model name from unique_id like "model.nba_analytics.team" -> "team"
                            model_name = (
                                dbt_model.split(".")[-1]
                                if "." in dbt_model
                                else dbt_model
                            )
                            model_to_entity[model_name] = entity_id
                        # Also map entity_id to itself for non-bound entities
                        model_to_entity[entity_id] = entity_id
            except Exception as e:
                print(f"Warning: Could not load ontology for entity mapping: {e}")

        relationships = []

        # Scan all yml files in the models directory
        for filename in os.listdir(models_dir):
            if not filename.endswith((".yml", ".yaml")):
                continue

            filepath = os.path.join(models_dir, filename)
            try:
                with open(filepath, "r") as f:
                    schema_data = yaml.safe_load(f) or {}

                models_list = schema_data.get("models", [])
                for model in models_list:
                    model_name = model.get("name")
                    if not model_name:
                        continue

                    # Map model name to entity ID using bound dbt models
                    entity_id = model_to_entity.get(model_name, model_name)

                    columns = model.get("columns", [])
                    for column in columns:
                        data_tests = column.get("data_tests", [])
                        for test in data_tests:
                            if "relationships" in test:
                                rel_test = test["relationships"]
                                # Extract target model from ref('model_name') or just 'model_name'
                                to_ref = rel_test.get("to", "")
                                target_field = rel_test.get("field", "")

                                # Parse ref('model_name') -> model_name
                                target_model = to_ref
                                if to_ref.startswith("ref('") and to_ref.endswith("')"):
                                    target_model = to_ref[5:-2]
                                elif to_ref.startswith('ref("') and to_ref.endswith(
                                    '")'
                                ):
                                    target_model = to_ref[5:-2]

                                # Map target model name to entity ID using bound dbt models
                                target_entity_id = model_to_entity.get(
                                    target_model, target_model
                                )

                                # Create relationship (one_to_many by default, as FK implies many side)
                                # Include field mappings
                                relationships.append(
                                    {
                                        "source": target_entity_id,  # The referenced entity
                                        "target": entity_id,  # The entity with the FK
                                        "label": "",  # Empty label, can be filled later
                                        "type": "one_to_many",  # FK on many side = one_to_many from referenced entity
                                        "source_field": target_field,  # The field in the referenced entity (PK)
                                        "target_field": column.get(
                                            "name"
                                        ),  # The FK field in the current entity
                                    }
                                )
            except Exception as e:
                print(f"Warning: Could not parse {filename}: {e}")
                continue

        # Remove duplicates (same source-target-fields combination)
        seen = set()
        unique_relationships = []
        for rel in relationships:
            key = (
                rel["source"],
                rel["target"],
                rel.get("source_field"),
                rel.get("target_field"),
            )
            if key not in seen:
                seen.add(key)
                unique_relationships.append(rel)

        return {"relationships": unique_relationships}

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Error inferring relationships: {str(e)}"
        )


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
