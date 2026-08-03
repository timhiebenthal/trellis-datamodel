"""
Bruin adapter implementation.

Implements the TransformationAdapter protocol for the Bruin transformation
framework. Bruin keeps a model's schema inline in the asset file's `@bruin`
comment block rather than in a sidecar YAML, so reads scan those blocks and
writes rewrite them in place.

Two Bruin conventions carry most of the mapping:

- `depends:` gives table-level lineage. An asset with no upstreams, or an
  `ingestr` asset, is an ingestion point and is reported as a source; its
  source system is the `parameters.source_connection` it pulls from.
- `columns[].foreign_key: {table, column}` is Bruin's native way to declare a
  reference between assets, which is what Trellis relationships map onto.

Bruin has no exposures concept and no column-level lineage, both of which are
advertised through `get_project_status()["capabilities"]` rather than failing
at the call site.
"""

import logging
import os
from pathlib import Path
from typing import Any, Optional

from trellis_datamodel import config as cfg
from trellis_datamodel.exceptions import NotFoundError
from trellis_datamodel.models.entity_keys import get_model_ref
from trellis_datamodel.utils.bruin_parser import (
    BruinAsset,
    asset_folder,
    scan_pipeline_assets,
)
from trellis_datamodel.utils.bruin_rewriter import (
    rewrite_bruin_block,
    write_bruin_asset,
)
from . import entity_type_inference
from .base import (
    Capabilities,
    ColumnInfo,
    ColumnSchema,
    Exposure,
    LineageGraph,
    LineageNode,
    ModelInfo,
    ModelSchema,
    ProjectStatus,
    Relationship,
)

logger = logging.getLogger(__name__)

FRAMEWORK_NAME = "bruin"

# Asset types that ingest from outside the warehouse rather than transform
# within it. These terminate a lineage walk the way a dbt source does.
INGESTION_ASSET_TYPE_PREFIXES = ("ingestr",)


def _split_asset_name(name: str) -> tuple[str, str]:
    """Split a dotted asset name into (schema_part, short_name).

    ``core.dim__game`` -> ``("core", "dim__game")``
    ``simple_model``   -> ``("", "simple_model")``
    """
    if "." in name:
        parts = name.split(".", 1)
        return parts[0], parts[1]
    return "", name


def _short_name(name: str) -> str:
    """The asset name without its schema prefix."""
    return _split_asset_name(name)[1]


def _column_type(column: dict) -> str:
    """Bruin writes a column's type as `type`; tolerate `data_type` too."""
    return column.get("type", column.get("data_type", "")) or ""


def _is_ingestion_asset(asset: BruinAsset) -> bool:
    """Whether an asset pulls data in rather than transforming existing data."""
    return (asset.type or "").lower().startswith(INGESTION_ASSET_TYPE_PREFIXES)


def _asset_source_name(asset: BruinAsset) -> Optional[str]:
    """The upstream system an ingestion asset reads from.

    `parameters.source_connection` is what an ingestr asset names; a Python or
    custom ingestion asset only has its `connection`, which is the best
    available answer.
    """
    return asset.parameters.get("source_connection") or asset.connection or None


def _asset_to_model_info(asset: BruinAsset) -> ModelInfo:
    """Convert a BruinAsset to a ModelInfo dict."""
    schema_part, short_name = _split_asset_name(asset.name)
    columns: list[ColumnInfo] = [
        {
            "name": column["name"],
            "type": _column_type(column),
            "description": column.get("description"),
        }
        for column in asset.columns
        if column.get("name")
    ]
    materialization = (
        asset.materialization.get("type", "")
        if isinstance(asset.materialization, dict)
        else ""
    )
    return ModelInfo(
        unique_id=asset.name,
        name=short_name,
        version=None,
        schema=schema_part,
        table=short_name,
        columns=columns,
        description=asset.description or None,
        materialization=materialization,
        file_path=asset.file_path,
        tags=asset.tags or [],
    )


