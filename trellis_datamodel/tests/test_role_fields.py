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
import trellis_datamodel.exceptions as domain_exceptions


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
        with pytest.raises(domain_exceptions.ValidationError, match="role must be a string"):
            AnnotationEntry(
                id="entry_test",
                text="Customer",
                role=123  # Invalid: not a string
            )

        with pytest.raises(domain_exceptions.ValidationError, match="role must be a string"):
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

        roles = [{"label": "Sales Agent", "role": "employee", "source": "proc_001"}]
        model_data = {
            "version": 0.1,
            "entities": [
                {
                    "id": "customer",
                    "label": "Customer",
                    "description": "Customer entity",
                    "roles": roles,
                }
            ],
            "relationships": [],
        }

        # Save and reload
        YamlHandler().save_file(model_path, model_data)

        with open(model_path, "r") as f:
            loaded_data = yaml.safe_load(f)

        assert len(loaded_data["entities"]) == 1
        entity = loaded_data["entities"][0]
        assert entity["roles"] == roles

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
                    "description": "Customer entity",
                }
            ],
            "relationships": [],
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

        role_a = {"label": "Sales Agent", "role": "employee", "source": "proc_001"}
        role_b = {"label": "Manager", "role": "manager", "source": "proc_002"}
        model_data = {
            "version": 0.1,
            "entities": [
                {
                    "id": "customer",
                    "label": "Customer",
                    "roles": [role_a],
                },
                {
                    "id": "order",
                    "label": "Order",
                    "roles": [role_a, role_b],
                },
                {
                    "id": "product",
                    "label": "Product",
                    # No roles field
                },
            ],
            "relationships": [],
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
        assert loaded_data_2["entities"][0]["roles"] == [role_a]
        assert loaded_data_2["entities"][1]["roles"] == [role_a, role_b]
        assert "roles" not in loaded_data_2["entities"][2]


class TestRolesFieldValidation:
    """Test validation of roles field in data model API."""

    def test_roles_must_be_list_or_none(self):
        """Test that roles field must be a list of strings/dicts or None."""
        from trellis_datamodel.routes.data_model import _validate_roles

        # Valid cases — None, empty list, strings, dicts, mixed str+dict
        _validate_roles(None)
        _validate_roles([])
        _validate_roles(["dimension"])
        _validate_roles(["dimension", "primary"])
        _validate_roles([{"label": "Sales Agent", "role": "employee", "source": "proc_001"}])
        _validate_roles([{"label": "Sales Agent"}])  # Partial dict also valid
        _validate_roles(["dimension", {"label": "Sales Agent", "role": "employee", "source": "proc_001"}])

        # Invalid: not a list at all
        with pytest.raises(Exception, match="must be a list") as exc_info:
            _validate_roles("dimension")  # String not list
        assert exc_info.type.__name__ == "ValidationError"

        with pytest.raises(Exception, match="must be a list") as exc_info:
            _validate_roles(123)  # Number not list
        assert exc_info.type.__name__ == "ValidationError"

        # Invalid: list containing a non-string, non-dict item
        with pytest.raises(Exception, match="must be a list") as exc_info:
            _validate_roles([123])  # List with integer
        assert exc_info.type.__name__ == "ValidationError"

        with pytest.raises(Exception, match="must be a list") as exc_info:
            _validate_roles(["dimension", 123])  # Mixed with integer
        assert exc_info.type.__name__ == "ValidationError"


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

    def test_flat_string_roles_do_not_crash_validator(self):
        """Test that old flat-string roles list is accepted by _validate_roles (backward compat)."""
        from trellis_datamodel.routes.data_model import _validate_roles

        # Old format: list of plain strings — validator must not raise
        _validate_roles(["employee"])
        _validate_roles(["employee", "manager"])
        _validate_roles([])

    def test_flat_string_roles_load_from_yaml(self, temp_dir):
        """Test that loading an entity with old flat roles: ['employee'] does not crash."""
        model_path = os.path.join(temp_dir, "data_model.yml")

        old_yaml = """
version: 0.1
entities:
  - id: dim__employee
    label: Employee
    description: Employee dimension
    roles:
      - employee
relationships: []
"""
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        with open(model_path, "w") as f:
            f.write(old_yaml)

        with open(model_path, "r") as f:
            data = yaml.safe_load(f)

        entity = data["entities"][0]
        assert entity["roles"] == ["employee"]

        # Validator must accept it without raising
        from trellis_datamodel.routes.data_model import _validate_roles
        _validate_roles(entity["roles"])  # Should not raise
