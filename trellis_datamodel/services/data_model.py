"""Single owner of the YAML data model (data_model.yml + canvas_layout.yml).

Reads merge the canvas layout, entity-type inference and source-system lineage
into the model; writes validate the payload and split it back into the model
and layout files. Routes stay thin and only translate HTTP to these calls.
"""

import logging
import os
from typing import Any, Dict, List, Tuple

from trellis_datamodel import config as cfg
from trellis_datamodel.adapters import get_adapter
from trellis_datamodel.exceptions import FileOperationError, ValidationError
from trellis_datamodel.models.entity_keys import (
    FRAMEWORK_TAGS_KEY,
    LEGACY_FRAMEWORK_TAGS_KEY,
    LEGACY_MODEL_REF_KEY,
    MODEL_REF_KEY,
    get_framework_tags,
    get_model_ref,
    set_framework_tags,
    set_model_ref,
)
from trellis_datamodel.observability import timed_phase
from trellis_datamodel.services.lineage import extract_source_systems_for_models
from trellis_datamodel.services.tag_ownership import (
    PUSHED_TAGS_KEY,
    compute_display_tags,
)
from trellis_datamodel.utils.origin import parse_origin
from trellis_datamodel.utils.structured_data import load_yaml_or_json
from trellis_datamodel.utils.yaml_handler import YamlHandler

logger = logging.getLogger(__name__)

VALID_ENTITY_TYPES = {"fact", "dimension", "unclassified", "entity"}


def _normalize_field_origin(field: Dict[str, Any]) -> None:
    origin = parse_origin(field.get("origin"))
    if origin:
        field["origin"] = origin
    elif "origin" in field:
        del field["origin"]


def _normalize_model_origins(model_data: Dict[str, Any]) -> None:
    for entity in model_data.get("entities", []):
        for field in entity.get("drafted_fields") or []:
            _normalize_field_origin(field)


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
        model_data = load_yaml_or_json(cfg.DATA_MODEL_PATH) or {}

        if not model_data.get("entities"):
            model_data["entities"] = []
        if not model_data.get("relationships"):
            model_data["relationships"] = []

        return model_data
    except Exception as e:
        raise FileOperationError(f"Error loading data model: {e}") from e


def save_data_model_raw(model_data: Dict[str, Any]) -> None:
    """
    Save the raw data model to YAML file.

    Args:
        model_data: Dictionary with version, entities, and relationships
    """
    try:
        YamlHandler().save_file(cfg.DATA_MODEL_PATH, model_data)
    except Exception as e:
        raise FileOperationError(f"Error saving data model: {e}") from e


def _empty_layout() -> Dict[str, Any]:
    return {
        "version": 0.1,
        "entities": {},
        "relationships": {},
        "source_colors": {},
    }


def _load_canvas_layout() -> Dict[str, Any]:
    """Load canvas layout file if it exists."""
    with timed_phase("layout_read"):
        if not os.path.exists(cfg.CANVAS_LAYOUT_PATH):
            return _empty_layout()

        try:
            layout = load_yaml_or_json(cfg.CANVAS_LAYOUT_PATH) or {}
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
            logger.warning("Could not load canvas layout: %s", e)
            return _empty_layout()


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


def _infer_type_from_name(name: str, dim_prefixes: List[str], fact_prefixes: List[str]) -> str | None:
    """Infer entity type from a name string using configured dim/fact prefixes."""
    name_lower = name.lower()
    for prefix in dim_prefixes:
        if name_lower.startswith(prefix.lower()):
            return "dimension"
    for prefix in fact_prefixes:
        if name_lower.startswith(prefix.lower()):
            return "fact"
    return None


