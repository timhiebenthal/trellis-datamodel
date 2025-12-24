"""
dbt-core adapter implementation.

Handles parsing dbt manifest.json/catalog.json and generating dbt schema YAML files.
"""

import copy
import json
import os
import re
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

    def get_model_dirs(self) -> list[str]:
        """
        Resolve configured models directories, normalizing common dbt prefixes.

        Users may configure entries like "3_core", "models/3_entity", or absolute
        paths. We normalize these to real directories so downstream scans work.
        """

        def _normalize(subdir: str) -> str:
            # Absolute path - return as-is
            if os.path.isabs(subdir):
                return os.path.abspath(subdir).rstrip(os.sep)

            # Remove leading "./"
            while subdir.startswith("./"):
                subdir = subdir[2:]

            # Strip an optional leading "models/" so we don't double-prepend
            prefix = f"models{os.sep}"
            if subdir.startswith(prefix):
                subdir = subdir[len(prefix) :]

            return os.path.abspath(
                os.path.join(self.project_path, "models", subdir)
            ).rstrip(os.sep)

        if self.model_paths:
            # Remove duplicates while preserving order
            seen = set()
            normalized = []
            for path in self.model_paths:
                norm = _normalize(path)
                if norm not in seen:
                    seen.add(norm)
                    normalized.append(norm)
            return normalized

        return [
            os.path.abspath(os.path.join(self.project_path, "models")).rstrip(os.sep)
        ]

    def _entity_to_model_name(self, entity: dict[str, Any]) -> str:
        """
        Resolve the dbt model name for an entity.

        Prefers the bound dbt_model (strips project prefix), otherwise falls back to
        the entity ID so unbound entities still persist somewhere.
        """
        dbt_model = entity.get("dbt_model")
        if dbt_model:
            # dbt unique_id for versioned models looks like model.<project>.<name>.v2
            parts = dbt_model.split(".")
            if len(parts) >= 2 and re.match(r"v\d+$", parts[-1]):
                # Use the model name part (the element before the vN suffix)
                return parts[-2]
            return parts[-1]
        return entity.get("id") or ""

    def _build_model_keys(self, base: str, version: Optional[str] = None) -> list[str]:
        """
        Generate a set of lookup keys for a model, including versioned variants.
        """
        keys = [base]
        if version is not None:
            # Version may come through as int from YAML; normalize to string
            version_str = str(version)
            # Support common ref patterns:
            # - ref('model', v=2)   -> base.v2
            # - alias names         -> base_v2
            # - fully qualified     -> base.v2 and base_v2
            version_num = version_str.lstrip("v")
            keys.extend(
                [
                    f"{base}.v{version_num}",
                    f"{base}_v{version_num}",
                    f"{base}v{version_num}",
                ]
            )
        # Deduplicate while preserving order
        seen = set()
        ordered_keys = []
        for k in keys:
            if k not in seen:
                seen.add(k)
                ordered_keys.append(k)
        return ordered_keys

    def _get_model_to_entity_map(self) -> dict[str, str]:
        """Build mapping from model names (with version aliases) to entity IDs."""
        model_to_entity: dict[str, str] = {}
        data_model = self._load_data_model()
        entities = data_model.get("entities", [])
        for entity in entities:
            entity_id = entity.get("id")
            dbt_model = entity.get("dbt_model")
            if dbt_model:
                parts = dbt_model.split(".")
                version_part = None
                if len(parts) >= 2 and re.match(r"v\d+$", parts[-1]):
                    version_part = parts[-1].lstrip("v")
                    base_name = parts[-2]
                else:
                    base_name = parts[-1]

                # Map the raw unique_id as well as base/version variants
                model_to_entity[dbt_model] = entity_id
                for key in self._build_model_keys(base_name, version_part):
                    model_to_entity[key] = entity_id
            # Map additional models to the same entity
            additional_models = entity.get("additional_models", [])
            for add_model in additional_models:
                parts = add_model.split(".")
                version_part = None
                if len(parts) >= 2 and re.match(r"v\d+$", parts[-1]):
                    version_part = parts[-1].lstrip("v")
                    base_name = parts[-2]
                else:
                    base_name = parts[-1]

                model_to_entity[add_model] = entity_id
                for key in self._build_model_keys(base_name, version_part):
                    model_to_entity[key] = entity_id
            if entity_id:
                model_to_entity[entity_id] = entity_id
        return model_to_entity

    def _get_model_yml_path(
        self, model_name: str, target_version: Optional[int] = None
    ) -> Optional[str]:
        """Get the yml file path for a model from the manifest."""
        if not os.path.exists(self.manifest_path):
            return None

        manifest = self._load_manifest()
        preferred_node: Optional[dict] = None
        fallback_node: Optional[dict] = None
        for key, node in manifest.get("nodes", {}).items():
            if node.get("resource_type") == "model" and node.get("name") == model_name:
                if target_version is not None and node.get("version") == target_version:
                    preferred_node = node
                    break
                if fallback_node is None:
                    fallback_node = node

        node = preferred_node or fallback_node
        if not node:
            return None

        return self._derive_yml_path_from_node(node)

    def _normalize_patch_path(self, patch_path: str) -> str:
        """
        Convert a manifest patch_path (which may include a scheme) into an
        absolute filesystem path rooted at the dbt project.
        """
        if "://" in patch_path:
            patch_path = patch_path.split("://", 1)[1]

        patch_path = patch_path.lstrip("/")

        if os.path.isabs(patch_path):
            return patch_path

        # Default: resolve relative to the dbt project directory
        base = self.project_path or "."
        return os.path.abspath(os.path.join(base, patch_path))

    def _derive_yml_path_from_node(self, node: dict) -> Optional[str]:
        """
        Determine the YAML file path for a manifest node, preferring patch_path.
        """
        patch_path = node.get("patch_path")
        if patch_path:
            return self._normalize_patch_path(patch_path)

        original_file_path = node.get("original_file_path", "")
        if not original_file_path:
            return None

        sql_path = os.path.join(self.project_path, original_file_path)
        base_path = os.path.splitext(sql_path)[0]
        yml_path = f"{base_path}.yml"

        # Common versioned layout: player_v2.sql + player.yml
        if not os.path.exists(yml_path):
            base_path = re.sub(r"_v\d+$", "", base_path)
            yml_path = f"{base_path}.yml"

        return yml_path

    def _extract_version_from_string(self, value: str) -> Optional[int]:
        """Extract integer version from strings like 'model.proj.player.v2'."""
        if not value:
            return None

        match = re.search(r"\.v(\d+)$", value)
        if match:
            return int(match.group(1))

        if value.startswith("v") and value[1:].isdigit():
            return int(value[1:])

        return None

    def _resolve_model_version(
        self, model_name: str, entity_id: str, data_model: dict[str, Any]
    ) -> Optional[int]:
        """
        Resolve target version from data model (dbt_model) or manifest node.

        Prefers explicit dbt_model binding with .vN suffix, falls back to
        manifest node version.
        """
        for entity in data_model.get("entities", []):
            if entity.get("id") != entity_id:
                continue
            dbt_model = entity.get("dbt_model") or ""
            # Check last token after split to support fully-qualified model IDs
            last_token = dbt_model.split(".")[-1] if dbt_model else ""
            version = self._extract_version_from_string(last_token)
            if version is not None:
                return version

        if os.path.exists(self.manifest_path):
            manifest = self._load_manifest()
            for node in manifest.get("nodes", {}).values():
                if node.get("resource_type") != "model":
                    continue
                if node.get("name") != model_name:
                    continue
                node_version = node.get("version")
                if node_version:
                    return int(node_version)

        return None

    def _find_manifest_model_nodes(
        self, manifest: dict[str, Any], model_name: str
    ) -> list[dict[str, Any]]:
        """Collect manifest nodes matching a given model name."""
        return [
            node
            for node in manifest.get("nodes", {}).values()
            if node.get("resource_type") == "model" and node.get("name") == model_name
        ]

    def _select_model_node(
        self, candidates: list[dict[str, Any]], target_version: Optional[int]
    ) -> Optional[dict[str, Any]]:
        """
        Choose the best matching manifest node.

        Prefers an exact version match when requested; otherwise picks the
        highest numbered version when available, or the first candidate.
        """
        if target_version is not None:
            for node in candidates:
                node_version = node.get("version")
                if node_version is not None and int(node_version) == target_version:
                    return node

        if not candidates:
            return None

        versioned = [n for n in candidates if n.get("version") is not None]
        if versioned:
            return sorted(versioned, key=lambda n: n.get("version") or 0)[-1]

        return candidates[0]

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
                    "version": node.get("version"),
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

    def get_model_schema(
        self, model_name: str, version: Optional[int] = None
    ) -> ModelSchema:
        """Get the current schema definition for a specific model from its YAML file."""
        if not os.path.exists(self.manifest_path):
            raise FileNotFoundError(f"Manifest not found at {self.manifest_path}")

        manifest = self._load_manifest()

        candidate_nodes = self._find_manifest_model_nodes(manifest, model_name)
        model_node = self._select_model_node(candidate_nodes, target_version=version)

        if not model_node:
            raise ValueError(f"Model '{model_name}' not found in manifest")

        yml_path = self._derive_yml_path_from_node(model_node)
        if not yml_path:
            raise ValueError(
                f"No patch_path or original_file_path found for model '{model_name}'"
            )

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

        target_version = version if version is not None else model_node.get("version")
        version_entry = None
        versions = model_entry.get("versions") or []
        if versions:
            if target_version is not None:
                for ver in versions:
                    if ver.get("v") == target_version:
                        version_entry = ver
                        break
            if version_entry is None:
                version_entry = sorted(versions, key=lambda ver: ver.get("v") or 0)[-1]

        # Prefer versioned block if present
        node_for_schema = version_entry or model_entry

        columns = self.yaml_handler.get_columns(node_for_schema)
        tags = self.yaml_handler.get_model_tags(node_for_schema)
        return {
            "model_name": model_name,
            "description": node_for_schema.get("description", ""),
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
        version: Optional[int] = None,
    ) -> Path:
        """Save/update the schema definition for a model."""
        if not os.path.exists(self.manifest_path):
            raise FileNotFoundError(f"Manifest not found at {self.manifest_path}")

        manifest = self._load_manifest()

        candidate_nodes = self._find_manifest_model_nodes(manifest, model_name)
        model_node = self._select_model_node(candidate_nodes, target_version=version)

        if not model_node:
            raise ValueError(f"Model '{model_name}' not found in manifest")

        yml_path = self._derive_yml_path_from_node(model_node)
        if not yml_path:
            raise ValueError(
                f"No patch_path or original_file_path found for model '{model_name}'"
            )

        data = self.yaml_handler.load_file(yml_path)
        if not data:
            data = {"version": 2, "models": []}

        model_entry = self.yaml_handler.ensure_model(data, model_name)

        target_version = version if version is not None else model_node.get("version")
        if target_version is not None:
            # Versioned model: update version entry and keep latest_version in sync (non-decreasing)
            self.yaml_handler.set_latest_version(model_entry, target_version)
            version_entry = self.yaml_handler.ensure_model_version(
                model_entry, target_version
            )

            if description is not None:
                self.yaml_handler.update_model_description(version_entry, description)
                # Keep top-level description aligned when present
                self.yaml_handler.update_model_description(model_entry, description)

            self.yaml_handler.update_columns_batch(version_entry, columns)

            if tags is not None:
                self.yaml_handler.update_version_tags(version_entry, tags)
        else:
            # Non-versioned model
            if description is not None:
                self.yaml_handler.update_model_description(model_entry, description)

            self.yaml_handler.update_columns_batch(model_entry, columns)

            if tags is not None:
                self.yaml_handler.update_model_tags(model_entry, tags)

        self.yaml_handler.save_file(yml_path, data)
        return Path(yml_path)

    def _parse_ref(self, ref_value: str) -> tuple[str, Optional[str]]:
        """
        Parse ref() targets, supporting optional version arguments.

        Examples:
            ref('player') -> ("player", None)
            ref('player', v=1) -> ("player", "1")
            ref("player", version=2) -> ("player", "2")
        """
        ref_pattern = (
            r"ref\(\s*['\"]([^,'\"]+)['\"](?:\s*,\s*(?:v|version)\s*=\s*([0-9]+))?\s*\)"
        )
        match = re.fullmatch(ref_pattern, ref_value.strip())
        if match:
            return match.group(1), match.group(2)
        return ref_value, None

    def _resolve_entity_id(
        self, model_to_entity: dict[str, str], base_name: str, version: Optional[str]
    ) -> str:
        """
        Resolve an entity id using base model name plus optional version.
        Falls back to the base name if no mapping is found.
        """
        for key in self._build_model_keys(base_name, version):
            if key in model_to_entity:
                return model_to_entity[key]
        # Fallback: try the raw base name
        return model_to_entity.get(base_name, base_name)

    def infer_relationships(self, include_unbound: bool = False) -> list[Relationship]:
        """Scan dbt yml files and infer entity relationships from relationship tests.
        
        When include_unbound=True, returns ALL relationships found in dbt yml files
        using raw model names. The frontend is responsible for mapping model names
        to entity IDs based on current canvas state (which may not be saved yet).
        """
        model_dirs = self.get_model_dirs()
        model_to_entity = self._get_model_to_entity_map()

        # Only keep relationships where both ends map to entities that are bound to
        # at least one dbt model (including additional_models). This prevents writing
        # relationships for unbound entities in large projects.
        # When include_unbound is True, skip filtering entirely - return all relationships
        # using raw model names so the frontend can map them to current canvas state.
        bound_entities: set[str] = set()
        if not include_unbound:
            data_model = self._load_data_model()
            bound_entities = {
                e.get("id")
                for e in data_model.get("entities", [])
                if e.get("id") and (e.get("dbt_model") or e.get("additional_models"))
            }

        relationships: list[Relationship] = []
        yml_found = False

        for models_dir in model_dirs:
            if not os.path.exists(models_dir):
                continue

            for root, _, files in os.walk(models_dir):
                for filename in files:
                    if not filename.endswith((".yml", ".yaml")):
                        continue
                    yml_found = True

                    filepath = os.path.join(root, filename)
                    try:
                        with open(filepath, "r") as f:
                            schema_data = yaml.safe_load(f) or {}

                        models_list = schema_data.get("models", [])
                        for model in models_list:
                            base_model_name = model.get("name")
                            if not base_model_name:
                                continue

                            # Versioned models may declare columns inside versions list
                            version_entries = model.get("versions", [])
                            versioned_columns = []
                            base_columns = model.get("columns", []) or []

                            if isinstance(version_entries, list) and version_entries:
                                # Carry forward columns when a version uses "include: all"
                                previous_columns = copy.deepcopy(base_columns)
                                for ver in version_entries:
                                    raw_columns = ver.get("columns", []) or []
                                    expanded_columns: list[dict] = []
                                    for col in raw_columns:
                                        if isinstance(col, dict) and col.get("include") == "all":
                                            expanded_columns.extend(copy.deepcopy(previous_columns))
                                        else:
                                            expanded_columns.append(col)

                                    # If no columns are explicitly provided, fall back to previous set
                                    if not expanded_columns and previous_columns:
                                        expanded_columns = copy.deepcopy(previous_columns)

                                    versioned_columns.append(
                                        (ver.get("v") or ver.get("version"), expanded_columns)
                                    )
                                    previous_columns = copy.deepcopy(expanded_columns)
                            else:
                                versioned_columns.append((None, base_columns))

                            for model_version, columns in versioned_columns:
                                # When include_unbound, use raw model name so frontend can remap
                                # Otherwise resolve to entity ID from saved data model
                                if include_unbound:
                                    entity_id = base_model_name
                                else:
                                    entity_id = self._resolve_entity_id(
                                        model_to_entity, base_model_name, model_version
                                    )

                                for column in columns or []:
                                    test_blocks = []
                                    for key in ("tests", "data_tests"):
                                        value = column.get(key, [])
                                        if isinstance(value, list):
                                            test_blocks.extend(value)

                                    for test in test_blocks:
                                        if (
                                            not isinstance(test, dict)
                                            or "relationships" not in test
                                        ):
                                            continue

                                        rel_test = test["relationships"]
                                        args = rel_test.get("arguments", {}) or {}

                                        # Support both the recommended arguments block and legacy top-level keys
                                        to_ref = rel_test.get("to", "") or args.get(
                                            "to", ""
                                        )
                                        target_field = rel_test.get(
                                            "field", ""
                                        ) or args.get("field", "")

                                        # If either ref target or field is missing, skip and log for debugging
                                        if not to_ref or not target_field:
                                            continue

                                        target_base, target_version_str = self._parse_ref(
                                            to_ref
                                        )
                                        
                                        # Convert version string to int if present
                                        target_version_int = None
                                        if target_version_str:
                                            try:
                                                target_version_int = int(target_version_str)
                                            except ValueError:
                                                pass
                                        
                                        # Convert model_version to int if present
                                        source_version_int = None
                                        if model_version is not None:
                                            try:
                                                source_version_int = int(model_version)
                                            except (ValueError, TypeError):
                                                pass
                                        
                                        # When include_unbound, use raw model name
                                        if include_unbound:
                                            target_entity_id = target_base
                                        else:
                                            target_entity_id = self._resolve_entity_id(
                                                model_to_entity, target_base, target_version_str
                                            )

                                            # Skip relationships where either side is not bound
                                            if (
                                                entity_id not in bound_entities
                                                or target_entity_id not in bound_entities
                                            ):
                                                continue

                                        relationships.append(
                                            {
                                                "source": target_entity_id,
                                                "target": entity_id,
                                                "label": "",
                                                "type": "one_to_many",
                                                "source_field": target_field,
                                                "target_field": column.get("name"),
                                                "source_model_name": target_base,
                                                "source_model_version": target_version_int,
                                                "target_model_name": base_model_name,
                                                "target_model_version": source_version_int,
                                            }
                                        )
                    except Exception as e:
                        print(f"Warning: Could not parse {filepath}: {e}")
                        continue

        if not yml_found:
            raise FileNotFoundError(
                f"No schema yml files found under configured dbt model paths: {model_dirs}"
            )

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
        entity_map = {e["id"]: e for e in entities if e.get("id")}
        # Map entity_id -> dbt model name (best-effort)
        entity_model_name: dict[str, str] = {
            eid: self._entity_to_model_name(ent) for eid, ent in entity_map.items()
        }

        # Group relationships by entity (the one with the FK)
        # FK is always on the "many" side of the relationship
        fk_by_entity: dict[str, list[dict]] = {}
        
        # Track all fields that appear in ANY relationship in the data model
        # This helps us identify which relationship tests are managed by us vs manually added
        all_relationship_fields_by_entity: dict[str, set[str]] = {}

        for rel in relationships:
            source_id = rel.get("source")
            target_id = rel.get("target")
            rel_type = rel.get("type", "one_to_many")
            source_field = rel.get("source_field")
            target_field = rel.get("target_field")

            if not source_field or not target_field:
                continue

            # Determine which side has the "many" cardinality (where FK should be)
            # Relationship types ending in "_to_many" or starting with "many_to_" have FK on target/source respectively
            # For one_to_one, FK is typically on source (FK holder → referenced table per spec)
            if rel_type in ("one_to_many", "one_to_zero_or_many", "zero_or_one_to_many", "zero_or_many_to_many"):
                # FK on target (target is the "many" side)
                fk_entity = target_id
                fk_field = target_field
                ref_entity = source_id
                ref_field = source_field
            elif rel_type in ("many_to_one", "many_to_many", "zero_or_many_to_one"):
                # FK on source (source is the "many" side)
                fk_entity = source_id
                fk_field = source_field
                ref_entity = target_id
                ref_field = target_field
            elif rel_type == "one_to_one":
                # For one_to_one, FK is on source (FK holder → referenced table per spec)
                fk_entity = source_id
                fk_field = source_field
                ref_entity = target_id
                ref_field = target_field
            else:
                # Fallback: assume FK on target (default behavior)
                fk_entity = target_id
                fk_field = target_field
                ref_entity = source_id
                ref_field = source_field

            fk_by_entity.setdefault(fk_entity, []).append(
                {
                    "fk_field": fk_field,
                    "ref_entity": ref_entity,
                    "ref_field": ref_field,
                }
            )
            
            # Track which fields are involved in relationships
            all_relationship_fields_by_entity.setdefault(source_id, set()).add(source_field)
            all_relationship_fields_by_entity.setdefault(target_id, set()).add(target_field)

        models_dir = self.get_model_dirs()[0]
        os.makedirs(models_dir, exist_ok=True)

        updated_files: list[Path] = []

        for entity in entities:
            entity_id = entity.get("id")
            if not entity_id:
                continue

            model_name = entity_model_name.get(entity_id, entity_id)

            # For bound entities, use the correct path from manifest
            # For unbound entities, fall back to models_dir/{entity_id}.yml
            yml_path = None
            if entity.get("dbt_model"):
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
            # Build a map of which fields should have which relationship tests
            fk_list = fk_by_entity.get(entity_id, [])
            fk_fields = {fk_info["fk_field"] for fk_info in fk_list}
            
            # Get all fields that appear in relationships for this entity
            relationship_fields = all_relationship_fields_by_entity.get(entity_id, set())
            
            # Clean up: Remove relationship tests from fields that:
            # 1. Are in a relationship in the data model (relationship_fields)
            # 2. But are NOT currently FKs (not in fk_fields)
            # This removes tests when relationships are moved or type changes
            # But preserves manually added tests (not in relationship_fields)
            if "columns" in model_entry:
                for col in model_entry.get("columns", []):
                    col_name = col.get("name")
                    if col_name and col_name in relationship_fields and col_name not in fk_fields:
                        # This field was in a relationship but is no longer an FK
                        # Remove its relationship test
                        self.yaml_handler.remove_relationship_test(col)
            
            # Now add/update relationship tests for current FKs
            for fk_info in fk_list:
                fk_field = fk_info["fk_field"]
                ref_entity = fk_info["ref_entity"]
                ref_field = fk_info["ref_field"]

                # Resolve reference model name (dbt model) for relationship test
                ref_model_name = entity_model_name.get(ref_entity, ref_entity)

                col = self.yaml_handler.ensure_column(model_entry, fk_field)

                if "data_type" not in col:
                    col["data_type"] = "text"

                self.yaml_handler.add_relationship_test(col, ref_model_name, ref_field)

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
        # Map entity -> dbt model name for refs
        entity_model_name = {
            e.get("id"): self._entity_to_model_name(e)
            for e in data_model.get("entities", [])
            if e.get("id")
        }

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
                ref_model = entity_model_name.get(
                    rel_info["target_entity"], rel_info["target_entity"]
                )
                column_dict["data_tests"] = [
                    {
                        "relationships": {
                            "arguments": {
                                "to": f"ref('{ref_model}')",
                                "field": rel_info["target_field"],
                            }
                        }
                    }
                ]

            columns.append(column_dict)

        target_version = self._resolve_model_version(
            model_name=model_name, entity_id=entity_id, data_model=data_model
        )

        # Prefer manifest-derived path; fall back to default models directory
        yml_path = self._get_model_yml_path(model_name, target_version=target_version)
        if not yml_path:
            models_dir = self.get_model_dirs()[0]
            os.makedirs(models_dir, exist_ok=True)
            yml_path = os.path.join(models_dir, f"{entity_id}.yml")

        data = self.yaml_handler.load_file(yml_path)
        if not data:
            data = {"version": 2, "models": []}

        model_entry = self.yaml_handler.ensure_model(data, model_name)

        if target_version is not None:
            # Versioned model: update version block and latest_version
            self.yaml_handler.set_latest_version(model_entry, target_version)
            if entity_description:
                self.yaml_handler.update_model_description(
                    model_entry, entity_description
                )

            version_entry = self.yaml_handler.ensure_model_version(
                model_entry, target_version
            )
            self.yaml_handler.update_columns_batch(version_entry, columns)

            if entity_description:
                self.yaml_handler.update_model_description(
                    version_entry, entity_description
                )
            if tags is not None:
                self.yaml_handler.update_version_tags(version_entry, tags)
        else:
            # Non-versioned model: update columns and metadata directly
            if entity_description:
                self.yaml_handler.update_model_description(
                    model_entry, entity_description
                )

            self.yaml_handler.update_columns_batch(model_entry, columns)

            if tags is not None:
                self.yaml_handler.update_model_tags(model_entry, tags)

        self.yaml_handler.save_file(yml_path, data)
        return Path(yml_path)
