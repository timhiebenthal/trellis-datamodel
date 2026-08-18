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

    status = get_adapter().get_project_status()
    data_model_exists = (
        os.path.exists(cfg.DATA_MODEL_PATH) if cfg.DATA_MODEL_PATH else False
    )

    # A missing config file outranks anything the adapter can report: without it
    # there is nothing configured to be wrong yet.
    error = "Config file not found." if not config_present else status["error"]

    return {
        "config_present": config_present,
        "config_filename": config_filename,
        "framework": status["framework"],
        "project_path": status["project_path"],
        "project_path_exists": status["project_path_exists"],
        "artifacts_present": status["artifacts_present"],
        "artifacts": status["artifacts"],
        "capabilities": status["capabilities"],
        "data_model_exists": data_model_exists,
        "error": error,
        # Legacy dbt-named keys the frontend still reads. Sourced from the
        # adapter's artifact report rather than from config, so they are absent
        # for a framework that has no manifest or catalog.
        **_legacy_artifact_keys(status),
    }


def _legacy_artifact_keys(status: dict) -> dict:
    """Re-emit dbt's artifact paths under their historical response keys."""
    artifacts = status["artifacts"]
    legacy: dict = {}

    if "manifest" in artifacts:
        legacy["manifest_path"] = artifacts["manifest"]["path"]
        legacy["manifest_exists"] = artifacts["manifest"]["exists"]
    if "catalog" in artifacts:
        legacy["catalog_path"] = artifacts["catalog"]["path"]
        legacy["catalog_exists"] = artifacts["catalog"]["exists"]
    if status["framework"] == "dbt-core":
        legacy["dbt_project_path"] = status["project_path"]

    return legacy


@router.get("/config-info")
async def get_config_info():
    """
    Return resolved config paths and their existence for transparency/debugging.
    """
    config_path = _resolve_config_path()

    status = get_adapter().get_project_status()

    return {
        "config_path": config_path,
        "framework": status["framework"],
        "project_path": status["project_path"],
        "project_path_exists": status["project_path_exists"],
        "artifacts_present": status["artifacts_present"],
        "artifacts": status["artifacts"],
        "capabilities": status["capabilities"],
        "data_model_path": cfg.DATA_MODEL_PATH,
        "data_model_exists": bool(
            cfg.DATA_MODEL_PATH and os.path.exists(cfg.DATA_MODEL_PATH)
        ),
        "canvas_layout_path": cfg.CANVAS_LAYOUT_PATH,
        "canvas_layout_exists": bool(
            cfg.CANVAS_LAYOUT_PATH and os.path.exists(cfg.CANVAS_LAYOUT_PATH)
        ),
        "frontend_build_dir": cfg.FRONTEND_BUILD_DIR,
        "start_page": cfg.START_PAGE,
        "canvas_default_filters": {
            "domains": list(cfg.CANVAS_DEFAULT_FILTERS.get("domains", [])),
            "tags": list(cfg.CANVAS_DEFAULT_FILTERS.get("tags", [])),
        },
        "model_paths_configured": status["model_paths_configured"],
        "model_paths_resolved": status["model_paths_resolved"],
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
        # Legacy dbt-named keys the frontend still reads.
        **_legacy_artifact_keys(status),
    }


@router.get("/manifest")
async def get_manifest():
    """Return parsed models from the transformation framework."""
    models = get_models()
    return {"models": models}
