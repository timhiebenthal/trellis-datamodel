"""Routes for dbt schema sync operations."""
from fastapi import APIRouter, HTTPException
import json
import yaml
import os

from config import (
    MANIFEST_PATH,
    DATA_MODEL_PATH,
    DBT_PROJECT_PATH,
    DBT_MODEL_PATHS,
)
from models.schemas import DbtSchemaRequest, ModelSchemaRequest
from utils.yaml_handler import YamlHandler

router = APIRouter(prefix="/api", tags=["dbt-schema"])


@router.post("/dbt-schema")
async def save_dbt_schema(request: DbtSchemaRequest):
    """Generate and save a dbt schema YAML file for the drafted fields."""
    try:
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

        os.makedirs(models_dir, exist_ok=True)

        # Load data model to get relationships and description
        data_model = {}
        if DATA_MODEL_PATH and os.path.exists(DATA_MODEL_PATH):
            try:
                with open(DATA_MODEL_PATH, "r") as f:
                    data_model = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Warning: Could not load data model: {e}")

        # Use description from request if available, otherwise fallback to data model
        entity_description = request.description
        if not entity_description:
            entities = data_model.get("entities", [])
            for entity in entities:
                if entity.get("id") == request.entity_id:
                    entity_description = entity.get("description")
                    break

        # Build a map of field names to relationships for this entity
        relationships = data_model.get("relationships", [])
        field_to_relationship = {}

        for rel in relationships:
            source_id = rel.get("source")
            target_id = rel.get("target")
            rel_type = rel.get("type", "one_to_many")
            source_field = rel.get("source_field")
            target_field = rel.get("target_field")

            if not source_field or not target_field:
                continue

            fk_on_target = rel_type == "one_to_many"
            fk_entity = target_id if fk_on_target else source_id
            fk_field = target_field if fk_on_target else source_field
            ref_entity = source_id if fk_on_target else target_id
            ref_field = source_field if fk_on_target else target_field

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

            if field.get("description"):
                column_dict["description"] = field["description"]

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

        if entity_description:
            model_dict["description"] = entity_description

        if request.tags:
            model_dict["tags"] = request.tags

        schema_content = {
            "version": 2,
            "models": [model_dict],
        }

        output_path = os.path.join(models_dir, f"{request.entity_id}.yml")

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


@router.post("/sync-dbt-tests")
async def sync_dbt_tests():
    """Sync relationship tests from data model to dbt yml files."""
    try:
        if not DBT_PROJECT_PATH:
            raise HTTPException(
                status_code=400,
                detail="dbt_project_path is not configured. Please set it in config.yml",
            )

        if not DATA_MODEL_PATH or not os.path.exists(DATA_MODEL_PATH):
            raise HTTPException(status_code=404, detail="Data model file not found")

        with open(DATA_MODEL_PATH, "r") as f:
            data_model = yaml.safe_load(f) or {}

        entities = data_model.get("entities", [])
        relationships = data_model.get("relationships", [])

        # Build entity lookup
        entity_map = {e["id"]: e for e in entities}

        # Group relationships by target entity (the one with the FK)
        fk_by_entity = {}

        for rel in relationships:
            source_id = rel.get("source")
            target_id = rel.get("target")
            rel_type = rel.get("type", "one_to_many")
            source_field = rel.get("source_field")
            target_field = rel.get("target_field")

            if not source_field or not target_field:
                continue

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

        os.makedirs(models_dir, exist_ok=True)

        updated_files = []

        for entity in entities:
            entity_id = entity.get("id")
            if not entity_id:
                continue

            model_name = entity_id
            dbt_model = entity.get("dbt_model")
            if dbt_model:
                model_name = dbt_model.split(".")[-1] if "." in dbt_model else dbt_model

            yml_path = os.path.join(models_dir, f"{entity_id}.yml")

            handler = YamlHandler()
            data = handler.load_file(yml_path)

            if not data:
                data = {"version": 2, "models": []}

            model_entry = handler.ensure_model(data, model_name)

            if entity.get("description"):
                handler.update_model_description(model_entry, entity.get("description"))

            # Sync Drafted Fields
            drafted_fields = entity.get("drafted_fields", [])
            for field in drafted_fields:
                f_name = field.get("name")
                f_type = field.get("datatype")
                f_desc = field.get("description")

                if not f_name:
                    continue

                col = handler.ensure_column(model_entry, f_name)
                handler.update_column(col, data_type=f_type, description=f_desc)

            # Sync Relationships (FKs)
            fk_list = fk_by_entity.get(entity_id, [])
            for fk_info in fk_list:
                fk_field = fk_info["fk_field"]
                ref_entity = fk_info["ref_entity"]
                ref_field = fk_info["ref_field"]

                col = handler.ensure_column(model_entry, fk_field)

                if "data_type" not in col:
                    col["data_type"] = "text"

                handler.add_relationship_test(col, ref_entity, ref_field)

            handler.save_file(yml_path, data)
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


