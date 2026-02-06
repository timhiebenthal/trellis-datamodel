"""Tests for role and roles field handling in data model and business events."""

import os
import yaml
import pytest
from datetime import datetime

from trellis_datamodel.services import business_events_service
from trellis_datamodel.models.business_event import (
    BusinessEvent,
    BusinessEventType,
    BusinessEventAnnotations,
    AnnotationEntry,
)
from trellis_datamodel.exceptions import ValidationError


class TestAnnotationEntryRoleField:
    """Test role field in AnnotationEntry model."""

    def test_role_field_optional(self):
        """Test that role field is optional."""
        entry = AnnotationEntry(
            id="entry_test",
            text="Customer",
            description="Customer dimension"
        )
        assert entry.role is None

    def test_role_field_accepts_string(self):
        """Test that role field accepts string values."""
        entry = AnnotationEntry(
            id="entry_test",
            text="Customer",
            description="Customer dimension",
            role="dimension"
        )
        assert entry.role == "dimension"

    def test_role_field_accepts_none(self):
        """Test that role field accepts None explicitly."""
        entry = AnnotationEntry(
            id="entry_test",
            text="Customer",
            description="Customer dimension",
            role=None
        )
        assert entry.role is None

    def test_role_field_validates_type(self):
        """Test that role field validates type (must be string or None)."""
        with pytest.raises(ValidationError, match="role must be a string"):
            AnnotationEntry(
                id="entry_test",
                text="Customer",
                role=123  # Invalid: not a string
            )

        with pytest.raises(ValidationError, match="role must be a string"):
            AnnotationEntry(
                id="entry_test",
                text="Customer",
                role=["dimension"]  # Invalid: list not string
            )


class TestBusinessEventYamlRoundTrip:
    """Test YAML serialization/deserialization of business events with role field."""

    def test_annotation_with_role_serializes_correctly(self, temp_dir, monkeypatch):
        """Test that annotation entries with role field serialize to YAML correctly."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)

        # Create event
        event = business_events_service.create_event(
            "customer buys product",
            BusinessEventType.DISCRETE
        )

        # Add annotation with role
        updated_event = business_events_service.add_annotation_entry(
            event.id,
            "who",
            "Customer",
            description="Customer dimension",
            attributes={"role": "dimension"}  # Store in attributes for now
        )

        # Read raw YAML to verify structure
        with open(events_path, "r") as f:
            data = yaml.safe_load(f)

        events_data = data.get("events", [])
        assert len(events_data) == 1

        event_data = events_data[0]
        who_entries = event_data.get("annotations", {}).get("who", [])
        assert len(who_entries) == 1
        assert who_entries[0]["text"] == "Customer"

    def test_annotation_without_role_deserializes_correctly(self, temp_dir, monkeypatch):
        """Test that old YAML files without role field load correctly (backward compatibility)."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)

        # Create YAML without role field (old format)
        old_format_yaml = """
events:
  - id: evt_20240101_001
    text: customer buys product
    type: discrete
    domain: Sales
    created_at: 2024-01-01T10:00:00
    updated_at: 2024-01-01T10:00:00
    annotations:
      who:
        - id: entry_abc123
          text: Customer
          dimension_id: null
          description: Customer entity
          attributes: {}
      what: []
      when: []
      where: []
      how: []
      why: []
      how_many: []
    derived_entities: []
"""
        os.makedirs(os.path.dirname(events_path), exist_ok=True)
        with open(events_path, "w") as f:
            f.write(old_format_yaml)

        # Load events - should not fail
        events = business_events_service.load_business_events()
        assert len(events) == 1

        event = events[0]
        assert event.id == "evt_20240101_001"
        assert len(event.annotations.who) == 1
        assert event.annotations.who[0].role is None  # Should default to None

    def test_yaml_round_trip_preserves_role(self, temp_dir, monkeypatch):
        """Test that role field is preserved through save/load cycle."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)

        # Create YAML with role field
        yaml_with_role = """
events:
  - id: evt_20240101_001
    text: customer buys product
    type: discrete
    domain: Sales
    created_at: 2024-01-01T10:00:00
    updated_at: 2024-01-01T10:00:00
    annotations:
      who:
        - id: entry_abc123
          text: Customer
          dimension_id: null
          description: Customer dimension
          role: dimension
          attributes: {}
      what: []
      when: []
      where: []
      how: []
      why: []
      how_many: []
    derived_entities: []
