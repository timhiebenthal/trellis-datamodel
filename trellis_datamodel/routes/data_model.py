"""Routes for data model CRUD operations."""

from fastapi import APIRouter, HTTPException
import yaml
import os
from typing import Dict, Any, List, Tuple

from trellis_datamodel import config as cfg
from trellis_datamodel.models.schemas import DataModelUpdate
from trellis_datamodel.adapters import get_adapter

router = APIRouter(prefix="/api", tags=["data-model"])


def _load_canvas_layout() -> Dict[str, Any]:
    """Load canvas layout file if it exists."""
    if not os.path.exists(cfg.CANVAS_LAYOUT_PATH):
        return {"version": 0.1, "entities": {}, "relationships": {}}

    try:
        with open(cfg.CANVAS_LAYOUT_PATH, "r") as f:
            layout = yaml.safe_load(f) or {}
        return {
            "version": layout.get("version", 0.1),
            "entities": layout.get("entities", {}),
            "relationships": layout.get("relationships", {}),
        }
    except Exception as e:
        print(f"Warning: Could not load canvas layout: {e}")
        return {"version": 0.1, "entities": {}, "relationships": {}}


def _merge_layout_into_model(
    model_data: Dict[str, Any], layout_data: Dict[str, Any]
) -> Dict[str, Any]:
    """Merge canvas layout data into model data."""
    entities_layout = layout_data.get("entities", {})
    relationships_layout = layout_data.get("relationships", {})

    # Merge entity visual properties
    entities = model_data.get("entities", [])
    for entity in entities:
        entity_id = entity.get("id")

        # region agent log - Before defaulting entity_type (Hypothesis: _merge_layout is overwriting entity_type)
        import json

        log_data = {
            "location": "data_model.py:45",
            "message": "In _merge_layout_into_model",
            "data": {
                "entity_id": entity_id,
                "entity_type_before_default": entity.get("entity_type"),
                "has_entity_type_key": "entity_type" in entity,
            },
            "timestamp": 1736366400000,
            "sessionId": "debug-session",
            "hypothesisId": "merge-layout-overwrites-entity-type",
        }
        with open(
            "/home/tim_ubuntu/git_repos/trellis-datamodel/.cursor/debug.log", "a"
        ) as log_file:
            log_file.write(json.dumps(log_data) + "\n")
        # endregion

        # Only merge layout properties (position, width, etc.) - do NOT default entity_type here
        # Entity type defaults to "unclassified" are handled during POST saves, not during GET merges
        # This prevents overwriting manually-set entity types during page loads

        if entity_id and entity_id in entities_layout:
            layout = entities_layout[entity_id]
            if "position" in layout:
                entity["position"] = layout["position"]
            if "width" in layout:
                entity["width"] = layout["width"]
            if "panel_height" in layout:
                entity["panel_height"] = layout["panel_height"]
            if "collapsed" in layout:
                entity["collapsed"] = layout["collapsed"]

    # Merge relationship visual properties
    relationships = model_data.get("relationships", [])
    for idx, relationship in enumerate(relationships):
        source = relationship.get("source")
        target = relationship.get("target")
        if source and target:
            # Create key: source-target-index
            rel_key = f"{source}-{target}-{idx}"
            if rel_key in relationships_layout:
                layout = relationships_layout[rel_key]
                if "label_dx" in layout:
                    relationship["label_dx"] = layout["label_dx"]
                if "label_dy" in layout:
                    relationship["label_dy"] = layout["label_dy"]

    return model_data


