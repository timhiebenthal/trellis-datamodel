"""
Config API routes for managing trellis.yml settings.

Provides GET and PUT endpoints for viewing and editing configuration
with validation, conflict detection, and backup.
"""

import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Query

from trellis_datamodel.config import find_config_file, reload_config
from trellis_datamodel.exceptions import ConfigurationError, ValidationError
from trellis_datamodel.models.schemas import (
    ConfigGetResponse,
    ConfigUpdateRequest,
    ConfigConflictInfo,
)
from trellis_datamodel.services.config_service import (
    get_schema_metadata,
    load_config,
    save_config,
    validate_config,
)

logger = logging.getLogger(__name__)

config_router = APIRouter(prefix="/api/config", tags=["config"])


@config_router.get("", response_model=ConfigGetResponse)
async def get_config(
    config_path: Optional[str] = Query(None, description="Override config file path")
) -> ConfigGetResponse:
    """
    Get current configuration with schema metadata.

    Returns the current trellis.yml values, schema metadata for UI rendering,
    and file information for conflict detection.
    """
    try:
        # Load config and file info
        config, file_info = load_config(config_path)

        # Get schema metadata
        schema = get_schema_metadata()

        # Add beta flag metadata to response
        response = ConfigGetResponse(
            config=config, schema_metadata=schema, file_info=file_info, error=None
        )

        return response

    except ConfigurationError as e:
        # Config file not found or unreadable - return error but don't crash
        schema = get_schema_metadata()
        return ConfigGetResponse(
            config={},
            schema_metadata=schema,
            file_info=None,
            error=str(e),
        )
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load configuration: {e}",
        )


@config_router.get("/schema")
async def get_config_schema():
    """
    Get schema metadata for config UI.

    Returns field definitions and beta flag list without loading config.
    """
    try:
        schema = get_schema_metadata()
        return schema
    except Exception as e:
        logger.error(f"Error loading schema: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load schema: {e}",
        )


@config_router.put("")
async def update_config(request: ConfigUpdateRequest) -> Dict[str, Any]:
    """
    Update configuration with validation, conflict detection, and backup.

    Validates the config, checks for conflicts (mtime/hash), creates a backup,
    and atomically writes the new config.

    If a conflict is detected, returns 409 with conflict details.
    If validation fails, returns 422 with validation errors.
    """
    try:
        # Get config path (use override if not provided)
        config_path = find_config_file()

        if not config_path:
            raise ConfigurationError(
                "No config file found. Please create trellis.yml in the current directory."
            )

        # Save config with conflict detection
        saved_config, conflict_message = save_config(
            config=request.config,
            config_path=config_path,
            expected_mtime=request.expected_mtime,
            expected_hash=request.expected_hash,
        )

        # If there's a conflict, return 409
        if conflict_message:
            # Get current file info for conflict response
            from trellis_datamodel.services.config_service import (
                _get_file_mtime,
                _get_file_hash,
            )

            current_mtime = _get_file_mtime(config_path)
            current_hash = _get_file_hash(config_path)

            conflict_info = ConfigConflictInfo(
                current_mtime=current_mtime,
                current_hash=current_hash,
                expected_mtime=request.expected_mtime,
                expected_hash=request.expected_hash,
            )
            # Use dict() for Pydantic v1/v2 compatibility
            conflict_dict = conflict_info.dict() if hasattr(conflict_info, 'dict') else conflict_info.model_dump()
            
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "conflict",
                    "message": conflict_message,
                    "conflict": conflict_dict,
                },
            )

        # Success - return updated config and new file info
        from trellis_datamodel.services.config_service import (
            _get_file_mtime,
            _get_file_hash,
        )

        response = {
            "config": saved_config,
            "file_info": {
                "path": config_path,
                "mtime": _get_file_mtime(config_path),
                "hash": _get_file_hash(config_path),
            },
        }

        logger.info(f"Successfully updated config: {config_path}")
        return response

    except ConfigurationError as e:
        logger.error(f"Config error: {e}")
        raise HTTPException(
            status_code=400,
            detail={"error": "configuration_error", "message": str(e)},
        )
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=422,
            detail={"error": "validation_error", "message": str(e)},
        )
    except HTTPException:
        # Re-raise HTTPException (like 409 conflict)
        raise
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": str(e)},
        )


@config_router.post("/reload")
async def reload_config_endpoint() -> Dict[str, Any]:
    """
    Reload configuration from trellis.yml at runtime.

    Reloads the config file and updates all global configuration variables,
    clearing any cached state that depends on config. Should be called after
    config file changes to apply new settings without restarting the server.

    Returns:
        Success response with status message.

    Raises:
        HTTPException: If config cannot be reloaded (file not found, invalid, etc.)
    """
    try:
        # Reload config (updates all global variables)
        reload_config()

        # Clear adapter caches that depend on config
        from trellis_datamodel.adapters.dbt_core import DbtCoreAdapter
        DbtCoreAdapter.reset_inference_cache()

        logger.info("Configuration reloaded successfully via API")
        return {
            "status": "success",
            "message": "Configuration reloaded successfully",
        }
    except ConfigurationError as e:
        logger.error(f"Config error during reload: {e}")
        raise HTTPException(
            status_code=400,
            detail={"error": "configuration_error", "message": str(e)},
        )
    except Exception as e:
        logger.error(f"Error reloading config: {e}")
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": str(e)},
        )


@config_router.post("/validate")
async def validate_config_endpoint(
    config: Dict[str, Any],
    config_path: Optional[str] = Query(None, description="Override config file path"),
) -> Dict[str, Any]:
    """
    Validate a config without saving it.

    Useful for client-side validation before applying changes.
    """
    try:
        is_valid, error_msg = validate_config(config)

        return {
            "valid": is_valid,
            "error": error_msg,
        }
    except Exception as e:
        logger.error(f"Error validating config: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to validate configuration: {e}",
        )
