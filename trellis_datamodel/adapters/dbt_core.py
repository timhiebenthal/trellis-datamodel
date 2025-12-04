"""
dbt-core adapter implementation.

Handles parsing dbt manifest.json/catalog.json and generating dbt schema YAML files.
"""

import json
import os
import yaml
from pathlib import Path
from typing import Any, Optional

from trellis_datamodel.utils.yaml_handler import YamlHandler
from .base import (
    ColumnInfo,
    ColumnSchema,
    ModelInfo,
    ModelSchema,
    Relationship,
)


class DbtCoreAdapter:
    """Adapter for dbt-core transformation framework."""

    def __init__(
        self,
        manifest_path: str,
        catalog_path: str,
        project_path: str,
        data_model_path: str,
        model_paths: list[str],
    ):
        self.manifest_path = manifest_path
        self.catalog_path = catalog_path
        self.project_path = project_path
        self.data_model_path = data_model_path
        self.model_paths = model_paths
        self.yaml_handler = YamlHandler()

    def _load_catalog(self) -> Optional[dict]:
        """Load catalog.json if it exists."""
        if not os.path.exists(self.catalog_path):
            return None
        try:
            with open(self.catalog_path, "r") as f:
                return json.load(f)
        except Exception as exc:
            print(f"Warning: failed to read catalog at {self.catalog_path}: {exc}")
            return None

    def _load_manifest(self) -> dict:
        """Load manifest.json."""
        with open(self.manifest_path, "r") as f:
            return json.load(f)

    def _load_data_model(self) -> dict:
        """Load data model YAML if it exists."""
        if not self.data_model_path or not os.path.exists(self.data_model_path):
            return {}
        try:
            with open(self.data_model_path, "r") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Could not load data model: {e}")
            return {}

    def _get_models_dir(self) -> str:
        """Get the models directory path."""
        if self.model_paths and len(self.model_paths) > 0:
            models_subdir = self.model_paths[0]
        else:
            models_subdir = "models"
        return os.path.abspath(os.path.join(self.project_path, "models", models_subdir))

    def _get_model_to_entity_map(self) -> dict[str, str]:
        """Build mapping from model names to entity IDs."""
        model_to_entity: dict[str, str] = {}
        data_model = self._load_data_model()
        entities = data_model.get("entities", [])
        for entity in entities:
            entity_id = entity.get("id")
            dbt_model = entity.get("dbt_model")
            if dbt_model:
                model_name = dbt_model.split(".")[-1] if "." in dbt_model else dbt_model
                model_to_entity[model_name] = entity_id
            # Map additional models to the same entity
            additional_models = entity.get("additional_models", [])
            for add_model in additional_models:
                model_name = add_model.split(".")[-1] if "." in add_model else add_model
                model_to_entity[model_name] = entity_id
            if entity_id:
                model_to_entity[entity_id] = entity_id
        return model_to_entity

    def _get_model_yml_path(self, model_name: str) -> Optional[str]:
        """Get the yml file path for a model from the manifest."""
        if not os.path.exists(self.manifest_path):
            return None

        manifest = self._load_manifest()
        for key, node in manifest.get("nodes", {}).items():
            if node.get("resource_type") == "model" and node.get("name") == model_name:
                original_file_path = node.get("original_file_path", "")
                if original_file_path:
                    sql_path = os.path.join(self.project_path, original_file_path)
                    base_path = os.path.splitext(sql_path)[0]
                    return f"{base_path}.yml"
        return None

    def get_models(self) -> list[ModelInfo]:
        """Parse dbt manifest and catalog to return available models."""
        if not os.path.exists(self.manifest_path):
            raise FileNotFoundError(f"Manifest not found at {self.manifest_path}")

        manifest = self._load_manifest()
        catalog = self._load_catalog()
        catalog_nodes = (catalog or {}).get("nodes", {})

        models: list[ModelInfo] = []
        for key, node in manifest.get("nodes", {}).items():
            if node.get("resource_type") != "model":
                continue

            # Filter by path
            original_path = node.get("original_file_path", "")
            if self.model_paths:
                match = any(pattern in original_path for pattern in self.model_paths)
                if not match:
                    continue

            # Get columns from catalog or manifest
            columns: list[ColumnInfo] = []
            unique_id = node.get("unique_id")
            catalog_node = catalog_nodes.get(unique_id)

            if catalog_node:
                for col in catalog_node.get("columns", {}).values():
                    columns.append(
                        {
                            "name": col.get("name"),
                            "type": col.get("type") or col.get("data_type"),
                        }
                    )
            else:
                for col_name, col_data in node.get("columns", {}).items():
                    columns.append({"name": col_name, "type": col_data.get("type")})

            # Extract materialization
            config = node.get("config", {})
            materialized = config.get("materialized", "view")

            models.append(
                {
                    "unique_id": unique_id,
                    "name": node.get("name"),
                    "schema": node.get("schema"),
                    "table": node.get("alias", node.get("name")),
                    "columns": columns,
                    "description": node.get("description"),
                    "materialization": materialized,
                    "file_path": original_path,
                    "tags": node.get("tags", []),
                }
            )

        models.sort(key=lambda x: x["name"])
        return models

    def get_model_schema(self, model_name: str) -> ModelSchema:
        """Get the current schema definition for a specific model from its YAML file."""
        if not os.path.exists(self.manifest_path):
            raise FileNotFoundError(f"Manifest not found at {self.manifest_path}")

        manifest = self._load_manifest()

        # Find model in manifest
        model_node = None
        for key, node in manifest.get("nodes", {}).items():
            if node.get("resource_type") == "model" and node.get("name") == model_name:
                model_node = node
                break

        if not model_node:
            raise ValueError(f"Model '{model_name}' not found in manifest")

        original_file_path = model_node.get("original_file_path", "")
        if not original_file_path:
            raise ValueError(f"No original_file_path found for model '{model_name}'")

        sql_path = os.path.join(self.project_path, original_file_path)
        base_path = os.path.splitext(sql_path)[0]
        yml_path = f"{base_path}.yml"

        data = self.yaml_handler.load_file(yml_path)
        if not data:
            return {
                "model_name": model_name,
                "description": "",
                "columns": [],
                "tags": [],
                "file_path": yml_path,
            }

        model_entry = self.yaml_handler.find_model(data, model_name)
        if not model_entry:
            return {
                "model_name": model_name,
                "description": "",
                "columns": [],
                "tags": [],
                "file_path": yml_path,
            }

        columns = self.yaml_handler.get_columns(model_entry)
        tags = self.yaml_handler.get_model_tags(model_entry)
        return {
            "model_name": model_name,
            "description": model_entry.get("description", ""),
            "columns": columns,
            "tags": tags,
            "file_path": yml_path,
        }

    def save_model_schema(
        self,
        model_name: str,
        columns: list[ColumnSchema],
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> Path:
        """Save/update the schema definition for a model."""
        if not os.path.exists(self.manifest_path):
            raise FileNotFoundError(f"Manifest not found at {self.manifest_path}")

        manifest = self._load_manifest()

        # Find model in manifest
        model_node = None
        for key, node in manifest.get("nodes", {}).items():
            if node.get("resource_type") == "model" and node.get("name") == model_name:
                model_node = node
                break

        if not model_node:
            raise ValueError(f"Model '{model_name}' not found in manifest")

        original_file_path = model_node.get("original_file_path", "")
        if not original_file_path:
            raise ValueError(f"No original_file_path found for model '{model_name}'")

        sql_path = os.path.join(self.project_path, original_file_path)
        base_path = os.path.splitext(sql_path)[0]
        yml_path = f"{base_path}.yml"

        data = self.yaml_handler.load_file(yml_path)
        if not data:
            data = {"version": 2, "models": []}

        model_entry = self.yaml_handler.ensure_model(data, model_name)

        if description is not None:
            self.yaml_handler.update_model_description(model_entry, description)

        self.yaml_handler.update_columns_batch(model_entry, columns)

        if tags is not None:
            self.yaml_handler.update_model_tags(model_entry, tags)

        self.yaml_handler.save_file(yml_path, data)
        return Path(yml_path)

    def infer_relationships(self) -> list[Relationship]:
        """Scan dbt yml files and infer entity relationships from relationship tests."""
        models_dir = self._get_models_dir()

        if not os.path.exists(models_dir):
            return []

        model_to_entity = self._get_model_to_entity_map()
        relationships: list[Relationship] = []

        for root, _, files in os.walk(models_dir):
            for filename in files:
                if not filename.endswith((".yml", ".yaml")):
                    continue

                filepath = os.path.join(root, filename)
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
                                if "relationships" not in test:
                                    continue

                                rel_test = test["relationships"]
                                to_ref = rel_test.get("to", "")
                                target_field = rel_test.get("field", "")

                                # Parse ref('model_name')
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
                    print(f"Warning: Could not parse {filepath}: {e}")
                    continue

        # Remove duplicates
        seen: set[tuple] = set()
        unique_relationships: list[Relationship] = []
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

        return unique_relationships

    def sync_relationships(
        self,
        entities: list[dict[str, Any]],
        relationships: list[dict[str, Any]],
    ) -> list[Path]:
        """Sync relationship definitions from data model to dbt yml files."""
        # Build entity lookup
        entity_map = {e["id"]: e for e in entities}

        # Group relationships by target entity (the one with the FK)
        fk_by_entity: dict[str, list[dict]] = {}

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

        models_dir = self._get_models_dir()
        os.makedirs(models_dir, exist_ok=True)

        updated_files: list[Path] = []

        for entity in entities:
            entity_id = entity.get("id")
            if not entity_id:
                continue

            model_name = entity_id
            dbt_model = entity.get("dbt_model")
            if dbt_model:
                model_name = dbt_model.split(".")[-1] if "." in dbt_model else dbt_model

            # For bound entities, use the correct path from manifest
            # For unbound entities, fall back to models_dir/{entity_id}.yml
            yml_path = None
            if dbt_model:
                yml_path = self._get_model_yml_path(model_name)
            if not yml_path:
                yml_path = os.path.join(models_dir, f"{entity_id}.yml")

            data = self.yaml_handler.load_file(yml_path)
            if not data:
                data = {"version": 2, "models": []}

            model_entry = self.yaml_handler.ensure_model(data, model_name)

            if entity.get("description"):
                self.yaml_handler.update_model_description(
                    model_entry, entity.get("description")
                )

            # Sync Tags
            entity_tags = entity.get("tags")
            if entity_tags is not None:
                self.yaml_handler.update_model_tags(model_entry, entity_tags)

            # Sync Drafted Fields
            drafted_fields = entity.get("drafted_fields", [])
            for field in drafted_fields:
                f_name = field.get("name")
                f_type = field.get("datatype")
                f_desc = field.get("description")

                if not f_name:
                    continue

                col = self.yaml_handler.ensure_column(model_entry, f_name)
                self.yaml_handler.update_column(
                    col, data_type=f_type, description=f_desc
                )

            # Sync Relationships (FKs)
            fk_list = fk_by_entity.get(entity_id, [])
            for fk_info in fk_list:
                fk_field = fk_info["fk_field"]
                ref_entity = fk_info["ref_entity"]
                ref_field = fk_info["ref_field"]

                col = self.yaml_handler.ensure_column(model_entry, fk_field)

                if "data_type" not in col:
                    col["data_type"] = "text"

                self.yaml_handler.add_relationship_test(col, ref_entity, ref_field)

            self.yaml_handler.save_file(yml_path, data)
            updated_files.append(Path(yml_path))

        return updated_files

    def save_dbt_schema(
        self,
        entity_id: str,
        model_name: str,
        fields: list[dict[str, str]],
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> Path:
        """
        Generate and save a dbt schema YAML file for drafted fields.

        This is used for creating new schema files from the data model editor.
        """
        data_model = self._load_data_model()

        # Use description from request if available, otherwise fallback to data model
        entity_description = description
        if not entity_description:
            entities = data_model.get("entities", [])
            for entity in entities:
                if entity.get("id") == entity_id:
                    entity_description = entity.get("description")
                    break

        # Build a map of field names to relationships for this entity
        relationships = data_model.get("relationships", [])
        field_to_relationship: dict[str, dict] = {}

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

            if fk_entity == entity_id:
                field_to_relationship[fk_field] = {
                    "target_entity": ref_entity,
                    "target_field": ref_field,
                }

        # Generate YAML content with relationship tests
        columns = []
        for field in fields:
            column_dict: dict[str, Any] = {
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

        model_dict: dict[str, Any] = {
            "name": model_name,
            "columns": columns,
        }

        if entity_description:
            model_dict["description"] = entity_description

        if tags:
            model_dict["tags"] = tags

        schema_content = {
            "version": 2,
            "models": [model_dict],
        }

        models_dir = self._get_models_dir()
        os.makedirs(models_dir, exist_ok=True)
        output_path = os.path.join(models_dir, f"{entity_id}.yml")

        print(f"Writing dbt schema to: {output_path}")

        with open(output_path, "w") as f:
            yaml.dump(schema_content, f, default_flow_style=False, sort_keys=False)

        return Path(output_path)

