"""
Bus Matrix service for dimensional modeling.

Handles computation of bus matrix showing dimension-fact connections.
The bus matrix is a dimensional modeling concept that shows which dimensions
are connected to which facts through relationships.

This service:
- Filters entities by entity_type (dimension/fact)
- Builds connections from relationships in the data model
- Supports filtering by dimension_id, fact_id, and tags
- Returns sorted results for consistent display

Only available when modeling_style is set to "dimensional_model" in trellis.yml.
"""

import os
from typing import Any

import yaml

from trellis_datamodel import config as cfg
from trellis_datamodel.exceptions import ConfigurationError, FileOperationError


def get_bus_matrix(
    dimension_id: str | None = None,
    fact_id: str | None = None,
    tag: str | None = None,
) -> dict[str, Any]:
    """
    Return Bus Matrix data showing dimension-fact connections.

    Args:
        dimension_id: Optional filter by specific dimension entity ID
        fact_id: Optional filter by specific fact entity ID
        tag: Optional filter by tag (entities must have this tag)

    Returns:
        Dictionary containing dimensions, facts, and their connections

    Raises:
        ConfigurationError: If bus matrix is disabled or data model path not configured
        FileOperationError: If data model file cannot be read
    """
    # Bus Matrix is only available in dimensional modeling mode
    if cfg.MODELING_STYLE != "dimensional_model" or not cfg.Bus_MATRIX_ENABLED:
        raise ConfigurationError("Bus Matrix is disabled for entity_model")

    if not cfg.DATA_MODEL_PATH:
        raise ConfigurationError(
            "data_model_file is not configured. Set it in trellis.yml to use the Bus Matrix."
        )
    if not os.path.exists(cfg.DATA_MODEL_PATH):
        raise FileOperationError(
            f"Data model file not found at {cfg.DATA_MODEL_PATH}. "
            "Run 'trellis init' or point data_model_file to an existing data_model.yml."
        )

    try:
        with open(cfg.DATA_MODEL_PATH, "r") as f:
            data_model = yaml.safe_load(f) or {}
    except Exception as e:
        raise FileOperationError(f"Error reading data model: {str(e)}") from e

    entities = data_model.get("entities", [])
    relationships = data_model.get("relationships", [])

    # Filter dimensions and facts - include unclassified entities for now
    dimensions = [
        e for e in entities if e.get("entity_type") in ["dimension", "unclassified"]
    ]
    facts = [e for e in entities if e.get("entity_type") in ["fact", "unclassified"]]

    # Apply tag filter if specified
    if tag:
        dimensions = [d for d in dimensions if tag in (d.get("tags") or [])]
        facts = [f for f in facts if tag in (f.get("tags") or [])]

    # Apply entity ID filters
    if dimension_id:
        dimensions = [d for d in dimensions if d.get("id") == dimension_id]
    if fact_id:
        facts = [f for f in facts if f.get("id") == fact_id]

    # Build connections from relationships
    # A connection exists when a dimension has a relationship to a fact
    connections = []
    dimension_ids = {d.get("id") for d in dimensions}
    fact_ids = {f.get("id") for f in facts}

    for rel in relationships:
        source = rel.get("source")
        target = rel.get("target")

        # Check if this relationship connects a dimension to a fact
        # Direction doesn't matter - we just want to know they're connected
        if source in dimension_ids and target in fact_ids:
            connections.append({"dimension_id": source, "fact_id": target})
        elif source in fact_ids and target in dimension_ids:
            connections.append({"dimension_id": target, "fact_id": source})

    # Remove duplicate connections (same dimension-fact pair)
    seen = set()
    unique_connections = []
    for conn in connections:
        key = (conn["dimension_id"], conn["fact_id"])
        if key not in seen:
            seen.add(key)
            unique_connections.append(conn)

    # Sort alphabetically for consistent display
    dimensions.sort(key=lambda x: x.get("id", ""))
    facts.sort(key=lambda x: x.get("id", ""))
    unique_connections.sort(key=lambda x: (x["dimension_id"], x["fact_id"]))

    return {
        "dimensions": dimensions,
        "facts": facts,
        "connections": unique_connections,
    }