def _apply_entity_type_inference(model_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply entity type inference to model data when dimensional modeling is enabled.

    Inference is only applied to entities that don't already have entity_type set.
    Manually set entity_type values are preserved.
    """
    try:
        adapter = get_adapter()
        inferred_types = adapter.infer_entity_types()
    except Exception as e:
        print(f"Warning: Could not infer entity types: {e}")
        return model_data

    entities = model_data.get("entities", [])
    for entity in entities:
        entity_id = entity.get("id")
        if not entity_id:
            continue

        # Only apply inference if entity_type is not already set
        if "entity_type" not in entity or entity.get("entity_type") is None:
            if entity_id in inferred_types:
                entity["entity_type"] = inferred_types[entity_id]
                print(
                    f"Inferred entity_type '{inferred_types[entity_id]}' for entity '{entity_id}'"
                )

    return model_data


@router.get("/data-model")
async def get_data_model():
    """Return the current data model with layout merged in."""
    if not os.path.exists(cfg.DATA_MODEL_PATH):
        return {"version": 0.1, "entities": [], "relationships": []}

    try:
        # Load model data
        with open(cfg.DATA_MODEL_PATH, "r") as f:
            model_data = yaml.safe_load(f) or {}

        if not model_data.get("entities"):
            model_data["entities"] = []
        if not model_data.get("relationships"):
            model_data["relationships"] = []

        # Apply entity type inference when dimensional modeling is enabled
        # region agent log - Before inference (Hypothesis: inference is overwriting manual entity_type)
        import json

        entity_types_before_inference = [
            {"id": e.get("id"), "entity_type": e.get("entity_type")}
            for e in model_data.get("entities", [])
        ]
        log_data = {
            "location": "data_model.py:126",
            "message": "Before entity_type inference",
            "data": {"entity_types": entity_types_before_inference},
            "timestamp": 1736366400000,
            "sessionId": "debug-session",
            "hypothesisId": "inference-overwrites-manual-type",
        }
        with open(
            "/home/tim_ubuntu/git_repos/trellis-datamodel/.cursor/debug.log", "a"
        ) as log_file:
            log_file.write(json.dumps(log_data) + "\n")
        # endregion

        if cfg.DIMENSIONAL_MODELING_CONFIG.enabled:
            model_data = _apply_entity_type_inference(model_data)

        # region agent log - After inference and before merge (Hypothesis: merge is overwriting entity_type)
        entity_types_after_inference = [
            {"id": e.get("id"), "entity_type": e.get("entity_type")}
            for e in model_data.get("entities", [])
        ]
        log_data = {
            "location": "data_model.py:130",
            "message": "After entity_type inference",
            "data": {"entity_types": entity_types_after_inference},
            "timestamp": 1736366400000,
            "sessionId": "debug-session",
            "hypothesisId": "inference-overwrites-manual-type",
        }
        with open(
            "/home/tim_ubuntu/git_repos/trellis-datamodel/.cursor/debug.log", "a"
        ) as log_file:
            log_file.write(json.dumps(log_data) + "\n")
        # endregion

        # Load and merge layout data
        layout_data = _load_canvas_layout()
        merged_data = _merge_layout_into_model(model_data, layout_data)

        # region agent log - After merge (Hypothesis: merge is overwriting entity_type)
        entity_types_after_merge = [
            {"id": e.get("id"), "entity_type": e.get("entity_type")}
            for e in merged_data.get("entities", [])
        ]
        log_data = {
            "location": "data_model.py:132",
            "message": "After layout merge",
            "data": {"entity_types": entity_types_after_merge},
            "timestamp": 1736366400000,
            "sessionId": "debug-session",
            "hypothesisId": "inference-overwrites-manual-type",
        }
        with open(
            "/home/tim_ubuntu/git_repos/trellis-datamodel/.cursor/debug.log", "a"
        ) as log_file:
            log_file.write(json.dumps(log_data) + "\n")
        # endregion

        return merged_data
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error reading data model: {str(e)}"
        )


def _split_model_and_layout(
    content: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Split incoming data into model-only and layout-only dictionaries."""
    model_data = {
        "version": content.get("version", 0.1),
        "entities": [],
        "relationships": [],
    }

    layout_data = {"version": 0.1, "entities": {}, "relationships": {}}

    # Split entities
    entities = content.get("entities", [])
    # region agent log - Entity types in POST request (Hypothesis: Frontend sends correct types)
    import json

    log_data = {
        "location": "data_model.py:233",
        "message": "POST request entities before split",
        "data": {
            "entities": [
                {
                    "id": e.get("id"),
                    "entity_type": e.get("entity_type"),
                    "has_entity_type": "entity_type" in e,
                }
                for e in entities
            ]
        },
        "timestamp": 1736366400000,
        "sessionId": "debug-session",
        "hypothesisId": "post-entities-check",
    }
    with open(
        "/home/tim_ubuntu/git_repos/trellis-datamodel/.cursor/debug.log", "a"
    ) as log_file:
        log_file.write(json.dumps(log_data) + "\n")
    # endregion

    for entity in entities:
        entity_id = entity.get("id")
        if not entity_id:
            continue

        # Model-only properties
        model_entity = {
            "id": entity_id,
            "label": entity.get("label", ""),
        }
        if "description" in entity:
            model_entity["description"] = entity["description"]
        if "dbt_model" in entity:
            model_entity["dbt_model"] = entity["dbt_model"]
        if "additional_models" in entity:
            model_entity["additional_models"] = entity["additional_models"]
        if "drafted_fields" in entity:
            model_entity["drafted_fields"] = entity["drafted_fields"]
        if "tags" in entity:
            model_entity["tags"] = entity["tags"]
        if "entity_type" in entity:
            model_entity["entity_type"] = entity["entity_type"]

        model_data["entities"].append(model_entity)

        # Layout-only properties
        layout_entity = {}
        if "position" in entity:
            layout_entity["position"] = entity["position"]
        if "width" in entity:
            layout_entity["width"] = entity["width"]
        if "panel_height" in entity:
            layout_entity["panel_height"] = entity["panel_height"]
        if "collapsed" in entity:
            layout_entity["collapsed"] = entity["collapsed"]

        if layout_entity:
            layout_data["entities"][entity_id] = layout_entity

    # Split relationships
    relationships = content.get("relationships", [])
    for idx, relationship in enumerate(relationships):
        source = relationship.get("source")
        target = relationship.get("target")
        if not source or not target:
            continue

        # Model-only properties
        model_rel = {
            "source": source,
            "target": target,
        }
        if "label" in relationship:
            model_rel["label"] = relationship["label"]
        if "type" in relationship:
            model_rel["type"] = relationship["type"]
        if "source_field" in relationship:
            model_rel["source_field"] = relationship["source_field"]
        if "target_field" in relationship:
            model_rel["target_field"] = relationship["target_field"]

        model_data["relationships"].append(model_rel)

        # Layout-only properties
        layout_rel = {}
        if "label_dx" in relationship:
            layout_rel["label_dx"] = relationship["label_dx"]
        if "label_dy" in relationship:
            layout_rel["label_dy"] = relationship["label_dy"]

        if layout_rel:
            # Use source-target-index as key
            rel_key = f"{source}-{target}-{idx}"
            layout_data["relationships"][rel_key] = layout_rel

    return model_data, layout_data


def _validate_entity_type(entity_type: str) -> None:
    """
    Validate that entity_type is one of the allowed values.

    Raises HTTPException if invalid.
    """
    valid_types = {"fact", "dimension", "unclassified"}
    if entity_type and entity_type not in valid_types:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid entity_type '{entity_type}'. Must be one of: {', '.join(sorted(valid_types))}",
        )


