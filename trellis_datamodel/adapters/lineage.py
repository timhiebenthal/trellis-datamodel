"""Upstream lineage walk shared across transformation-framework adapters."""

from collections import deque
from typing import Callable, Iterable


def walk_upstream(
    root: str,
    upstreams_of: Callable[[str], Iterable[str]],
    should_expand: Callable[[str], bool],
) -> tuple[set[str], list[dict[str, str]]]:
    """Breadth-first walk from ``root`` back through its dependencies.

    Args:
        root: Identifier of the starting node.
        upstreams_of: Identifiers a node depends on. Called once per expanded node.
        should_expand: Whether a newly reached node's own upstreams are walked.
            Returning False makes it a leaf (e.g. a dbt source or ingestion asset).

    Returns:
        ``(node_ids, edges)``, where each edge is ``{"source": upstream,
        "target": dependent}``. An edge is emitted for every dependency listed,
        even when the upstream was already visited.
    """
    node_ids: set[str] = {root}
    edges: list[dict[str, str]] = []
    queue = deque([root])
    visited = {root}

    while queue:
        current = queue.popleft()
        for upstream in upstreams_of(current):
            edges.append({"source": upstream, "target": current})
            node_ids.add(upstream)
            if upstream not in visited:
                visited.add(upstream)
                if should_expand(upstream):
                    queue.append(upstream)

    return node_ids, edges
