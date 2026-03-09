"""Routes for data model CRUD operations."""
from fastapi import APIRouter, HTTPException
import yaml
import os
from typing import Dict, Any, List, Tuple

from trellis_datamodel import config as cfg
from trellis_datamodel.exceptions import ValidationError
from trellis_datamodel.models.schemas import DataModelUpdate
from trellis_datamodel.services.lineage import extract_source_systems_for_model
from trellis_datamodel.adapters import get_adapter
from trellis_datamodel.utils.yaml_handler import YamlHandler

router = APIRouter(prefix="/api", tags=["data-model"])


def load_data_model_raw() -> Dict[str, Any]:
    """
    Load the raw data model from YAML file without layout merging.
    
    Returns:
        Dictionary with version, entities, and relationships
    """
    if not os.path.exists(cfg.DATA_MODEL_PATH):
        return {
            "version": 0.1,
            "entities": [],
            "relationships": [],
        }
    
    try:
        with open(cfg.DATA_MODEL_PATH, "r") as f:
            model_data = yaml.safe_load(f) or {}
        
        if not model_data.get("entities"):
            model_data["entities"] = []
        if not model_data.get("relationships"):
            model_data["relationships"] = []
        
        return model_data
    except Exception as e:
        raise RuntimeError(f"Error loading data model: {e}") from e


def save_data_model_raw(model_data: Dict[str, Any]) -> None:
    """
    Save the raw data model to YAML file.
    
    Args:
        model_data: Dictionary with version, entities, and relationships
    """
    try:
        YamlHandler().save_file(cfg.DATA_MODEL_PATH, model_data)
    except Exception as e:
        raise RuntimeError(f"Error saving data model: {e}") from e


def _load_canvas_layout() -> Dict[str, Any]:
    """Load canvas layout file if it exists."""
    if not os.path.exists(cfg.CANVAS_LAYOUT_PATH):
        return {
            "version": 0.1,
            "entities": {},
            "relationships": {},
            "source_colors": {},
        }

    try:
        with open(cfg.CANVAS_LAYOUT_PATH, "r") as f:
            layout = yaml.safe_load(f) or {}
        source_colors = layout.get("source_colors")
        # Ensure source_colors is always a dict, not None
        if source_colors is None:
            source_colors = {}
        return {
            "version": layout.get("version", 0.1),
            "entities": layout.get("entities", {}),
            "relationships": layout.get("relationships", {}),
            "source_colors": source_colors,
        }
    except Exception as e:
        print(f"Warning: Could not load canvas layout: {e}")
        return {
            "version": 0.1,
            "entities": {},
            "relationships": {},
            "source_colors": {},
        }


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

        # Apply inference if entity_type is missing or still unclassified
        existing_type = entity.get("entity_type")
        should_infer = existing_type is None or existing_type == "unclassified"
        if should_infer and entity_id in inferred_types:
            entity["entity_type"] = inferred_types[entity_id]
            print(
                f"Inferred entity_type '{inferred_types[entity_id]}' for entity '{entity_id}'"
            )
        else:
            pass

    return model_data


@router.get("/data-model")
async def get_data_model():
    """Return current data model with layout merged in."""
    # Load layout data (including source_colors) even if data_model.yml doesn't exist
    layout_data = _load_canvas_layout()

    if not os.path.exists(cfg.DATA_MODEL_PATH):
        # No data model file, but still return source_colors from canvas_layout.yml
        return {
            "version": 0.1,
            "entities": [],
            "relationships": [],
            "source_colors": layout_data.get("source_colors", {}),
        }

    try:
        # Load model data
        with open(cfg.DATA_MODEL_PATH, "r") as f:
            model_data = yaml.safe_load(f) or {}

        if not model_data.get("entities"):
            model_data["entities"] = []
        if not model_data.get("relationships"):
            model_data["relationships"] = []

        # Apply entity type inference when dimensional modeling is enabled
        if cfg.DIMENSIONAL_MODELING_CONFIG.enabled:
            model_data = _apply_entity_type_inference(model_data)

        # Merge layout data
        merged_data = _merge_layout_into_model(model_data, layout_data)

        # Pass through source_colors from canvas_layout.yml
        merged_data["source_colors"] = layout_data.get("source_colors", {})

        # Add source_system field to entities
        # For bound entities: extract from lineage
        # For unbound entities: read from persisted YAML
        entities = merged_data.get("entities", [])
        for entity in entities:
            dbt_model = entity.get("dbt_model")
            additional_models = entity.get("additional_models", [])

            if dbt_model:
                # Bound entity: extract source systems from lineage
                # Extract for primary model
                source_systems = set()
                try:
                    if cfg.MANIFEST_PATH and os.path.exists(cfg.MANIFEST_PATH):
                        primary_sources = extract_source_systems_for_model(
                            cfg.MANIFEST_PATH,
                            (
                                cfg.CATALOG_PATH
                                if cfg.CATALOG_PATH and os.path.exists(cfg.CATALOG_PATH)
                                else None
                            ),
                            dbt_model,
                        )
                        source_systems.update(primary_sources)
                except Exception:
                    # Gracefully handle errors - log but don't fail
                    pass

                # Extract for additional models
                for model_id in additional_models:
                    try:
                        if cfg.MANIFEST_PATH and os.path.exists(cfg.MANIFEST_PATH):
                            additional_sources = extract_source_systems_for_model(
                                cfg.MANIFEST_PATH,
                                (
                                    cfg.CATALOG_PATH
                                    if cfg.CATALOG_PATH
                                    and os.path.exists(cfg.CATALOG_PATH)
                                    else None
                                ),
                                model_id,
                            )
                            source_systems.update(additional_sources)
                    except Exception:
                        # Gracefully handle errors
                        pass

                # Set source_system if any sources found
                if source_systems:
                    entity["source_system"] = sorted(list(source_systems))
            else:
                # Unbound entity: read from persisted YAML
                if "source_system" in entity:
                    # Already loaded from YAML, keep as-is
                    pass
                # If not present, entity won't have source_system field (optional)

        return merged_data
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error reading data model: {str(e)}"
        )


