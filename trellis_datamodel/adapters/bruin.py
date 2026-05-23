"""
Bruin adapter implementation.

Implements the TransformationAdapter protocol for the Bruin transformation
framework. Scans pipeline asset files for @bruin blocks, maps them to the
standard Trellis data model types (ModelInfo, ModelSchema, etc.), and
writes schema updates back via the @bruin block rewriter.
"""

from pathlib import Path
from typing import Any, Optional

from trellis_datamodel.utils.bruin_parser import (
    BruinAsset,
    parse_bruin_block,
    scan_pipeline_assets,
)
from trellis_datamodel.utils.bruin_rewriter import rewrite_bruin_block
from .base import (
    ColumnInfo,
    ColumnSchema,
    ModelInfo,
    ModelSchema,
    Relationship,
)


def _split_asset_name(name: str) -> tuple[str, str]:
    """Split a dotted asset name into (schema_part, short_name).

    ``core.dim__game`` -> ``("core", "dim__game")``
    ``simple_model``   -> ``("", "simple_model")``
    """
    if "." in name:
        parts = name.split(".", 1)
        return parts[0], parts[1]
    return "", name


def _asset_to_model_info(asset: BruinAsset) -> ModelInfo:
    """Convert a BruinAsset to a ModelInfo dict."""
    schema_part, short_name = _split_asset_name(asset.name)
    columns: list[ColumnInfo] = [
        {
            "name": c["name"],
            "type": c.get("type", c.get("data_type", "")),
        }
        for c in asset.columns
    ]
    return ModelInfo(
        unique_id=asset.name,
        name=short_name,
        version=None,
        schema=schema_part,
        table=short_name,
        columns=columns,
        description=asset.description or None,
        materialization=asset.materialization.get("type", "") if isinstance(asset.materialization, dict) else "",
        file_path=asset.file_path,
        tags=asset.tags or [],
    )


def _asset_to_model_schema(asset: BruinAsset) -> ModelSchema:
    """Convert a BruinAsset to a ModelSchema dict."""
    _, short_name = _split_asset_name(asset.name)
    columns: list[ColumnSchema] = [
        ColumnSchema(
            name=c["name"],
            data_type=c.get("type", c.get("data_type", "")),
            description=c.get("description", ""),
            data_tests=c.get("checks", None),
        )
        for c in asset.columns
    ]
    return ModelSchema(
        model_name=short_name,
        description=asset.description or "",
        columns=columns,
        tags=asset.tags or [],
        file_path=asset.file_path,
    )


def _find_asset(
    pipeline_path: str,
    asset_paths: list[str],
    model_name: str,
) -> BruinAsset:
    """Find the asset matching *model_name* across all pipeline assets.

    *model_name* may be a short name (e.g. ``"dim__game"``) or a fully
    qualified name (e.g. ``"core.dim__game"``).
    """
    assets = scan_pipeline_assets(pipeline_path, asset_paths)
    for asset in assets:
        _, short_name = _split_asset_name(asset.name)
        if asset.name == model_name or short_name == model_name:
            return asset
    raise ValueError(f"Model '{model_name}' not found in pipeline assets")


class BruinAdapter:
    """Adapter for Bruin transformation framework."""

    def __init__(
        self,
        pipeline_path: str,
        data_model_path: str,
        asset_paths: list[str],
    ):
        self.pipeline_path = pipeline_path
        self.data_model_path = data_model_path
        self.asset_paths = asset_paths

    # ------------------------------------------------------------------
    # Public protocol methods
    # ------------------------------------------------------------------

    def get_models(self) -> list[ModelInfo]:
        """Scan pipeline assets and return ModelInfo for each."""
        assets = scan_pipeline_assets(self.pipeline_path, self.asset_paths)
        return [_asset_to_model_info(a) for a in assets]

    def get_model_schema(
        self,
        model_name: str,
        version: Optional[int] = None,
    ) -> ModelSchema:
        """Get the current schema definition for a specific model."""
        asset = _find_asset(
            self.pipeline_path, self.asset_paths, model_name
        )
        return _asset_to_model_schema(asset)

    def save_model_schema(
        self,
        model_name: str,
        columns: list[ColumnSchema],
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        version: Optional[int] = None,
    ) -> Path:
        """Save/update the schema definition for a model."""
        asset = _find_asset(
            self.pipeline_path, self.asset_paths, model_name
        )

        updates: dict[str, Any] = {}
        if columns is not None:
            updates["columns"] = columns
        if description is not None:
            updates["description"] = description
        if tags is not None:
            updates["tags"] = tags

        return rewrite_bruin_block(asset.file_path, updates)

    def infer_relationships(
        self,
        include_unbound: bool = False,
    ) -> list[Relationship]:
        """Bruin does not currently support relationship inference."""
        return []

    def sync_relationships(
        self,
        entities: list[dict[str, Any]],
        relationships: list[dict[str, Any]],
    ) -> list[Path]:
        """Bruin does not currently support relationship syncing."""
        return []
