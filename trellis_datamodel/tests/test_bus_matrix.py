"""Tests for Bus Matrix endpoint."""

import pytest
import yaml
from pathlib import Path

from trellis_datamodel.services.bus_matrix import get_bus_matrix
from trellis_datamodel.exceptions import ConfigurationError, FileOperationError
import trellis_datamodel.config as cfg


@pytest.fixture
def sample_data_model(temp_data_model_path):
    """Create a sample data model with dimensions, facts, and relationships."""
    data = {
        "version": 0.1,
        "entities": [
            {
                "id": "dim_customer",
                "name": "Customer Dimension",
                "entity_type": "dimension",
                "tags": ["core", "crm"],
            },
            {
                "id": "dim_product",
                "name": "Product Dimension",
                "entity_type": "dimension",
                "tags": ["core"],
            },
            {
                "id": "dim_date",
                "name": "Date Dimension",
                "entity_type": "dimension",
                "tags": ["utility"],
            },
            {
                "id": "fct_orders",
                "name": "Orders Fact",
                "entity_type": "fact",
                "tags": ["core"],
            },
            {
                "id": "fct_sales",
                "name": "Sales Fact",
                "entity_type": "fact",
                "tags": ["core", "revenue"],
            },
            {
                "id": "unclassified_entity",
                "name": "Some Entity",
                "entity_type": "unclassified",
                "tags": ["other"],
            },
        ],
        "relationships": [
            {"source": "dim_customer", "target": "fct_orders", "type": "one-to-many"},
            {"source": "dim_product", "target": "fct_orders", "type": "one-to-many"},
            {"source": "fct_sales", "target": "dim_customer", "type": "many-to-one"},
            {"source": "dim_product", "target": "fct_sales", "type": "one-to-many"},
            {"source": "dim_date", "target": "fct_orders", "type": "one-to-many"},
            # Dimension-to-dimension relationship (should be ignored)
            {"source": "dim_customer", "target": "dim_product", "type": "one-to-many"},
        ],
    }
    with open(temp_data_model_path, "w") as f:
        yaml.dump(data, f)
    return temp_data_model_path


@pytest.fixture
def enable_bus_matrix(monkeypatch):
    """Enable bus matrix for dimensional modeling."""
    monkeypatch.setattr(cfg, "MODELING_STYLE", "dimensional_model")
    monkeypatch.setattr(cfg, "Bus_MATRIX_ENABLED", True)


