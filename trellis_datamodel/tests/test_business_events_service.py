"""Tests for business events service CRUD operations."""

import os
import yaml
import pytest
from datetime import datetime

from trellis_datamodel.services import business_events_service
from trellis_datamodel.models.business_event import (
    BusinessEvent,
    BusinessEventType,
    BusinessEventProcess,
    BusinessEventAnnotations,
    AnnotationEntry,
)
from trellis_datamodel.exceptions import ValidationError, NotFoundError, FileOperationError

TEST_PROCESS_DOMAIN = "Sales"


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

    def test_defaults_to_empty_derived_entities(self, temp_dir, monkeypatch):
        """Test that new events have empty derived_entities list."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)

        event = business_events_service.create_event("test event", BusinessEventType.DISCRETE)

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


class TestCreateProcess:
    """Test create_process() function."""

    def test_creates_process_with_auto_generated_id(self, temp_dir, monkeypatch):
        """Test that create_process generates ID in format proc_YYYYMMDD_NNN."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)
        monkeypatch.setattr(business_events_service, "_get_processes_path", lambda: events_path)

        # Create events first
        event1 = business_events_service.create_event("event 1", BusinessEventType.DISCRETE)
        event2 = business_events_service.create_event("event 2", BusinessEventType.DISCRETE)

        process = business_events_service.create_process(
            "Test Process",
            BusinessEventType.DISCRETE,
            TEST_PROCESS_DOMAIN,
            [event1.id, event2.id],
        )

        assert process.id.startswith("proc_")
        assert len(process.id.split("_")) == 3  # proc_YYYYMMDD_NNN
        assert process.id.endswith("001")  # First process of the day

    def test_increments_id_for_multiple_processes_same_day(self, temp_dir, monkeypatch):
        """Test that ID increments for multiple processes created on same day."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)
        monkeypatch.setattr(business_events_service, "_get_processes_path", lambda: events_path)

        # Create events
        event1 = business_events_service.create_event("event 1", BusinessEventType.DISCRETE)
        event2 = business_events_service.create_event("event 2", BusinessEventType.DISCRETE)
        event3 = business_events_service.create_event("event 3", BusinessEventType.DISCRETE)

        process1 = business_events_service.create_process(
            "Process 1",
            BusinessEventType.DISCRETE,
            TEST_PROCESS_DOMAIN,
            [event1.id],
        )
        process2 = business_events_service.create_process(
            "Process 2",
            BusinessEventType.EVOLVING,
            TEST_PROCESS_DOMAIN,
            [event2.id, event3.id],
        )

        assert process1.id.endswith("001")
        assert process2.id.endswith("002")

    def test_sets_timestamps(self, temp_dir, monkeypatch):
        """Test that created_at and updated_at are set."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)
        monkeypatch.setattr(business_events_service, "_get_processes_path", lambda: events_path)

        event = business_events_service.create_event("test event", BusinessEventType.DISCRETE)

        before = datetime.now()
        process = business_events_service.create_process(
            "Test Process",
            BusinessEventType.DISCRETE,
            TEST_PROCESS_DOMAIN,
            [event.id],
        )
        after = datetime.now()

        assert before <= process.created_at <= after
        assert before <= process.updated_at <= after
        assert process.created_at == process.updated_at

    def test_links_events_to_process(self, temp_dir, monkeypatch):
        """Test that events are linked to the process via process_id."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)
        monkeypatch.setattr(business_events_service, "_get_processes_path", lambda: events_path)

        event1 = business_events_service.create_event("event 1", BusinessEventType.DISCRETE)
        event2 = business_events_service.create_event("event 2", BusinessEventType.DISCRETE)

        process = business_events_service.create_process(
            "Test Process",
            BusinessEventType.DISCRETE,
            TEST_PROCESS_DOMAIN,
            [event1.id, event2.id],
        )

        # Reload events to check process_id
        events = business_events_service.load_business_events()
        event1_reloaded = next(e for e in events if e.id == event1.id)
        event2_reloaded = next(e for e in events if e.id == event2.id)

        assert event1_reloaded.process_id == process.id
        assert event2_reloaded.process_id == process.id

    def test_computes_annotations_superset(self, temp_dir, monkeypatch):
        """Test that annotations superset is computed from member events."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)
        monkeypatch.setattr(business_events_service, "_get_processes_path", lambda: events_path)

        # Create events with annotations
        event1 = business_events_service.create_event("event 1", BusinessEventType.DISCRETE)
        event2 = business_events_service.create_event("event 2", BusinessEventType.DISCRETE)

        # Add annotations to events
        annotations1 = BusinessEventAnnotations(
            who=[AnnotationEntry(id="entry1", text="Customer A")],
            what=[AnnotationEntry(id="entry2", text="Product X")],
        )
        annotations2 = BusinessEventAnnotations(
            who=[AnnotationEntry(id="entry3", text="Customer B")],
            what=[AnnotationEntry(id="entry2", text="Product X")],  # Duplicate
        )

        business_events_service.update_event(event1.id, {"annotations": annotations1.model_dump()})
        business_events_service.update_event(event2.id, {"annotations": annotations2.model_dump()})

        process = business_events_service.create_process(
            "Test Process",
            BusinessEventType.DISCRETE,
            TEST_PROCESS_DOMAIN,
            [event1.id, event2.id],
        )

        assert process.annotations_superset is not None
        assert len(process.annotations_superset.who) == 2  # Both customers
        assert len(process.annotations_superset.what) == 1  # Duplicate Product X deduplicated

    def test_process_domain_persisted(self, temp_dir, monkeypatch):
        """Test that the selected domain is saved in the process record."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)
        monkeypatch.setattr(business_events_service, "_get_processes_path", lambda: events_path)

        event = business_events_service.create_event("event 1", BusinessEventType.DISCRETE)
        process = business_events_service.create_process(
            "Test Process",
            BusinessEventType.DISCRETE,
            TEST_PROCESS_DOMAIN,
            [event.id],
        )

        processes = business_events_service.load_processes()
        loaded_process = next(p for p in processes if p.id == process.id)
        assert loaded_process.domain == TEST_PROCESS_DOMAIN

    def test_raises_validation_error_for_empty_name(self, temp_dir, monkeypatch):
        """Test that empty name raises ValidationError."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)
        monkeypatch.setattr(business_events_service, "_get_processes_path", lambda: events_path)

        event = business_events_service.create_event("test event", BusinessEventType.DISCRETE)

        with pytest.raises(ValidationError, match="Process name is required"):
            business_events_service.create_process(
                "",
                BusinessEventType.DISCRETE,
                TEST_PROCESS_DOMAIN,
                [event.id],
            )

        with pytest.raises(ValidationError, match="Process name is required"):
            business_events_service.create_process(
                "   ",
                BusinessEventType.DISCRETE,
                TEST_PROCESS_DOMAIN,
                [event.id],
            )

    def test_raises_validation_error_for_empty_event_ids(self, temp_dir, monkeypatch):
        """Test that empty event_ids raises ValidationError."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)
        monkeypatch.setattr(business_events_service, "_get_processes_path", lambda: events_path)

        with pytest.raises(ValidationError, match="At least one event ID is required"):
            business_events_service.create_process(
                "Test Process",
                BusinessEventType.DISCRETE,
                TEST_PROCESS_DOMAIN,
                [],
            )

    def test_raises_not_found_error_for_invalid_event_id(self, temp_dir, monkeypatch):
        """Test that invalid event_id raises NotFoundError."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)
        monkeypatch.setattr(business_events_service, "_get_processes_path", lambda: events_path)

        with pytest.raises(NotFoundError, match="not found"):
            business_events_service.create_process(
                "Test Process",
                BusinessEventType.DISCRETE,
                TEST_PROCESS_DOMAIN,
                ["evt_20260101_999"],
            )

    def test_raises_validation_error_for_missing_domain(self, temp_dir, monkeypatch):
        """Test that missing or blank domain raises ValidationError."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)
        monkeypatch.setattr(business_events_service, "_get_processes_path", lambda: events_path)

        event = business_events_service.create_event("test event", BusinessEventType.DISCRETE)

        with pytest.raises(ValidationError, match="Process domain is required"):
            business_events_service.create_process(
                "Test Process",
                BusinessEventType.DISCRETE,
                domain=None,
                event_ids=[event.id],
            )

        with pytest.raises(ValidationError, match="Process domain is required"):
            business_events_service.create_process(
                "Test Process",
                BusinessEventType.DISCRETE,
                domain="   ",
                event_ids=[event.id],
            )


class TestAnnotationUnionLogic:
    """Test _compute_annotation_union() function."""

    def test_unions_annotations_from_multiple_events(self, temp_dir, monkeypatch):
        """Test that union combines annotations from multiple events."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)
        monkeypatch.setattr(business_events_service, "_get_processes_path", lambda: events_path)

        event1 = business_events_service.create_event("event 1", BusinessEventType.DISCRETE)
        event2 = business_events_service.create_event("event 2", BusinessEventType.DISCRETE)

        annotations1 = BusinessEventAnnotations(
            who=[AnnotationEntry(id="entry1", text="Customer A")],
            what=[AnnotationEntry(id="entry2", text="Product X")],
        )
        annotations2 = BusinessEventAnnotations(
            who=[AnnotationEntry(id="entry3", text="Customer B")],
            when=[AnnotationEntry(id="entry4", text="2024-01-01")],
        )

        business_events_service.update_event(event1.id, {"annotations": annotations1.model_dump()})
        business_events_service.update_event(event2.id, {"annotations": annotations2.model_dump()})

        events = business_events_service.load_business_events()
        process_events = [e for e in events if e.id in [event1.id, event2.id]]
        union = business_events_service._compute_annotation_union(process_events)

        assert len(union.who) == 2
        assert len(union.what) == 1
        assert len(union.when) == 1

    def test_deduplicates_by_dimension_id(self, temp_dir, monkeypatch):
        """Test that entries with same dimension_id are deduplicated."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)
        monkeypatch.setattr(business_events_service, "_get_processes_path", lambda: events_path)

        event1 = business_events_service.create_event("event 1", BusinessEventType.DISCRETE)
        event2 = business_events_service.create_event("event 2", BusinessEventType.DISCRETE)

        annotations1 = BusinessEventAnnotations(
            who=[AnnotationEntry(id="entry1", text="Customer A", dimension_id="dim_customer")]
        )
        annotations2 = BusinessEventAnnotations(
            who=[AnnotationEntry(id="entry2", text="Customer B", dimension_id="dim_customer")]
        )

        business_events_service.update_event(event1.id, {"annotations": annotations1.model_dump()})
        business_events_service.update_event(event2.id, {"annotations": annotations2.model_dump()})

        events = business_events_service.load_business_events()
        process_events = [e for e in events if e.id in [event1.id, event2.id]]
        union = business_events_service._compute_annotation_union(process_events)

        # Should deduplicate by dimension_id, keeping first occurrence
        assert len(union.who) == 1
        assert union.who[0].dimension_id == "dim_customer"

    def test_deduplicates_when_dimension_id_missing_in_one_entry(self, temp_dir, monkeypatch):
        """Test that text matches dedupe when only one entry has dimension_id."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)
        monkeypatch.setattr(business_events_service, "_get_processes_path", lambda: events_path)

        event1 = business_events_service.create_event("event 1", BusinessEventType.DISCRETE)
        event2 = business_events_service.create_event("event 2", BusinessEventType.DISCRETE)

        annotations1 = BusinessEventAnnotations(
            who=[AnnotationEntry(id="entry1", text="Employee")]
        )
        annotations2 = BusinessEventAnnotations(
            who=[AnnotationEntry(id="entry2", text="Employee", dimension_id="dim_employee")]
        )

        business_events_service.update_event(event1.id, {"annotations": annotations1.model_dump()})
        business_events_service.update_event(event2.id, {"annotations": annotations2.model_dump()})

        events = business_events_service.load_business_events()
        process_events = [e for e in events if e.id in [event1.id, event2.id]]
        union = business_events_service._compute_annotation_union(process_events)

        assert len(union.who) == 1
        assert union.who[0].dimension_id == "dim_employee"

    def test_deduplicates_by_normalized_text(self, temp_dir, monkeypatch):
        """Test that entries with same normalized text are deduplicated."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)
        monkeypatch.setattr(business_events_service, "_get_processes_path", lambda: events_path)

        event1 = business_events_service.create_event("event 1", BusinessEventType.DISCRETE)
        event2 = business_events_service.create_event("event 2", BusinessEventType.DISCRETE)

        annotations1 = BusinessEventAnnotations(
            what=[AnnotationEntry(id="entry1", text="Product X", description="A product")]
        )
        annotations2 = BusinessEventAnnotations(
            what=[AnnotationEntry(id="entry2", text="product x", description="a product")]
        )

        business_events_service.update_event(event1.id, {"annotations": annotations1.model_dump()})
        business_events_service.update_event(event2.id, {"annotations": annotations2.model_dump()})

        events = business_events_service.load_business_events()
        process_events = [e for e in events if e.id in [event1.id, event2.id]]
        union = business_events_service._compute_annotation_union(process_events)

        # Should deduplicate by normalized text+description
        assert len(union.what) == 1

    def test_preserves_distinct_entries(self, temp_dir, monkeypatch):
        """Test that distinct entries are preserved."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)
        monkeypatch.setattr(business_events_service, "_get_processes_path", lambda: events_path)

        event1 = business_events_service.create_event("event 1", BusinessEventType.DISCRETE)
        event2 = business_events_service.create_event("event 2", BusinessEventType.DISCRETE)

        annotations1 = BusinessEventAnnotations(
            who=[
                AnnotationEntry(id="entry1", text="Customer A"),
                AnnotationEntry(id="entry2", text="Customer B"),
            ]
        )
        annotations2 = BusinessEventAnnotations(
            who=[AnnotationEntry(id="entry3", text="Customer C")]
        )

        business_events_service.update_event(event1.id, {"annotations": annotations1.model_dump()})
        business_events_service.update_event(event2.id, {"annotations": annotations2.model_dump()})

        events = business_events_service.load_business_events()
        process_events = [e for e in events if e.id in [event1.id, event2.id]]
        union = business_events_service._compute_annotation_union(process_events)

        assert len(union.who) == 3


