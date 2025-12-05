"""
Adapter factory for transformation framework integrations.

Provides get_adapter() to instantiate the appropriate adapter based on config.
"""

from typing import Union

from trellis_datamodel import config as cfg
from .base import TransformationAdapter
from .dbt_core import DbtCoreAdapter


def get_adapter() -> Union[DbtCoreAdapter, TransformationAdapter]:
    """
    Get the appropriate adapter based on the configured framework.

    Returns:
        An adapter instance implementing TransformationAdapter.

    Raises:
        ValueError: If the configured framework is not supported.
    """
    # Always read from the live config module (cfg) to respect load_config()
    if cfg.FRAMEWORK == "dbt-core":
        return DbtCoreAdapter(
            manifest_path=cfg.MANIFEST_PATH,
            catalog_path=cfg.CATALOG_PATH,
            project_path=cfg.DBT_PROJECT_PATH,
            data_model_path=cfg.DATA_MODEL_PATH,
            model_paths=cfg.DBT_MODEL_PATHS,
        )

    raise ValueError(
        f"Unknown framework: {cfg.FRAMEWORK}. "
        f"Supported frameworks: dbt-core"
    )


__all__ = ["get_adapter", "TransformationAdapter", "DbtCoreAdapter"]