@router.post("/data-model")
async def save_data_model(data: DataModelUpdate):
    """Save the data model, splitting model and layout into separate files."""
    try:
        # region agent log - Check POST request data (Hypothesis: What data is frontend sending)
        import json

        entities_in_request = data.dict().get("entities", [])
        entity_types_in_request = [
            {"id": e.get("id"), "entity_type": e.get("entity_type")}
            for e in entities_in_request
        ]
        log_data = {
            "location": "data_model.py:319",
            "message": "POST request received",
            "data": {"entity_types": entity_types_in_request},
            "timestamp": 1736366400000,
            "sessionId": "debug-session",
            "hypothesisId": "post-request-check",
        }
        with open(
            "/home/tim_ubuntu/git_repos/trellis-datamodel/.cursor/debug.log", "a"
        ) as log_file:
            log_file.write(json.dumps(log_data) + "\n")
        # endregion

        content = data.dict()  # Pydantic v1 (required by dbt-core==1.10)

        # Validate entity_type values in all entities
        entities = content.get("entities", [])
        for entity in entities:
            entity_type = entity.get("entity_type")
            if entity_type:
                _validate_entity_type(entity_type)

        # Split into model and layout
        model_data, layout_data = _split_model_and_layout(content)

        # region agent log - model_data after split (Hypothesis: Check if split is corrupting types)
        import json

        log_data = {
            "location": "data_model.py:342",
            "message": "model_data returned from split",
            "data": {
                "entity_types": [
                    {"id": e.get("id"), "entity_type": e.get("entity_type")}
                    for e in model_data.get("entities", [])
                ]
            },
            "timestamp": 1736366400000,
            "sessionId": "debug-session",
            "hypothesisId": "split-corruption-check",
        }
        with open(
            "/home/tim_ubuntu/git_repos/trellis-datamodel/.cursor/debug.log", "a"
        ) as log_file:
            log_file.write(json.dumps(log_data) + "\n")
        # endregion

        # region agent log - Check entity types before save (Hypothesis: entity_type being lost during save)
        entities_in_model = model_data.get("entities", [])
        entity_types_in_save = [
            {"id": e.get("id"), "entity_type": e.get("entity_type")}
            for e in entities_in_model
        ]
        import json

        log_data = {
            "location": "data_model.py:261",
            "message": "Before saving to file",
            "data": {"entity_types": entity_types_in_save},
            "timestamp": 1736366400000,
            "sessionId": "debug-session",
            "hypothesisId": "save-entity-type-loss",
        }
        with open(
            "/home/tim_ubuntu/git_repos/trellis-datamodel/.cursor/debug.log", "a"
        ) as log_file:
            log_file.write(json.dumps(log_data) + "\n")
        # endregion

        # Save model file
        print(f"Saving data model to: {cfg.DATA_MODEL_PATH}")

        # region agent log - After dumping to YAML (Hypothesis: YAML dump is corrupting entity_type)
        # Dump the YAML and check what it looks like before writing
        yaml_dumped = yaml.dump(model_data, default_flow_style=False, sort_keys=False)
        log_data = {
            "location": "data_model.py:272",
            "message": "YAML dump before write",
            "data": {
                "yaml_preview": (
                    yaml_dumped[:500] if len(yaml_dumped) > 500 else yaml_dumped
                ),
                "yaml_length": len(yaml_dumped),
            },
            "timestamp": 1736366400000,
            "sessionId": "debug-session",
            "hypothesisId": "yaml-dump-corruption",
        }
        with open(
            "/home/tim_ubuntu/git_repos/trellis-datamodel/.cursor/debug.log", "a"
        ) as log_file:
            log_file.write(json.dumps(log_data) + "\n")
        # endregion
        os.makedirs(os.path.dirname(cfg.DATA_MODEL_PATH), exist_ok=True)
        with open(cfg.DATA_MODEL_PATH, "w") as f:
            yaml.dump(model_data, f, default_flow_style=False, sort_keys=False)
            f.flush()
            os.fsync(f.fileno())

        # region agent log - After file write (Hypothesis: Check if file was corrupted during/after write)
        # Open file immediately to verify content
        with open(cfg.DATA_MODEL_PATH, "r") as verify_f:
            verify_content = verify_f.read()
            log_data = {
                "location": "data_model.py:441",
                "message": "File verification after write",
                "data": {
                    "file_path": cfg.DATA_MODEL_PATH,
                    "content_length": len(verify_content),
                    "sample_preview": (
                        verify_content[:500]
                        if len(verify_content) > 500
                        else verify_content
                    ),
                },
                "timestamp": 1736366400000,
                "sessionId": "debug-session",
                "hypothesisId": "verify-write",
            }
            with open(
                "/home/tim_ubuntu/git_repos/trellis-datamodel/.cursor/debug.log", "a"
            ) as log_file:
                log_file.write(json.dumps(log_data) + "\n")
        # endregion

        # Save layout file
        print(f"Saving canvas layout to: {cfg.CANVAS_LAYOUT_PATH}")
        os.makedirs(os.path.dirname(cfg.CANVAS_LAYOUT_PATH), exist_ok=True)
        with open(cfg.CANVAS_LAYOUT_PATH, "w") as f:
            yaml.dump(layout_data, f, default_flow_style=False, sort_keys=False)
            f.flush()
            os.fsync(f.fileno())

        return {"status": "success"}
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Error saving data model: {str(e)}"
        )