class TestBusMatrixEndpoint:
    """Test Bus Matrix API endpoint."""

    def test_basic_data_retrieval(self, sample_data_model, enable_bus_matrix):
        """Test basic Bus Matrix data retrieval (no filters)."""
        result = get_bus_matrix()

        # Should return structure with dimensions, facts, and connections
        assert "dimensions" in result
        assert "facts" in result
        assert "connections" in result
        assert isinstance(result["dimensions"], list)
        assert isinstance(result["facts"], list)
        assert isinstance(result["connections"], list)

    def test_identifies_dimensions(self, sample_data_model, enable_bus_matrix):
        """Test that only entities with entity_type == 'dimension' are returned."""
        result = get_bus_matrix()

        dimension_ids = {d["id"] for d in result["dimensions"]}
        assert dimension_ids == {"dim_customer", "dim_product", "dim_date"}
        assert len(result["dimensions"]) == 3

    def test_identifies_facts(self, sample_data_model, enable_bus_matrix):
        """Test that only entities with entity_type == 'fact' are returned."""
        result = get_bus_matrix()

        fact_ids = {f["id"] for f in result["facts"]}
        assert fact_ids == {"fct_orders", "fct_sales"}
        assert len(result["facts"]) == 2

    def test_detects_connections(self, sample_data_model, enable_bus_matrix):
        """Test correct connection detection."""
        result = get_bus_matrix()

        # Should parse relationships from data model and build connections
        connections = result["connections"]
        assert len(connections) > 0

        # Verify specific connections exist
        connection_pairs = {
            (c["dimension_id"], c["fact_id"]) for c in connections
        }
        assert ("dim_customer", "fct_orders") in connection_pairs
        assert ("dim_product", "fct_orders") in connection_pairs
        assert ("dim_customer", "fct_sales") in connection_pairs
        assert ("dim_product", "fct_sales") in connection_pairs
        assert ("dim_date", "fct_orders") in connection_pairs

    def test_dimension_filtering(self, sample_data_model, enable_bus_matrix):
        """Test filtering by dimension_id."""
        result = get_bus_matrix(dimension_id="dim_customer")

        # Should only return dim_customer
        assert len(result["dimensions"]) == 1
        assert result["dimensions"][0]["id"] == "dim_customer"

        # Should only return connections involving dim_customer
        for conn in result["connections"]:
            assert conn["dimension_id"] == "dim_customer"

    def test_fact_filtering(self, sample_data_model, enable_bus_matrix):
        """Test filtering by fact_id."""
        result = get_bus_matrix(fact_id="fct_orders")

        # Should only return fct_orders
        assert len(result["facts"]) == 1
        assert result["facts"][0]["id"] == "fct_orders"

        # Should only return connections involving fct_orders
        for conn in result["connections"]:
            assert conn["fact_id"] == "fct_orders"

    def test_tag_filtering(self, sample_data_model, enable_bus_matrix):
        """Test filtering by tag."""
        result = get_bus_matrix(tag="core")

        # Should only return entities with "core" tag
        for dim in result["dimensions"]:
            assert "core" in dim.get("tags", [])
        for fact in result["facts"]:
            assert "core" in fact.get("tags", [])

    def test_tag_filtering_uses_computed_union_for_bound_entities(
        self, temp_data_model_path, enable_bus_matrix
    ):
        """A bound dimension's tags for filtering/display are the union of
        dbt_tags and ui_tags — never a persisted `tags` field."""
        data = {
            "version": 0.1,
            "entities": [
                {
                    "id": "dim_bound",
                    "entity_type": "dimension",
                    "dbt_model": "model.proj.dim_bound",
                    "dbt_tags": ["nightly"],
                    "ui_tags": ["pii"],
                },
                {
                    "id": "fct_unrelated",
                    "entity_type": "fact",
                    "tags": ["other"],
                },
            ],
            "relationships": [],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data, f)

        result = get_bus_matrix(tag="pii")
        assert [d["id"] for d in result["dimensions"]] == ["dim_bound"]
        assert result["dimensions"][0]["tags"] == ["nightly", "pii"]

        result_nightly = get_bus_matrix(tag="nightly")
        assert [d["id"] for d in result_nightly["dimensions"]] == ["dim_bound"]

    def test_multiple_connections(self, sample_data_model, enable_bus_matrix):
        """Test handling of multiple connections between same dimension and fact."""
        # Add duplicate relationship to data model
        with open(cfg.DATA_MODEL_PATH, "r") as f:
            data = yaml.safe_load(f)

        data["relationships"].append(
            {"source": "dim_customer", "target": "fct_orders", "type": "one-to-many"}
        )

        with open(cfg.DATA_MODEL_PATH, "w") as f:
            yaml.dump(data, f)

        result = get_bus_matrix()

        # Should deduplicate connections
        connection_pairs = [
            (c["dimension_id"], c["fact_id"]) for c in result["connections"]
        ]
        # Count occurrences of the duplicate connection
        count = connection_pairs.count(("dim_customer", "fct_orders"))
        assert count == 1, "Duplicate connections should be removed"

    def test_sorted_results(self, sample_data_model, enable_bus_matrix):
        """Test that results are sorted alphabetically."""
        result = get_bus_matrix()

        # Dimensions should be sorted by id
        dimension_ids = [d["id"] for d in result["dimensions"]]
        assert dimension_ids == sorted(dimension_ids)

        # Facts should be sorted by id
        fact_ids = [f["id"] for f in result["facts"]]
        assert fact_ids == sorted(fact_ids)

        # Connections should be sorted by dimension_id, then fact_id
        connections = result["connections"]
        for i in range(len(connections) - 1):
            curr = (connections[i]["dimension_id"], connections[i]["fact_id"])
            next_conn = (connections[i + 1]["dimension_id"], connections[i + 1]["fact_id"])
            assert curr <= next_conn

    def test_empty_data_model(self, temp_data_model_path, enable_bus_matrix, monkeypatch):
        """Test behavior with empty data model."""
        # Create empty data model
        data = {"version": 0.1, "entities": [], "relationships": []}
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data, f)

        monkeypatch.setattr(cfg, "DATA_MODEL_PATH", temp_data_model_path)

        result = get_bus_matrix()

        # Should return empty arrays
        assert result["dimensions"] == []
        assert result["facts"] == []
        assert result["connections"] == []

    def test_no_dimensions_or_facts(self, temp_data_model_path, enable_bus_matrix, monkeypatch):
        """Test that unclassified-only data model returns empty dimensions and facts."""
        # Create data model with only unclassified entities
        data = {
            "version": 0.1,
            "entities": [
                {
                    "id": "entity1",
                    "name": "Entity 1",
                    "entity_type": "unclassified",
                },
                {
                    "id": "entity2",
                    "name": "Entity 2",
                    "entity_type": "unclassified",
                },
            ],
            "relationships": [],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data, f)

        monkeypatch.setattr(cfg, "DATA_MODEL_PATH", temp_data_model_path)

        result = get_bus_matrix()

        assert result["dimensions"] == []
        assert result["facts"] == []

    def test_reverse_direction_connections(self, temp_data_model_path, enable_bus_matrix, monkeypatch):
        """Test connections work regardless of direction."""
        # Create data model with relationships in different directions
        data = {
            "version": 0.1,
            "entities": [
                {"id": "dim_a", "name": "Dimension A", "entity_type": "dimension"},
                {"id": "fct_b", "name": "Fact B", "entity_type": "fact"},
            ],
            "relationships": [
                # Dimension -> Fact
                {"source": "dim_a", "target": "fct_b", "type": "one-to-many"},
            ],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data, f)

        monkeypatch.setattr(cfg, "DATA_MODEL_PATH", temp_data_model_path)

        result1 = get_bus_matrix()
        assert len(result1["connections"]) == 1
        assert result1["connections"][0]["dimension_id"] == "dim_a"
        assert result1["connections"][0]["fact_id"] == "fct_b"

        # Now reverse the direction: Fact -> Dimension
        data["relationships"] = [
            {"source": "fct_b", "target": "dim_a", "type": "many-to-one"}
        ]
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data, f)

        result2 = get_bus_matrix()
        # Should still detect the connection (direction doesn't matter)
        assert len(result2["connections"]) == 1
        assert result2["connections"][0]["dimension_id"] == "dim_a"
        assert result2["connections"][0]["fact_id"] == "fct_b"

    def test_unclassified_entities_ignored(self, sample_data_model, enable_bus_matrix):
        """Test that unclassified entities are excluded from Bus Matrix dimensions and facts."""
        result = get_bus_matrix()

        dimension_ids = {d["id"] for d in result["dimensions"]}
        fact_ids = {f["id"] for f in result["facts"]}

        assert "unclassified_entity" not in dimension_ids
        assert "unclassified_entity" not in fact_ids

    def test_connections_only_between_dimension_and_fact(self, sample_data_model, enable_bus_matrix):
        """Test only dimension-fact connections included."""
        result = get_bus_matrix()

        # Verify dimension-to-dimension connection is not included
        # The sample data has dim_customer -> dim_product which should be ignored
        for conn in result["connections"]:
            dim_id = conn["dimension_id"]
            fact_id = conn["fact_id"]

            # Verify dimension_id is actually a dimension
            dimensions = {d["id"] for d in result["dimensions"]}
            assert dim_id in dimensions

            # Verify fact_id is actually a fact
            facts = {f["id"] for f in result["facts"]}
            assert fact_id in facts

    def test_disabled_bus_matrix_raises_error(self, sample_data_model, monkeypatch):
        """Test that disabled bus matrix raises ConfigurationError."""
        monkeypatch.setattr(cfg, "MODELING_STYLE", "entity_model")
        monkeypatch.setattr(cfg, "Bus_MATRIX_ENABLED", False)

        with pytest.raises(ConfigurationError) as exc_info:
            get_bus_matrix()

        assert "disabled" in str(exc_info.value).lower()

    def test_missing_data_model_file_raises_error(self, enable_bus_matrix, monkeypatch):
        """Test that missing data model file raises FileOperationError."""
        monkeypatch.setattr(cfg, "DATA_MODEL_PATH", "/nonexistent/path/data_model.yml")

        with pytest.raises(FileOperationError) as exc_info:
            get_bus_matrix()

        assert "not found" in str(exc_info.value).lower()

    def test_no_data_model_path_raises_error(self, enable_bus_matrix, monkeypatch):
        """Test that missing data_model_path config raises ConfigurationError."""
        monkeypatch.setattr(cfg, "DATA_MODEL_PATH", None)

        with pytest.raises(ConfigurationError) as exc_info:
            get_bus_matrix()

        assert "not configured" in str(exc_info.value).lower()


