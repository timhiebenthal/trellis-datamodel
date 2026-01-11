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
    # region agent log
    import json

    log_path = "/home/tim_ubuntu/git_repos/trellis-datamodel/.cursor/debug.log"
    log_entry = json.dumps(
        {
            "id": "log_get_adapter_entry_D",
            "timestamp": 0,
            "location": "adapters/__init__.py:14",
            "message": "get_adapter called",
            "data": {
                "FRAMEWORK": cfg.FRAMEWORK,
                "MANIFEST_PATH": cfg.MANIFEST_PATH,
                "CATALOG_PATH": cfg.CATALOG_PATH,
                "DBT_PROJECT_PATH": cfg.DBT_PROJECT_PATH,
                "DBT_MODEL_PATHS": cfg.DBT_MODEL_PATHS,
                "hypothesisId": "B,D",
            },
            "sessionId": "debug-session",
            "runId": "run1",
        }
    )
    with open(log_path, "a") as f:
        f.write(log_entry + "\n")
    # endregion

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
        f"Unknown framework: {cfg.FRAMEWORK}. " f"Supported frameworks: dbt-core"
    )


__all__ = ["get_adapter", "TransformationAdapter", "DbtCoreAdapter"]