def _apply_entity_type_inference(model_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply entity type inference to model data when dimensional modeling is enabled.

    Inference is only applied to entities that don't already have entity_type set.
    Manually set entity_type values are preserved.

    Two-pass inference:
    1. Manifest-based: bound entities whose dbt model name matches dim_/fct_ prefixes.
    2. ID-based fallback: unbound entities not in the manifest but whose entity ID
       itself matches the configured dimension/fact prefix patterns.
    """
    entities = model_data.get("entities", [])
    if not any(
        entity.get("entity_type") is None or entity.get("entity_type") == "unclassified"
        for entity in entities
    ):
        return model_data

    try:
        adapter = get_adapter()
        inferred_types = adapter.infer_entity_types()
    except Exception as e:
        logger.warning("Could not infer entity types: %s", e)
        return model_data

    dim_prefixes: List[str] = cfg.DIMENSIONAL_MODELING_CONFIG.dimension_prefix
    fact_prefixes: List[str] = cfg.DIMENSIONAL_MODELING_CONFIG.fact_prefix

    for entity in entities:
        entity_id = entity.get("id")
        if not entity_id:
            continue

        existing_type = entity.get("entity_type")
        should_infer = existing_type is None or existing_type == "unclassified"
        if not should_infer:
            continue

        if entity_id in inferred_types:
            # Manifest-based inference (bound entities)
            entity["entity_type"] = inferred_types[entity_id]
            logger.debug(
                "Inferred entity_type '%s' for entity '%s'",
                inferred_types[entity_id],
                entity_id,
            )
        else:
            # ID-based fallback for unbound entities not in the dbt manifest
            inferred = _infer_type_from_name(entity_id, dim_prefixes, fact_prefixes)
            if inferred:
                entity["entity_type"] = inferred
                logger.debug(
                    "Inferred entity_type '%s' for unbound entity '%s' from ID prefix",
                    inferred,
                    entity_id,
                )

    return model_data


def _bound_model_ids(entities: List[Dict[str, Any]]) -> List[str]:
    """Collect every primary and additional model id, deduplicated in order."""
    bound_model_ids: List[str] = []
    for entity in entities:
        model_ref = get_model_ref(entity)
        if not model_ref:
            continue
        additional_models = entity.get("additional_models", [])
        if not isinstance(additional_models, list):
            additional_models = []
        for model_id in [model_ref, *additional_models]:
            if isinstance(model_id, str) and model_id not in bound_model_ids:
                bound_model_ids.append(model_id)
    return bound_model_ids


def get_data_model() -> Dict[str, Any]:
    """Return the current data model with layout, inference and lineage merged in."""
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
        model_data = load_yaml_or_json(cfg.DATA_MODEL_PATH) or {}
    except Exception as e:
        raise FileOperationError(f"Error reading data model: {e}") from e

    if not model_data.get("entities"):
        model_data["entities"] = []
    if not model_data.get("relationships"):
        model_data["relationships"] = []

    _normalize_model_origins(model_data)

    # Apply entity type inference when dimensional modeling is enabled
    if cfg.DIMENSIONAL_MODELING_CONFIG.enabled:
        with timed_phase("entity_inference"):
            model_data = _apply_entity_type_inference(model_data)

    merged_data = _merge_layout_into_model(model_data, layout_data)

    # Pass through source_colors from canvas_layout.yml
    merged_data["source_colors"] = layout_data.get("source_colors", {})

    # Collect all bound model IDs before doing one source-system lookup.
    entities = merged_data.get("entities", [])
    bound_model_ids = _bound_model_ids(entities)

    source_index: Dict[str, List[str]] = {}
    if bound_model_ids:
        try:
            with timed_phase("source_lineage"):
                source_index = extract_source_systems_for_models(bound_model_ids)
        except Exception:
            # Source enrichment is optional and must not break the response.
            logger.debug("Source-system enrichment failed", exc_info=True)

    # Add source_system field to bound entities from the batch index; unbound
    # entities keep whatever source_system was persisted in YAML (optional).
    for entity in entities:
        model_ref = get_model_ref(entity)

        # `tags` for display/export is computed here, never persisted:
        # the union of framework_tags + ui_tags for bound entities, or the
        # entity's own `tags` field for unbound entities.
        entity["tags"] = compute_display_tags(entity)

        if model_ref:
            additional_models = entity.get("additional_models", [])
            if not isinstance(additional_models, list):
                additional_models = []
            source_systems = set()
            for model_id in [model_ref, *additional_models]:
                source_systems.update(source_index.get(model_id, []))

            if source_systems:
                entity["source_system"] = sorted(list(source_systems))

    return merged_data


def merge_roles(existing: list | None, incoming: list | None) -> list:
    """Union two roles lists, deduplicating by (label, source).

    Tolerates mixed formats: structured roles (``{label, role, source}`` dicts)
    are deduplicated by their (label, source) key. Legacy flat-string roles are
    kept as-is from ``existing`` and skipped in ``incoming`` (they carry no
    (label, source) key to merge on).

    Args:
        existing: Roles list already on the entity (e.g. persisted in data_model.yml).
        incoming: Roles list to merge in.

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


def split_model_and_layout(
    content: Dict[str, Any],
    existing_model_data: Dict[str, Any] | None = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Split incoming data into model-only and layout-only dictionaries."""
    model_data = {
        "version": content.get("version", 0.1),
        "entities": [],
        "relationships": [],
    }

    layout_data = _empty_layout()

    # Preserve existing roles when older clients omit the field.
    existing_entities_by_id: Dict[str, Dict[str, Any]] = {}
    existing_roles_by_id: Dict[str, Any] = {}
    if existing_model_data:
        for existing_entity in existing_model_data.get("entities", []):
            existing_entity_id = existing_entity.get("id")
            if existing_entity_id:
                existing_entities_by_id[existing_entity_id] = existing_entity
            if existing_entity_id and "roles" in existing_entity:
                existing_roles_by_id[existing_entity_id] = existing_entity.get("roles")

    # Preserve a bound entity's reconcile-owned `framework_tags` when auto-save
    # omits it. `framework_tags` mirrors schema.yml and is never intentionally
    # sent by auto-save.ts for bound entities (only ui_tags is) — omission
    # here must not be read as "clear it", unlike unbound entities where
    # `tags` is freely editable and an omission does mean the user cleared it.
    existing_framework_tags_by_id: Dict[str, Any] = {}
    if existing_model_data:
        for existing_entity in existing_model_data.get("entities", []):
            existing_entity_id = existing_entity.get("id")
            if existing_entity_id and (
                FRAMEWORK_TAGS_KEY in existing_entity
                or LEGACY_FRAMEWORK_TAGS_KEY in existing_entity
            ):
                existing_framework_tags_by_id[existing_entity_id] = get_framework_tags(
                    existing_entity
                )

    # `pushed_tags` is backend-owned — written only by a push, never sent by
    # auto-save.ts — so it is carried over from disk and never taken from the
    # payload. It is kept only while the entity stays bound to the model it was
    # pushed to: on any other model it would drive removals of tags Trellis
    # never put there.
    existing_pushed_tags_by_id: Dict[str, Tuple[str | None, Any]] = {}
    if existing_model_data:
        for existing_entity in existing_model_data.get("entities", []):
            existing_entity_id = existing_entity.get("id")
            if existing_entity_id and PUSHED_TAGS_KEY in existing_entity:
                existing_pushed_tags_by_id[existing_entity_id] = (
                    get_model_ref(existing_entity),
                    existing_entity[PUSHED_TAGS_KEY],
                )

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
        if MODEL_REF_KEY in entity or LEGACY_MODEL_REF_KEY in entity:
            set_model_ref(model_entity, get_model_ref(entity))
        elif get_model_ref(existing_entities_by_id.get(entity_id, {})):
            # #141: an omitted model_ref is "no opinion", not an unbind. An
            # auto-save racing a concurrent session posts entities built from
            # an older GET, where JSON.stringify has already dropped the key
            # (undefined) — dropping the on-disk binding here silently
            # unbound every entity and made push a no-op. The frontend always
            # telegraphs an intentional unbind as an explicit `model_ref:
            # null` (EntityNode.unbind), and JSON.stringify keeps null, so
            # the explicit-clear path above is unchanged.
            set_model_ref(
                model_entity,
                get_model_ref(existing_entities_by_id[entity_id]),
            )
        if "additional_models" in entity:
            model_entity["additional_models"] = entity["additional_models"]
        if "drafted_fields" in entity:
            drafted_fields = []
            for field in entity["drafted_fields"]:
                normalized = dict(field)
                _normalize_field_origin(normalized)
                drafted_fields.append(normalized)
            model_entity["drafted_fields"] = drafted_fields
        # `tags` is only a persisted field for unbound entities (their single,
        # freely-editable tag list). Bound entities never persist `tags` —
        # only `framework_tags` (reconcile-owned) and `ui_tags` (user-added).
        if "tags" in entity and not get_model_ref(entity):
            model_entity["tags"] = entity["tags"]
        if FRAMEWORK_TAGS_KEY in entity or LEGACY_FRAMEWORK_TAGS_KEY in entity:
            set_framework_tags(model_entity, get_framework_tags(entity))
        elif get_model_ref(entity) and entity_id in existing_framework_tags_by_id:
            set_framework_tags(model_entity, existing_framework_tags_by_id[entity_id])
        if "ui_tags" in entity:
            model_entity["ui_tags"] = entity["ui_tags"]
        pushed_model_ref, pushed_tags = existing_pushed_tags_by_id.get(
            entity_id, (None, None)
        )
        if pushed_model_ref and pushed_model_ref == get_model_ref(entity):
            model_entity[PUSHED_TAGS_KEY] = pushed_tags
            # auto-save sends ui_tags as undefined once the list is emptied;
            # for an entity with a push record that means "cleared", not "no
            # opinion", so the push can remove what Trellis previously added.
            if "ui_tags" not in entity:
                model_entity["ui_tags"] = []
        if "domain" in entity:
            model_entity["domain"] = entity["domain"]
        if "domains" in entity:
            model_entity["domains"] = entity["domains"]
        if "entity_type" in entity:
            model_entity["entity_type"] = entity["entity_type"]
        elif current_entity := existing_entities_by_id.get(entity_id):
            # #141: auto-save omits entity_type whenever modeling_style is
            # entity_model, so omission is "no opinion" there — dropping a
            # user-set dimension/fact during such a save would erase it on
            # every pass. Explicit edits send the key with a value (or the
            # frontend's 'unclassified'), so they keep winning below.
            if "entity_type" in current_entity:
                model_entity["entity_type"] = current_entity["entity_type"]
        if "annotation_type" in entity:
            model_entity["annotation_type"] = entity["annotation_type"]
        if "roles" in entity:
            incoming_roles = entity["roles"]
            existing_roles = existing_roles_by_id.get(entity_id)
            if existing_roles is not None and incoming_roles is not None:
                # Merge: union incoming roles with existing, deduplicated by (label, source)
                model_entity["roles"] = merge_roles(existing_roles, incoming_roles)
            elif incoming_roles is not None:
                # No existing roles — take incoming as-is
                model_entity["roles"] = incoming_roles
            elif existing_roles is not None:
                model_entity["roles"] = existing_roles
        elif entity_id in existing_roles_by_id:
            # Incoming payload omitted the roles field entirely — preserve existing
            model_entity["roles"] = existing_roles_by_id[entity_id]
        # Only persist source_system for unbound entities (not for bound entities)
        if "source_system" in entity and not get_model_ref(entity):
            model_entity["source_system"] = entity["source_system"]

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


def _validate_entity_type(entity_type: str) -> None:
    """Raise ValidationError unless entity_type is one of the allowed values."""
    if entity_type and entity_type not in VALID_ENTITY_TYPES:
        raise ValidationError(
            f"Invalid entity_type '{entity_type}'. Must be one of: {', '.join(sorted(VALID_ENTITY_TYPES))}"
        )


def _validate_roles(roles) -> None:
    """Raise ValidationError unless roles is None or a list of strings/dicts."""
    if roles is None:
        return

    if not isinstance(roles, list):
        raise ValidationError("roles must be a list of strings or null/undefined")

    for role in roles:
        if not isinstance(role, (str, dict)):
            raise ValidationError("roles must be a list of strings or null/undefined")


def save_data_model(content: Dict[str, Any]) -> None:
    """Validate a save payload and write it split into model and layout files.

    Fields older clients omit are preserved from the model already on disk.

    Raises:
        ValidationError: An entity carries an invalid entity_type or roles value.
        FileOperationError: data_model.yml or canvas_layout.yml cannot be
            read or written.
    """
    for entity in content.get("entities", []):
        entity_type = entity.get("entity_type")
        if entity_type:
            _validate_entity_type(entity_type)
        roles = entity.get("roles")
        if roles is not None:
            _validate_roles(roles)

    existing_model_data = load_data_model_raw()
    model_data, layout_data = split_model_and_layout(content, existing_model_data)

    try:
        logger.info("Saving data model to: %s", cfg.DATA_MODEL_PATH)
        YamlHandler().save_file(cfg.DATA_MODEL_PATH, model_data)

        logger.info("Saving canvas layout to: %s", cfg.CANVAS_LAYOUT_PATH)
        YamlHandler().save_file(cfg.CANVAS_LAYOUT_PATH, layout_data)
    except Exception as e:
        raise FileOperationError(f"Error saving data model: {e}") from e


def get_source_system_suggestions() -> List[str]:
    """
    Return a sorted, consolidated list of known source system names.

    Includes:
    - Mock sources from data_model.yml (unbound entities)
    - Lineage-derived sources from all bound entities
    """
    suggestions: set[str] = set()

    # Load data_model.yml once for both persisted and lineage-derived sources.
    model_data: Dict[str, Any] = {}
    if os.path.exists(cfg.DATA_MODEL_PATH):
        try:
            model_data = load_yaml_or_json(cfg.DATA_MODEL_PATH) or {}
        except Exception:
            logger.debug("Could not read data model for suggestions", exc_info=True)

    # 1. Collect mock sources from unbound entities.
    entities = model_data.get("entities", [])
    for entity in entities:
        if not get_model_ref(entity) and entity.get("source_system"):
            source_systems = entity.get("source_system", [])
            if isinstance(source_systems, list):
                for source in source_systems:
                    if source and isinstance(source, str):
                        suggestions.add(source.strip())

    # 2. Collect lineage-derived sources in one batch.
    bound_model_ids = _bound_model_ids(entities)
    if bound_model_ids:
        try:
            with timed_phase("source_lineage"):
                source_index = extract_source_systems_for_models(bound_model_ids)
            for source_systems in source_index.values():
                suggestions.update(source_systems)
        except Exception:
            logger.debug("Source-system lineage lookup failed", exc_info=True)

    # Parsing dbt sources.yml for source names is a possible future addition.
    return sorted(suggestions)
