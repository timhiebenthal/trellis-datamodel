"""
Lineage extraction service.

Turns the active framework's raw upstream graph, obtained from the adapter, into
the layered node/edge shape the lineage view renders. Everything here is
framework-neutral: level calculation, layer assignment against the configured
`lineage.layers`, and per-level counts. Which model depends on which is the
adapter's business.
"""

import logging
from collections import deque
from collections.abc import Iterable, Mapping
from typing import Any

from trellis_datamodel import config as cfg
from trellis_datamodel.adapters import get_adapter
from trellis_datamodel.adapters.base import LineageGraph, LineageNode
from trellis_datamodel.exceptions import DomainError, FileOperationError, NotFoundError

logger = logging.getLogger(__name__)


class LineageError(DomainError):
    """Error during lineage extraction."""

    pass


def extract_upstream_lineage(model_unique_id: str) -> dict[str, Any]:
    """
    Extract upstream table-level lineage for a given model.

    Args:
        model_unique_id: Framework-native identifier of the model
            (e.g., "model.project.model_name")

    Returns:
        Dictionary with:
        - nodes: List of lineage nodes with id, label, level, isSource
        - edges: List of edges with source, target, level
        - metadata: Additional metadata including model counts per level

    Raises:
        LineageError: If lineage extraction fails
        FileOperationError: If the framework's metadata is missing
        NotFoundError: If the model is not part of the project
    """
    try:
        graph = get_adapter().get_lineage(model_unique_id)
    except (FileNotFoundError, FileOperationError, NotFoundError):
        raise
    except Exception as e:
        raise LineageError(f"Failed to extract lineage: {str(e)}") from e

    return _transform_lineage_data(graph, model_unique_id)


def extract_source_systems_for_model(model_unique_id: str) -> list[str]:
    """
    Extract unique source system names from upstream lineage.

    Args:
        model_unique_id: Framework-native identifier of the model

    Returns:
        List of unique source-name values (e.g., ["salesforce_prod",
        "postgres_warehouse"]). Empty rather than raising: this feeds optional
        display and must never break a response.
    """
    try:
        return get_adapter().get_source_systems_for_model(model_unique_id)
    except Exception as e:
        logger.warning(
            "Failed to extract source systems for model %s: %s", model_unique_id, e
        )
        return []


def extract_source_systems_for_models(
    model_unique_ids: Iterable[str],
) -> dict[str, list[str]]:
    """Extract source systems for multiple models in one adapter pass.

    The adapter owns framework-specific graph loading and traversal.  This
    service function keeps the batch contract framework-neutral and returns
    entries in the first-seen order of ``model_unique_ids``.  Duplicate model
    IDs therefore share one result and never trigger duplicate adapter work.
    """
    ordered_model_ids = list(dict.fromkeys(model_unique_ids))
    if not ordered_model_ids:
        return {}

    try:
        adapter = get_adapter()
        batch_method = getattr(adapter, "get_source_systems_for_models", None)
        if callable(batch_method):
            batch_result = batch_method(ordered_model_ids)
            if not isinstance(batch_result, Mapping):
                raise TypeError("batch source-system result must be a mapping")
            return {
                model_id: list(batch_result.get(model_id, ()))
                for model_id in ordered_model_ids
            }

        # Keep third-party adapters that predate the batch contract usable.
        return {
            model_id: adapter.get_source_systems_for_model(model_id)
            for model_id in ordered_model_ids
        }
    except Exception as e:
        logger.warning("Failed to extract source systems for models: %s", e)
        return {model_id: [] for model_id in ordered_model_ids}


def _transform_lineage_data(
    graph: LineageGraph,
    root_model_id: str,
) -> dict[str, Any]:
    """
    Transform an adapter's raw lineage graph into the frontend's format.

    Args:
        graph: Nodes and edges from the adapter
        root_model_id: The root model unique_id

    Returns:
        Transformed lineage data with nodes, edges, and metadata
    """
    graph_nodes = graph.get("nodes", [])
    graph_edges = graph.get("edges", [])

    # Calculate depth/level for each node using BFS from root
    levels = _calculate_node_levels(graph_edges, root_model_id)

    nodes: list[dict[str, Any]] = []
    node_map: dict[str, dict[str, Any]] = {}
    for graph_node in graph_nodes:
        node_info = _get_node_info(graph_node, levels)
        nodes.append(node_info)
        node_map[graph_node["unique_id"]] = node_info

    edges: list[dict[str, Any]] = []
    for edge in graph_edges:
        source_id = edge.get("source")
        target_id = edge.get("target")
        if source_id in node_map and target_id in node_map:
            edges.append(
                {
                    "source": source_id,
                    "target": target_id,
                    "level": node_map[source_id]["level"],  # Use source level
                }
            )

    # Calculate model counts per level
    level_counts: dict[int, int] = {}
    for node in nodes:
        level = node["level"]
        level_counts[level] = level_counts.get(level, 0) + 1

    metadata: dict[str, Any] = {
        "root_model_id": root_model_id,
        "level_counts": level_counts,
        "total_nodes": len(nodes),
        "total_edges": len(edges),
    }

    # Include configured layers in metadata if layers are configured
    if cfg.LINEAGE_LAYERS:
        metadata["lineage_layers"] = cfg.LINEAGE_LAYERS

    return {
        "nodes": nodes,
        "edges": edges,
        "metadata": metadata,
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
            adjacency.setdefault(target, []).append(source)

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
    node: LineageNode,
    levels: dict[str, int],
) -> dict[str, Any]:
    """
    Shape one lineage node for visualization.

    Args:
        node: Node as reported by the adapter
        levels: Dictionary mapping unique_id to level

    Returns:
        Node info dictionary
    """
    unique_id = node["unique_id"]
    is_source = node["is_source"]

    result: dict[str, Any] = {
        "id": unique_id,
        "label": node.get("name") or unique_id.split(".")[-1],
        "level": levels.get(unique_id, 0),
        "isSource": is_source,
    }

    # Add source-name if this is a source node
    if node.get("source_name") is not None:
        result["sourceName"] = node["source_name"]

    # Assign layer based on the folder the model lives in. Only when layers are
    # configured, so a project that never opted in keeps its flat lineage.
    lineage_layers = cfg.LINEAGE_LAYERS
    if is_source:
        # Sources always get "sources" layer
        result["layer"] = "sources"
    elif lineage_layers:
        folder = node.get("folder")
        result["layer"] = folder if folder in lineage_layers else "unassigned"

    if not lineage_layers:
        result.pop("layer", None)

    return result