class TestResolveProcess:
    """Test resolve_process() function."""

    def test_resolves_process_and_unlinks_events(self, temp_dir, monkeypatch):
        """Test that resolving a process unlinks events."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)
        monkeypatch.setattr(business_events_service, "_get_processes_path", lambda: events_path)

        event1 = business_events_service.create_event("event 1", BusinessEventType.DISCRETE)
        event2 = business_events_service.create_event("event 2", BusinessEventType.DISCRETE)

        process = business_events_service.create_process(
            "Test Process",
            BusinessEventType.DISCRETE,
            TEST_PROCESS_DOMAIN,
            [event1.id, event2.id],
        )

        resolved = business_events_service.resolve_process(process.id)

        assert resolved.resolved_at is not None
        assert len(resolved.event_ids) == 0
        assert resolved.annotations_superset is None

        # Check events are unlinked
        events = business_events_service.load_business_events()
        event1_reloaded = next(e for e in events if e.id == event1.id)
        event2_reloaded = next(e for e in events if e.id == event2.id)

        assert event1_reloaded.process_id is None
        assert event2_reloaded.process_id is None

    def test_resolve_restores_events_to_domain_listing(self, temp_dir, monkeypatch):
        """Regression: resolved events should remain associated with their domain."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)
        monkeypatch.setattr(business_events_service, "_get_processes_path", lambda: events_path)

        event = business_events_service.create_event(
            "event 3", BusinessEventType.DISCRETE, domain=TEST_PROCESS_DOMAIN
        )
        process = business_events_service.create_process(
            "Domain Process",
            BusinessEventType.DISCRETE,
            TEST_PROCESS_DOMAIN,
            [event.id],
        )

        business_events_service.resolve_process(process.id)

        reloaded = next(
            e for e in business_events_service.load_business_events() if e.id == event.id
        )
        domains = business_events_service.get_unique_domains()

        assert reloaded.process_id is None
        assert reloaded.domain == TEST_PROCESS_DOMAIN
        assert TEST_PROCESS_DOMAIN in domains

    def test_raises_not_found_error_for_missing_process(self, temp_dir, monkeypatch):
        """Test that resolving non-existent process raises NotFoundError."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)
        monkeypatch.setattr(business_events_service, "_get_processes_path", lambda: events_path)

        with pytest.raises(NotFoundError, match="not found"):
            business_events_service.resolve_process("proc_20260101_999")

    def test_raises_validation_error_for_already_resolved_process(self, temp_dir, monkeypatch):
        """Test that resolving already resolved process raises ValidationError."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)
        monkeypatch.setattr(business_events_service, "_get_processes_path", lambda: events_path)

        event = business_events_service.create_event("event 1", BusinessEventType.DISCRETE)
        process = business_events_service.create_process(
            "Test Process",
            BusinessEventType.DISCRETE,
            TEST_PROCESS_DOMAIN,
            [event.id],
        )

        business_events_service.resolve_process(process.id)

        with pytest.raises(ValidationError, match="already resolved"):
            business_events_service.resolve_process(process.id)


