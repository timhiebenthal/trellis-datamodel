"""Shared, immutable snapshots of framework artifact files.

The cache is deliberately independent of any transformation framework.  A
caller supplies the artifact paths and may supply a parser; the snapshot
contains parsed documents plus indexes useful to adapters.  File identity is
the resolved path, nanosecond mtime, and byte size, so replacement and
in-place edits cannot reuse stale data.
"""

from __future__ import annotations

import json
import os
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from threading import Event, RLock
from types import MappingProxyType
from typing import Any, Callable, Mapping

from trellis_datamodel.observability import timed_phase


Parser = Callable[[Path], Mapping[str, Any]]
ArtifactKey = tuple["ArtifactIdentity", ...]


@dataclass(frozen=True)
class ArtifactIdentity:
    """Filesystem identity used as the cache key for one artifact."""

    path: Path
    mtime_ns: int
    size: int

    @classmethod
    def from_path(cls, path: str | os.PathLike[str]) -> "ArtifactIdentity":
        resolved = Path(path).expanduser().resolve(strict=True)
        stat = resolved.stat()
        return cls(resolved, stat.st_mtime_ns, stat.st_size)


@dataclass(frozen=True)
class ArtifactSnapshot:
    """An immutable view of parsed artifacts and adapter-facing indexes."""

    identities: ArtifactKey
    manifest: Mapping[str, Any]
    catalog: Mapping[str, Any] | None
    models: tuple[Mapping[str, Any], ...]
    model_index: Mapping[str, Mapping[str, Any]]
    dependency_index: Mapping[str, tuple[str, ...]]
    schema_index: Mapping[str, Mapping[str, Mapping[str, Any]]]
    source_index: Mapping[str, Mapping[str, Any]]
    relationship_index: Mapping[str, tuple[Mapping[str, Any], ...]]

    @property
    def indexes(self) -> Mapping[str, Mapping[str, Any]]:
        """Return all indexes through one immutable mapping."""
        return MappingProxyType(
            {
                "model": self.model_index,
                "dependency": self.dependency_index,
                "schema": self.schema_index,
                "source": self.source_index,
                "relationship": self.relationship_index,
            }
        )


def _freeze(value: Any) -> Any:
    """Recursively convert JSON collections to immutable equivalents."""
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, set):
        return frozenset(_freeze(item) for item in value)
    return value


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _dependency_ids(node: Mapping[str, Any]) -> tuple[str, ...]:
    depends_on = node.get("depends_on", ())
    if isinstance(depends_on, Mapping):
        depends_on = depends_on.get("nodes", ())
    if not isinstance(depends_on, (list, tuple)):
        return ()
    return tuple(item for item in depends_on if isinstance(item, str))


def _relationship_entries(
    unique_id: str, node: Mapping[str, Any]
) -> tuple[Mapping[str, Any], ...]:
    """Extract relationship metadata without imposing framework semantics."""
    entries: list[Mapping[str, Any]] = []
    direct = node.get("relationships", ())
    if isinstance(direct, (list, tuple)):
        entries.extend(
            {"model": unique_id, "relationship": relationship}
            for relationship in direct
            if isinstance(relationship, Mapping)
        )

    columns = _as_mapping(node.get("columns"))
    for column_name, column in columns.items():
        if not isinstance(column, Mapping):
            continue
        for test_key in ("tests", "data_tests"):
            tests = column.get(test_key, ())
            if not isinstance(tests, (list, tuple)):
                continue
            for test in tests:
                if not isinstance(test, Mapping):
                    continue
                relationship = test.get("relationships")
                if isinstance(relationship, Mapping):
                    entries.append(
                        {
                            "model": unique_id,
                            "column": column_name,
                            "relationship": relationship,
                        }
                    )
    return tuple(_freeze(entry) for entry in entries)