def _asset_to_model_schema(asset: BruinAsset) -> ModelSchema:
    """Convert a BruinAsset to a ModelSchema dict."""
    columns: list[ColumnSchema] = []
    for column in asset.columns:
        if not column.get("name"):
            continue
        entry: ColumnSchema = ColumnSchema(
            name=column["name"],
            data_type=_column_type(column),
            description=column.get("description", ""),
            data_tests=column.get("checks") or None,
        )
        # Bruin-owned metadata Trellis does not model but must not silently
        # drop, since a save round-trips whatever a read returned.
        for key in ("primary_key", "nullable", "foreign_key"):
            if key in column:
                entry[key] = column[key]
        columns.append(entry)

    return ModelSchema(
        model_name=_short_name(asset.name),
        description=asset.description or "",
        columns=columns,
        tags=asset.tags or [],
        file_path=asset.file_path,
    )


class BruinAdapter:
    """Adapter for the Bruin transformation framework."""

    def __init__(
        self,
        pipeline_path: str,
        data_model_path: str,
        asset_paths: list[str],
        default_asset_type: str = "duckdb.sql",
    ):
        self.pipeline_path = pipeline_path
        self.data_model_path = data_model_path
        self.asset_paths = asset_paths or []
        self.default_asset_type = default_asset_type

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _scan_assets(self) -> list[BruinAsset]:
        """Every parseable asset in the configured pipeline paths."""
        return scan_pipeline_assets(self.pipeline_path, self.asset_paths)

    def _scan_all_assets(self) -> list[BruinAsset]:
        """Every asset in the pipeline, ignoring the asset-path filter.

        Lineage and foreign-key resolution must see the whole pipeline: an
        upstream asset outside the configured paths is still a real dependency,
        and hiding it would silently truncate the graph.
        """
        return scan_pipeline_assets(self.pipeline_path, [])

    def _find_asset(self, model_name: str) -> BruinAsset:
        """Find the asset matching *model_name*.

        *model_name* may be a short name (``dim__game``) or fully qualified
        (``core.dim__game``); Bruin users write both, and an entity binding may
        hold either.
        """
        asset = self._lookup_asset(self._scan_all_assets(), model_name)
        if asset is None:
            raise ValueError(f"Model '{model_name}' not found in pipeline assets")
        return asset

    @staticmethod
    def _lookup_asset(
        assets: list[BruinAsset], model_name: str
    ) -> Optional[BruinAsset]:
        """Match a name against both the dotted and short spelling."""
        if not model_name:
            return None
        for asset in assets:
            if asset.name == model_name or _short_name(asset.name) == model_name:
                return asset
        return None

    def _load_data_model(self) -> dict:
        """Load data model YAML if it exists."""
        if not self.data_model_path or not os.path.exists(self.data_model_path):
            return {}
        try:
            import yaml

            with open(self.data_model_path, "r") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning("Could not load data model: %s", e)
            return {}

    def _get_model_to_entity_map(self) -> dict[str, str]:
        """Map asset names to the entity bound to them.

        Both spellings of every bound asset are registered, because a binding
        may hold either and callers look up by whichever they have.
        """
        model_to_entity: dict[str, str] = {}

        for entity in self._load_data_model().get("entities", []):
            entity_id = entity.get("id")
            if not entity_id:
                continue

            bound_models = [get_model_ref(entity)]
            bound_models.extend(entity.get("additional_models") or [])

            for model in bound_models:
                if not model:
                    continue
                model_to_entity[model] = entity_id
                model_to_entity[_short_name(model)] = entity_id

            model_to_entity[entity_id] = entity_id

        return model_to_entity

    # ------------------------------------------------------------------
    # Models and schemas
    # ------------------------------------------------------------------

    def get_models(self) -> list[ModelInfo]:
        """Scan pipeline assets and return ModelInfo for each."""
        return [_asset_to_model_info(asset) for asset in self._scan_assets()]

    def get_model_schema(
        self,
        model_name: str,
        version: Optional[int] = None,
    ) -> ModelSchema:
        """Get the current schema definition for a specific model.

        Bruin has no model versioning, so *version* is accepted for protocol
        compatibility and ignored.
        """
        return _asset_to_model_schema(self._find_asset(model_name))

    def save_model_schema(
        self,
        model_name: str,
        columns: list[ColumnSchema],
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        version: Optional[int] = None,
    ) -> Path:
        """Save/update the schema definition for a model."""
        asset = self._find_asset(model_name)

        updates: dict[str, Any] = {}
        if columns is not None:
            updates["columns"] = self._merge_columns(asset, columns)
        if description is not None:
            updates["description"] = description
        if tags is not None:
            updates["tags"] = self._union_tags(asset, tags)

        return rewrite_bruin_block(asset.file_path, updates)

    @staticmethod
    def _merge_columns(
        asset: BruinAsset, columns: list[ColumnSchema]
    ) -> list[dict[str, Any]]:
        """Overlay incoming columns onto what the asset already declares.

        The rewriter replaces the column list wholesale, so anything Bruin owns
        and Trellis does not send — `primary_key`, `nullable`, `checks`,
        `foreign_key` — has to be carried over here or a schema push would
        quietly strip it. An incoming key always wins, which is what makes
        deliberate removal possible.
        """
        existing = {c["name"]: c for c in asset.columns if c.get("name")}

        merged: list[dict[str, Any]] = []
        for column in columns:
            name = column.get("name")
            if not name:
                continue

            entry: dict[str, Any] = dict(existing.get(name, {}))
            entry.pop("data_type", None)

            for key, value in column.items():
                if key == "data_tests":
                    # Trellis's protocol name for Bruin's column checks.
                    if value is not None:
                        entry["checks"] = value
                elif key == "data_type":
                    if value:
                        entry["type"] = value
                elif value is not None or key in entry:
                    entry[key] = value

            merged.append(entry)

        return merged

    @staticmethod
    def _union_tags(asset: BruinAsset, tags: list[str]) -> list[str]:
        """Add tags without dropping any the asset already carries.

        Matches the dbt adapter: incoming tags are Trellis-authored additions,
        never a replacement for the live list.
        """
        result = list(asset.tags or [])
        for tag in tags:
            if tag not in result:
                result.append(tag)
        return result

    def save_schema_file(
        self,
        entity_id: str,
        model_name: str,
        fields: list[dict[str, str]],
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> Path:
        """Write drafted fields into the entity's asset, scaffolding if needed.

        Bruin has no sidecar schema file, so "save the schema" means editing the
        asset's `@bruin` block. When the entity has no asset yet, one is
        scaffolded with a placeholder body: Trellis cannot know the query, so
        the file is deliberately left obviously unfinished for the user to
        complete.
        """
        data_model = self._load_data_model()
        entity = next(
            (
                e
                for e in data_model.get("entities", [])
                if e.get("id") == entity_id
            ),
            None,
        )

        if entity and not description:
            description = entity.get("description")

        columns = [
            {
                "name": field["name"],
                "data_type": field.get("data_type") or field.get("type") or "",
                "description": field.get("description", ""),
            }
            for field in fields
            if field.get("name")
        ]

        asset = self._lookup_asset(self._scan_all_assets(), model_name)
        if asset is None:
            return self._scaffold_asset(model_name, columns, description, tags)

        updates: dict[str, Any] = {"columns": self._merge_columns(asset, columns)}
        if description is not None:
            updates["description"] = description
        if tags is not None:
            updates["tags"] = self._union_tags(asset, tags)

        return rewrite_bruin_block(asset.file_path, updates)

    def _scaffold_asset(
        self,
        model_name: str,
        columns: list[dict[str, Any]],
        description: Optional[str],
        tags: Optional[list[str]],
    ) -> Path:
        """Create a new asset file for a model the pipeline does not have yet."""
        block: dict[str, Any] = {
            "name": model_name,
            "type": self.default_asset_type,
        }
        if description:
            block["description"] = description
        if tags:
            block["tags"] = list(tags)
        if columns:
            block["columns"] = columns

        short_name = _short_name(model_name)
        body = (
            f"-- TODO: Trellis scaffolded this asset from the data model.\n"
            f"-- Replace this placeholder with the query that builds {model_name}.\n"
            f"SELECT NULL AS placeholder\n"
            f"WHERE 1 = 0;\n"
        )

        logger.info(
            "Scaffolding new Bruin asset %s at %s",
            model_name,
            self._scaffold_path(short_name),
        )
        return write_bruin_asset(self._scaffold_path(short_name), block, body)

    def _scaffold_path(self, short_name: str) -> str:
        """Where a scaffolded asset file goes.

        Into the first configured asset path when the pipeline filters them, so
        a scaffolded asset lands where Trellis is actually looking; otherwise
        directly under `assets/`.
        """
        parts = [self.pipeline_path, "assets"]
        if self.asset_paths:
            parts.append(self.asset_paths[0])
        return os.path.join(*parts, f"{short_name}.sql")

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    def infer_relationships(
        self,
        include_unbound: bool = False,
    ) -> list[Relationship]:
        """Read relationships from Bruin's column-level `foreign_key` blocks."""
        assets = self._scan_all_assets()
        model_to_entity = self._get_model_to_entity_map()

        relationships: list[Relationship] = []
        for asset in assets:
            source_entity = self._resolve_entity(asset.name, model_to_entity)
            if source_entity is None and not include_unbound:
                continue
            source_entity = source_entity or _short_name(asset.name)

            for column in asset.columns:
                foreign_key = column.get("foreign_key")
                if not isinstance(foreign_key, dict):
                    continue

                target_table = foreign_key.get("table")
                target_column = foreign_key.get("column")
                if not target_table or not target_column:
                    logger.warning(
                        "Ignoring incomplete foreign_key on %s.%s: %s",
                        asset.name,
                        column.get("name"),
                        foreign_key,
                    )
                    continue

                target_asset = self._lookup_asset(assets, target_table)
                if target_asset is None:
                    logger.warning(
                        "foreign_key on %s.%s references unknown asset '%s'",
                        asset.name,
                        column.get("name"),
                        target_table,
                    )
                    continue

                target_entity = self._resolve_entity(
                    target_asset.name, model_to_entity
                )
                if target_entity is None and not include_unbound:
                    continue
                target_entity = target_entity or _short_name(target_asset.name)

                relationships.append(
                    Relationship(
                        source=source_entity,
                        target=target_entity,
                        label="",
                        type="one_to_many",
                        source_field=column["name"],
                        target_field=target_column,
                        source_model_name=_short_name(asset.name),
                        source_model_version=None,
                        target_model_name=_short_name(target_asset.name),
                        target_model_version=None,
                    )
                )

        return relationships

    def _resolve_entity(
        self, asset_name: str, model_to_entity: dict[str, str]
    ) -> Optional[str]:
        """The entity bound to an asset, by either spelling of its name."""
        return model_to_entity.get(asset_name) or model_to_entity.get(
            _short_name(asset_name)
        )

    def sync_relationships(
        self,
        entities: list[dict[str, Any]],
        relationships: list[dict[str, Any]],
    ) -> list[Path]:
        """Write relationships back as Bruin `foreign_key` column blocks.

        One-way, entity-model-wins: every foreign_key on a synced asset is
        rebuilt from *relationships*, so a relationship deleted in Trellis has
        its foreign_key pruned. Only assets bound to an entity in the payload
        are touched — an asset Trellis does not know about is never rewritten.
        """
        assets = self._scan_all_assets()
        entity_to_asset = self._entity_to_asset_map(entities, assets)

        # asset name -> {column name: foreign_key block}
        desired: dict[str, dict[str, dict[str, str]]] = {}
        for relationship in relationships:
            source_asset = entity_to_asset.get(relationship.get("source"))
            target_asset = entity_to_asset.get(relationship.get("target"))
            source_field = relationship.get("source_field")
            target_field = relationship.get("target_field")

            if not (source_asset and target_asset and source_field and target_field):
                continue

            desired.setdefault(source_asset.name, {})[source_field] = {
                # Write back the spelling the target asset itself declares, so
                # the file stays consistent with the rest of the pipeline.
                "table": target_asset.name,
                "column": target_field,
            }

        updated: list[Path] = []
        for asset in self._assets_to_sync(assets, entity_to_asset):
            wanted = desired.get(asset.name, {})
            columns = self._apply_foreign_keys(asset, wanted)
            if columns is None:
                continue
            updated.append(rewrite_bruin_block(asset.file_path, {"columns": columns}))

        return updated

    @staticmethod
    def _assets_to_sync(
        assets: list[BruinAsset], entity_to_asset: dict[str, BruinAsset]
    ) -> list[BruinAsset]:
        """Only assets bound to an entity in the payload are eligible."""
        bound_names = {asset.name for asset in entity_to_asset.values()}
        return [asset for asset in assets if asset.name in bound_names]

    def _entity_to_asset_map(
        self, entities: list[dict[str, Any]], assets: list[BruinAsset]
    ) -> dict[str, BruinAsset]:
        """Map each entity id to the asset it is bound to, if any."""
        mapping: dict[str, BruinAsset] = {}
        for entity in entities:
            entity_id = entity.get("id")
            model_ref = get_model_ref(entity)
            if not entity_id or not model_ref:
                continue
            asset = self._lookup_asset(assets, model_ref)
            if asset is not None:
                mapping[entity_id] = asset
        return mapping

    @staticmethod
    def _apply_foreign_keys(
        asset: BruinAsset, wanted: dict[str, dict[str, str]]
    ) -> Optional[list[dict[str, Any]]]:
        """Rebuild an asset's columns with exactly the wanted foreign keys.

        Returns None when nothing would change, so a sync only touches files it
        actually needs to.
        """
        columns: list[dict[str, Any]] = []
        changed = False

        for column in asset.columns:
            entry = dict(column)
            name = entry.get("name")
            current = entry.get("foreign_key")
            target = wanted.get(name)

            if target is not None:
                if current != target:
                    entry["foreign_key"] = target
                    changed = True
            elif current is not None:
                # Relationship removed in Trellis: prune the stale foreign key.
                entry.pop("foreign_key")
                changed = True

            columns.append(entry)

        declared = {c.get("name") for c in asset.columns}
        for name, target in wanted.items():
            if name not in declared:
                # The relationship names a column the asset does not declare.
                # Add it so the reference is not silently lost.
                columns.append({"name": name, "foreign_key": target})
                changed = True

        return columns if changed else None

    # ------------------------------------------------------------------
    # Entity type inference
    # ------------------------------------------------------------------

    @classmethod
    def reset_inference_cache(cls) -> None:
        """Reset the entity type inference cache."""
        entity_type_inference.reset_cache(FRAMEWORK_NAME)

    def infer_entity_types(self) -> dict[str, str]:
        """Infer entity types from Bruin asset naming patterns."""
        if not cfg.DIMENSIONAL_MODELING_CONFIG.enabled:
            return {}

        return entity_type_inference.infer_entity_types(
            framework=FRAMEWORK_NAME,
            cache_key=self._inference_cache_key(),
            get_models=self.get_models,
            get_model_to_entity_map=self._get_model_to_entity_map,
        )

    def _inference_cache_key(self) -> str:
        """Staleness token for inference: the newest asset file's mtime.

        Bruin has no compiled manifest to watch, so the asset files themselves
        are the source of truth for whether inference can be reused.
        """
        newest = 0.0
        for asset in self._scan_assets():
            try:
                newest = max(newest, os.path.getmtime(asset.file_path))
            except OSError:
                continue
        return f"{self.pipeline_path}:{newest}"

    def get_model_dirs(self) -> list[str]:
        """Return the directories the pipeline's assets live in."""
        assets_dir = os.path.join(self.pipeline_path, "assets")
        if not self.asset_paths:
            return [os.path.abspath(assets_dir).rstrip(os.sep)]

        dirs = []
        for asset_path in self.asset_paths:
            resolved = os.path.abspath(os.path.join(assets_dir, asset_path)).rstrip(
                os.sep
            )
            if resolved not in dirs:
                dirs.append(resolved)
        return dirs

    # ------------------------------------------------------------------
    # Lineage, exposures, and project status
    # ------------------------------------------------------------------

    def get_lineage(self, model_unique_id: str) -> LineageGraph:
        """Build the upstream lineage graph for an asset from `depends:`."""
        from collections import deque

        assets = self._scan_all_assets()
        by_name: dict[str, BruinAsset] = {}
        for asset in assets:
            by_name[asset.name] = asset
            by_name.setdefault(_short_name(asset.name), asset)

        root = by_name.get(model_unique_id)
        if root is None:
            raise NotFoundError(
                self._asset_not_found_message(model_unique_id, assets)
            )

        node_names: set[str] = {root.name}
        edges: list[dict[str, str]] = []

        queue = deque([root])
        visited = {root.name}

        while queue:
            current = queue.popleft()
            for upstream_name in current.depends:
                upstream = by_name.get(upstream_name)
                # Report the canonical asset name when we can resolve it, so a
                # short-name `depends` entry does not appear as a second node.
                resolved_name = upstream.name if upstream else upstream_name

                edges.append({"source": resolved_name, "target": current.name})
                node_names.add(resolved_name)

                if resolved_name not in visited:
                    visited.add(resolved_name)
                    if upstream is not None and not _is_ingestion_asset(upstream):
                        queue.append(upstream)

        return LineageGraph(
            nodes=[self._lineage_node(name, by_name) for name in sorted(node_names)],
            edges=edges,
        )

    def _lineage_node(
        self, asset_name: str, by_name: dict[str, BruinAsset]
    ) -> LineageNode:
        """Describe one lineage node from its asset."""
        asset = by_name.get(asset_name)

        if asset is None:
            # A `depends` entry naming an asset that is not in the pipeline.
            # Keep it in the graph rather than dropping the dependency.
            return LineageNode(
                unique_id=asset_name,
                name=_short_name(asset_name),
                resource_type="model",
                is_source=False,
                source_name=None,
                folder=None,
            )

        # An asset with no upstreams is where data enters the pipeline, which is
        # the role a dbt source plays.
        is_source = _is_ingestion_asset(asset) or not asset.depends

        node = LineageNode(
            unique_id=asset.name,
            name=_short_name(asset.name),
            resource_type="source" if is_source else "model",
            is_source=is_source,
            source_name=_asset_source_name(asset) if is_source else None,
            folder=asset_folder(self.pipeline_path, asset.file_path),
        )
        if asset.file_path:
            node["file_path"] = asset.file_path
        return node

    @staticmethod
    def _asset_not_found_message(model_unique_id: str, assets: list[BruinAsset]) -> str:
        """Build the not-found message, naming near-misses when there are any."""
        short = _short_name(model_unique_id)
        similar = [a.name for a in assets if _short_name(a.name) == short]
        if similar:
            return (
                f"Asset '{model_unique_id}' not found in pipeline. "
                f"Found similar assets: {', '.join(similar[:3])}"
            )
        return (
            f"Asset '{model_unique_id}' not found in pipeline. "
            f"Available assets: {len(assets)} asset(s)"
        )

    def get_source_systems_for_model(self, model_unique_id: str) -> list[str]:
        """Return the source connections feeding an asset."""
        try:
            graph = self.get_lineage(model_unique_id)
        except Exception as e:
            logger.warning(
                "Failed to extract source systems for asset %s: %s",
                model_unique_id,
                e,
            )
            return []

        return sorted(
            {
                node["source_name"]
                for node in graph["nodes"]
                if node["is_source"] and node["source_name"]
            }
        )

    def get_exposures(self) -> list[Exposure]:
        """Bruin has no exposures concept.

        Reported as `capabilities.exposures = False` by get_project_status, so
        callers can tell this apart from a project that declares none.
        """
        return []

    def get_project_status(self) -> ProjectStatus:
        """Report whether the configured Bruin pipeline is present and usable."""
        pipeline_exists = bool(
            self.pipeline_path and os.path.isdir(self.pipeline_path)
        )
        assets_dir = os.path.join(self.pipeline_path, "assets")
        assets_dir_exists = bool(self.pipeline_path and os.path.isdir(assets_dir))

        pipeline_definition = os.path.join(self.pipeline_path, "pipeline.yml")
        assets_found = len(self._scan_assets()) if assets_dir_exists else 0

        if not self.pipeline_path:
            error = "bruin_pipeline_path not set in config."
        elif not pipeline_exists:
            error = f"Pipeline not found at {self.pipeline_path}"
        elif not assets_dir_exists:
            error = f"No assets directory found at {assets_dir}"
        elif not assets_found:
            error = f"No assets with an @bruin block found under {assets_dir}"
        else:
            error = None

        return ProjectStatus(
            framework=FRAMEWORK_NAME,
            artifacts_present=assets_found > 0,
            artifacts={
                "pipeline": {
                    "label": "pipeline.yml",
                    "path": pipeline_definition,
                    "exists": os.path.exists(pipeline_definition),
                    "hint": "A Bruin pipeline is a directory with pipeline.yml and assets/.",
                },
                "assets": {
                    "label": "assets",
                    "path": assets_dir,
                    "exists": assets_dir_exists,
                    "hint": "Assets carry their schema in an @bruin comment block.",
                },
            },
            project_path=self.pipeline_path,
            project_path_exists=pipeline_exists,
            model_paths_configured=self.asset_paths,
            model_paths_resolved=self.get_model_dirs() if self.pipeline_path else [],
            capabilities=Capabilities(
                lineage=True,
                # `depends` is table-level only; Bruin resolves column-level
                # upstreams itself and does not write them into the asset file.
                column_lineage=False,
                exposures=False,
                relationships=True,
                scaffolding=True,
            ),
            error=error,
        )
