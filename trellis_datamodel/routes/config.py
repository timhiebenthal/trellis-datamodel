"""Routes for config status/info endpoints."""

from dataclasses import asdict
import os
from typing import Any, Dict, List

from fastapi import APIRouter

from trellis_datamodel import config as cfg
from trellis_datamodel.models.schemas import ConfigInfoResponse, ConfigStatusResponse

router = APIRouter(prefix="/api", tags=["config"])


def _load_config_payload() -> Dict[str, Any]:
    if not cfg.CONFIG_PATH or not os.path.exists(cfg.CONFIG_PATH):
        return {}
    try:
        return cfg._load_yaml_config(cfg.CONFIG_PATH)
    except Exception:
        return {}


def _resolve_model_paths(
    config_payload: Dict[str, Any], project_path: str, config_path: str
) -> tuple[List[str], List[str]]:
    configured = config_payload.get("dbt_model_paths", [])
    if not isinstance(configured, list):
        configured = []

    base_dir = project_path or os.path.dirname(config_path) if config_path else ""
    resolved: List[str] = []
    for entry in configured:
        if not isinstance(entry, str):
            continue
        if os.path.isabs(entry) or not base_dir:
            resolved.append(entry)
        else:
            resolved.append(os.path.abspath(os.path.join(base_dir, entry)))
    return configured, resolved


def _resolve_label_prefixes(config_payload: Dict[str, Any]) -> List[str]:
    label_prefixes = config_payload.get("label_prefixes", [])
    if isinstance(label_prefixes, list):
        return [p for p in label_prefixes if isinstance(p, str)]
    if isinstance(label_prefixes, str):
        return [label_prefixes]
    return []


@router.get("/config/status", response_model=ConfigStatusResponse)
async def get_config_status():
    """Return configuration status for debugging/health checks."""
    config_present = bool(cfg.CONFIG_PATH and os.path.exists(cfg.CONFIG_PATH))
    return ConfigStatusResponse(
        config_present=config_present,
        config_filename=os.path.basename(cfg.CONFIG_PATH) if cfg.CONFIG_PATH else "",
        framework=cfg.FRAMEWORK,
        dbt_project_path=cfg.DBT_PROJECT_PATH or None,
        manifest_path=cfg.MANIFEST_PATH or None,
        catalog_path=cfg.CATALOG_PATH or None,
        manifest_exists=bool(cfg.MANIFEST_PATH and os.path.exists(cfg.MANIFEST_PATH)),
        catalog_exists=bool(cfg.CATALOG_PATH and os.path.exists(cfg.CATALOG_PATH)),
        data_model_exists=bool(cfg.DATA_MODEL_PATH and os.path.exists(cfg.DATA_MODEL_PATH)),
        error=None,
    )


@router.get("/config/info", response_model=ConfigInfoResponse)
async def get_config_info():
    """Return detailed configuration info for transparency/debugging."""
    config_present = bool(cfg.CONFIG_PATH and os.path.exists(cfg.CONFIG_PATH))
    config_payload = _load_config_payload()
    model_paths_configured, model_paths_resolved = _resolve_model_paths(
        config_payload, cfg.DBT_PROJECT_PATH, cfg.CONFIG_PATH
    )
    label_prefixes = _resolve_label_prefixes(config_payload)
    guidance_payload = asdict(cfg.GUIDANCE_CONFIG)

    return ConfigInfoResponse(
        config_path=cfg.CONFIG_PATH or None,
        framework=cfg.FRAMEWORK,
        dbt_project_path=cfg.DBT_PROJECT_PATH or None,
        manifest_path=cfg.MANIFEST_PATH or None,
        manifest_exists=bool(cfg.MANIFEST_PATH and os.path.exists(cfg.MANIFEST_PATH)),
        catalog_path=cfg.CATALOG_PATH or None,
        catalog_exists=bool(cfg.CATALOG_PATH and os.path.exists(cfg.CATALOG_PATH)),
        data_model_path=cfg.DATA_MODEL_PATH or None,
        data_model_exists=bool(cfg.DATA_MODEL_PATH and os.path.exists(cfg.DATA_MODEL_PATH)),
        canvas_layout_path=cfg.CANVAS_LAYOUT_PATH or None,
        canvas_layout_exists=bool(
            cfg.CANVAS_LAYOUT_PATH and os.path.exists(cfg.CANVAS_LAYOUT_PATH)
        ),
        frontend_build_dir=cfg.FRONTEND_BUILD_DIR or None,
        model_paths_configured=model_paths_configured,
        model_paths_resolved=model_paths_resolved,
        guidance=guidance_payload,
        entity_creation_guidance=guidance_payload,
        lineage_enabled=cfg.LINEAGE_ENABLED,
        lineage_layers=cfg.LINEAGE_LAYERS or [],
        exposures_enabled=cfg.EXPOSURES_ENABLED,
        exposures_default_layout=cfg.EXPOSURES_DEFAULT_LAYOUT,
        bus_matrix_enabled=cfg.Bus_MATRIX_ENABLED,
        modeling_style=cfg.MODELING_STYLE,
        label_prefixes=label_prefixes,
        dimension_prefix=cfg.DIMENSIONAL_MODELING_CONFIG.dimension_prefix,
        fact_prefix=cfg.DIMENSIONAL_MODELING_CONFIG.fact_prefix,
        entity_prefix=cfg.ENTITY_MODELING_CONFIG.entity_prefix,
    )
