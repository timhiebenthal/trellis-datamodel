"""
Lineage extraction service using dbt-colibri.

Extracts table-level upstream lineage from dbt manifest.json and catalog.json files.
"""

import json
import os
from typing import Any, Optional
from collections import deque

try:
    from dbt_colibri import extract_lineage
except ImportError:
    # Fallback if dbt-colibri is not available
    extract_lineage = None


class LineageError(Exception):
    """Error during lineage extraction."""
    pass


def extract_upstream_lineage(
    manifest_path: str,
    catalog_path: Optional[str],
    model_unique_id: str,
) -> dict[str, Any]:
    """
    Extract upstream table-level lineage for a given model using dbt-colibri.

    Args:
        manifest_path: Path to dbt manifest.json file
        catalog_path: Path to dbt catalog.json file (optional but recommended)
        model_unique_id: Unique ID of the model (e.g., "model.project.model_name")

    Returns:
        Dictionary with:
        - nodes: List of lineage nodes with id, label, level, isSource
        - edges: List of edges with source, target, level
        - metadata: Additional metadata including model counts per level

    Raises:
        LineageError: If lineage extraction fails
        FileNotFoundError: If manifest.json is missing
    """
    if extract_lineage is None:
        raise LineageError(
            "dbt-colibri is not installed. Please install it with: pip install dbt-colibri"
        )

    # Validate manifest exists
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"Manifest not found at {manifest_path}")

    # Check catalog exists (warn but don't fail)
    if catalog_path and not os.path.exists(catalog_path):
        raise LineageError(
            f"Catalog not found at {catalog_path}. "
            "Please run 'dbt docs generate' to create catalog.json"
        )

    try:
        # Load manifest
        with open(manifest_path, "r") as f:
            manifest = json.load(f)

        # Load catalog if available
        catalog = None
        if catalog_path and os.path.exists(catalog_path):
            with open(catalog_path, "r") as f:
                catalog = json.load(f)

        # Verify model exists in manifest
        nodes = manifest.get("nodes", {})
        if model_unique_id not in nodes:
            raise LineageError(f"Model '{model_unique_id}' not found in manifest")

        # Extract lineage using dbt-colibri
        # Note: dbt-colibri API may vary - this is a placeholder implementation
        # We'll need to adjust based on actual dbt-colibri API
        lineage_data = extract_lineage(
            manifest=manifest,
            catalog=catalog,
            model_unique_id=model_unique_id,
            upstream=True,  # Get upstream lineage
            table_level=True,  # Table-level (not column-level)
        )

        # Transform dbt-colibri output to our format
        return _transform_lineage_data(lineage_data, model_unique_id)

    except FileNotFoundError:
        raise
    except Exception as e:
        raise LineageError(f"Failed to extract lineage: {str(e)}") from e


def _transform_lineage_data(
    lineage_data: dict[str, Any],
    root_model_id: str,
) -> dict[str, Any]:
    """
    Transform dbt-colibri lineage output to frontend-friendly format.

    Args:
        lineage_data: Raw lineage data from dbt-colibri
        root_model_id: The root model unique_id

    Returns:
        Transformed lineage data with nodes, edges, and metadata
    """
    # This is a placeholder - actual transformation depends on dbt-colibri output format
    # We'll need to adjust based on actual API

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    node_map: dict[str, dict[str, Any]] = {}

    # Extract nodes and edges from lineage_data
    # Assuming lineage_data has structure like:
    # {
    #   "nodes": [...],
    #   "edges": [...],
    #   "sources": [...]
    # }

    lineage_nodes = lineage_data.get("nodes", [])
    lineage_edges = lineage_data.get("edges", [])
    sources = lineage_data.get("sources", [])

    # Build source set for quick lookup
    source_set = set(sources) if sources else set()

    # Calculate depth/level for each node using BFS from root
    levels = _calculate_node_levels(lineage_edges, root_model_id)

    # Create nodes
    for node_id in lineage_nodes:
        node_info = _get_node_info(node_id, source_set, levels, root_model_id)
        nodes.append(node_info)
        node_map[node_id] = node_info

    # Create edges
    for edge in lineage_edges:
        source_id = edge.get("source")
        target_id = edge.get("target")
        if source_id in node_map and target_id in node_map:
            source_level = node_map[source_id]["level"]
            edges.append({
                "source": source_id,
                "target": target_id,
                "level": source_level,  # Use source level
            })

    # Calculate model counts per level
    level_counts = {}
    for node in nodes:
        level = node["level"]
        level_counts[level] = level_counts.get(level, 0) + 1

    return {
        "nodes": nodes,
        "edges": edges,
        "metadata": {
            "root_model_id": root_model_id,
            "level_counts": level_counts,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
        },
    }


def _calculate_node_levels(
    edges: list[dict[str, Any]],
    root_id: str,
) -> dict[str, int]:
    """
    Calculate depth/level for each node using BFS from root.

    Level 0 = root model
    Level 1 = direct dependencies
    Level 2 = dependencies of level 1, etc.
    """
    levels: dict[str, int] = {root_id: 0}

    # Build adjacency list (reverse: target -> sources)
    # For upstream lineage, we want to traverse from root to sources
    adjacency: dict[str, list[str]] = {}
    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")
        if source and target:
            if target not in adjacency:
                adjacency[target] = []
            adjacency[target].append(source)

    # BFS from root
    queue = deque([root_id])
    visited = {root_id}

    while queue:
        current = queue.popleft()
        current_level = levels[current]

        # Process upstream nodes (sources of current)
        for upstream in adjacency.get(current, []):
            if upstream not in visited:
                visited.add(upstream)
                levels[upstream] = current_level + 1
                queue.append(upstream)

    return levels


def _get_node_info(
    node_id: str,
    source_set: set[str],
    levels: dict[str, int],
    root_model_id: str,
) -> dict[str, Any]:
    """
    Get node information for lineage visualization.

    Args:
        node_id: Unique ID of the node
        source_set: Set of source node IDs
        levels: Dictionary mapping node_id to level
        root_model_id: Root model unique_id

    Returns:
        Node info dictionary
    """
    # Extract model name from unique_id (e.g., "model.project.name" -> "name")
    parts = node_id.split(".")
    label = parts[-1] if parts else node_id

    # Determine if this is a source table
    is_source = node_id in source_set or node_id.startswith("source.")

    # Get level (distance from root)
    level = levels.get(node_id, 0)

    return {
        "id": node_id,
        "label": label,
        "level": level,
        "isSource": is_source,
    }