def _build_snapshot(
    identities: ArtifactKey,
    manifest: Mapping[str, Any],
    catalog: Mapping[str, Any] | None,
) -> ArtifactSnapshot:
    nodes = _as_mapping(manifest.get("nodes"))
    sources = _as_mapping(manifest.get("sources"))
    catalog_nodes = _as_mapping((catalog or {}).get("nodes"))

    models: list[Mapping[str, Any]] = []
    model_index: dict[str, Mapping[str, Any]] = {}
    dependency_index: dict[str, tuple[str, ...]] = {}
    schema_index: dict[str, Mapping[str, Mapping[str, Any]]] = {}
    relationship_index: dict[str, tuple[Mapping[str, Any], ...]] = {}

    for unique_id, raw_node in nodes.items():
        if not isinstance(unique_id, str) or not isinstance(raw_node, Mapping):
            continue
        if raw_node.get("resource_type") != "model":
            continue

        models.append(raw_node)
        model_index[unique_id] = raw_node
        model_name = raw_node.get("name")
        if isinstance(model_name, str):
            model_index.setdefault(model_name, raw_node)
        dependency_index[unique_id] = _dependency_ids(raw_node)

        manifest_columns = _as_mapping(raw_node.get("columns"))
        catalog_node = _as_mapping(catalog_nodes.get(unique_id))
        catalog_columns = _as_mapping(catalog_node.get("columns"))
        columns: dict[str, Mapping[str, Any]] = dict(manifest_columns)
        columns.update(
            {
                column_name: column
                for column_name, column in catalog_columns.items()
                if isinstance(column, Mapping)
            }
        )
        schema_index[unique_id] = MappingProxyType(columns)
        relationship_index[unique_id] = _relationship_entries(unique_id, raw_node)

    frozen_sources = {
        unique_id: source
        for unique_id, source in sources.items()
        if isinstance(unique_id, str) and isinstance(source, Mapping)
    }
    return ArtifactSnapshot(
        identities=identities,
        manifest=manifest,
        catalog=catalog,
        models=tuple(models),
        model_index=MappingProxyType(model_index),
        dependency_index=MappingProxyType(dependency_index),
        schema_index=MappingProxyType(schema_index),
        source_index=MappingProxyType(frozen_sources),
        relationship_index=MappingProxyType(relationship_index),
    )