def _split_model_and_layout(
    content: Dict[str, Any],
    existing_model_data: Dict[str, Any] | None = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Split incoming data into model-only and layout-only dictionaries."""
    model_data = {
        "version": content.get("version", 0.1),
        "entities": [],
        "relationships": [],
    }

    layout_data = {
        "version": 0.1,
        "entities": {},
        "relationships": {},
        "source_colors": {},
    }

    # Preserve existing roles when older clients omit the field.
    existing_roles_by_id: Dict[str, Any] = {}
    if existing_model_data:
        for existing_entity in existing_model_data.get("entities", []):
            existing_entity_id = existing_entity.get("id")
            if existing_entity_id and "roles" in existing_entity:
                existing_roles_by_id[existing_entity_id] = existing_entity.get("roles")

    # Split entities
    entities = content.get("entities", [])
    seen_entity_ids: set = set()

    for entity in entities:
        entity_id = entity.get("id")
        if not entity_id:
            continue
        if entity_id in seen_entity_ids:
            continue
        seen_entity_ids.add(entity_id)

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
        if "domain" in entity:
            model_entity["domain"] = entity["domain"]
        if "domains" in entity:
            model_entity["domains"] = entity["domains"]
        if "entity_type" in entity:
            model_entity["entity_type"] = entity["entity_type"]
        if "annotation_type" in entity:
            model_entity["annotation_type"] = entity["annotation_type"]
        if "roles" in entity:
            incoming_roles = entity["roles"]
            existing_roles = existing_roles_by_id.get(entity_id)
            if existing_roles is not None and incoming_roles is not None:
                # Merge: union incoming roles with existing, deduplicated by (label, source)
                model_entity["roles"] = _merge_roles(existing_roles, incoming_roles)
            elif incoming_roles is not None:
                # No existing roles — take incoming as-is (filter to dicts only for new format)
                model_entity["roles"] = incoming_roles
            # If incoming_roles is None and existing_roles exist: fall through to elif below
            elif existing_roles is not None:
                model_entity["roles"] = existing_roles
        elif entity_id in existing_roles_by_id:
            # Incoming payload omitted the roles field entirely — preserve existing
            model_entity["roles"] = existing_roles_by_id[entity_id]
        # Only persist source_system for unbound entities (not for bound entities)
        if "source_system" in entity and not entity.get("dbt_model"):
            model_entity["source_system"] = entity["source_system"]
            # Log instrumentation
            print(
                f"DEBUG: Entity {entity_id} is unbound, persisting source_system: {entity.get('source_system')}"
            )

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

    # Preserve source_colors if present in the request
    if "source_colors" in content and content["source_colors"] is not None:
        layout_data["source_colors"] = content["source_colors"]

    return model_data, layout_data


@router.get("/source-systems/suggestions")
async def get_source_system_suggestions():
    """
    Return a consolidated list of known source system names for suggestions.

    Includes:
    - Mock sources from data_model.yml (unbound entities)
    - Lineage-derived sources from all bound entities
    - dbt sources.yml source-names (if available)
    """
    suggestions: set[str] = set()

    # 1. Collect mock sources from data_model.yml
    if os.path.exists(cfg.DATA_MODEL_PATH):
        try:
            with open(cfg.DATA_MODEL_PATH, "r") as f:
                model_data = yaml.safe_load(f) or {}

            entities = model_data.get("entities", [])
            for entity in entities:
                # Only collect from unbound entities (mock sources)
                if not entity.get("dbt_model") and entity.get("source_system"):
                    source_systems = entity.get("source_system", [])
                    if isinstance(source_systems, list):
                        for source in source_systems:
                            if source and isinstance(source, str):
                                suggestions.add(source.strip())
        except Exception:
            # Gracefully handle errors
            pass

    # 2. Collect lineage-derived sources from all bound entities
    if cfg.MANIFEST_PATH and os.path.exists(cfg.MANIFEST_PATH):
        try:
            with open(cfg.DATA_MODEL_PATH, "r") as f:
                model_data = yaml.safe_load(f) or {}

            entities = model_data.get("entities", [])
            for entity in entities:
                dbt_model = entity.get("dbt_model")
                additional_models = entity.get("additional_models", [])

                if dbt_model:
                    # Extract from primary model
                    try:
                        sources = extract_source_systems_for_model(
                            cfg.MANIFEST_PATH,
                            (
                                cfg.CATALOG_PATH
                                if cfg.CATALOG_PATH and os.path.exists(cfg.CATALOG_PATH)
                                else None
                            ),
                            dbt_model,
                        )
                        suggestions.update(sources)
                    except Exception:
                        pass

                    # Extract from additional models
                    for model_id in additional_models:
                        try:
                            sources = extract_source_systems_for_model(
                                cfg.MANIFEST_PATH,
                                (
                                    cfg.CATALOG_PATH
                                    if cfg.CATALOG_PATH
                                    and os.path.exists(cfg.CATALOG_PATH)
                                    else None
                                ),
                                model_id,
                            )
                            suggestions.update(sources)
                        except Exception:
                            pass
        except Exception:
            # Gracefully handle errors
            pass

    # 3. Collect from dbt sources.yml (if available)
    # Note: This would require parsing sources.yml files, which is out of scope for now
    # Future enhancement: parse sources.yml to extract source-name values

    # Return sorted list
    return {"suggestions": sorted(list(suggestions))}


def _validate_entity_type(entity_type: str) -> None:
    """
    Validate that entity_type is one of the allowed values.

    Raises ValidationError if invalid.
    """
    from trellis_datamodel.exceptions import ValidationError

    valid_types = {"fact", "dimension", "unclassified"}
    if entity_type and entity_type not in valid_types:
        raise ValidationError(
            f"Invalid entity_type '{entity_type}'. Must be one of: {', '.join(sorted(valid_types))}"
        )


def _merge_roles(existing: list, incoming: list) -> list:
    """Union two roles lists, deduplicating by (label, source).

    Handles mixed formats: entries that are dicts (new format) are deduplicated
    by (label, source) key. Entries that are plain strings (old format) are
    skipped during merge to avoid TypeError — they are preserved as-is from the
    existing list only.

    Args:
        existing: Roles list currently persisted in data_model.yml.
        incoming: Roles list arriving in the save payload.

    Returns:
        Merged list without duplicates.
    """
    if not incoming:
        return list(existing) if existing else []
    if not existing:
        return [r for r in incoming if isinstance(r, dict)]

    seen = {
        (r.get("label"), r.get("source"))
        for r in existing
        if isinstance(r, dict)
    }
    result = list(existing)
    for r in incoming:
        if not isinstance(r, dict):
            continue  # skip flat strings (old format)
        key = (r.get("label"), r.get("source"))
        if key not in seen:
            result.append(r)
            seen.add(key)
    return result


def _validate_roles(roles) -> None:
    """
    Validate that roles field is a list of strings, dicts, or None.

    Raises ValidationError if invalid.
    """
    from trellis_datamodel.exceptions import ValidationError

    if roles is None:
        return

    if not isinstance(roles, list):
        raise ValidationError("roles must be a list of strings or null/undefined")

    for role in roles:
        if not isinstance(role, (str, dict)):
            raise ValidationError("roles must be a list of strings or null/undefined")


@router.post("/data-model")
async def save_data_model(data: DataModelUpdate):
    """Save data model, splitting model and layout into separate files."""
    try:
        # Prefer model_dump() to avoid Pydantic v2 dict() deprecation warnings.
        content = data.model_dump() if hasattr(data, "model_dump") else data.dict()

        # Validate entity_type and roles values in all entities
        entities = content.get("entities", [])
        for entity in entities:
            entity_type = entity.get("entity_type")
            if entity_type:
                _validate_entity_type(entity_type)

            roles = entity.get("roles")
            if roles is not None:
                _validate_roles(roles)

        # Split into model and layout. Preserve selected fields from existing model
        # when omitted by older frontend payloads.
        existing_model_data = load_data_model_raw()
        model_data, layout_data = _split_model_and_layout(content, existing_model_data)

        # Save model file
        print(f"Saving data model to: {cfg.DATA_MODEL_PATH}")

        YamlHandler().save_file(cfg.DATA_MODEL_PATH, model_data)

        # Save layout file
        print(f"Saving canvas layout to: {cfg.CANVAS_LAYOUT_PATH}")
        YamlHandler().save_file(cfg.CANVAS_LAYOUT_PATH, layout_data)

        return {"status": "success"}
    except ValidationError:
        # Let ValidationError propagate to exception handler
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Error saving data model: {str(e)}"
        )
