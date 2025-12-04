"""
Adapter factory for transformation framework integrations.

Provides get_adapter() to instantiate the appropriate adapter based on config.
"""

from typing import Union

from trellis_datamodel.config import (
    FRAMEWORK,
    MANIFEST_PATH,
    CATALOG_PATH,
    DBT_PROJECT_PATH,
    DATA_MODEL_PATH,
    DBT_MODEL_PATHS,
)
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
    if FRAMEWORK == "dbt-core":
        return DbtCoreAdapter(
            manifest_path=MANIFEST_PATH,
            catalog_path=CATALOG_PATH,
            project_path=DBT_PROJECT_PATH,
            data_model_path=DATA_MODEL_PATH,
            model_paths=DBT_MODEL_PATHS,
        )

    raise ValueError(
        f"Unknown framework: {FRAMEWORK}. "
        f"Supported frameworks: dbt-core"
    )


__all__ = ["get_adapter", "TransformationAdapter", "DbtCoreAdapter"]