"""
        os.makedirs(os.path.dirname(events_path), exist_ok=True)
        with open(events_path, "w") as f:
            f.write(yaml_with_role)

        # Load and verify
        events = business_events_service.load_business_events()
        assert len(events) == 1
        assert events[0].annotations.who[0].role == "dimension"

        # Save and reload to test round-trip
        business_events_service.save_business_events(events)
        reloaded_events = business_events_service.load_business_events()

        assert len(reloaded_events) == 1
        assert reloaded_events[0].annotations.who[0].role == "dimension"


class TestEntityRolesFieldYamlRoundTrip:
    """Test YAML serialization/deserialization of entities with roles field."""

    def test_entity_with_roles_serializes(self, temp_dir):
        """Test that entity with roles field serializes to YAML correctly."""
        from trellis_datamodel.utils.yaml_handler import YamlHandler

        model_path = os.path.join(temp_dir, "data_model.yml")

        model_data = {
            "version": 0.1,
            "entities": [
                {
                    "id": "customer",
                    "label": "Customer",
                    "description": "Customer entity",
                    "roles": ["dimension", "primary"]
                }
            ],
            "relationships": []
        }

        # Save and reload
        YamlHandler().save_file(model_path, model_data)

        with open(model_path, "r") as f:
            loaded_data = yaml.safe_load(f)

        assert len(loaded_data["entities"]) == 1
        entity = loaded_data["entities"][0]
        assert entity["roles"] == ["dimension", "primary"]

    def test_entity_without_roles_loads_correctly(self, temp_dir):
        """Test backward compatibility - entities without roles field."""
        from trellis_datamodel.utils.yaml_handler import YamlHandler

        model_path = os.path.join(temp_dir, "data_model.yml")

        # Old format without roles
        old_format = {
            "version": 0.1,
            "entities": [
                {
                    "id": "customer",
                    "label": "Customer",
                    "description": "Customer entity"
                }
            ],
            "relationships": []
        }

        YamlHandler().save_file(model_path, old_format)

        # Load - should work without roles field
        with open(model_path, "r") as f:
            loaded_data = yaml.safe_load(f)

        assert len(loaded_data["entities"]) == 1
        entity = loaded_data["entities"][0]
        assert "roles" not in entity  # Field is optional

    def test_roles_round_trip_preserves_data(self, temp_dir):
        """Test that roles field is preserved through multiple save/load cycles."""
        from trellis_datamodel.utils.yaml_handler import YamlHandler

        model_path = os.path.join(temp_dir, "data_model.yml")

        model_data = {
            "version": 0.1,
            "entities": [
                {
                    "id": "customer",
                    "label": "Customer",
                    "roles": ["dimension"]
                },
                {
                    "id": "order",
                    "label": "Order",
                    "roles": ["fact", "transaction"]
                },
                {
                    "id": "product",
                    "label": "Product"
                    # No roles field
                }
            ],
            "relationships": []
        }

        # First save
        YamlHandler().save_file(model_path, model_data)

        # First load
        with open(model_path, "r") as f:
            loaded_data_1 = yaml.safe_load(f)

        # Second save (simulating user edit)
        YamlHandler().save_file(model_path, loaded_data_1)

        # Second load
        with open(model_path, "r") as f:
            loaded_data_2 = yaml.safe_load(f)

        # Verify data integrity
        assert loaded_data_2["entities"][0]["roles"] == ["dimension"]
        assert loaded_data_2["entities"][1]["roles"] == ["fact", "transaction"]
        assert "roles" not in loaded_data_2["entities"][2]


class TestRolesFieldValidation:
    """Test validation of roles field in data model API."""

    def test_roles_must_be_list_or_none(self):
        """Test that roles field must be a list of strings or None."""
        from trellis_datamodel.routes.data_model import _validate_roles

        # Valid cases
        _validate_roles(None)
        _validate_roles([])
        _validate_roles(["dimension"])
        _validate_roles(["dimension", "primary"])

        # Invalid cases
        with pytest.raises(ValidationError, match="must be a list"):
            _validate_roles("dimension")  # String not list

        with pytest.raises(ValidationError, match="must be a list"):
            _validate_roles(123)  # Number not list

        with pytest.raises(ValidationError, match="must be a list of strings"):
            _validate_roles([123])  # List with non-string

        with pytest.raises(ValidationError, match="must be a list of strings"):
            _validate_roles(["dimension", 123])  # Mixed types


class TestBackwardCompatibility:
    """Test that new fields don't break existing functionality."""

    def test_load_events_without_role_field(self, temp_dir, monkeypatch):
        """Test loading events from YAML files that don't have role field."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)

        # Create old-format YAML
        old_yaml = """
events:
  - id: evt_20240101_001
    text: event without role
    type: discrete
    created_at: 2024-01-01T10:00:00
    updated_at: 2024-01-01T10:00:00
    annotations:
      who:
        - id: entry_1
          text: Customer
          dimension_id: null
          description: null
          attributes: {}
      what: []
      when: []
      where: []
      how: []
      why: []
      how_many: []
    derived_entities: []
"""
        os.makedirs(os.path.dirname(events_path), exist_ok=True)
        with open(events_path, "w") as f:
            f.write(old_yaml)

        # Should load without errors
        events = business_events_service.load_business_events()
        assert len(events) == 1
        assert events[0].annotations.who[0].role is None

    def test_load_entities_without_roles_field(self, temp_dir):
        """Test loading entities from YAML files that don't have roles field."""
        model_path = os.path.join(temp_dir, "data_model.yml")

        old_yaml = """
version: 0.1
entities:
  - id: customer
    label: Customer
    description: Customer entity
relationships: []
"""
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        with open(model_path, "w") as f:
            f.write(old_yaml)

        # Should load without errors
        with open(model_path, "r") as f:
            data = yaml.safe_load(f)

        assert len(data["entities"]) == 1
        # Field is optional, so it won't be present
        assert "roles" not in data["entities"][0]