def test_bus_matrix_tag_source_for_bound_vs_unbound_entity(
    temp_data_model_path, enable_bus_matrix
):
    """A bound dimension's displayed tags are the union of its
    framework-mirrored tags and ui_tags; an unbound dimension's displayed
    tags are simply its own `tags` field."""
    from trellis_datamodel.tests._entity_compat import get_model_ref

    data = {
        "version": 0.1,
        "entities": [
            {
                "id": "dim_bound",
                "entity_type": "dimension",
                "dbt_model": "model.project.dim_bound",
                "dbt_tags": ["nightly", "core"],
                "ui_tags": ["pii"],
            },
            {
                "id": "dim_unbound",
                "entity_type": "dimension",
                "tags": ["draft-tag"],
            },
        ],
        "relationships": [],
    }
    with open(temp_data_model_path, "w") as f:
        yaml.dump(data, f)

    result = get_bus_matrix()

    bound = next(d for d in result["dimensions"] if d["id"] == "dim_bound")
    unbound = next(d for d in result["dimensions"] if d["id"] == "dim_unbound")

    assert get_model_ref(bound) == "model.project.dim_bound"
    assert bound["tags"] == ["nightly", "core", "pii"]

    assert get_model_ref(unbound) is None
    assert unbound["tags"] == ["draft-tag"]
