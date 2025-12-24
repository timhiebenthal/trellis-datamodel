"""Routes for exposures operations."""

from fastapi import APIRouter, HTTPException
import yaml
import os
import re
import json
import time
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


@router.get("/exposures")
async def get_exposures():
    """
    Return exposures data and entity usage mapping.

    Reads exposures.yml from the dbt project models directory,
    resolves model references, and maps them to entities.
    """
    # #region agent log
    log_data = {"location": "exposures.py:get_exposures", "message": "endpoint called", "data": {"dbt_project_path": cfg.DBT_PROJECT_PATH}, "timestamp": int(time.time() * 1000), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "C"}
    with open("/home/thiebenthal_ubuntu/git_repos/trellis-datamodel/.cursor/debug.log", "a") as log_file:
        log_file.write(json.dumps(log_data) + "\n")
    # #endregion agent log
    # Find exposures.yml file
    exposures_path = None
    if cfg.DBT_PROJECT_PATH:
        # Standard location: models/exposures.yml
        standard_path = os.path.join(cfg.DBT_PROJECT_PATH, "models", "exposures.yml")
        if os.path.exists(standard_path):
            exposures_path = standard_path
        else:
            # Also check for exposures.yml directly in models directory
            models_dir = os.path.join(cfg.DBT_PROJECT_PATH, "models")
            if os.path.exists(models_dir):
                for file in os.listdir(models_dir):
                    if file == "exposures.yml":
                        exposures_path = os.path.join(models_dir, file)
                        break

    # #region agent log
    log_data = {"location": "exposures.py:get_exposures", "message": "exposures_path resolved", "data": {"exposures_path": exposures_path, "exists": exposures_path and os.path.exists(exposures_path) if exposures_path else False}, "timestamp": int(time.time() * 1000), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "C"}
    with open("/home/thiebenthal_ubuntu/git_repos/trellis-datamodel/.cursor/debug.log", "a") as log_file:
        log_file.write(json.dumps(log_data) + "\n")
    # #endregion agent log
    # If no exposures.yml found, return empty response
    if not exposures_path or not os.path.exists(exposures_path):
        return {"exposures": [], "entityUsage": {}}

    # Load exposures.yml
    try:
        with open(exposures_path, "r") as f:
            exposures_data = yaml.safe_load(f) or {}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error reading exposures.yml: {str(e)}"
        )

    exposures_list = exposures_data.get("exposures", [])
    # #region agent log
    log_data = {"location": "exposures.py:get_exposures", "message": "exposures parsed", "data": {"exposures_count": len(exposures_list) if isinstance(exposures_list, list) else 0}, "timestamp": int(time.time() * 1000), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "C"}
    with open("/home/thiebenthal_ubuntu/git_repos/trellis-datamodel/.cursor/debug.log", "a") as log_file:
        log_file.write(json.dumps(log_data) + "\n")
    # #endregion agent log
    if not isinstance(exposures_list, list):
        return {"exposures": [], "entityUsage": {}}

    # Load manifest and data model for resolution
    manifest = _load_manifest()
    data_model = _load_data_model()

    # Build response: extract exposure metadata
    exposures_response = []
    entity_usage: Dict[str, List[str]] = {}  # entity_id -> [exposure_names]

    for exposure in exposures_list:
        if not isinstance(exposure, dict):
            continue

        # Extract exposure metadata
        exposure_meta = {
            "name": exposure.get("name", ""),
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
        depends_on = exposure.get("depends_on", [])
        if not isinstance(depends_on, list):
            continue

        exposure_name = exposure.get("name", "")
        if not exposure_name:
            continue

        for ref_string in depends_on:
            if not isinstance(ref_string, str):
                continue

            # Resolve ref() to model unique_id
            unique_id = _resolve_model_ref(ref_string, manifest)
            if not unique_id:
                print(f"Warning: Could not resolve {ref_string} to a model")
                continue

            # Find entities bound to this model
            entity_ids = _find_entities_for_model(unique_id, data_model)
            for entity_id in entity_ids:
                if entity_id not in entity_usage:
                    entity_usage[entity_id] = []
                if exposure_name not in entity_usage[entity_id]:
                    entity_usage[entity_id].append(exposure_name)

    # #region agent log
    log_data = {"location": "exposures.py:get_exposures", "message": "response prepared", "data": {"exposures_count": len(exposures_response), "entity_usage_keys": len(entity_usage)}, "timestamp": int(time.time() * 1000), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "C"}
    with open("/home/thiebenthal_ubuntu/git_repos/trellis-datamodel/.cursor/debug.log", "a") as log_file:
        log_file.write(json.dumps(log_data) + "\n")
    # #endregion agent log
    return {
        "exposures": exposures_response,
        "entityUsage": entity_usage,
    }

