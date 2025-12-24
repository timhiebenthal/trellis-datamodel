"""
Lineage extraction service.

Extracts table-level upstream lineage from dbt manifest.json and catalog.json files.
Uses native manifest parsing (primary) with optional dbt-colibri support.
"""

import json
import os
from typing import Any, Optional
from collections import deque

try:
    from dbt_colibri import extract_lineage as colibri_extract_lineage
    COLIBRI_AVAILABLE = True
except ImportError:
    COLIBRI_AVAILABLE = False


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
    # Validate manifest exists
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"Manifest not found at {manifest_path}")

    try:
        # Load manifest
        with open(manifest_path, "r") as f:
            manifest = json.load(f)

        # Load catalog if available (optional)
        catalog = None
        if catalog_path and os.path.exists(catalog_path):
            with open(catalog_path, "r") as f:
                catalog = json.load(f)

        # Verify model exists in manifest
        nodes = manifest.get("nodes", {})
        if model_unique_id not in nodes:
            # Check if it's a versioned model issue
            model_name = model_unique_id.split(".")[-1] if "." in model_unique_id else model_unique_id
            matching_models = [
                uid for uid in nodes.keys()
                if uid.endswith(f".{model_name}") or uid.endswith(f".{model_name}.v")
            ]
            if matching_models:
                raise LineageError(
                    f"Model '{model_unique_id}' not found in manifest. "
                    f"Found similar models: {', '.join(matching_models[:3])}"
                )
            raise LineageError(
                f"Model '{model_unique_id}' not found in manifest. "
                f"Available models: {len([n for n in nodes.values() if n.get('resource_type') == 'model'])} model(s)"
            )

        # Extract lineage using native manifest parsing
        # This works without dbt-colibri by traversing depends_on relationships
        lineage_data = _extract_lineage_from_manifest(manifest, model_unique_id)

        # Transform to our format
        return _transform_lineage_data(lineage_data, model_unique_id)

    except FileNotFoundError:
        raise
    except Exception as e:
        raise LineageError(f"Failed to extract lineage: {str(e)}") from e


def _extract_lineage_from_manifest(
    manifest: dict[str, Any],
    root_model_id: str,
) -> dict[str, Any]:
    """
    Extract upstream lineage directly from manifest.json.
    
    Traverses depends_on relationships to build upstream lineage graph.
    
    Args:
        manifest: Parsed manifest.json dictionary
        root_model_id: Starting model unique_id
        
    Returns:
        Dictionary with nodes (list of unique_ids) and edges (list of {source, target})
    """
    nodes = manifest.get("nodes", {})
    sources = manifest.get("sources", {})
    
    # Track all nodes in lineage
    lineage_node_ids: set[str] = {root_model_id}
    lineage_edges: list[dict[str, str]] = []
    
    def _is_intermediate_model_only_sources(model_id: str) -> bool:
        """Check if a model only depends on sources (no other models)."""
        model_node = nodes.get(model_id)
        if not model_node:
            return False
            
        depends_on = model_node.get("depends_on")
        if not depends_on:
            return False
            
        if isinstance(depends_on, dict):
            upstream_nodes = depends_on.get("nodes", [])
        elif isinstance(depends_on, list):
            upstream_nodes = depends_on
        else:
            upstream_nodes = []
        
        # Check if all dependencies are sources
        for upstream_id in upstream_nodes:
            if upstream_id.startswith("model."):
                return False  # Has at least one model dependency
        return len(upstream_nodes) > 0  # Has dependencies and they're all sources
    
    # BFS to find all upstream dependencies
    queue = deque([root_model_id])
    visited = {root_model_id}
    
    while queue:
        current_id = queue.popleft()
        current_node = nodes.get(current_id)
        
        if not current_node:
            continue
            
        # Get upstream dependencies
        depends_on = current_node.get("depends_on")
        if not depends_on:
            continue
            
        # Handle both dict and list formats
        if isinstance(depends_on, dict):
            upstream_nodes = depends_on.get("nodes", [])
        elif isinstance(depends_on, list):
            upstream_nodes = depends_on
        else:
            upstream_nodes = []
        
        for upstream_id in upstream_nodes:
            # Check if this is an intermediate model that only connects to sources
            if upstream_id.startswith("model.") and _is_intermediate_model_only_sources(upstream_id):
                # Skip this intermediate model, connect its sources directly to current
                upstream_node = nodes.get(upstream_id)
                if upstream_node:
                    upstream_depends_on = upstream_node.get("depends_on")
                    if upstream_depends_on:
                        if isinstance(upstream_depends_on, dict):
                            source_deps = upstream_depends_on.get("nodes", [])
                        elif isinstance(upstream_depends_on, list):
                            source_deps = upstream_depends_on
                        else:
                            source_deps = []
                        
                        # Connect sources directly to current (skipping intermediate model)
                        for source_id in source_deps:
                            if source_id.startswith("source."):
                                lineage_edges.append({
                                    "source": source_id,
                                    "target": current_id,
                                })
                                lineage_node_ids.add(source_id)
            else:
                # Normal dependency - add edge
                lineage_edges.append({
                    "source": upstream_id,
                    "target": current_id,
                })
                
                # Add upstream node to lineage
                lineage_node_ids.add(upstream_id)
                
                # Continue BFS if not visited
                if upstream_id not in visited:
                    visited.add(upstream_id)
                    # Only continue BFS for models (not sources)
                    if upstream_id.startswith("model."):
                        queue.append(upstream_id)
    
    # Identify source tables
    source_ids = set()
    for node_id in lineage_node_ids:
        if node_id.startswith("source."):
            source_ids.add(node_id)
        elif node_id in sources:
            source_ids.add(node_id)
    
    return {
        "nodes": list(lineage_node_ids),
        "edges": lineage_edges,
        "sources": list(source_ids),
    }


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
    # Structure:
    # {
    #   "nodes": [list of unique_ids],
    #   "edges": [list of {source, target}],
    #   "sources": [list of source unique_ids]
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

    # Extract source-name for source nodes
    # Source IDs follow format: source.project.source_name.table_name
    source_name = None
    if is_source and len(parts) >= 3:
        source_name = parts[2]  # Third part is the source-name

    # Get level (distance from root)
    level = levels.get(node_id, 0)

    result = {
        "id": node_id,
        "label": label,
        "level": level,
        "isSource": is_source,
    }
    
    # Add source-name if this is a source node
    if source_name is not None:
        result["sourceName"] = source_name

    return result

