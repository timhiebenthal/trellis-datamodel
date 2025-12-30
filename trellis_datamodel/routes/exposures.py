"""Routes for exposures operations."""

from fastapi import APIRouter, HTTPException
import json
import yaml
import os
import re
from collections import deque
from typing import Dict, Any, List, Optional

from trellis_datamodel import config as cfg
from trellis_datamodel.adapters import get_adapter

router = APIRouter(prefix="/api", tags=["exposures"])


def _parse_ref(ref_value: str) -> tuple[str, Optional[str]]:
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


def _load_manifest() -> Dict[str, Any]:
    """Load dbt manifest.json."""
    if not cfg.MANIFEST_PATH or not os.path.exists(cfg.MANIFEST_PATH):
        return {}
    try:
        with open(cfg.MANIFEST_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load manifest: {e}")
        return {}


def _load_data_model() -> Dict[str, Any]:
    """Load data model YAML."""
    if not cfg.DATA_MODEL_PATH or not os.path.exists(cfg.DATA_MODEL_PATH):
        return {}
    try:
        with open(cfg.DATA_MODEL_PATH, "r") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Warning: Could not load data model: {e}")
        return {}


def _resolve_model_ref(ref_string: str, manifest: Dict[str, Any]) -> Optional[str]:
    """
    Resolve a ref('model_name') string to a model unique_id.

    Returns the unique_id if found, None otherwise.
    """
    model_name, version = _parse_ref(ref_string)
    if not model_name:
        return None

    # Search manifest nodes for matching model
    nodes = manifest.get("nodes", {})
    for unique_id, node in nodes.items():
        if node.get("resource_type") != "model":
            continue
        if node.get("name") == model_name:
            # If version specified, check if it matches
            if version is not None:
                node_version = node.get("version")
                if node_version is not None and str(node_version) == version:
                    return unique_id
            else:
                # No version specified, return first match
                return unique_id

    return None


def _find_entities_for_model(unique_id: str, data_model: Dict[str, Any]) -> List[str]:
    """
    Find all entity IDs that are bound to the given model unique_id.

    Checks both dbt_model and additional_models fields.
    """
    entity_ids = []
    entities = data_model.get("entities", [])
    for entity in entities:
        entity_id = entity.get("id")
        if not entity_id:
            continue

        # Check primary dbt_model
        if entity.get("dbt_model") == unique_id:
            entity_ids.append(entity_id)
            continue

        # Check additional_models
        additional_models = entity.get("additional_models", [])
        if isinstance(additional_models, list) and unique_id in additional_models:
            entity_ids.append(entity_id)

    return entity_ids


def _collect_upstream_model_ids(
    manifest: Dict[str, Any], model_unique_id: str
) -> set[str]:
    """
    Collect all upstream model unique_ids (including the starting model) by traversing
    manifest depends_on relationships.

    Notes:
    - This is table-level lineage, not column-level.
    - We only return dbt models (unique_id starts with "model.").
    - Sources are traversed only as stopping points; they are not returned.
    """
    nodes = manifest.get("nodes", {}) if isinstance(manifest, dict) else {}
    if not nodes or not model_unique_id:
        return set()

    visited: set[str] = set()
    upstream_models: set[str] = set()

    queue: deque[str] = deque([model_unique_id])
    while queue:
        current_id = queue.popleft()
        if current_id in visited:
            continue
        visited.add(current_id)

        if current_id.startswith("model."):
            upstream_models.add(current_id)

        current_node = nodes.get(current_id)
        if not current_node:
            continue

        depends_on = current_node.get("depends_on")
        if not depends_on:
            continue

        if isinstance(depends_on, dict):
            upstream_nodes = depends_on.get("nodes", [])
        elif isinstance(depends_on, list):
            upstream_nodes = depends_on
        else:
            upstream_nodes = []

        for upstream_id in upstream_nodes:
            if isinstance(upstream_id, str) and upstream_id not in visited:
                # Continue traversal for all upstream ids; non-model ids will
                # naturally stop when not present in manifest["nodes"].
                queue.append(upstream_id)

    return upstream_models


@router.get("/exposures")
async def get_exposures():
    """
    Return exposures data and entity usage mapping.

    First tries to read exposures from manifest.json (canonical source after dbt compilation).
    Falls back to reading exposures.yml from various locations if manifest doesn't have exposures.
    """
    # Load manifest and data model
    manifest = _load_manifest()
    data_model = _load_data_model()

    # Try to read exposures from manifest first (canonical source)
    exposures_dict = manifest.get("exposures", {})
    exposures_list = []
    
    if exposures_dict and isinstance(exposures_dict, dict):
        # Convert manifest exposures dict to list format
        for unique_id, exposure in exposures_dict.items():
            if not isinstance(exposure, dict):
                continue
            exposures_list.append(exposure)
    else:
        # Fallback: try to read from exposures.yml file
        exposures_path = None
        if cfg.DBT_PROJECT_PATH:
            # Check multiple locations:
            # 1. Root of dbt project
            root_path = os.path.join(cfg.DBT_PROJECT_PATH, "exposures.yml")
            if os.path.exists(root_path):
                exposures_path = root_path
            # 2. Standard location: models/exposures.yml
            elif os.path.exists(os.path.join(cfg.DBT_PROJECT_PATH, "models", "exposures.yml")):
                exposures_path = os.path.join(cfg.DBT_PROJECT_PATH, "models", "exposures.yml")
            # 3. Search in models directory
            else:
                models_dir = os.path.join(cfg.DBT_PROJECT_PATH, "models")
                if os.path.exists(models_dir):
                    for file in os.listdir(models_dir):
                        if file == "exposures.yml":
                            exposures_path = os.path.join(models_dir, file)
                            break

        # Load exposures.yml if found
        if exposures_path and os.path.exists(exposures_path):
            try:
                with open(exposures_path, "r") as f:
                    exposures_data = yaml.safe_load(f) or {}
                exposures_list = exposures_data.get("exposures", [])
                if not isinstance(exposures_list, list):
                    exposures_list = []
            except Exception as e:
                print(f"Warning: Could not read exposures.yml: {e}")

    # If no exposures found, return empty response
    if not exposures_list:
        return {"exposures": [], "entityUsage": {}}

    # Build response: extract exposure metadata
    exposures_response = []
    entity_usage: Dict[str, List[str]] = {}  # entity_id -> [exposure_names]
    upstream_cache: Dict[str, set[str]] = {}  # model_unique_id -> upstream model ids

    for exposure in exposures_list:
        if not isinstance(exposure, dict):
            continue

        # Extract exposure metadata
        exposure_name = exposure.get("name", "")
        if not exposure_name:
            continue

        exposure_meta = {
            "name": exposure_name,
            "label": exposure.get("label"),
            "type": exposure.get("type"),
            "description": exposure.get("description"),
        }

        # Extract owner info
        owner = exposure.get("owner")
        if isinstance(owner, dict):
            exposure_meta["owner"] = {"name": owner.get("name")}
        elif owner:
            # Handle case where owner might be a string
            exposure_meta["owner"] = {"name": str(owner)}

        exposures_response.append(exposure_meta)

        # Resolve depends_on references
        # In manifest, depends_on is a dict with 'nodes' list containing unique_ids
        # In YAML, depends_on is a list of ref() strings
        depends_on_nodes = []
        depends_on = exposure.get("depends_on")
        
        if isinstance(depends_on, dict):
            # Manifest format: depends_on.nodes contains unique_ids
            depends_on_nodes = depends_on.get("nodes", [])
        elif isinstance(depends_on, list):
            # YAML format: list of ref() strings, need to resolve
            for ref_string in depends_on:
                if not isinstance(ref_string, str):
                    continue
                # Resolve ref() to model unique_id
                unique_id = _resolve_model_ref(ref_string, manifest)
                if unique_id:
                    depends_on_nodes.append(unique_id)
                else:
                    print(f"Warning: Could not resolve {ref_string} to a model")

        # Process each model that this exposure depends on
        for unique_id in depends_on_nodes:
            if not isinstance(unique_id, str):
                continue

            # Expand to *all upstream models* before mapping to entities.
            # This ensures exposures that depend on mart/int models still mark
            # the underlying entity-bound models as "used".
            if unique_id not in upstream_cache:
                upstream_cache[unique_id] = _collect_upstream_model_ids(
                    manifest, unique_id
                )

            for upstream_model_id in upstream_cache[unique_id]:
                entity_ids = _find_entities_for_model(upstream_model_id, data_model)
                for entity_id in entity_ids:
                    if entity_id not in entity_usage:
                        entity_usage[entity_id] = []
                    if exposure_name not in entity_usage[entity_id]:
                        entity_usage[entity_id].append(exposure_name)

    return {
        "exposures": exposures_response,
        "entityUsage": entity_usage,
    }
