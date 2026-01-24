"""Tests for entity generator service."""

import pytest
from unittest.mock import Mock
from datetime import datetime

from trellis_datamodel.services import entity_generator
from trellis_datamodel.models.business_event import (
    BusinessEvent,
    BusinessEventType,
    GeneratedEntitiesResult,
    BusinessEventAnnotations,
    AnnotationEntry,
)


class TestTextToSnakeCase:
    """Test _text_to_snake_case() helper function."""

    def test_converts_spaces_to_underscores(self):
        """Test that spaces are converted to underscores."""
        assert entity_generator._text_to_snake_case("customer name") == "customer_name"

    def test_converts_hyphens_to_underscores(self):
        """Test that hyphens are converted to underscores."""
        assert entity_generator._text_to_snake_case("customer-name") == "customer_name"

    def test_handles_special_characters(self):
        """Test that special characters are replaced with underscores."""
        assert (
            entity_generator._text_to_snake_case("customer@name#123")
            == "customer_name_123"
        )

    def test_handles_multiple_spaces(self):
        """Test that multiple spaces are collapsed to single underscore."""
        assert (
            entity_generator._text_to_snake_case("customer    name") == "customer_name"
        )

    def test_handles_mixed_case(self):
        """Test that text is lowercased."""
        assert entity_generator._text_to_snake_case("Customer Name") == "customer_name"

    def test_handles_numbers(self):
        """Test that numbers are preserved."""
        assert entity_generator._text_to_snake_case("customer123") == "customer123"

    def test_handles_empty_string(self):
        """Test that empty string returns 'entity'."""
        assert entity_generator._text_to_snake_case("") == "entity"

    def test_handles_only_special_chars(self):
        """Test that only special characters returns 'entity'."""
        assert entity_generator._text_to_snake_case("!!!") == "entity"

    def test_removes_leading_trailing_underscores(self):
        """Test that leading/trailing underscores are removed."""
        assert (
            entity_generator._text_to_snake_case("  customer name  ") == "customer_name"
        )


class TestTextToTitleCase:
    """Test _text_to_title_case() helper function."""

    def test_converts_snake_case_to_title_case(self):
        """Test that snake_case is converted to Title Case."""
        assert entity_generator._text_to_title_case("customer_name") == "Customer Name"

    def test_converts_spaces_to_title_case(self):
        """Test that space-separated words are capitalized."""
        assert entity_generator._text_to_title_case("customer name") == "Customer Name"

    def test_converts_hyphens_to_title_case(self):
        """Test that hyphen-separated words are capitalized."""
        assert entity_generator._text_to_title_case("customer-name") == "Customer Name"

    def test_handles_mixed_case(self):
        """Test that mixed case is normalized."""
        assert entity_generator._text_to_title_case("CuStOmEr NaMe") == "Customer Name"

    def test_handles_single_word(self):
        """Test that single word is capitalized."""
        assert entity_generator._text_to_title_case("customer") == "Customer"

    def test_handles_multiple_spaces(self):
        """Test that multiple spaces are handled."""
        assert (
            entity_generator._text_to_title_case("customer    name") == "Customer Name"
        )

    def test_handles_empty_string(self):
        """Test that empty string returns as-is."""
        assert entity_generator._text_to_title_case("") == ""

    def test_handles_numbers(self):
        """Test that numbers are preserved."""
        assert entity_generator._text_to_title_case("customer123") == "Customer123"