class TestEventRelink:
    """Test attach_events_to_process() and detach_events_from_process() functions."""

    def test_attach_events_updates_process_and_links_events(self, temp_dir, monkeypatch):
        """Test that attaching events updates process and links events."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)
        monkeypatch.setattr(business_events_service, "_get_processes_path", lambda: events_path)

        event1 = business_events_service.create_event("event 1", BusinessEventType.DISCRETE)
        event2 = business_events_service.create_event("event 2", BusinessEventType.DISCRETE)
        event3 = business_events_service.create_event("event 3", BusinessEventType.DISCRETE)

        process = business_events_service.create_process(
            "Test Process",
            BusinessEventType.DISCRETE,
            TEST_PROCESS_DOMAIN,
            [event1.id],
        )

        updated = business_events_service.attach_events_to_process(process.id, [event2.id, event3.id])

        assert len(updated.event_ids) == 3
        assert event2.id in updated.event_ids
        assert event3.id in updated.event_ids

        # Check events are linked
        events = business_events_service.load_business_events()
        event2_reloaded = next(e for e in events if e.id == event2.id)
        event3_reloaded = next(e for e in events if e.id == event3.id)

        assert event2_reloaded.process_id == process.id
        assert event3_reloaded.process_id == process.id

    def test_detach_events_updates_process_and_unlinks_events(self, temp_dir, monkeypatch):
        """Test that detaching events updates process and unlinks events."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)
        monkeypatch.setattr(business_events_service, "_get_processes_path", lambda: events_path)

        event1 = business_events_service.create_event("event 1", BusinessEventType.DISCRETE)
        event2 = business_events_service.create_event("event 2", BusinessEventType.DISCRETE)
        event3 = business_events_service.create_event("event 3", BusinessEventType.DISCRETE)

        process = business_events_service.create_process(
            "Test Process",
            BusinessEventType.DISCRETE,
            TEST_PROCESS_DOMAIN,
            [event1.id, event2.id, event3.id],
        )

        updated = business_events_service.detach_events_from_process(process.id, [event2.id])

        assert len(updated.event_ids) == 2
        assert event2.id not in updated.event_ids

        # Check event is unlinked
        events = business_events_service.load_business_events()
        event2_reloaded = next(e for e in events if e.id == event2.id)

        assert event2_reloaded.process_id is None

    def test_attach_raises_error_for_event_in_another_process(self, temp_dir, monkeypatch):
        """Test that attaching event already in another process raises ValidationError."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)
        monkeypatch.setattr(business_events_service, "_get_processes_path", lambda: events_path)

        event1 = business_events_service.create_event("event 1", BusinessEventType.DISCRETE)
        event2 = business_events_service.create_event("event 2", BusinessEventType.DISCRETE)

        process1 = business_events_service.create_process(
            "Process 1",
            BusinessEventType.DISCRETE,
            TEST_PROCESS_DOMAIN,
            [event1.id],
        )
        process2 = business_events_service.create_process(
            "Process 2",
            BusinessEventType.DISCRETE,
            TEST_PROCESS_DOMAIN,
            [event2.id],
        )

        with pytest.raises(ValidationError, match="already attached"):
            business_events_service.attach_events_to_process(process2.id, [event1.id])

    def test_update_process_reorders_event_ids(self, temp_dir, monkeypatch):
        """Test that updating event_ids preserves order and links."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)
        monkeypatch.setattr(business_events_service, "_get_processes_path", lambda: events_path)

        event1 = business_events_service.create_event("event 1", BusinessEventType.DISCRETE)
        event2 = business_events_service.create_event("event 2", BusinessEventType.DISCRETE)
        event3 = business_events_service.create_event("event 3", BusinessEventType.DISCRETE)

        process = business_events_service.create_process(
            "Test Process",
            BusinessEventType.DISCRETE,
            TEST_PROCESS_DOMAIN,
            [event1.id, event2.id, event3.id],
        )

        updated = business_events_service.update_process(
            process.id,
            {"event_ids": [event3.id, event1.id, event2.id]},
        )

        assert updated.event_ids == [event3.id, event1.id, event2.id]

        events = business_events_service.load_business_events()
        for event_id in updated.event_ids:
            reloaded = next(e for e in events if e.id == event_id)
            assert reloaded.process_id == process.id


