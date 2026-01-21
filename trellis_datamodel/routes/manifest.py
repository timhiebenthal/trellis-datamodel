"""Routes for manifest and catalog operations."""

from fastapi import APIRouter
import os

from trellis_datamodel import config as cfg
from trellis_datamodel.config import find_config_file
from trellis_datamodel.adapters import get_adapter
from trellis_datamodel.services.manifest import get_models

router = APIRouter(prefix="/api", tags=["manifest"])


def _resolve_config_path() -> str | None:
    """Resolve config file path, preferring CONFIG_PATH from startup, falling back to search."""
    if cfg.CONFIG_PATH and os.path.exists(cfg.CONFIG_PATH):
        return cfg.CONFIG_PATH
    return find_config_file()


def _resolve_label_prefixes() -> list[str]:
    """Return the prefix list that should be used for label formatting."""
    modeling_style = cfg.MODELING_STYLE

    if modeling_style == "entity_model" and cfg.ENTITY_MODELING_CONFIG.enabled:
        return list(cfg.ENTITY_MODELING_CONFIG.entity_prefix)

    if modeling_style == "dimensional_model" and cfg.DIMENSIONAL_MODELING_CONFIG.enabled:
        return [
            *cfg.DIMENSIONAL_MODELING_CONFIG.dimension_prefix,
            *cfg.DIMENSIONAL_MODELING_CONFIG.fact_prefix,
        ]

    return []


@router.get("/config-status")
async def get_config_status():
    """Return configuration status for the frontend."""
    found_config = _resolve_config_path()
    config_present = found_config is not None

    # Determine expected config filename for display
    if config_present:
        config_filename = os.path.basename(found_config)
    else:
        # Default to trellis.yml (primary config file name)
        config_filename = "trellis.yml"

    manifest_exists = os.path.exists(cfg.MANIFEST_PATH) if cfg.MANIFEST_PATH else False
    catalog_exists = os.path.exists(cfg.CATALOG_PATH) if cfg.CATALOG_PATH else False
    data_model_exists = (
        os.path.exists(cfg.DATA_MODEL_PATH) if cfg.DATA_MODEL_PATH else False
    )

    error = None
    if not config_present:
        error = "Config file not found."
    elif not cfg.DBT_PROJECT_PATH:
        error = "dbt_project_path not set in config."
    elif not manifest_exists:
        error = f"Manifest not found at {cfg.MANIFEST_PATH}"

    return {
        "config_present": config_present,
        "config_filename": config_filename,
        "framework": cfg.FRAMEWORK,
        "dbt_project_path": cfg.DBT_PROJECT_PATH,
        "manifest_path": cfg.MANIFEST_PATH,
        "catalog_path": cfg.CATALOG_PATH,
        "manifest_exists": manifest_exists,
        "catalog_exists": catalog_exists,
        "data_model_exists": data_model_exists,
        "error": error,
    }


@router.get("/config-info")
async def get_config_info():
    """
    Return resolved config paths and their existence for transparency/debugging.
    """
    config_path = _resolve_config_path()

    adapter = get_adapter()
    try:
        model_dirs = adapter.get_model_dirs()  # type: ignore[attr-defined]
    except Exception:
        model_dirs = []

    return {
        "config_path": config_path,
        "framework": cfg.FRAMEWORK,
        "dbt_project_path": cfg.DBT_PROJECT_PATH,
        "manifest_path": cfg.MANIFEST_PATH,
        "manifest_exists": bool(
            cfg.MANIFEST_PATH and os.path.exists(cfg.MANIFEST_PATH)
        ),
        "catalog_path": cfg.CATALOG_PATH,
        "catalog_exists": bool(cfg.CATALOG_PATH and os.path.exists(cfg.CATALOG_PATH)),
        "data_model_path": cfg.DATA_MODEL_PATH,
        "data_model_exists": bool(
            cfg.DATA_MODEL_PATH and os.path.exists(cfg.DATA_MODEL_PATH)
        ),
        "canvas_layout_path": cfg.CANVAS_LAYOUT_PATH,
        "canvas_layout_exists": bool(
            cfg.CANVAS_LAYOUT_PATH and os.path.exists(cfg.CANVAS_LAYOUT_PATH)
        ),
        "frontend_build_dir": cfg.FRONTEND_BUILD_DIR,
        "model_paths_configured": cfg.DBT_MODEL_PATHS,
        "model_paths_resolved": model_dirs,
        "guidance": {
            "entity_wizard_enabled": cfg.GUIDANCE_CONFIG.entity_wizard_enabled,
            "push_warning_enabled": cfg.GUIDANCE_CONFIG.push_warning_enabled,
            "min_description_length": cfg.GUIDANCE_CONFIG.min_description_length,
            "disabled_guidance": cfg.GUIDANCE_CONFIG.disabled_guidance,
        },
        "entity_creation_guidance": {
            "entity_wizard_enabled": cfg.GUIDANCE_CONFIG.entity_wizard_enabled,
            "push_warning_enabled": cfg.GUIDANCE_CONFIG.push_warning_enabled,
            "min_description_length": cfg.GUIDANCE_CONFIG.min_description_length,
            "disabled_guidance": cfg.GUIDANCE_CONFIG.disabled_guidance,
        },
        "lineage_enabled": cfg.LINEAGE_ENABLED,
        "lineage_layers": cfg.LINEAGE_LAYERS,
        "exposures_enabled": cfg.EXPOSURES_ENABLED,
        "exposures_default_layout": cfg.EXPOSURES_DEFAULT_LAYOUT,
        "bus_matrix_enabled": cfg.Bus_MATRIX_ENABLED,
        "business_events_enabled": cfg.BUSINESS_EVENTS_ENABLED,
        "modeling_style": cfg.MODELING_STYLE,
        "entity_prefix": (
            cfg.ENTITY_MODELING_CONFIG.entity_prefix
            if cfg.ENTITY_MODELING_CONFIG.enabled
            else []
        ),
        "label_prefixes": _resolve_label_prefixes(),
        "dimension_prefix": (
            cfg.DIMENSIONAL_MODELING_CONFIG.dimension_prefix
            if cfg.DIMENSIONAL_MODELING_CONFIG.enabled
            else []
        ),
        "fact_prefix": (
            cfg.DIMENSIONAL_MODELING_CONFIG.fact_prefix
            if cfg.DIMENSIONAL_MODELING_CONFIG.enabled
            else []
        ),
    }


@router.get("/manifest")
async def get_manifest():
    """Return parsed models from the transformation framework."""
    models = get_models()
    return {"models": models}
