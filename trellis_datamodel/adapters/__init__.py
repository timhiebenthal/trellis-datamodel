"""
Adapter factory for transformation framework integrations.

Provides get_adapter() to instantiate the appropriate adapter based on config.
"""

from typing import Callable

from trellis_datamodel import config as cfg
from trellis_datamodel.models.schemas import FrameworkEnum
from .base import TransformationAdapter
from .bruin import BruinAdapter
from .dbt_core import DbtCoreAdapter


def _build_dbt_core() -> TransformationAdapter:
    return DbtCoreAdapter(
        manifest_path=cfg.MANIFEST_PATH,
        catalog_path=cfg.CATALOG_PATH,
        project_path=cfg.DBT_PROJECT_PATH,
        data_model_path=cfg.DATA_MODEL_PATH,
        model_paths=cfg.DBT_MODEL_PATHS,
    )


def _build_bruin() -> TransformationAdapter:
    return BruinAdapter(
        pipeline_path=cfg.BRUIN_PIPELINE_PATH,
        data_model_path=cfg.DATA_MODEL_PATH,
        asset_paths=cfg.BRUIN_ASSET_PATHS,
        default_asset_type=cfg.BRUIN_DEFAULT_ASSET_TYPE,
    )


# A new framework is one adapter plus one entry here and in FrameworkEnum.
_ADAPTER_BUILDERS: dict[str, Callable[[], TransformationAdapter]] = {
    FrameworkEnum.DBT_CORE.value: _build_dbt_core,
    FrameworkEnum.BRUIN.value: _build_bruin,
}


def get_adapter() -> TransformationAdapter:
    """
    Get the appropriate adapter based on the configured framework.

    Returns:
        An adapter instance implementing TransformationAdapter.

    Raises:
        ValueError: If the configured framework is not supported.
    """
    # Always read from the live config module (cfg) to respect load_config()
    builder = _ADAPTER_BUILDERS.get(cfg.FRAMEWORK)
    if builder is None:
        raise ValueError(
            f"Unknown framework: {cfg.FRAMEWORK}. "
            f"Supported frameworks: {', '.join(_ADAPTER_BUILDERS)}"
        )
    return builder()


__all__ = [
    "get_adapter",
    "TransformationAdapter",
    "BruinAdapter",
    "DbtCoreAdapter",
]
