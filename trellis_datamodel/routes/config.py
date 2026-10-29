"""
Config API routes for managing trellis.yml settings.

Provides GET and PUT endpoints for viewing and editing configuration
with validation, conflict detection, and backup.
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from trellis_datamodel import __version__ as trellis_version
from trellis_datamodel.adapters import get_adapter
from trellis_datamodel.config import reload_config
from trellis_datamodel.models.schemas import (
    ConfigConflictInfo,
    ConfigFileInfo,
    ConfigGetResponse,
    ConfigReloadResponse,
    ConfigSchemaResponse,
    ConfigUpdateRequest,
    ConfigUpdateResponse,
    ConfigValidateResponse,
)
from trellis_datamodel.services.config_service import (
    _get_file_hash,
    _get_file_mtime,
    get_schema_metadata,
    read_config,
    require_config_path,
    save_config,
    validate_config,
)

logger = logging.getLogger(__name__)

config_router = APIRouter(prefix="/api/config", tags=["config"])


@config_router.get("", response_model=ConfigGetResponse)
async def get_config() -> ConfigGetResponse:
    """
    Get current configuration with schema metadata.

    Returns the current trellis.yml values, schema metadata for UI rendering,
    and file information for conflict detection.

    Raises:
        ConfigurationError: No config file, or it cannot be read (400)
    """
    config, file_info = read_config()

    return ConfigGetResponse(
        config=config,
        schema_metadata=get_schema_metadata(),
        file_info=file_info,
        trellis_version=trellis_version,
    )


@config_router.get("/schema", response_model=ConfigSchemaResponse)
async def get_config_schema() -> ConfigSchemaResponse:
    """
    Get schema metadata for config UI.

    Returns field definitions and beta flag list without loading config.
    """
    return get_schema_metadata()


@config_router.put("", response_model=ConfigUpdateResponse)
async def update_config(request: ConfigUpdateRequest) -> ConfigUpdateResponse:
    """
    Update configuration with validation, conflict detection, and atomic write.

    Validates the config, checks for conflicts (mtime/hash), and atomically writes the new config.

    Raises:
        HTTPException: 409 with the current and expected file identity
        ConfigurationError: No config file, or it cannot be read/written (400)
        ValidationError: The config does not validate (422)
    """
    config_path = require_config_path()

    saved_config, conflict_message = save_config(
        config=request.config,
        config_path=config_path,
        expected_mtime=request.expected_mtime,
        expected_hash=request.expected_hash,
    )

    if conflict_message:
        # The frontend reads this structured detail to show the conflict, which
        # the global handlers' {"detail": <message>} shape cannot carry.
        conflict_info = ConfigConflictInfo(
            current_mtime=_get_file_mtime(config_path),
            current_hash=_get_file_hash(config_path),
            expected_mtime=request.expected_mtime,
            expected_hash=request.expected_hash,
        )
        raise HTTPException(
            status_code=409,
            detail={
                "error": "conflict",
                "message": conflict_message,
                "conflict": conflict_info.model_dump(),
            },
        )

    logger.info(f"Successfully updated config: {config_path}")
    return ConfigUpdateResponse(
        config=saved_config,
        file_info=ConfigFileInfo(
            path=config_path,
            mtime=_get_file_mtime(config_path),
            hash=_get_file_hash(config_path),
        ),
    )


@config_router.post("/reload", response_model=ConfigReloadResponse)
async def reload_config_endpoint() -> ConfigReloadResponse:
    """
    Reload configuration from trellis.yml at runtime.

    Reloads the config file and updates all global configuration variables,
    clearing any cached state that depends on config. Should be called after
    config file changes to apply new settings without restarting the server.

    Raises:
        ConfigurationError: Config file not found or invalid (400)
    """
    reload_config()

    # Reset through a fresh adapter so the shared, framework-neutral
    # cache boundary is applied after the new configuration is active.
    get_adapter().reset_inference_cache()

    logger.info("Configuration reloaded successfully via API")
    return ConfigReloadResponse(message="Configuration reloaded successfully")


@config_router.post("/validate", response_model=ConfigValidateResponse)
async def validate_config_endpoint(config: Dict[str, Any]) -> ConfigValidateResponse:
    """
    Validate a config without saving it.

    Useful for client-side validation before applying changes.
    """
    is_valid, error_msg = validate_config(config)
    return ConfigValidateResponse(valid=is_valid, error=error_msg)
