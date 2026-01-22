"""Tests for entity generator service."""

import pytest
from unittest.mock import Mock
from datetime import datetime

from trellis_datamodel.services import entity_generator
from trellis_datamodel.models.business_event import (
    BusinessEvent,
    BusinessEventType,
    Annotation,
    GeneratedEntitiesResult,
    BusinessEventSevenWs,
    SevenWsEntry,
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


class TestGenerateEntitiesFromEvent:
    """Test generate_entities_from_event() function."""

    def test_generates_dimension_and_fact_entities(self, monkeypatch):
        """Test that dimensions and facts are generated correctly."""
        # Mock config
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
            annotations=[
                Annotation(text="customer", type="dimension", start_pos=0, end_pos=8),
                Annotation(text="buys", type="fact", start_pos=9, end_pos=13),
                Annotation(text="product", type="dimension", start_pos=14, end_pos=21),
            ],
            derived_entities=[],
        )

        result = entity_generator.generate_entities_from_event(event, mock_config)

        assert len(result.entities) == 3
        assert len(result.errors) == 0

        # Check dimensions
        dim_entities = [e for e in result.entities if e["entity_type"] == "dimension"]
        assert len(dim_entities) == 2
        assert dim_entities[0]["id"] == "dim_customer"
        assert dim_entities[0]["label"] == "Customer"
        assert dim_entities[1]["id"] == "dim_product"
        assert dim_entities[1]["label"] == "Product"

        # Check fact
        fact_entities = [e for e in result.entities if e["entity_type"] == "fact"]
        assert len(fact_entities) == 1
        assert fact_entities[0]["id"] == "fct_buys"
        assert fact_entities[0]["label"] == "Buys"
        assert fact_entities[0]["metadata"]["event_type"] == "discrete"

    def test_creates_relationships_dimension_to_fact(self, monkeypatch):
        """Test that relationships connect dimensions to facts."""
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
            annotations=[
                Annotation(text="customer", type="dimension", start_pos=0, end_pos=8),
                Annotation(text="buys", type="fact", start_pos=9, end_pos=13),
                Annotation(text="product", type="dimension", start_pos=14, end_pos=21),
            ],
            derived_entities=[],
        )

        result = entity_generator.generate_entities_from_event(event, mock_config)

        assert len(result.relationships) == 2  # 2 dimensions × 1 fact
        assert result.relationships[0]["source"] == "dim_customer"
        assert result.relationships[0]["target"] == "fct_buys"
        assert result.relationships[1]["source"] == "dim_product"
        assert result.relationships[1]["target"] == "fct_buys"

    def test_inherits_event_type_in_fact_metadata(self, monkeypatch):
        """Test that fact entities inherit event type as metadata."""
        mock_config = Mock()
        mock_config.dimension_prefix = ["dim_"]
        mock_config.fact_prefix = ["fct_"]

        now = datetime.now()
        for event_type in BusinessEventType:
            event = BusinessEvent(
                domain=None,
                id="evt_20260101_001",
                text="test event",
                type=event_type,
                created_at=now,
                updated_at=now,
                annotations=[
                    Annotation(text="test", type="fact", start_pos=0, end_pos=4),
                ],
                derived_entities=[],
            )

            result = entity_generator.generate_entities_from_event(event, mock_config)
            fact = result.entities[0]
            assert fact["metadata"]["event_type"] == event_type.value

    def test_requires_at_least_one_dimension(self, monkeypatch):
        """Test that missing dimension annotation returns error."""
        mock_config = Mock()
        mock_config.dimension_prefix = ["dim_"]
        mock_config.fact_prefix = ["fct_"]

        now = datetime.now()
        event = BusinessEvent(
            domain=None,
            id="evt_20260101_001",
            text="buys something",
            type=BusinessEventType.DISCRETE,
            created_at=now,
            updated_at=now,
            annotations=[
                Annotation(text="buys", type="fact", start_pos=0, end_pos=4),
            ],
            derived_entities=[],
        )

        result = entity_generator.generate_entities_from_event(event, mock_config)

        assert len(result.entities) == 0
        assert len(result.errors) == 1
        assert "dimension" in result.errors[0].lower()

    def test_requires_at_least_one_fact(self, monkeypatch):
        """Test that missing fact annotation returns error."""
        mock_config = Mock()
        mock_config.dimension_prefix = ["dim_"]
        mock_config.fact_prefix = ["fct_"]

        now = datetime.now()
        event = BusinessEvent(
            domain=None,
            id="evt_20260101_001",
            text="customer and product",
            type=BusinessEventType.DISCRETE,
            created_at=now,
            updated_at=now,
            annotations=[
                Annotation(text="customer", type="dimension", start_pos=0, end_pos=8),
                Annotation(text="product", type="dimension", start_pos=13, end_pos=20),
            ],
            derived_entities=[],
        )

        result = entity_generator.generate_entities_from_event(event, mock_config)

        assert len(result.entities) == 0
        assert len(result.errors) == 1
        assert "fact" in result.errors[0].lower()

    def test_detects_duplicate_entity_names(self, monkeypatch):
        """Test that duplicate entity names are detected."""
        mock_config = Mock()
        mock_config.dimension_prefix = ["dim_"]
        mock_config.fact_prefix = ["fct_"]

        now = datetime.now()
        event = BusinessEvent(
            domain=None,
            id="evt_20260101_001",
            text="customer customer",
            type=BusinessEventType.DISCRETE,
            created_at=now,
            updated_at=now,
            annotations=[
                Annotation(text="customer", type="dimension", start_pos=0, end_pos=8),
                Annotation(text="customer", type="dimension", start_pos=9, end_pos=17),
                Annotation(text="buys", type="fact", start_pos=18, end_pos=22),
            ],
            derived_entities=[],
        )

        result = entity_generator.generate_entities_from_event(event, mock_config)

        assert len(result.errors) > 0
        assert "duplicate" in result.errors[0].lower()

    def test_handles_multiple_facts(self, monkeypatch):
        """Test that multiple facts create multiple relationships."""
        mock_config = Mock()
        mock_config.dimension_prefix = ["dim_"]
        mock_config.fact_prefix = ["fct_"]

        now = datetime.now()
        event = BusinessEvent(
            domain=None,
            id="evt_20260101_001",
            text="customer buys and returns product",
            type=BusinessEventType.DISCRETE,
            created_at=now,
            updated_at=now,
            annotations=[
                Annotation(text="customer", type="dimension", start_pos=0, end_pos=8),
                Annotation(text="buys", type="fact", start_pos=9, end_pos=13),
                Annotation(text="returns", type="fact", start_pos=17, end_pos=24),
                Annotation(text="product", type="dimension", start_pos=25, end_pos=32),
            ],
            derived_entities=[],
        )

        result = entity_generator.generate_entities_from_event(event, mock_config)

        # 2 dimensions × 2 facts = 4 relationships
        assert len(result.relationships) == 4

    def test_uses_global_config_when_no_config_provided(self, monkeypatch):
        """Test that global config is used when config parameter is None."""
        # Mock global config
        mock_global_config = Mock()
        mock_global_config.dimension_prefix = ["dim_"]
        mock_global_config.fact_prefix = ["fct_"]
        monkeypatch.setattr(
            entity_generator.cfg,
            "DIMENSIONAL_MODELING_CONFIG",
            mock_global_config,
        )

        now = datetime.now()
        event = BusinessEvent(
            domain=None,
            id="evt_20260101_001",
            text="customer buys product",
            type=BusinessEventType.DISCRETE,
            created_at=now,
            updated_at=now,
            annotations=[
                Annotation(text="customer", type="dimension", start_pos=0, end_pos=8),
                Annotation(text="buys", type="fact", start_pos=9, end_pos=13),
            ],
            derived_entities=[],
        )

        result = entity_generator.generate_entities_from_event(event, None)

        assert len(result.entities) == 2
        assert result.entities[0]["id"] == "dim_customer"
        assert result.entities[1]["id"] == "fct_buys"

    def test_handles_empty_text_gracefully(self, monkeypatch):
        """Test that empty annotation text is handled."""
        mock_config = Mock()
        mock_config.dimension_prefix = ["dim_"]
        mock_config.fact_prefix = ["fct_"]

        now = datetime.now()
        event = BusinessEvent(
            domain=None,
            id="evt_20260101_001",
            text="test",
            type=BusinessEventType.DISCRETE,
            created_at=now,
            updated_at=now,
            annotations=[
                Annotation(text="", type="dimension", start_pos=0, end_pos=0),
                Annotation(text="test", type="fact", start_pos=0, end_pos=4),
            ],



class TestGenerateEntitiesFromSevenWs:
    """Test generate_entities_from_event() with 7 Ws entries."""

    def test_generates_entities_from_seven_ws(self, monkeypatch):
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
            seven_ws=BusinessEventSevenWs(
                who=[SevenWsEntry(id="w1", text="customer", dimension_id=None, description=None, attributes={})],
                what=[SevenWsEntry(id="w2", text="product", dimension_id=None, description=None, attributes={})],
                when=[SevenWsEntry(id="w3", text="date", dimension_id=None, description=None, attributes={})],
                how_many=[SevenWsEntry(id="w4", text="quantity", dimension_id=None, description=None, attributes={})],
            ),
            annotations=[],
            derived_entities=[],
        )

        result = entity_generator.generate_entities_from_event(event, mock_config)

        assert len(result.entities) == 3
        assert len(result.errors) == 0

        # Check dimensions
        dim_entities = [e for e in result.entities if e["entity_type"] == "dimension"]
        assert len(dim_entities) == 2
        assert dim_entities[0]["id"] == "dim_customer"
        assert dim_entities[0]["metadata"]["seven_w_type"] == "who"
        assert dim_entities[1]["id"] == "dim_product"
        assert dim_entities[1]["metadata"]["seven_w_type"] == "what"

        # Check fact
        fact_entities = [e for e in result.entities if e["entity_type"] == "fact"]
        assert len(fact_entities) == 1
        assert fact_entities[0]["id"] == "fct_customer_buys_product"
        assert fact_entities[0]["metadata"]["event_type"] == "discrete"
        assert "drafted_fields" in fact_entities[0]
        assert fact_entities[0]["drafted_fields"][0]["name"] == "quantity"

    def test_creates_relationships_from_seven_ws(self, monkeypatch):
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
            seven_ws=BusinessEventSevenWs(
                who=[SevenWsEntry(id="w1", text="customer", dimension_id=None, description=None, attributes={})],
                what=[SevenWsEntry(id="w2", text="product", dimension_id=None, description=None, attributes={})],
                when=[SevenWsEntry(id="w3", text="date", dimension_id=None, description=None, attributes={})],
                how_many=[SevenWsEntry(id="w4", text="quantity", dimension_id=None, description=None, attributes={})],
            ),
            annotations=[],
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
            seven_ws=BusinessEventSevenWs(
                how_many=[SevenWsEntry(id="w1", text="quantity", dimension_id=None, description=None, attributes={})],
            ),
            annotations=[],
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
            seven_ws=BusinessEventSevenWs(
                who=[SevenWsEntry(id="w1", text="customer", dimension_id=None, description=None, attributes={})],
            ),
            annotations=[],
            derived_entities=[],
        )

        result = entity_generator.generate_entities_from_event(event, mock_config)

        assert len(result.entities) == 0
        assert len(result.errors) == 1
        assert "how many" in result.errors[0].lower()

    def test_maintains_backward_compatibility_with_annotations(self, monkeypatch):
        """Test that events with annotations (no seven_ws) still work."""
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
            annotations=[
                Annotation(text="customer", type="dimension", start_pos=0, end_pos=8),
                Annotation(text="buys", type="fact", start_pos=9, end_pos=13),
                Annotation(text="product", type="dimension", start_pos=14, end_pos=21),
            ],
            seven_ws=BusinessEventSevenWs(),
            derived_entities=[],
        )

        result = entity_generator.generate_entities_from_event(event, mock_config)

        assert len(result.entities) == 3
        assert len(result.errors) == 0

        # Check that annotation-based generation still works
        dim_entities = [e for e in result.entities if e["entity_type"] == "dimension"]
        assert len(dim_entities) == 2
        assert dim_entities[0]["id"] == "dim_customer"
        assert dim_entities[1]["id"] == "dim_product"

        fact_entities = [e for e in result.entities if e["entity_type"] == "fact"]
        assert len(fact_entities) == 1
        assert fact_entities[0]["id"] == "fct_buys"
        assert "drafted_fields" not in fact_entities[0]

    def test_falls_back_to_annotations_if_seven_ws_empty(self, monkeypatch):
        """Test that empty seven_ws falls back to annotation-based generation."""
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
            annotations=[
                Annotation(text="customer", type="dimension", start_pos=0, end_pos=8),
                Annotation(text="buys", type="fact", start_pos=9, end_pos=13),
                Annotation(text="product", type="dimension", start_pos=14, end_pos=21),
            ],
            seven_ws=BusinessEventSevenWs(),
            derived_entities=[],
        )

        result = entity_generator.generate_entities_from_event(event, mock_config)

        # Should use annotation-based generation when seven_ws is empty
        assert len(result.entities) == 3
        assert len(result.errors) == 0

        # Verify annotation-based structure (not 7 Ws)
        fact_entities = [e for e in result.entities if e["entity_type"] == "fact"]
        assert fact_entities[0]["id"] == "fct_buys"
        assert "drafted_fields" not in fact_entities[0]

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
            seven_ws=BusinessEventSevenWs(
                who=[SevenWsEntry(id="w1", text="customer", dimension_id=None, description=None, attributes={})],
                what=[SevenWsEntry(id="w2", text="product", dimension_id=None, description=None, attributes={})],
                how_many=[
                    SevenWsEntry(id="w3", text="quantity", description="Items purchased", attributes={}),
                    SevenWsEntry(id="w4", text="amount", description="Total sales amount", attributes={}),
                ],
            ),
            annotations=[],
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
            seven_ws=BusinessEventSevenWs(
                who=[SevenWsEntry(id="w1", text="customer", dimension_id=None, description=None, attributes={})],
                what=[SevenWsEntry(id="w2", text="product", dimension_id=None, description=None, attributes={})],
                when=[SevenWsEntry(id="w3", text="date", dimension_id=None, description=None, attributes={})],
                where=[SevenWsEntry(id="w4", text="store", dimension_id=None, description=None, attributes={})],
                how=[SevenWsEntry(id="w5", text="online", dimension_id=None, description=None, attributes={})],
                why=[SevenWsEntry(id="w6", text="promotion", dimension_id=None, description=None, attributes={})],
                how_many=[SevenWsEntry(id="w7", text="quantity", dimension_id=None, description=None, attributes={})],
            ),
            annotations=[],
            derived_entities=[],
        )

        result = entity_generator.generate_entities_from_event(event, mock_config)

        assert len(result.entities) == 7

        # Check 6 dimensions (one for each W type)
        dim_entities = [e for e in result.entities if e["entity_type"] == "dimension"]
        assert len(dim_entities) == 6

        # Check seven_w_type metadata is set correctly
        w_types = [e["metadata"]["seven_w_type"] for e in dim_entities]
        assert set(w_types) == {"who", "what", "when", "where", "how", "why"}

    def test_detects_no_data_without_seven_ws_or_annotations(self, monkeypatch):
        """Test that event without seven_ws or annotations returns error."""
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
            seven_ws=BusinessEventSevenWs(),
            annotations=[],
            derived_entities=[],
        )

        result = entity_generator.generate_entities_from_event(event, mock_config)

        assert len(result.entities) == 0
        assert len(result.errors) == 1
        assert "seven_ws" in result.errors[0].lower() or "annotations" in result.errors[0].lower()
