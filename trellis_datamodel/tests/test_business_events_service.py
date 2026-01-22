"""Tests for business events service CRUD operations."""

import os
import yaml
import pytest
from datetime import datetime

from trellis_datamodel.services import business_events_service
from trellis_datamodel.models.business_event import BusinessEvent, BusinessEventType, Annotation
from trellis_datamodel.exceptions import ValidationError, NotFoundError, FileOperationError


class TestCreateEvent:
    """Test create_event() function."""

    def test_creates_event_with_auto_generated_id(self, temp_dir, monkeypatch):
        """Test that create_event generates ID in format evt_YYYYMMDD_NNN."""
        # Set BUSINESS_EVENTS_PATH to temp directory
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)

        event = business_events_service.create_event("customer buys product", BusinessEventType.DISCRETE)

        assert event.id.startswith("evt_")
        assert len(event.id.split("_")) == 3  # evt_YYYYMMDD_NNN
        assert event.id.endswith("001")  # First event of the day

    def test_increments_id_for_multiple_events_same_day(self, temp_dir, monkeypatch):
        """Test that ID increments for multiple events created on same day."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)

        event1 = business_events_service.create_event("first event", BusinessEventType.DISCRETE)
        event2 = business_events_service.create_event("second event", BusinessEventType.EVOLVING)

        assert event1.id.endswith("001")
        assert event2.id.endswith("002")

    def test_sets_timestamps(self, temp_dir, monkeypatch):
        """Test that created_at and updated_at are set."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)

        before = datetime.now()
        event = business_events_service.create_event("test event", BusinessEventType.DISCRETE)
        after = datetime.now()

        assert before <= event.created_at <= after
        assert before <= event.updated_at <= after
        assert event.created_at == event.updated_at

    def test_defaults_to_empty_annotations(self, temp_dir, monkeypatch):
        """Test that new events have empty annotations list."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)

        event = business_events_service.create_event("test event", BusinessEventType.DISCRETE)

        assert event.annotations == []
        assert event.derived_entities == []

    def test_strips_text_whitespace(self, temp_dir, monkeypatch):
        """Test that event text is stripped of leading/trailing whitespace."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)

        event = business_events_service.create_event("  customer buys product  ", BusinessEventType.DISCRETE)

        assert event.text == "customer buys product"

    def test_raises_validation_error_for_empty_text(self, temp_dir, monkeypatch):
        """Test that empty text raises ValidationError."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)

        with pytest.raises(ValidationError, match="Event text is required"):
            business_events_service.create_event("", BusinessEventType.DISCRETE)

        with pytest.raises(ValidationError, match="Event text is required"):
            business_events_service.create_event("   ", BusinessEventType.DISCRETE)


class TestUpdateEvent:
    """Test update_event() function."""

    def test_updates_text(self, temp_dir, monkeypatch):
        """Test updating event text."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)

        event = business_events_service.create_event("original text", BusinessEventType.DISCRETE)
        updated = business_events_service.update_event(event.id, {"text": "updated text"})

        assert updated.text == "updated text"
        assert updated.updated_at > event.created_at

    def test_updates_type(self, temp_dir, monkeypatch):
        """Test updating event type."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)

        event = business_events_service.create_event("test event", BusinessEventType.DISCRETE)
        updated = business_events_service.update_event(event.id, {"type": "recurring"})

        assert updated.type == BusinessEventType.RECURRING

    def test_clears_annotations_when_text_changes(self, temp_dir, monkeypatch):
        """Test that annotations are cleared when text is updated."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)

        event = business_events_service.create_event("customer buys product", BusinessEventType.DISCRETE)
        # Add an annotation
        business_events_service.add_annotation(event.id, "customer", "dimension", 0, 8)
        # Update text
        updated = business_events_service.update_event(event.id, {"text": "new text"})

        assert updated.annotations == []

    def test_raises_validation_error_for_invalid_type(self, temp_dir, monkeypatch):
        """Test that invalid event type raises ValidationError."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)

        event = business_events_service.create_event("test event", BusinessEventType.DISCRETE)

        with pytest.raises(ValidationError, match="Invalid event type"):
            business_events_service.update_event(event.id, {"type": "invalid_type"})

    def test_raises_not_found_error_for_missing_event(self, temp_dir, monkeypatch):
        """Test that updating non-existent event raises NotFoundError."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)

        with pytest.raises(NotFoundError, match="not found"):
            business_events_service.update_event("evt_20260101_999", {"text": "test"})