class TestSupersetRecompute:
    """Test superset recomputation when events change."""

    def test_recomputes_superset_when_event_annotations_change(self, temp_dir, monkeypatch):
        """Test that process superset is recomputed when event annotations change."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)
        monkeypatch.setattr(business_events_service, "_get_processes_path", lambda: events_path)

        event = business_events_service.create_event("event 1", BusinessEventType.DISCRETE)
        process = business_events_service.create_process(
            "Test Process",
            BusinessEventType.DISCRETE,
            TEST_PROCESS_DOMAIN,
            [event.id],
        )

        # Initial superset should be empty
        assert process.annotations_superset is not None
        assert len(process.annotations_superset.who) == 0

        # Update event annotations
        new_annotations = BusinessEventAnnotations(
            who=[AnnotationEntry(id="entry1", text="Customer A")]
        )
        business_events_service.update_event(event.id, {"annotations": new_annotations.model_dump()})

        # Reload process and check superset was recomputed
        processes = business_events_service.load_processes()
        updated_process = next(p for p in processes if p.id == process.id)

        assert updated_process.annotations_superset is not None
        assert len(updated_process.annotations_superset.who) == 1
        assert updated_process.annotations_superset.who[0].text == "Customer A"

    def test_recomputes_superset_when_event_added_to_process(self, temp_dir, monkeypatch):
        """Test that process superset is recomputed when event is added."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)
        monkeypatch.setattr(business_events_service, "_get_processes_path", lambda: events_path)

        event1 = business_events_service.create_event("event 1", BusinessEventType.DISCRETE)
        event2 = business_events_service.create_event("event 2", BusinessEventType.DISCRETE)

        annotations1 = BusinessEventAnnotations(
            who=[AnnotationEntry(id="entry1", text="Customer A")]
        )
        annotations2 = BusinessEventAnnotations(
            who=[AnnotationEntry(id="entry2", text="Customer B")]
        )

        business_events_service.update_event(event1.id, {"annotations": annotations1.model_dump()})
        business_events_service.update_event(event2.id, {"annotations": annotations2.model_dump()})

        process = business_events_service.create_process(
            "Test Process",
            BusinessEventType.DISCRETE,
            TEST_PROCESS_DOMAIN,
            [event1.id],
        )

        # Initial superset has only Customer A
        assert len(process.annotations_superset.who) == 1

        # Attach event2
        business_events_service.attach_events_to_process(process.id, [event2.id])

        # Manually recompute superset (attach doesn't auto-recompute, so we need to call it)
        updated_process = business_events_service.recompute_process_superset(process.id)

        assert len(updated_process.annotations_superset.who) == 2

    def test_recomputes_superset_when_event_removed_from_process(self, temp_dir, monkeypatch):
        """Test that process superset is recomputed when event is removed."""
        events_path = os.path.join(temp_dir, "business_events.yml")
        monkeypatch.setattr(business_events_service, "_get_business_events_path", lambda: events_path)
        monkeypatch.setattr(business_events_service, "_get_processes_path", lambda: events_path)

        event1 = business_events_service.create_event("event 1", BusinessEventType.DISCRETE)
        event2 = business_events_service.create_event("event 2", BusinessEventType.DISCRETE)

        annotations1 = BusinessEventAnnotations(
            who=[AnnotationEntry(id="entry1", text="Customer A")]
        )
        annotations2 = BusinessEventAnnotations(
            who=[AnnotationEntry(id="entry2", text="Customer B")]
        )

        business_events_service.update_event(event1.id, {"annotations": annotations1.model_dump()})
        business_events_service.update_event(event2.id, {"annotations": annotations2.model_dump()})

        process = business_events_service.create_process(
            "Test Process",
            BusinessEventType.DISCRETE,
            TEST_PROCESS_DOMAIN,
            [event1.id, event2.id],
        )

        # Initial superset has both customers
        assert len(process.annotations_superset.who) == 2

        # Detach event2
        business_events_service.detach_events_from_process(process.id, [event2.id])

        # Manually recompute superset
        updated_process = business_events_service.recompute_process_superset(process.id)

        assert len(updated_process.annotations_superset.who) == 1
        assert updated_process.annotations_superset.who[0].text == "Customer A"
