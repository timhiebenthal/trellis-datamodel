"""Tests for the framework-neutral artifact snapshot cache."""

from __future__ import annotations

import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest


def _write_artifact(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_reuses_parsed_manifest_catalog_and_indexes_for_identical_file_identity(
    tmp_path: Path,
) -> None:
    from trellis_datamodel.adapters.artifact_snapshot import ArtifactSnapshotCache

    manifest_path = tmp_path / "manifest.json"
    catalog_path = tmp_path / "catalog.json"
    _write_artifact(
        manifest_path,
        {
            "nodes": {
                "model.project.orders": {
                    "unique_id": "model.project.orders",
                    "resource_type": "model",
                    "name": "orders",
                    "depends_on": {"nodes": ["source.project.crm.orders"]},
                    "columns": {"id": {"name": "id", "data_type": "integer"}},
                }
            },
            "sources": {
                "source.project.crm.orders": {
                    "unique_id": "source.project.crm.orders",
                    "resource_type": "source",
                    "source_name": "crm",
                }
            },
        },
    )
    _write_artifact(
        catalog_path,
        {"nodes": {"model.project.orders": {"columns": {"id": {"type": "INTEGER"}}}}},
    )
    parse_calls: list[Path] = []

    def parse(path: Path) -> dict[str, Any]:
        parse_calls.append(path)
        return json.loads(path.read_text(encoding="utf-8"))

    cache = ArtifactSnapshotCache(parser=parse)
    first = cache.load(manifest_path, catalog_path)
    second = cache.load(manifest_path.resolve(), catalog_path.resolve())

    assert first is second
    assert parse_calls == [manifest_path.resolve(), catalog_path.resolve()]
    assert first.manifest is second.manifest
    assert first.catalog is second.catalog
    assert first.model_index is second.model_index
    assert first.dependency_index is second.dependency_index
    assert first.schema_index is second.schema_index
    assert first.source_index is second.source_index
    assert first.relationship_index is second.relationship_index


def test_invalidates_when_mtime_ns_changes(tmp_path: Path) -> None:
    from trellis_datamodel.adapters.artifact_snapshot import ArtifactSnapshotCache

    manifest_path = tmp_path / "manifest.json"
    _write_artifact(manifest_path, {"version": 1})
    cache = ArtifactSnapshotCache()
    first = cache.load(manifest_path)

    original_stat = manifest_path.stat()
    _write_artifact(manifest_path, {"version": 2})
    os.utime(manifest_path, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns + 1))
    second = cache.load(manifest_path)

    assert first is not second
    assert second.manifest["version"] == 2


def test_invalidates_when_size_changes_even_with_same_mtime(tmp_path: Path) -> None:
    from trellis_datamodel.adapters.artifact_snapshot import ArtifactSnapshotCache

    manifest_path = tmp_path / "manifest.json"
    _write_artifact(manifest_path, {"version": 1})
    cache = ArtifactSnapshotCache()
    first = cache.load(manifest_path)
    original_stat = manifest_path.stat()

    _write_artifact(manifest_path, {"version": 200})
    assert manifest_path.stat().st_size != original_stat.st_size
    os.utime(manifest_path, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
    second = cache.load(manifest_path)

    assert first is not second
    assert second.manifest["version"] == 200


def test_resolved_paths_do_not_collide(tmp_path: Path) -> None:
    from trellis_datamodel.adapters.artifact_snapshot import ArtifactSnapshotCache

    first_path = tmp_path / "one" / "manifest.json"
    second_path = tmp_path / "two" / "manifest.json"
    first_path.parent.mkdir()
    second_path.parent.mkdir()
    _write_artifact(first_path, {"project": "one"})
    _write_artifact(second_path, {"project": "two"})
    cache = ArtifactSnapshotCache()

    first = cache.load(first_path)
    second = cache.load(second_path)

    assert first is not second
    assert first.manifest["project"] == "one"
    assert second.manifest["project"] == "two"


def test_config_reload_clears_snapshots(tmp_path: Path) -> None:
    from trellis_datamodel import config as cfg
    from trellis_datamodel.adapters.artifact_snapshot import (
        clear_snapshots,
        get_snapshot,
    )

    manifest_path = tmp_path / "manifest.json"
    config_path = tmp_path / "trellis.yml"
    _write_artifact(manifest_path, {"version": 1})
    config_path.write_text(
        "framework: dbt-core\n"
        f"dbt_project_path: {tmp_path}\n"
        f"dbt_manifest_path: {manifest_path.name}\n",
        encoding="utf-8",
    )
    clear_snapshots()
    first = get_snapshot(manifest_path)

    cfg.reload_config(str(config_path))
    second = get_snapshot(manifest_path)

    assert first is not second


def test_concurrent_first_load_parses_each_artifact_once(tmp_path: Path) -> None:
    from trellis_datamodel.adapters.artifact_snapshot import ArtifactSnapshotCache

    manifest_path = tmp_path / "manifest.json"
    catalog_path = tmp_path / "catalog.json"
    _write_artifact(manifest_path, {"nodes": {}})
    _write_artifact(catalog_path, {"nodes": {}})
    parse_calls: dict[Path, int] = {}
    parse_lock = threading.Lock()

    def parse(path: Path) -> dict[str, Any]:
        with parse_lock:
            parse_calls[path] = parse_calls.get(path, 0) + 1
        return json.loads(path.read_text(encoding="utf-8"))

    cache = ArtifactSnapshotCache(parser=parse)

    def load() -> Any:
        return cache.load(manifest_path, catalog_path)

    with ThreadPoolExecutor(max_workers=8) as executor:
        snapshots = list(executor.map(lambda _: load(), range(16)))

    assert parse_calls == {
        manifest_path.resolve(): 1,
        catalog_path.resolve(): 1,
    }
    assert all(snapshot is snapshots[0] for snapshot in snapshots)


def test_snapshot_does_not_expose_mutable_cached_collections(tmp_path: Path) -> None:
    from trellis_datamodel.adapters.artifact_snapshot import ArtifactSnapshotCache

    manifest_path = tmp_path / "manifest.json"
    _write_artifact(
        manifest_path,
        {
            "nodes": {
                "model.project.orders": {
                    "unique_id": "model.project.orders",
                    "resource_type": "model",
                    "name": "orders",
                    "columns": {"id": {"name": "id"}},
                }
            }
        },
    )
    snapshot = ArtifactSnapshotCache().load(manifest_path)

    with pytest.raises(TypeError):
        snapshot.manifest["changed"] = True
    with pytest.raises(TypeError):
        snapshot.model_index["changed"] = {}
    with pytest.raises(TypeError):
        snapshot.schema_index["model.project.orders"]["id"] = {}
    with pytest.raises(TypeError):
        snapshot.manifest["nodes"]["model.project.orders"]["name"] = "changed"
    assert isinstance(snapshot.models, tuple)