@router.get("/models/{model_name}/schema")
async def get_model_schema(model_name: str):
    """Get the schema for a specific model from its YAML file."""
    try:
        if not DBT_PROJECT_PATH:
            raise HTTPException(
                status_code=400,
                detail="dbt_project_path is not configured. Please set it in config.yml",
            )

        if not os.path.exists(MANIFEST_PATH):
            raise HTTPException(
                status_code=404, detail=f"Manifest not found at {MANIFEST_PATH}"
            )

        with open(MANIFEST_PATH, "r") as f:
            manifest = json.load(f)

        model_node = None
        for key, node in manifest.get("nodes", {}).items():
            if node.get("resource_type") == "model" and node.get("name") == model_name:
                model_node = node
                break

        if not model_node:
            raise HTTPException(
                status_code=404, detail=f"Model '{model_name}' not found in manifest"
            )

        original_file_path = model_node.get("original_file_path", "")
        if not original_file_path:
            raise HTTPException(
                status_code=404,
                detail=f"No original_file_path found for model '{model_name}'",
            )

        sql_path = os.path.join(DBT_PROJECT_PATH, original_file_path)
        base_path = os.path.splitext(sql_path)[0]
        yml_path = f"{base_path}.yml"

        handler = YamlHandler()
        data = handler.load_file(yml_path)

        if not data:
            return {
                "model_name": model_name,
                "description": "",
                "columns": [],
                "file_path": yml_path,
            }

        model_entry = handler.find_model(data, model_name)
        if not model_entry:
            return {
                "model_name": model_name,
                "description": "",
                "columns": [],
                "file_path": yml_path,
            }

        columns = handler.get_columns(model_entry)

        return {
            "model_name": model_name,
            "description": model_entry.get("description", ""),
            "columns": columns,
            "file_path": yml_path,
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Error reading model schema: {str(e)}"
        )


@router.post("/models/{model_name}/schema")
async def update_model_schema(model_name: str, request: ModelSchemaRequest):
    """Update the schema for a specific model in its YAML file."""
    try:
        if not DBT_PROJECT_PATH:
            raise HTTPException(
                status_code=400,
                detail="dbt_project_path is not configured. Please set it in config.yml",
            )

        if not os.path.exists(MANIFEST_PATH):
            raise HTTPException(
                status_code=404, detail=f"Manifest not found at {MANIFEST_PATH}"
            )

        with open(MANIFEST_PATH, "r") as f:
            manifest = json.load(f)

        model_node = None
        for key, node in manifest.get("nodes", {}).items():
            if node.get("resource_type") == "model" and node.get("name") == model_name:
                model_node = node
                break

        if not model_node:
            raise HTTPException(
                status_code=404, detail=f"Model '{model_name}' not found in manifest"
            )

        original_file_path = model_node.get("original_file_path", "")
        if not original_file_path:
            raise HTTPException(
                status_code=404,
                detail=f"No original_file_path found for model '{model_name}'",
            )

        sql_path = os.path.join(DBT_PROJECT_PATH, original_file_path)
        base_path = os.path.splitext(sql_path)[0]
        yml_path = f"{base_path}.yml"

        handler = YamlHandler()
        data = handler.load_file(yml_path)

        if not data:
            data = {"version": 2, "models": []}

        model_entry = handler.ensure_model(data, model_name)

        if request.description is not None:
            handler.update_model_description(model_entry, request.description)

        handler.update_columns_batch(model_entry, request.columns)

        if request.tags is not None:
            handler.update_model_tags(model_entry, request.tags)

        handler.save_file(yml_path, data)

        return {
            "status": "success",
            "message": f"Schema updated for model '{model_name}'",
            "file_path": yml_path,
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Error updating model schema: {str(e)}"
        )


@router.get("/infer-relationships")
async def infer_relationships():
    """Scan dbt yml files and infer entity relationships from relationship tests."""
    try:
        if not DBT_PROJECT_PATH:
            raise HTTPException(
                status_code=400,
                detail="dbt_project_path is not configured. Please set it in config.yml",
            )

        if DBT_MODEL_PATHS and len(DBT_MODEL_PATHS) > 0:
            models_subdir = DBT_MODEL_PATHS[0]
        else:
            models_subdir = "models"

        models_dir = os.path.abspath(
            os.path.join(DBT_PROJECT_PATH, "models", models_subdir)
        )

        if not os.path.exists(models_dir):
            return {"relationships": []}

        # Load data model to map model names to entity IDs
        model_to_entity = {}
        if DATA_MODEL_PATH and os.path.exists(DATA_MODEL_PATH):
            try:
                with open(DATA_MODEL_PATH, "r") as f:
                    data_model = yaml.safe_load(f) or {}
                    entities = data_model.get("entities", [])
                    for entity in entities:
                        entity_id = entity.get("id")
                        dbt_model = entity.get("dbt_model")
                        if dbt_model:
                            model_name = (
                                dbt_model.split(".")[-1]
                                if "." in dbt_model
                                else dbt_model
                            )
                            model_to_entity[model_name] = entity_id
                        model_to_entity[entity_id] = entity_id
            except Exception as e:
                print(f"Warning: Could not load data model for entity mapping: {e}")

        relationships = []

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

                    entity_id = model_to_entity.get(model_name, model_name)

                    columns = model.get("columns", [])
                    for column in columns:
                        data_tests = column.get("data_tests", [])
                        for test in data_tests:
                            if "relationships" in test:
                                rel_test = test["relationships"]
                                to_ref = rel_test.get("to", "")
                                target_field = rel_test.get("field", "")

                                target_model = to_ref
                                if to_ref.startswith("ref('") and to_ref.endswith("')"):
                                    target_model = to_ref[5:-2]
                                elif to_ref.startswith('ref("') and to_ref.endswith(
                                    '")'
                                ):
                                    target_model = to_ref[5:-2]

                                target_entity_id = model_to_entity.get(
                                    target_model, target_model
                                )

                                relationships.append(
                                    {
                                        "source": target_entity_id,
                                        "target": entity_id,
                                        "label": "",
                                        "type": "one_to_many",
                                        "source_field": target_field,
                                        "target_field": column.get("name"),
                                    }
                                )
            except Exception as e:
                print(f"Warning: Could not parse {filename}: {e}")
                continue

        # Remove duplicates
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