class TestAddAnnotation:
    """Test add_annotation() function."""

    def test_adds_annotation_successfully(self, temp_dir, monkeypatch):
        """Test adding a valid annotation."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)

        event = business_events_service.create_event("customer buys product", BusinessEventType.DISCRETE)
        updated = business_events_service.add_annotation(event.id, "customer", "dimension", 0, 8)

        assert len(updated.annotations) == 1
        assert updated.annotations[0].text == "customer"
        assert updated.annotations[0].type == "dimension"
        assert updated.annotations[0].start_pos == 0
        assert updated.annotations[0].end_pos == 8

    def test_detects_overlapping_annotations(self, temp_dir, monkeypatch):
        """Test that overlapping annotations raise ValidationError."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)

        event = business_events_service.create_event("customer buys product", BusinessEventType.DISCRETE)
        business_events_service.add_annotation(event.id, "customer", "dimension", 0, 8)

        # Try to add overlapping annotation
        with pytest.raises(ValidationError, match="overlap"):
            business_events_service.add_annotation(event.id, "stomer bu", "fact", 2, 10)

    def test_validates_position_bounds(self, temp_dir, monkeypatch):
        """Test that out-of-bounds positions raise ValidationError."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)

        event = business_events_service.create_event("test", BusinessEventType.DISCRETE)

        with pytest.raises(ValidationError, match="out of bounds"):
            business_events_service.add_annotation(event.id, "test", "dimension", -1, 4)

        with pytest.raises(ValidationError, match="out of bounds"):
            business_events_service.add_annotation(event.id, "test", "dimension", 0, 10)  # end_pos > len(text)

    def test_allows_non_overlapping_adjacent_annotations(self, temp_dir, monkeypatch):
        """Test that adjacent (non-overlapping) annotations are allowed."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)

        event = business_events_service.create_event("customer buys product", BusinessEventType.DISCRETE)
        business_events_service.add_annotation(event.id, "customer", "dimension", 0, 8)
        updated = business_events_service.add_annotation(event.id, "product", "dimension", 14, 21)

        assert len(updated.annotations) == 2

    def test_raises_not_found_error_for_missing_event(self, temp_dir, monkeypatch):
        """Test that annotating non-existent event raises NotFoundError."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)

        with pytest.raises(NotFoundError, match="not found"):
            business_events_service.add_annotation("evt_20260101_999", "test", "dimension", 0, 4)


class TestRemoveAnnotation:
    """Test remove_annotation() function."""

    def test_removes_annotation_by_index(self, temp_dir, monkeypatch):
        """Test removing annotation by index."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)

        event = business_events_service.create_event("customer buys product", BusinessEventType.DISCRETE)
        business_events_service.add_annotation(event.id, "customer", "dimension", 0, 8)
        business_events_service.add_annotation(event.id, "product", "dimension", 14, 21)

        updated = business_events_service.remove_annotation(event.id, 0)

        assert len(updated.annotations) == 1
        assert updated.annotations[0].text == "product"

    def test_raises_not_found_error_for_out_of_bounds_index(self, temp_dir, monkeypatch):
        """Test that out-of-bounds index raises NotFoundError."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)

        event = business_events_service.create_event("test", BusinessEventType.DISCRETE)

        with pytest.raises(NotFoundError, match="out of bounds"):
            business_events_service.remove_annotation(event.id, 0)

        with pytest.raises(NotFoundError, match="out of bounds"):
            business_events_service.remove_annotation(event.id, -1)

    def test_raises_not_found_error_for_missing_event(self, temp_dir, monkeypatch):
        """Test that removing annotation from non-existent event raises NotFoundError."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)

        with pytest.raises(NotFoundError, match="not found"):
            business_events_service.remove_annotation("evt_20260101_999", 0)


class TestLoadAndSaveBusinessEvents:
    """Test load_business_events() and save_business_events() functions."""

    def test_load_returns_empty_list_when_file_missing(self, temp_dir, monkeypatch):
        """Test that load returns empty list when file doesn't exist."""
        events_path = os.path.join(temp_dir, "nonexistent.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)

        events = business_events_service.load_business_events()

        assert events == []

    def test_save_creates_file(self, temp_dir, monkeypatch):
        """Test that save creates the file if it doesn't exist."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)

        event = business_events_service.create_event("test event", BusinessEventType.DISCRETE)
        business_events_service.save_business_events([event])

        assert os.path.exists(events_path)

    def test_load_after_save_returns_events(self, temp_dir, monkeypatch):
        """Test that loading after saving returns the same events."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)

        event1 = business_events_service.create_event("first event", BusinessEventType.DISCRETE)
        event2 = business_events_service.create_event("second event", BusinessEventType.EVOLVING)

        saved_events = [event1, event2]
        business_events_service.save_business_events(saved_events)
        loaded_events = business_events_service.load_business_events()

        assert len(loaded_events) == 2
        assert loaded_events[0].text == "first event"
        assert loaded_events[1].text == "second event"

    def test_handles_invalid_yaml_format(self, temp_dir, monkeypatch):
        """Test that invalid YAML raises FileOperationError."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)

        # Create invalid YAML file
        with open(events_path, "w") as f:
            f.write("invalid: yaml: content: [unclosed")

        with pytest.raises(FileOperationError, match="Invalid business events file format"):
            business_events_service.load_business_events()

    def test_handles_missing_events_key(self, temp_dir, monkeypatch):
        """Test that missing 'events' key raises FileOperationError."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)

        # Create YAML file without 'events' key
        with open(events_path, "w") as f:
            yaml.dump({"other_key": "value"}, f)

        with pytest.raises(FileOperationError, match="Invalid business events file format"):
            business_events_service.load_business_events()


class TestDeleteEvent:
    """Test delete_event() function."""

    def test_deletes_event_successfully(self, temp_dir, monkeypatch):
        """Test deleting an existing event."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)

        event1 = business_events_service.create_event("first event", BusinessEventType.DISCRETE)
        event2 = business_events_service.create_event("second event", BusinessEventType.EVOLVING)

        business_events_service.delete_event(event1.id)

        remaining = business_events_service.load_business_events()
        assert len(remaining) == 1
        assert remaining[0].id == event2.id

    def test_raises_not_found_error_for_missing_event(self, temp_dir, monkeypatch):
        """Test that deleting non-existent event raises NotFoundError."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)

        with pytest.raises(NotFoundError, match="not found"):
            business_events_service.delete_event("evt_20260101_999")