class TestGenerateEntitiesFromSevenWs:
    """Test generate_entities_from_event() with 7 Ws entries."""

    def test_generates_entities_from_annotations(self, monkeypatch):
        """Test that dimensions and fact are generated correctly from 7 Ws."""
        mock_config = Mock()
        mock_config.dimension_prefix = ["dim_"]
        mock_config.fact_prefix = ["fct_"]

        now = datetime.now()
        event = BusinessEvent(
            domain=None,
            id="evt_20260101_001",
            text="customer buys product",
            type=BusinessEventType.DISCRETE,
            created_at=now,
            updated_at=now,
            annotations=BusinessEventAnnotations(
                who=[AnnotationEntry(id="w1", text="customer", dimension_id=None, description=None, attributes={})],
                what=[AnnotationEntry(id="w2", text="product", dimension_id=None, description=None, attributes={})],
                when=[AnnotationEntry(id="w3", text="date", dimension_id=None, description=None, attributes={})],
                how_many=[AnnotationEntry(id="w4", text="quantity", dimension_id=None, description=None, attributes={})],
            ),
            derived_entities=[],
        )

        result = entity_generator.generate_entities_from_event(event, mock_config)

        assert len(result.entities) == 3
        assert len(result.errors) == 0

        # Check dimensions
        dim_entities = [e for e in result.entities if e["entity_type"] == "dimension"]
        assert len(dim_entities) == 2
        assert dim_entities[0]["id"] == "dim_customer"
        assert dim_entities[0]["metadata"]["annotation_type"] == "who"
        assert dim_entities[1]["id"] == "dim_product"
        assert dim_entities[1]["metadata"]["annotation_type"] == "what"

        # Check fact
        fact_entities = [e for e in result.entities if e["entity_type"] == "fact"]
        assert len(fact_entities) == 1
        assert fact_entities[0]["id"] == "fct_customer_buys_product"
        assert fact_entities[0]["metadata"]["event_type"] == "discrete"
        assert "drafted_fields" in fact_entities[0]
        assert fact_entities[0]["drafted_fields"][0]["name"] == "quantity"

    def test_creates_relationships_from_annotations(self, monkeypatch):
        """Test that all dimensions connect to fact."""
        mock_config = Mock()
        mock_config.dimension_prefix = ["dim_"]
        mock_config.fact_prefix = ["fct_"]

        now = datetime.now()
        event = BusinessEvent(
            domain=None,
            id="evt_20260101_001",
            text="customer buys product",
            type=BusinessEventType.DISCRETE,
            created_at=now,
            updated_at=now,
            annotations=BusinessEventAnnotations(
                who=[AnnotationEntry(id="w1", text="customer", dimension_id=None, description=None, attributes={})],
                what=[AnnotationEntry(id="w2", text="product", dimension_id=None, description=None, attributes={})],
                when=[AnnotationEntry(id="w3", text="date", dimension_id=None, description=None, attributes={})],
                how_many=[AnnotationEntry(id="w4", text="quantity", dimension_id=None, description=None, attributes={})],
            ),
            derived_entities=[],
        )

        result = entity_generator.generate_entities_from_event(event, mock_config)

        assert len(result.relationships) == 2
        assert result.relationships[0]["source"] == "dim_customer"
        assert result.relationships[0]["target"] == "fct_customer_buys_product"
        assert result.relationships[0]["type"] == "one_to_many"
        assert result.relationships[1]["source"] == "dim_product"
        assert result.relationships[1]["target"] == "fct_customer_buys_product"
        assert result.relationships[1]["type"] == "one_to_many"

    def test_requires_at_least_one_dimension(self, monkeypatch):
        """Test that missing dimension entries returns error."""
        mock_config = Mock()
        mock_config.dimension_prefix = ["dim_"]
        mock_config.fact_prefix = ["fct_"]

        now = datetime.now()
        event = BusinessEvent(
            domain=None,
            id="evt_20260101_001",
            text="test event",
            type=BusinessEventType.DISCRETE,
            created_at=now,
            updated_at=now,
            annotations=BusinessEventAnnotations(
                how_many=[AnnotationEntry(id="w1", text="quantity", dimension_id=None, description=None, attributes={})],
            ),
            derived_entities=[],
        )

        result = entity_generator.generate_entities_from_event(event, mock_config)

        assert len(result.entities) == 0
        assert len(result.errors) == 1
        assert "dimension" in result.errors[0].lower()

    def test_requires_at_least_one_how_many(self, monkeypatch):
        """Test that missing how_many entries returns error."""
        mock_config = Mock()
        mock_config.dimension_prefix = ["dim_"]
        mock_config.fact_prefix = ["fct_"]

        now = datetime.now()
        event = BusinessEvent(
            domain=None,
            id="evt_20260101_001",
            text="test event",
            type=BusinessEventType.DISCRETE,
            created_at=now,
            updated_at=now,
            annotations=BusinessEventAnnotations(
                who=[AnnotationEntry(id="w1", text="customer", dimension_id=None, description=None, attributes={})],
            ),
            derived_entities=[],
        )

        result = entity_generator.generate_entities_from_event(event, mock_config)

        assert len(result.entities) == 0
        assert len(result.errors) == 1
        assert "how many" in result.errors[0].lower()

    def test_handles_multiple_how_many_entries_as_drafted_fields(self, monkeypatch):
        """Test that multiple how_many entries become drafted fields."""
        mock_config = Mock()
        mock_config.dimension_prefix = ["dim_"]
        mock_config.fact_prefix = ["fct_"]

        now = datetime.now()
        event = BusinessEvent(
            domain=None,
            id="evt_20260101_001",
            text="customer buys product",
            type=BusinessEventType.DISCRETE,
            created_at=now,
            updated_at=now,
            annotations=BusinessEventAnnotations(
                who=[AnnotationEntry(id="w1", text="customer", dimension_id=None, description=None, attributes={})],
                what=[AnnotationEntry(id="w2", text="product", dimension_id=None, description=None, attributes={})],
                how_many=[
                    AnnotationEntry(id="w3", text="quantity", description="Items purchased", attributes={}),
                    AnnotationEntry(id="w4", text="amount", description="Total sales amount", attributes={}),
                ],
            ),
            derived_entities=[],
        )

        result = entity_generator.generate_entities_from_event(event, mock_config)

        assert len(result.entities) == 3

        # Check that fact has 2 drafted_fields
        fact_entities = [e for e in result.entities if e["entity_type"] == "fact"]
        assert len(fact_entities) == 1
        assert len(fact_entities[0]["drafted_fields"]) == 2
        assert fact_entities[0]["drafted_fields"][0]["name"] == "quantity"
        assert fact_entities[0]["drafted_fields"][0]["description"] == "Items purchased"
        assert fact_entities[0]["drafted_fields"][1]["name"] == "amount"
        assert fact_entities[0]["drafted_fields"][1]["description"] == "Total sales amount"

    def test_allows_all_dimension_w_types(self, monkeypatch):
        """Test that all 6 dimension W types (who, what, when, where, how, why) work."""
        mock_config = Mock()
        mock_config.dimension_prefix = ["dim_"]
        mock_config.fact_prefix = ["fct_"]

        now = datetime.now()
        event = BusinessEvent(
            domain=None,
            id="evt_20260101_001",
            text="customer buys product on date in store",
            type=BusinessEventType.DISCRETE,
            created_at=now,
            updated_at=now,
            annotations=BusinessEventAnnotations(
                who=[AnnotationEntry(id="w1", text="customer", dimension_id=None, description=None, attributes={})],
                what=[AnnotationEntry(id="w2", text="product", dimension_id=None, description=None, attributes={})],
                when=[AnnotationEntry(id="w3", text="date", dimension_id=None, description=None, attributes={})],
                where=[AnnotationEntry(id="w4", text="store", dimension_id=None, description=None, attributes={})],
                how=[AnnotationEntry(id="w5", text="online", dimension_id=None, description=None, attributes={})],
                why=[AnnotationEntry(id="w6", text="promotion", dimension_id=None, description=None, attributes={})],
                how_many=[AnnotationEntry(id="w7", text="quantity", dimension_id=None, description=None, attributes={})],
            ),
            derived_entities=[],
        )

        result = entity_generator.generate_entities_from_event(event, mock_config)

        assert len(result.entities) == 7

        # Check 6 dimensions (one for each W type)
        dim_entities = [e for e in result.entities if e["entity_type"] == "dimension"]
        assert len(dim_entities) == 6

        # Check annotation_type metadata is set correctly
        w_types = [e["metadata"]["annotation_type"] for e in dim_entities]
        assert set(w_types) == {"who", "what", "when", "where", "how", "why"}

    def test_detects_no_data_without_annotations(self, monkeypatch):
        """Test that event without annotations returns error."""
        mock_config = Mock()
        mock_config.dimension_prefix = ["dim_"]
        mock_config.fact_prefix = ["fct_"]

        now = datetime.now()
        event = BusinessEvent(
            domain=None,
            id="evt_20260101_001",
            text="test event",
            type=BusinessEventType.DISCRETE,
            created_at=now,
            updated_at=now,
            annotations=BusinessEventAnnotations(),
            derived_entities=[],
        )

        result = entity_generator.generate_entities_from_event(event, mock_config)

        assert len(result.entities) == 0
        assert len(result.errors) == 1
        assert "annotation" in result.errors[0].lower()