class ArtifactSnapshotCache:
    """Thread-safe cache for parsed artifacts and derived immutable indexes."""

    def __init__(self, parser: Parser | None = None, max_entries: int = 32):
        if max_entries < 1:
            raise ValueError("max_entries must be at least 1")
        self._parser = parser or self._parse_json
        self._max_entries = max_entries
        self._artifacts: OrderedDict[ArtifactIdentity, Mapping[str, Any]] = (
            OrderedDict()
        )
        self._snapshots: OrderedDict[ArtifactKey, ArtifactSnapshot] = OrderedDict()
        self._loading: dict[ArtifactIdentity, Event] = {}
        self._lock = RLock()

    @staticmethod
    def _parse_json(path: Path) -> Mapping[str, Any]:
        with timed_phase("artifact_read"):
            with path.open("r", encoding="utf-8") as artifact_file:
                content = artifact_file.read()
        with timed_phase("artifact_parse"):
            parsed = json.loads(content)
        if not isinstance(parsed, Mapping):
            raise ValueError(f"Artifact at {path} must contain a JSON object")
        return parsed

    def _release_replaced(self, identity: ArtifactIdentity) -> None:
        """Release prior identities for a path and snapshots built from them."""
        replaced = [
            cached
            for cached in self._artifacts
            if cached.path == identity.path and cached != identity
        ]
        for cached in replaced:
            self._artifacts.pop(cached, None)
        stale_snapshot_keys = [
            key for key in self._snapshots if identity.path in {item.path for item in key}
            and identity not in key
        ]
        for key in stale_snapshot_keys:
            self._snapshots.pop(key, None)

    def _trim(self) -> None:
        while len(self._artifacts) > self._max_entries:
            self._artifacts.popitem(last=False)
        while len(self._snapshots) > self._max_entries:
            self._snapshots.popitem(last=False)

    def _load_artifact(self, identity: ArtifactIdentity) -> Mapping[str, Any]:
        while True:
            with self._lock:
                cached = self._artifacts.get(identity)
                if cached is not None:
                    self._artifacts.move_to_end(identity)
                    return cached
                waiter = self._loading.get(identity)
                if waiter is None:
                    waiter = Event()
                    self._loading[identity] = waiter
                    break
            waiter.wait()

        try:
            parsed = _freeze(self._parser(identity.path))
            if not isinstance(parsed, Mapping):
                raise ValueError(f"Artifact at {identity.path} must contain an object")
        except BaseException:
            with self._lock:
                self._loading.pop(identity, None)
                waiter.set()
            raise

        with self._lock:
            self._release_replaced(identity)
            self._artifacts[identity] = parsed
            self._artifacts.move_to_end(identity)
            self._loading.pop(identity, None)
            waiter.set()
            self._trim()
        return parsed

    def load(
        self,
        manifest_path: str | os.PathLike[str],
        catalog_path: str | os.PathLike[str] | None = None,
    ) -> ArtifactSnapshot:
        """Load or reuse a snapshot for the current identities of two artifacts."""
        manifest_identity = ArtifactIdentity.from_path(manifest_path)
        identities: list[ArtifactIdentity] = [manifest_identity]
        catalog_identity = (
            ArtifactIdentity.from_path(catalog_path)
            if catalog_path is not None and Path(catalog_path).exists()
            else None
        )
        if catalog_identity is not None:
            identities.append(catalog_identity)
        key = tuple(identities)

        with self._lock:
            cached_snapshot = self._snapshots.get(key)
            if cached_snapshot is not None:
                self._snapshots.move_to_end(key)
                return cached_snapshot

        manifest = self._load_artifact(manifest_identity)
        catalog = (
            self._load_artifact(catalog_identity)
            if catalog_identity is not None
            else None
        )
        built = _build_snapshot(key, manifest, catalog)

        with self._lock:
            cached_snapshot = self._snapshots.get(key)
            if cached_snapshot is not None:
                self._snapshots.move_to_end(key)
                return cached_snapshot
            self._snapshots[key] = built
            self._snapshots.move_to_end(key)
            self._trim()
            return built

    def invalidate(
        self, path: str | os.PathLike[str] | None = None
    ) -> None:
        """Invalidate all snapshots, or only snapshots depending on ``path``."""
        with self._lock:
            if path is None:
                self._artifacts.clear()
                self._snapshots.clear()
                return
            resolved = Path(path).expanduser().resolve()
            identities = [
                identity for identity in self._artifacts if identity.path == resolved
            ]
            for identity in identities:
                self._artifacts.pop(identity, None)
            for key in list(self._snapshots):
                if resolved in {identity.path for identity in key}:
                    self._snapshots.pop(key, None)

    def clear(self) -> None:
        """Clear the complete cache, including parsed artifacts."""
        self.invalidate()


_DEFAULT_CACHE = ArtifactSnapshotCache()


def get_snapshot(
    manifest_path: str | os.PathLike[str],
    catalog_path: str | os.PathLike[str] | None = None,
) -> ArtifactSnapshot:
    """Load a snapshot from the process-shared default cache."""
    return _DEFAULT_CACHE.load(manifest_path, catalog_path)


def invalidate_snapshots(
    path: str | os.PathLike[str] | None = None,
) -> None:
    """Invalidate the process-shared cache for config reloads or file writes."""
    _DEFAULT_CACHE.invalidate(path)


def clear_snapshots() -> None:
    """Clear every snapshot from the process-shared cache."""
    _DEFAULT_CACHE.clear()


__all__ = [
    "ArtifactIdentity",
    "ArtifactSnapshot",
    "ArtifactSnapshotCache",
    "clear_snapshots",
    "get_snapshot",
    "invalidate_snapshots",
]
