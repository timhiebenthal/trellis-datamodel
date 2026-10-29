"""Tests for role and roles field handling in data model and business events."""

import os
import yaml
import pytest
from datetime import datetime

from trellis_datamodel.services import business_events as business_events_service
from trellis_datamodel.services.business_events import storage as _storage
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
        monkeypatch.setattr(_storage, "_get_business_events_path", lambda: events_path)

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
        monkeypatch.setattr(_storage, "_get_business_events_path", lambda: events_path)

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
        monkeypatch.setattr(_storage, "_get_business_events_path", lambda: events_path)

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


class TestRolesFieldValidation:
    """Test validation of roles field in data model API."""

    def test_roles_must_be_list_or_none(self):
        """Test that roles field must be a list of strings/dicts or None."""
        from trellis_datamodel.services.data_model import _validate_roles

        # Valid cases — None, empty list, strings, dicts, mixed str+dict
        _validate_roles(None)
        _validate_roles([])
        _validate_roles(["dimension"])
        _validate_roles(["dimension", "primary"])
        _validate_roles([{"label": "Sales Agent", "role": "employee", "source": "proc_001"}])
        _validate_roles([{"label": "Sales Agent"}])  # Partial dict also valid
        _validate_roles(["dimension", {"label": "Sales Agent", "role": "employee", "source": "proc_001"}])

        # Invalid: not a list at all
        with pytest.raises(domain_exceptions.ValidationError, match="must be a list"):
            _validate_roles("dimension")  # String not list

        with pytest.raises(domain_exceptions.ValidationError, match="must be a list"):
            _validate_roles(123)  # Number not list

        # Invalid: list containing a non-string, non-dict item
        with pytest.raises(domain_exceptions.ValidationError, match="must be a list"):
            _validate_roles([123])  # List with integer

        with pytest.raises(domain_exceptions.ValidationError, match="must be a list"):
            _validate_roles(["dimension", 123])  # Mixed with integer


class TestBackwardCompatibility:
    """Test that new fields don't break existing functionality."""

    def test_load_events_without_role_field(self, temp_dir, monkeypatch):
        """Test loading events from YAML files that don't have role field."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(_storage, "_get_business_events_path", lambda: events_path)

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

    def test_flat_string_roles_do_not_crash_validator(self):
        """Test that old flat-string roles list is accepted by _validate_roles (backward compat)."""
        from trellis_datamodel.services.data_model import _validate_roles

        # Old format: list of plain strings — validator must not raise
        _validate_roles(["employee"])
        _validate_roles(["employee", "manager"])
        _validate_roles([])


class TestMergeRolesLegacyStrings:
    """The single roles-merge helper tolerates legacy flat-string roles at both
    call sites: the data-model save and the entity generator."""

    def test_merge_keeps_existing_strings_and_skips_incoming_strings(self):
        from trellis_datamodel.services.data_model import merge_roles

        existing = ["employee", {"label": "Sales Agent", "source": "evt_1"}]
        incoming = [
            "manager",
            {"label": "Sales Agent", "source": "evt_1"},
            {"label": "Support Agent", "source": "evt_1"},
        ]

        assert merge_roles(existing, incoming) == [
            "employee",
            {"label": "Sales Agent", "source": "evt_1"},
            {"label": "Support Agent", "source": "evt_1"},
        ]
        assert merge_roles(["employee"], None) == ["employee"]
        assert merge_roles(None, ["manager", {"label": "A"}]) == [{"label": "A"}]

    def test_save_merges_into_legacy_string_roles_on_disk(
        self, test_client, temp_data_model_path, temp_canvas_layout_path
    ):
        with open(temp_data_model_path, "w") as f:
            yaml.safe_dump(
                {
                    "version": 0.1,
                    "entities": [
                        {"id": "employee", "label": "Employee", "roles": ["staff"]}
                    ],
                    "relationships": [],
                },
                f,
            )

        response = test_client.post(
            "/api/data-model",
            json={
                "version": 0.1,
                "entities": [
                    {
                        "id": "employee",
                        "label": "Employee",
                        "roles": [
                            "manager",
                            {"label": "Sales Agent", "source": "evt_1"},
                        ],
                    }
                ],
                "relationships": [],
            },
        )

        assert response.status_code == 200
        with open(temp_data_model_path) as f:
            saved = yaml.safe_load(f)
        assert saved["entities"][0]["roles"] == [
            "staff",
            {"label": "Sales Agent", "source": "evt_1"},
        ]

    def test_generator_merges_roles_for_dimension_with_legacy_string_roles(
        self, tmp_path, monkeypatch
    ):
        from unittest.mock import Mock

        from trellis_datamodel import config as cfg
        from trellis_datamodel.services import entity_generator

        path = tmp_path / "data_model.yml"
        path.write_text(
            yaml.safe_dump(
                {
                    "entities": [
                        {"id": "dim__employee", "label": "Employee", "roles": ["staff"]}
                    ]
                }
            )
        )
        monkeypatch.setattr(cfg, "DATA_MODEL_PATH", str(path))
        config = Mock(dimension_prefix=["dim__"], fact_prefix=["fct_"])
        now = datetime.now()
        who = [
            AnnotationEntry(
                id=f"w{i}",
                text=text,
                dimension_id="dim__employee",
                description=None,
                attributes={},
                role=text.lower(),
            )
            for i, text in enumerate(["Sales Agent", "Support Agent", "Sales Agent"])
        ]
        event = BusinessEvent(
            domain=None,
            id="evt_20260101_001",
            text="employee does something",
            type=BusinessEventType.DISCRETE,
            created_at=now,
            updated_at=now,
            annotations=BusinessEventAnnotations(
                who=who,
                how_many=[
                    AnnotationEntry(id="hm1", text="count", description=None, attributes={})
                ],
            ),
            derived_entities=[],
        )

        result = entity_generator.generate_entities_from_event(event, config)

        assert result.errors == []
        (dim,) = [e for e in result.entities if e["entity_type"] == "dimension"]
        assert [r["label"] for r in dim["roles"]] == ["Sales Agent", "Support Agent"]