class TestGenerateEntitiesFromSevenWs:
    """Test generate_entities_from_event() with 7 Ws entries."""

    def test_generates_entities_from_annotations(self, monkeypatch):
        """Test that dimensions and fact are generated correctly from 7 Ws."""
        mock_config = Mock()
        mock_config.dimension_prefix = ["dim_"]
        mock_config.fact_prefix = ["fct_"]

        now = datetime.now()
        event = BusinessEvent(
            domain=None,
            id="evt_20260101_001",
            text="customer buys product",
            type=BusinessEventType.DISCRETE,
            created_at=now,
            updated_at=now,
            annotations=BusinessEventAnnotations(
                who=[AnnotationEntry(id="w1", text="customer", dimension_id=None, description=None, attributes={})],
                what=[AnnotationEntry(id="w2", text="product", dimension_id=None, description=None, attributes={})],
                when=[AnnotationEntry(id="w3", text="date", dimension_id=None, description=None, attributes={})],
                how_many=[AnnotationEntry(id="w4", text="quantity", dimension_id=None, description=None, attributes={})],
            ),
            derived_entities=[],
        )

        result = entity_generator.generate_entities_from_event(event, mock_config)

        assert len(result.entities) == 4
        assert len(result.errors) == 0

        dim_entities = [e for e in result.entities if e["entity_type"] == "dimension"]
        assert len(dim_entities) == 3
        assert dim_entities[0]["id"] == "dim_customer"
        assert dim_entities[0]["metadata"]["annotation_type"] == "who"
        assert dim_entities[1]["id"] == "dim_product"
        assert dim_entities[1]["metadata"]["annotation_type"] == "what"
        assert dim_entities[2]["id"] == "dim_date"
        assert dim_entities[2]["metadata"]["annotation_type"] == "when"

        fact_entities = [e for e in result.entities if e["entity_type"] == "fact"]
        assert len(fact_entities) == 1
        assert fact_entities[0]["id"] == "fct_customer_buys_product"
        assert fact_entities[0]["metadata"]["event_type"] == "discrete"
        assert "drafted_fields" in fact_entities[0]
        assert fact_entities[0]["drafted_fields"][0]["name"] == "quantity"

    def test_creates_relationships_from_annotations(self, monkeypatch):
        """Test that all dimensions connect to fact."""
        mock_config = Mock()
        mock_config.dimension_prefix = ["dim_"]
        mock_config.fact_prefix = ["fct_"]

        now = datetime.now()
        event = BusinessEvent(
            domain=None,
            id="evt_20260101_001",
            text="customer buys product",
            type=BusinessEventType.DISCRETE,
            created_at=now,
            updated_at=now,
            annotations=BusinessEventAnnotations(
                who=[AnnotationEntry(id="w1", text="customer", dimension_id=None, description=None, attributes={})],
                what=[AnnotationEntry(id="w2", text="product", dimension_id=None, description=None, attributes={})],
                when=[AnnotationEntry(id="w3", text="date", dimension_id=None, description=None, attributes={})],
                how_many=[AnnotationEntry(id="w4", text="quantity", dimension_id=None, description=None, attributes={})],
            ),
            derived_entities=[],
        )

        result = entity_generator.generate_entities_from_event(event, mock_config)

        assert len(result.relationships) == 3
        assert result.relationships[0]["source"] == "dim_customer"
        assert result.relationships[0]["target"] == "fct_customer_buys_product"
        assert result.relationships[0]["type"] == "one_to_many"
        assert result.relationships[1]["source"] == "dim_product"
        assert result.relationships[1]["target"] == "fct_customer_buys_product"
        assert result.relationships[1]["type"] == "one_to_many"
        assert result.relationships[2]["source"] == "dim_date"
        assert result.relationships[2]["target"] == "fct_customer_buys_product"
        assert result.relationships[2]["type"] == "one_to_many"

    def test_requires_at_least_one_dimension(self, monkeypatch):
        """Test that missing dimension entries returns error."""
        mock_config = Mock()
        mock_config.dimension_prefix = ["dim_"]
        mock_config.fact_prefix = ["fct_"]

        now = datetime.now()
        event = BusinessEvent(
            domain=None,
            id="evt_20260101_001",
            text="test event",
            type=BusinessEventType.DISCRETE,
            created_at=now,
            updated_at=now,
            annotations=BusinessEventAnnotations(
                how_many=[AnnotationEntry(id="w1", text="quantity", dimension_id=None, description=None, attributes={})],
            ),
            derived_entities=[],
        )

        result = entity_generator.generate_entities_from_event(event, mock_config)

        assert len(result.entities) == 0
        assert len(result.errors) == 1
        assert "dimension" in result.errors[0].lower()

    def test_requires_at_least_one_how_many(self, monkeypatch):
        """Test that missing how_many entries returns error."""
        mock_config = Mock()
        mock_config.dimension_prefix = ["dim_"]
        mock_config.fact_prefix = ["fct_"]

        now = datetime.now()
        event = BusinessEvent(
            domain=None,
            id="evt_20260101_001",
            text="test event",
            type=BusinessEventType.DISCRETE,
            created_at=now,
            updated_at=now,
            annotations=BusinessEventAnnotations(
                who=[AnnotationEntry(id="w1", text="customer", dimension_id=None, description=None, attributes={})],
            ),
            derived_entities=[],
        )

        result = entity_generator.generate_entities_from_event(event, mock_config)

        assert len(result.entities) == 0
        assert len(result.errors) == 1
        assert "how many" in result.errors[0].lower()

    def test_handles_multiple_how_many_entries_as_drafted_fields(self, monkeypatch):
        """Test that multiple how_many entries become drafted fields."""
        mock_config = Mock()
        mock_config.dimension_prefix = ["dim_"]
        mock_config.fact_prefix = ["fct_"]

        now = datetime.now()
        event = BusinessEvent(
            domain=None,
            id="evt_20260101_001",
            text="customer buys product",
            type=BusinessEventType.DISCRETE,
            created_at=now,
            updated_at=now,
            annotations=BusinessEventAnnotations(
                who=[AnnotationEntry(id="w1", text="customer", dimension_id=None, description=None, attributes={})],
                what=[AnnotationEntry(id="w2", text="product", dimension_id=None, description=None, attributes={})],
                how_many=[
                    AnnotationEntry(id="w3", text="quantity", description="Items purchased", attributes={}),
                    AnnotationEntry(id="w4", text="amount", description="Total sales amount", attributes={}),
                ],
            ),
            derived_entities=[],
        )

        result = entity_generator.generate_entities_from_event(event, mock_config)

        assert len(result.entities) == 3

        fact_entities = [e for e in result.entities if e["entity_type"] == "fact"]
        assert len(fact_entities) == 1
        assert len(fact_entities[0]["drafted_fields"]) == 2
        assert fact_entities[0]["drafted_fields"][0]["name"] == "quantity"
        assert fact_entities[0]["drafted_fields"][0]["description"] == "Items purchased"
        assert fact_entities[0]["drafted_fields"][1]["name"] == "amount"
        assert fact_entities[0]["drafted_fields"][1]["description"] == "Total sales amount"

    def test_allows_all_dimension_w_types(self, monkeypatch):
        """Test that all 6 dimension W types (who, what, when, where, how, why) work."""
        mock_config = Mock()
        mock_config.dimension_prefix = ["dim_"]
        mock_config.fact_prefix = ["fct_"]

        now = datetime.now()
        event = BusinessEvent(
            domain=None,
            id="evt_20260101_001",
            text="customer buys product on date in store",
            type=BusinessEventType.DISCRETE,
            created_at=now,
            updated_at=now,
            annotations=BusinessEventAnnotations(
                who=[AnnotationEntry(id="w1", text="customer", dimension_id=None, description=None, attributes={})],
                what=[AnnotationEntry(id="w2", text="product", dimension_id=None, description=None, attributes={})],
                when=[AnnotationEntry(id="w3", text="date", dimension_id=None, description=None, attributes={})],
                where=[AnnotationEntry(id="w4", text="store", dimension_id=None, description=None, attributes={})],
                how=[AnnotationEntry(id="w5", text="online", dimension_id=None, description=None, attributes={})],
                why=[AnnotationEntry(id="w6", text="promotion", dimension_id=None, description=None, attributes={})],
                how_many=[AnnotationEntry(id="w7", text="quantity", dimension_id=None, description=None, attributes={})],
            ),
            derived_entities=[],
        )

        result = entity_generator.generate_entities_from_event(event, mock_config)

        assert len(result.entities) == 7

        dim_entities = [e for e in result.entities if e["entity_type"] == "dimension"]
        assert len(dim_entities) == 6

        w_types = [e["metadata"]["annotation_type"] for e in dim_entities]
        assert set(w_types) == {"who", "what", "when", "where", "how", "why"}

    def test_detects_no_data_without_annotations(self, monkeypatch):
        """Test that event without annotations returns error."""
        mock_config = Mock()
        mock_config.dimension_prefix = ["dim_"]
        mock_config.fact_prefix = ["fct_"]

        now = datetime.now()
        event = BusinessEvent(
            domain=None,
            id="evt_20260101_001",
            text="test event",
            type=BusinessEventType.DISCRETE,
            created_at=now,
            updated_at=now,
            annotations=BusinessEventAnnotations(),
            derived_entities=[],
        )

        result = entity_generator.generate_entities_from_event(event, mock_config)

        assert len(result.entities) == 0
        assert len(result.errors) == 1
        assert "annotation" in result.errors[0].lower()
