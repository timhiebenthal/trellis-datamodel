"""Routes for BUS Matrix operations."""

from fastapi import APIRouter, HTTPException, Query
import os
from typing import List

from trellis_datamodel import config as cfg
from trellis_datamodel.adapters import get_adapter

router = APIRouter(prefix="/api", tags=["bus-matrix"])


@router.get("/bus-matrix")
async def get_bus_matrix(
    dimension_id: str | None = Query(default=None, description="Filter by specific dimension entity ID"),
    fact_id: str | None = Query(default=None, description="Filter by specific fact entity ID"),
    tag: str | None = Query(default=None, description="Filter by tag (entities must have this tag)")
):
    """
    Return BUS Matrix data showing dimension-fact connections.

    Returns:
        Dictionary containing dimensions, facts, and their connections.
        - dimensions: List of dimension entities with entity_type == "dimension"
        - facts: List of fact entities with entity_type == "fact"
        - connections: List of dimension-fact connections derived from relationships
    """
    try:
        if not cfg.DATA_MODEL_PATH or not os.path.exists(cfg.DATA_MODEL_PATH):
            return {"dimensions": [], "facts": [], "connections": []}

        import yaml
        with open(cfg.DATA_MODEL_PATH, "r") as f:
            data_model = yaml.safe_load(f) or {}

        entities = data_model.get("entities", [])
        relationships = data_model.get("relationships", [])

        # Filter dimensions and facts
        dimensions = [e for e in entities if e.get("entity_type") == "dimension"]
        facts = [e for e in entities if e.get("entity_type") == "fact"]

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
                connections.append({
                    "dimension_id": source,
                    "fact_id": target
                })
            elif source in fact_ids and target in dimension_ids:
                connections.append({
                    "dimension_id": target,
                    "fact_id": source
                })

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
            "connections": unique_connections
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Error building BUS Matrix: {str(e)}"
        )

