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
        # region agent log - Bus Matrix API entry
        import json
        log_data = {"location": "bus_matrix.py:29", "message": "BUS Matrix API called", "data": {"dimension_id": dimension_id, "fact_id": fact_id, "tag": tag}, "timestamp": 1736366400000, "sessionId": "debug-session", "hypothesisId": "A,E"}
        with open("/home/tim_ubuntu/git_repos/trellis-datamodel/.cursor/debug.log", "a") as log_file:
            log_file.write(json.dumps(log_data) + "\n")
        # endregion

        # region agent log - Check DATA_MODEL_PATH (Hypothesis A)
        log_data = {"location": "bus_matrix.py:33", "message": "Checking DATA_MODEL_PATH", "data": {"DATA_MODEL_PATH": cfg.DATA_MODEL_PATH, "exists": os.path.exists(cfg.DATA_MODEL_PATH) if cfg.DATA_MODEL_PATH else None}, "timestamp": 1736366400000, "sessionId": "debug-session", "hypothesisId": "A"}
        with open("/home/tim_ubuntu/git_repos/trellis-datamodel/.cursor/debug.log", "a") as log_file:
            log_file.write(json.dumps(log_data) + "\n")
        # endregion

        if not cfg.DATA_MODEL_PATH or not os.path.exists(cfg.DATA_MODEL_PATH):
            print("BUS Matrix: Data model path not found or doesn't exist")
            return {"dimensions": [], "facts": [], "connections": []}

        import yaml
        with open(cfg.DATA_MODEL_PATH, "r") as f:
            data_model = yaml.safe_load(f) or {}

        entities = data_model.get("entities", [])
        relationships = data_model.get("relationships", [])

        # region agent log - Loaded entities and relationships (Hypothesis B)
        log_data = {"location": "bus_matrix.py:43", "message": "Loaded data model", "data": {"num_entities": len(entities), "num_relationships": len(relationships), "first_entity": entities[0] if entities else None, "all_entity_types": [e.get("entity_type") for e in entities]}, "timestamp": 1736366400000, "sessionId": "debug-session", "hypothesisId": "B"}
        with open("/home/tim_ubuntu/git_repos/trellis-datamodel/.cursor/debug.log", "a") as log_file:
            log_file.write(json.dumps(log_data) + "\n")
        # endregion

        print(f"BUS Matrix: Loaded data model with {len(entities)} entities and {len(relationships)} relationships")

        # region agent log - Entity type filtering (Hypothesis C)
        entity_types = [e.get("entity_type") for e in entities]
        dimensions_before = [e for e in entities if e.get("entity_type") in ["dimension", "unclassified"]]
        facts_before = [e for e in entities if e.get("entity_type") in ["fact", "unclassified"]]
        log_data = {"location": "bus_matrix.py:46", "message": "Entity type filtering", "data": {"all_entity_types": entity_types, "dimensions_before": len(dimensions_before), "facts_before": len(facts_before)}, "timestamp": 1736366400000, "sessionId": "debug-session", "hypothesisId": "C"}
        with open("/home/tim_ubuntu/git_repos/trellis-datamodel/.cursor/debug.log", "a") as log_file:
            log_file.write(json.dumps(log_data) + "\n")
        # endregion

        # Filter dimensions and facts - include unclassified entities for now
        dimensions = [e for e in entities if e.get("entity_type") in ["dimension", "unclassified"]]
        facts = [e for e in entities if e.get("entity_type") in ["fact", "unclassified"]]
        print(f"BUS Matrix: Found {len(dimensions)} dimensions and {len(facts)} facts")

        # Apply tag filter if specified
        # region agent log - Tag filtering (Hypothesis D)
        if tag:
            log_data = {"location": "bus_matrix.py:51", "message": "Before tag filter", "data": {"tag": tag, "dimensions_before": len(dimensions), "facts_before": len(facts)}, "timestamp": 1736366400000, "sessionId": "debug-session", "hypothesisId": "D"}
            with open("/home/tim_ubuntu/git_repos/trellis-datamodel/.cursor/debug.log", "a") as log_file:
                log_file.write(json.dumps(log_data) + "\n")
        # endregion

        if tag:
            dimensions = [d for d in dimensions if tag in (d.get("tags") or [])]
            facts = [f for f in facts if tag in (f.get("tags") or [])]
            print(f"BUS Matrix: After tag filter: {len(dimensions)} dimensions, {len(facts)} facts")

            # region agent log - After tag filter (Hypothesis D)
            log_data = {"location": "bus_matrix.py:55", "message": "After tag filter", "data": {"dimensions_after": len(dimensions), "facts_after": len(facts)}, "timestamp": 1736366400000, "sessionId": "debug-session", "hypothesisId": "D"}
            with open("/home/tim_ubuntu/git_repos/trellis-datamodel/.cursor/debug.log", "a") as log_file:
                log_file.write(json.dumps(log_data) + "\n")
            # endregion

        # Apply entity ID filters
        if dimension_id:
            dimensions = [d for d in dimensions if d.get("id") == dimension_id]
        if fact_id:
            facts = [f for f in facts if f.get("id") == fact_id]
        print(f"BUS Matrix: After ID filters: {len(dimensions)} dimensions, {len(facts)} facts")

        # Build connections from relationships
        # A connection exists when a dimension has a relationship to a fact
        connections = []
        dimension_ids = {d.get("id") for d in dimensions}
        fact_ids = {f.get("id") for f in facts}

        print(f"BUS Matrix: Building connections - dimension IDs: {list(dimension_ids)[:3]}..., fact IDs: {list(fact_ids)[:3]}...")

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
                print(f"BUS Matrix: Found connection - dimension {source} -> fact {target}")
            elif source in fact_ids and target in dimension_ids:
                connections.append({
                    "dimension_id": target,
                    "fact_id": source
                })
                print(f"BUS Matrix: Found connection - dimension {target} -> fact {source}")

        # Remove duplicate connections (same dimension-fact pair)
        seen = set()
        unique_connections = []
        for conn in connections:
            key = (conn["dimension_id"], conn["fact_id"])
            if key not in seen:
                seen.add(key)
                unique_connections.append(conn)

        print(f"BUS Matrix: Found {len(unique_connections)} unique connections")

        # Sort alphabetically for consistent display
        dimensions.sort(key=lambda x: x.get("id", ""))
        facts.sort(key=lambda x: x.get("id", ""))
        unique_connections.sort(key=lambda x: (x["dimension_id"], x["fact_id"]))

        # Log sample data for debugging
        if len(dimensions) > 0:
            print(f"BUS Matrix: Sample dimensions: {[d.get('id') for d in dimensions[:2]]}...")
        if len(facts) > 0:
            print(f"BUS Matrix: Sample facts: {[f.get('id') for f in facts[:2]]}...")
        if len(unique_connections) > 0:
            sample_conns = [f"{c['dimension_id']}-{c['fact_id']}" for c in unique_connections[:2]]
            print(f"BUS Matrix: Sample connections: {sample_conns}...")

        # region agent log - Return data (Final check)
        log_data = {"location": "bus_matrix.py:113", "message": "Returning BUS Matrix data", "data": {"num_dimensions": len(dimensions), "num_facts": len(facts), "num_connections": len(unique_connections), "sample_dimensions": [{"id": d.get("id"), "entity_type": d.get("entity_type")} for d in dimensions[:2]], "sample_facts": [{"id": f.get("id"), "entity_type": f.get("entity_type")} for f in facts[:2]]}, "timestamp": 1736366400000, "sessionId": "debug-session", "hypothesisId": "FINAL"}
        with open("/home/tim_ubuntu/git_repos/trellis-datamodel/.cursor/debug.log", "a") as log_file:
            log_file.write(json.dumps(log_data) + "\n")
        # endregion

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

