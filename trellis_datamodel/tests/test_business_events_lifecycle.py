"""Behaviour tests for business event lifecycles: annotations, role sync,
process membership, storage failures.

All checks go through the service's public functions and read state back via
``load_business_events`` / ``load_processes`` (or GET /api/data-model for the
role-to-dimension sync).
"""

import os

import pytest
from starlette.testclient import TestClient

from trellis_datamodel import config as cfg
from trellis_datamodel.exceptions import (
    FileOperationError,
    NotFoundError,
    ValidationError,
)
from trellis_datamodel.models.business_event import BusinessEventType
from trellis_datamodel.services import business_events_service as svc

DISCRETE = BusinessEventType.DISCRETE
ALL_WS = ["who", "what", "when", "where", "how", "how_many", "why"]


@pytest.fixture(autouse=True)
def events_file(tmp_path, monkeypatch):
    path = str(tmp_path / "business_events.yml")
    monkeypatch.setattr(svc, "_get_business_events_path", lambda: path)
    return path


@pytest.fixture
def client():
    from trellis_datamodel.server import app

    with TestClient(app) as test_client:
        yield test_client


def _event(text="customer buys product", **kwargs):
    return svc.create_event(text, DISCRETE, **kwargs)


def _stored_event(event_id):
    return next(e for e in svc.load_business_events() if e.id == event_id)


def _stored_process(process_id):
    return next(p for p in svc.load_processes() if p.id == process_id)


def _process(event_ids, name="Order to cash", domain="Sales"):
    return svc.create_process(name, DISCRETE, domain, event_ids)


def _texts(entries):
    return [e.text for e in entries]


def _put_dimension(client, dim_id, roles=None):
    entity = {
        "id": dim_id,
        "label": dim_id,
        "entity_type": "dimension",
        "position": {"x": 0, "y": 0},
        "width": 200,
        "collapsed": False,
    }
    if roles is not None:
        entity["roles"] = roles
    response = client.post(
        "/api/data-model",
        json={"version": 0.1, "entities": [entity], "relationships": []},
    )
    assert response.status_code == 200, response.text


def _roles_of(client, dim_id):
    entities = client.get("/api/data-model").json()["entities"]
    return next(e for e in entities if e["id"] == dim_id).get("roles")


# ---------------------------------------------------------------------------
# Storage location resolution and failures
# ---------------------------------------------------------------------------


class TestStorageLocation:
    @pytest.fixture(autouse=True)
    def real_path_resolution(self, monkeypatch):
        # undo the module-level redirect so config-driven resolution is used
        monkeypatch.undo()

    def test_explicit_config_path_is_used(self, tmp_path, monkeypatch):
        target = tmp_path / "custom.yml"
        monkeypatch.setattr(cfg, "BUSINESS_EVENTS_PATH", str(target))

        _event("configured location")

        assert target.exists()
        assert _texts(svc.load_business_events()) == ["configured location"]

    def test_defaults_to_directory_of_data_model(self, tmp_path, monkeypatch):
        model_dir = tmp_path / "model"
        model_dir.mkdir()
        monkeypatch.setattr(cfg, "BUSINESS_EVENTS_PATH", "")
        monkeypatch.setattr(cfg, "DATA_MODEL_PATH", str(model_dir / "data_model.yml"))

        _event("next to the data model")

        assert (model_dir / "business_events.yml").exists()

    def test_falls_back_to_working_directory(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cfg, "BUSINESS_EVENTS_PATH", "")
        monkeypatch.setattr(cfg, "DATA_MODEL_PATH", "")
        monkeypatch.chdir(tmp_path)

        _event("in cwd")

        assert (tmp_path / "business_events.yml").exists()


class TestStorageFailures:
    def test_load_events_from_unreadable_path_raises_file_operation_error(self, tmp_path):
        with pytest.raises(FileOperationError, match="Failed to read"):
            svc.load_business_events(path=str(tmp_path))

    def test_load_processes_from_unreadable_path_raises_file_operation_error(self, tmp_path):
        with pytest.raises(FileOperationError, match="Failed to read"):
            svc.load_processes(path=str(tmp_path))

    def test_load_processes_with_invalid_yaml_raises_file_operation_error(self, events_file):
        with open(events_file, "w") as f:
            f.write("processes: [unclosed")

        with pytest.raises(FileOperationError, match="Invalid business events file format"):
            svc.load_processes()

    def test_load_processes_with_malformed_process_raises_file_operation_error(self, events_file):
        with open(events_file, "w") as f:
            f.write("events: []\nprocesses:\n  - id: proc_1\n")

        with pytest.raises(FileOperationError, match="Invalid business events file format"):
            svc.load_processes()

    def test_save_events_to_directory_path_raises_file_operation_error(self, tmp_path):
        with pytest.raises(FileOperationError, match="Failed to write"):
            svc.save_business_events([], path=str(tmp_path))

    def test_save_processes_to_directory_path_raises_file_operation_error(self, tmp_path):
        with pytest.raises(FileOperationError, match="Failed to write"):
            svc.save_processes([], path=str(tmp_path))

    def test_load_with_empty_file_and_no_events_key_is_invalid(self, events_file):
        open(events_file, "w").close()

        with pytest.raises(FileOperationError, match="Invalid business events file format"):
            svc.load_business_events()

    def test_saving_events_keeps_existing_processes(self):
        event = _event()
        process = _process([event.id])

        svc.save_business_events(svc.load_business_events())

        assert [p.id for p in svc.load_processes()] == [process.id]

    def test_saving_processes_keeps_existing_events(self):
        event = _event()
        _process([event.id])

        svc.save_processes(svc.load_processes())

        assert [e.id for e in svc.load_business_events()] == [event.id]


class TestUniqueDomains:
    def test_returns_sorted_distinct_domains_without_blanks(self):
        _event("a", domain="Sales")
        _event("b", domain="Finance")
        _event("c", domain="Sales")
        _event("d")

        assert svc.get_unique_domains() == ["Finance", "Sales"]


# ---------------------------------------------------------------------------
# update_event field edge cases
# ---------------------------------------------------------------------------


class TestUpdateEventFields:
    def test_description_is_stripped(self):
        event = _event()

        svc.update_event(event.id, {"description": "  longer context  "})

        assert _stored_event(event.id).description == "longer context"

    def test_empty_description_clears_it(self):
        event = _event()
        svc.update_event(event.id, {"description": "something"})

        svc.update_event(event.id, {"description": ""})

        assert _stored_event(event.id).description is None

    @pytest.mark.xfail(
        strict=True,
        reason="Whitespace-only description is stored as '' instead of None (empty string clears to None).",
    )
    def test_whitespace_only_description_clears_it(self):
        event = _event()
        svc.update_event(event.id, {"description": "something"})

        svc.update_event(event.id, {"description": "   "})

        assert _stored_event(event.id).description is None

    def test_blank_domain_clears_it(self):
        event = _event(domain="Sales")

        svc.update_event(event.id, {"domain": "  "})

        assert _stored_event(event.id).domain is None

    def test_domain_is_stripped(self):
        event = _event()

        svc.update_event(event.id, {"domain": "  Sales "})

        assert _stored_event(event.id).domain == "Sales"

    def test_derived_entities_are_stored(self):
        event = _event()

        svc.update_event(
            event.id,
            {"derived_entities": [{"entity_id": "customer", "created_at": "2026-01-02T03:04:05"}]},
        )

        derived = _stored_event(event.id).derived_entities
        assert [d.entity_id for d in derived] == ["customer"]

    def test_blank_process_id_unlinks_event(self):
        event = _event()
        _process([event.id])

        svc.update_event(event.id, {"process_id": ""})

        assert _stored_event(event.id).process_id is None

    def test_missing_event_raises_not_found(self):
        with pytest.raises(NotFoundError):
            svc.update_event("evt_missing", {"text": "x"})

    def test_whitespace_only_text_is_rejected_and_event_unchanged(self):
        event = _event("original")

        with pytest.raises(ValidationError, match="cannot be empty"):
            svc.update_event(event.id, {"text": "   "})

        assert _stored_event(event.id).text == "original"


# ---------------------------------------------------------------------------
# Annotation entry CRUD
# ---------------------------------------------------------------------------


class TestAddAnnotationEntry:
    @pytest.mark.parametrize("category", ALL_WS)
    def test_entry_lands_in_requested_category_only(self, category):
        event = _event()

        svc.add_annotation_entry(event.id, category, "Thing")

        stored = _stored_event(event.id).annotations
        for other in ALL_WS:
            expected = ["Thing"] if other == category else []
            assert _texts(getattr(stored, other)) == expected

    def test_entry_gets_generated_id_and_stripped_text(self):
        event = _event()

        updated = svc.add_annotation_entry(event.id, "who", "  customer  ")

        entry = updated.annotations.who[0]
        assert entry.text == "customer"
        assert entry.id.startswith("entry_")

    def test_optional_fields_are_persisted(self):
        event = _event()

        svc.add_annotation_entry(
            event.id,
            "what",
            "product",
            dimension_id="dim_product",
            description="sold item",
            attributes={"source": "crm"},
        )

        entry = _stored_event(event.id).annotations.what[0]
        assert (entry.dimension_id, entry.description, entry.attributes) == (
            "dim_product",
            "sold item",
            {"source": "crm"},
        )

    def test_two_entries_get_distinct_ids(self):
        event = _event()
        svc.add_annotation_entry(event.id, "who", "customer")

        updated = svc.add_annotation_entry(event.id, "who", "seller")

        ids = [e.id for e in updated.annotations.who]
        assert len(set(ids)) == 2

    def test_invalid_category_is_rejected(self):
        event = _event()

        with pytest.raises(ValidationError, match="Invalid annotation_type"):
            svc.add_annotation_entry(event.id, "whom", "customer")

    def test_blank_text_is_rejected(self):
        event = _event()

        with pytest.raises(ValidationError, match="Entry text is required"):
            svc.add_annotation_entry(event.id, "who", "   ")

    def test_missing_event_raises_not_found(self):
        with pytest.raises(NotFoundError):
            svc.add_annotation_entry("evt_missing", "who", "customer")


class TestRemoveAnnotationEntry:
    def test_removes_only_the_targeted_entry(self):
        event = _event()
        svc.add_annotation_entry(event.id, "who", "customer")
        with_two = svc.add_annotation_entry(event.id, "what", "product")
        who_id = with_two.annotations.who[0].id

        svc.remove_annotation_entry(event.id, who_id)

        stored = _stored_event(event.id).annotations
        assert (_texts(stored.who), _texts(stored.what)) == ([], ["product"])

    def test_unknown_entry_raises_not_found(self):
        event = _event()
        svc.add_annotation_entry(event.id, "who", "customer")

        with pytest.raises(NotFoundError, match="entry_nope"):
            svc.remove_annotation_entry(event.id, "entry_nope")

    def test_unknown_entry_on_event_without_entries_raises_not_found(self):
        event = _event()

        with pytest.raises(NotFoundError, match="entry_nope"):
            svc.remove_annotation_entry(event.id, "entry_nope")

    def test_missing_event_raises_not_found(self):
        with pytest.raises(NotFoundError, match="evt_missing"):
            svc.remove_annotation_entry("evt_missing", "entry_x")


class TestUpdateAnnotationEntry:
    @pytest.fixture
    def event_with_entry(self):
        event = _event()
        updated = svc.add_annotation_entry(
            event.id,
            "who",
            "customer",
            description="buyer",
            attributes={"k": "v"},
        )
        return event.id, updated.annotations.who[0].id

    def test_text_is_replaced_and_stripped(self, event_with_entry):
        event_id, entry_id = event_with_entry

        svc.update_annotation_entry(event_id, entry_id, text="  client  ")

        assert _stored_event(event_id).annotations.who[0].text == "client"

    def test_fields_not_passed_are_left_untouched(self, event_with_entry):
        event_id, entry_id = event_with_entry

        svc.update_annotation_entry(event_id, entry_id, text="client")

        entry = _stored_event(event_id).annotations.who[0]
        assert (entry.description, entry.attributes) == ("buyer", {"k": "v"})

    def test_dimension_description_and_attributes_can_be_set(self, event_with_entry):
        event_id, entry_id = event_with_entry

        svc.update_annotation_entry(
            event_id,
            entry_id,
            dimension_id="dim_customer",
            description="the purchaser",
            attributes={"a": 1},
        )

        entry = _stored_event(event_id).annotations.who[0]
        assert (entry.dimension_id, entry.description, entry.attributes) == (
            "dim_customer",
            "the purchaser",
            {"a": 1},
        )

    def test_blank_text_is_rejected_and_entry_unchanged(self, event_with_entry):
        event_id, entry_id = event_with_entry

        with pytest.raises(ValidationError, match="cannot be empty"):
            svc.update_annotation_entry(event_id, entry_id, text="  ")

        assert _stored_event(event_id).annotations.who[0].text == "customer"

    def test_unknown_entry_raises_not_found(self, event_with_entry):
        event_id, _ = event_with_entry

        with pytest.raises(NotFoundError, match="entry_nope"):
            svc.update_annotation_entry(event_id, "entry_nope", text="x")

    def test_event_without_entries_raises_not_found(self):
        event = _event()

        with pytest.raises(NotFoundError, match="entry_nope"):
            svc.update_annotation_entry(event.id, "entry_nope", text="x")

    def test_missing_event_raises_not_found(self):
        with pytest.raises(NotFoundError, match="evt_missing"):
            svc.update_annotation_entry("evt_missing", "entry_x", text="x")


class TestReplaceAnnotations:
    def test_replaces_whole_annotation_structure(self):
        event = _event()
        svc.add_annotation_entry(event.id, "who", "customer")

        svc.update_event_annotations(
            event.id, {"what": [{"id": "e1", "text": "product"}]}
        )

        stored = _stored_event(event.id).annotations
        assert (_texts(stored.who), _texts(stored.what)) == ([], ["product"])

    def test_missing_event_raises_not_found(self):
        with pytest.raises(NotFoundError):
            svc.update_event_annotations("evt_missing", {})

    def test_duplicate_entry_ids_across_categories_are_rejected(self):
        event = _event()

        with pytest.raises(Exception, match="Duplicate entry IDs"):
            svc.update_event_annotations(
                event.id,
                {
                    "who": [{"id": "same", "text": "customer"}],
                    "what": [{"id": "same", "text": "product"}],
                },
            )

        assert _stored_event(event.id).annotations.who == []


# ---------------------------------------------------------------------------
# Deleting events that belong to processes
# ---------------------------------------------------------------------------


class TestDeleteEventInProcess:
    def test_deleting_one_of_two_events_shrinks_process_and_superset(self):
        e1 = _event("one")
        e2 = _event("two")
        svc.add_annotation_entry(e1.id, "who", "customer")
        svc.add_annotation_entry(e2.id, "who", "seller")
        process = _process([e1.id, e2.id])

        svc.delete_event(e2.id)

        stored = _stored_process(process.id)
        assert stored.event_ids == [e1.id]
        assert _texts(stored.annotations_superset.who) == ["customer"]
        assert stored.resolved_at is None

    def test_deleting_last_event_resolves_process(self):
        event = _event()
        process = _process([event.id])

        svc.delete_event(event.id)

        stored = _stored_process(process.id)
        assert stored.event_ids == []
        assert stored.resolved_at is not None


# ---------------------------------------------------------------------------
# Role to dimension sync (verified through GET /api/data-model)
# ---------------------------------------------------------------------------


class TestRoleToDimensionSync:
    def test_annotation_role_is_added_to_the_referenced_dimension(self, client):
        _put_dimension(client, "customer")
        event = _event()

        svc.update_event(
            event.id,
            {"annotations": {"who": [{"id": "a", "text": "buyer", "dimension_id": "customer", "role": "buyer"}]}},
        )

        assert _roles_of(client, "customer") == ["buyer"]

    def test_second_role_is_appended_after_the_first(self, client):
        _put_dimension(client, "customer")
        event = _event()
        who = lambda role: {"who": [{"id": "a", "text": "c", "dimension_id": "customer", "role": role}]}

        svc.update_event(event.id, {"annotations": who("buyer")})
        svc.update_event(event.id, {"annotations": who("seller")})

        assert _roles_of(client, "customer") == ["buyer", "seller"]

    def test_same_role_is_not_added_twice(self, client):
        _put_dimension(client, "customer")
        event = _event()
        annotations = {"who": [{"id": "a", "text": "c", "dimension_id": "customer", "role": "buyer"}]}

        svc.update_event(event.id, {"annotations": annotations})
        svc.update_event(event.id, {"annotations": annotations})

        assert _roles_of(client, "customer") == ["buyer"]

    def test_entry_without_role_leaves_dimension_roles_untouched(self, client):
        _put_dimension(client, "customer")
        event = _event()

        svc.update_event(
            event.id,
            {"annotations": {"who": [{"id": "a", "text": "c", "dimension_id": "customer"}]}},
        )

        assert _roles_of(client, "customer") is None

    def test_entry_without_dimension_does_not_create_roles(self, client):
        _put_dimension(client, "customer")
        event = _event()

        svc.update_event(
            event.id,
            {"annotations": {"who": [{"id": "a", "text": "c", "role": "buyer"}]}},
        )

        assert _roles_of(client, "customer") is None

    def test_how_many_entries_do_not_sync_roles(self, client):
        _put_dimension(client, "customer")
        event = _event()

        svc.update_event(
            event.id,
            {"annotations": {"how_many": [{"id": "a", "text": "c", "dimension_id": "customer", "role": "buyer"}]}},
        )

        assert _roles_of(client, "customer") is None

    def test_unknown_dimension_id_is_ignored_and_annotation_still_saved(self, client):
        _put_dimension(client, "customer")
        event = _event()

        svc.update_event(
            event.id,
            {"annotations": {"who": [{"id": "a", "text": "c", "dimension_id": "ghost", "role": "buyer"}]}},
        )

        assert _roles_of(client, "customer") is None
        assert _stored_event(event.id).annotations.who[0].role == "buyer"

    def test_process_recompute_syncs_member_event_roles(self, client):
        event = _event()
        # dimension does not exist yet, so the save-time sync has nothing to update
        svc.update_event(
            event.id,
            {"annotations": {"who": [{"id": "a", "text": "c", "dimension_id": "customer", "role": "buyer"}]}},
        )
        _put_dimension(client, "customer")
        assert _roles_of(client, "customer") is None
        process = _process([event.id])

        svc.recompute_process_superset(process.id)

        assert _roles_of(client, "customer") == ["buyer"]

    def test_explicit_process_superset_update_syncs_roles(self, client):
        _put_dimension(client, "customer")
        event = _event()
        process = _process([event.id])

        svc.update_process(
            process.id,
            {"annotations_superset": {"who": [{"id": "a", "text": "c", "dimension_id": "customer", "role": "buyer"}]}},
        )

        assert _roles_of(client, "customer") == ["buyer"]

    def test_role_is_synced_onto_dimension_that_already_has_structured_roles(self, client):
        _put_dimension(
            client,
            "customer",
            roles=[{"label": "payer", "role": "payer", "source": "manual"}],
        )
        event = _event()

        svc.update_event(
            event.id,
            {"annotations": {"who": [{"id": "a", "text": "c", "dimension_id": "customer", "role": "buyer"}]}},
        )

        assert "buyer" in str(_roles_of(client, "customer"))


# ---------------------------------------------------------------------------
# Process membership: attach / detach / update
# ---------------------------------------------------------------------------


class TestAttachEvents:
    def test_attached_event_is_listed_in_process_and_linked_back(self):
        e1, e2 = _event("one"), _event("two")
        process = _process([e1.id])

        svc.attach_events_to_process(process.id, [e2.id])

        assert _stored_process(process.id).event_ids == [e1.id, e2.id]
        assert _stored_event(e2.id).process_id == process.id

    def test_attaching_an_already_member_event_does_not_duplicate_it(self):
        e1 = _event()
        process = _process([e1.id])

        result = svc.attach_events_to_process(process.id, [e1.id])

        assert result.event_ids == [e1.id]

    def test_missing_process_raises_not_found(self):
        e1 = _event()

        with pytest.raises(NotFoundError, match="proc_missing"):
            svc.attach_events_to_process("proc_missing", [e1.id])

    def test_missing_event_raises_not_found_and_process_unchanged(self):
        e1 = _event()
        process = _process([e1.id])

        with pytest.raises(NotFoundError, match="evt_missing"):
            svc.attach_events_to_process(process.id, ["evt_missing"])

        assert _stored_process(process.id).event_ids == [e1.id]

    def test_event_in_other_process_is_rejected(self):
        e1, e2 = _event("one"), _event("two")
        _process([e1.id], name="first")
        other = _process([e2.id], name="second")

        with pytest.raises(ValidationError, match="already attached"):
            svc.attach_events_to_process(other.id, [e1.id])

    def test_resolved_process_rejects_attach(self):
        e1, e2 = _event("one"), _event("two")
        process = _process([e1.id])
        svc.resolve_process(process.id)

        with pytest.raises(ValidationError, match="resolved"):
            svc.attach_events_to_process(process.id, [e2.id])


class TestDetachEvents:
    def test_detached_event_leaves_process_and_is_unlinked(self):
        e1, e2 = _event("one"), _event("two")
        process = _process([e1.id, e2.id])

        svc.detach_events_from_process(process.id, [e2.id])

        assert _stored_process(process.id).event_ids == [e1.id]
        assert _stored_event(e2.id).process_id is None
        assert _stored_event(e1.id).process_id == process.id

    def test_detaching_non_member_changes_nothing(self):
        e1, e2 = _event("one"), _event("two")
        process = _process([e1.id])

        svc.detach_events_from_process(process.id, [e2.id])

        assert _stored_process(process.id).event_ids == [e1.id]

    def test_missing_process_raises_not_found(self):
        with pytest.raises(NotFoundError, match="proc_missing"):
            svc.detach_events_from_process("proc_missing", ["evt_x"])


class TestUpdateProcess:
    def test_name_is_stripped(self):
        process = _process([_event().id])

        svc.update_process(process.id, {"name": "  Renamed  "})

        assert _stored_process(process.id).name == "Renamed"

    def test_blank_name_is_rejected(self):
        process = _process([_event().id])

        with pytest.raises(ValidationError, match="name cannot be empty"):
            svc.update_process(process.id, {"name": " "})

    def test_type_can_be_changed(self):
        process = _process([_event().id])

        svc.update_process(process.id, {"type": "recurring"})

        assert _stored_process(process.id).type == BusinessEventType.RECURRING

    def test_invalid_type_is_rejected(self):
        process = _process([_event().id])

        with pytest.raises(ValidationError, match="Invalid process type"):
            svc.update_process(process.id, {"type": "sometimes"})

    def test_description_is_stripped_and_blank_clears_it(self):
        process = _process([_event().id])

        svc.update_process(process.id, {"description": "  context "})
        assert _stored_process(process.id).description == "context"

        svc.update_process(process.id, {"description": ""})
        assert _stored_process(process.id).description is None

    def test_domain_is_stripped(self):
        process = _process([_event().id])

        svc.update_process(process.id, {"domain": " Finance "})

        assert _stored_process(process.id).domain == "Finance"

    def test_blank_domain_is_rejected(self):
        process = _process([_event().id])

        with pytest.raises(ValidationError):
            svc.update_process(process.id, {"domain": " "})

    def test_derived_entities_are_stored(self):
        process = _process([_event().id])

        svc.update_process(
            process.id,
            {"derived_entities": [{"entity_id": "order", "created_at": "2026-01-02T03:04:05"}]},
        )

        assert [d.entity_id for d in _stored_process(process.id).derived_entities] == ["order"]

    def test_superset_can_be_cleared_with_none(self):
        event = _event()
        svc.add_annotation_entry(event.id, "who", "customer")
        process = _process([event.id])

        svc.update_process(process.id, {"annotations_superset": None})

        assert _stored_process(process.id).annotations_superset is None

    def test_explicit_superset_is_stored(self):
        process = _process([_event().id])

        svc.update_process(
            process.id,
            {"annotations_superset": {"why": [{"id": "w1", "text": "growth"}]}},
        )

        assert _texts(_stored_process(process.id).annotations_superset.why) == ["growth"]

    def test_replacing_event_ids_relinks_events_and_recomputes_superset(self):
        e1, e2 = _event("one"), _event("two")
        svc.add_annotation_entry(e1.id, "who", "customer")
        svc.add_annotation_entry(e2.id, "who", "seller")
        process = _process([e1.id])

        svc.update_process(process.id, {"event_ids": [e2.id]})

        stored = _stored_process(process.id)
        assert stored.event_ids == [e2.id]
        assert _texts(stored.annotations_superset.who) == ["seller"]
        assert _stored_event(e1.id).process_id is None
        assert _stored_event(e2.id).process_id == process.id

    def test_empty_event_ids_are_rejected(self):
        process = _process([_event().id])

        with pytest.raises(ValidationError, match="at least one event"):
            svc.update_process(process.id, {"event_ids": []})

    def test_unknown_event_id_is_rejected(self):
        process = _process([_event().id])

        with pytest.raises(NotFoundError, match="evt_missing"):
            svc.update_process(process.id, {"event_ids": ["evt_missing"]})

    def test_missing_process_raises_not_found(self):
        with pytest.raises(NotFoundError, match="proc_missing"):
            svc.update_process("proc_missing", {"name": "x"})

    def test_resolved_process_cannot_be_updated(self):
        process = _process([_event().id])
        svc.resolve_process(process.id)

        with pytest.raises(ValidationError, match="resolved"):
            svc.update_process(process.id, {"name": "x"})


class TestCreateProcessValidation:
    def test_blank_name_is_rejected(self):
        event = _event()

        with pytest.raises(ValidationError, match="name is required"):
            svc.create_process(" ", DISCRETE, "Sales", [event.id])

    def test_no_events_is_rejected(self):
        with pytest.raises(ValidationError, match="At least one event"):
            svc.create_process("p", DISCRETE, "Sales", [])

    def test_missing_domain_is_rejected(self):
        event = _event()

        with pytest.raises(ValidationError):
            svc.create_process("p", DISCRETE, "  ", [event.id])

    def test_unknown_event_is_rejected(self):
        with pytest.raises(NotFoundError, match="evt_missing"):
            svc.create_process("p", DISCRETE, "Sales", ["evt_missing"])

    def test_second_process_same_day_gets_next_sequence_number(self):
        e1, e2 = _event("one"), _event("two")

        p1 = _process([e1.id], name="first")
        p2 = _process([e2.id], name="second")

        assert p1.id.endswith("001") and p2.id.endswith("002")


# ---------------------------------------------------------------------------
# Resolve and superset recompute
# ---------------------------------------------------------------------------


class TestResolveProcess:
    def test_resolving_clears_superset_and_derived_entities(self):
        event = _event()
        svc.add_annotation_entry(event.id, "who", "customer")
        process = _process([event.id])
        svc.update_process(
            process.id,
            {"derived_entities": [{"entity_id": "order", "created_at": "2026-01-02T03:04:05"}]},
        )

        svc.resolve_process(process.id)

        stored = _stored_process(process.id)
        assert stored.annotations_superset is None
        assert stored.derived_entities == []
        assert stored.resolved_at is not None
        assert stored.event_ids == []

    def test_resolved_process_keeps_member_event_annotations(self):
        event = _event()
        svc.add_annotation_entry(event.id, "who", "customer")
        process = _process([event.id])

        svc.resolve_process(process.id)

        assert _texts(_stored_event(event.id).annotations.who) == ["customer"]


class TestRecomputeSuperset:
    def test_superset_follows_member_annotation_changes(self):
        event = _event()
        process = _process([event.id])

        svc.add_annotation_entry(event.id, "how", "online")

        assert _texts(_stored_process(process.id).annotations_superset.how) == ["online"]

    def test_unions_same_text_across_events_case_insensitively(self):
        e1, e2 = _event("one"), _event("two")
        svc.add_annotation_entry(e1.id, "who", "Customer")
        svc.add_annotation_entry(e2.id, "who", " customer ")
        process = _process([e1.id, e2.id])

        assert _texts(process.annotations_superset.who) == ["Customer"]

    def test_dimension_linked_entry_replaces_same_text_unlinked_one(self):
        e1, e2 = _event("one"), _event("two")
        svc.add_annotation_entry(e1.id, "who", "customer")
        svc.add_annotation_entry(e2.id, "who", "customer", dimension_id="dim_customer")

        process = _process([e1.id, e2.id])

        who = process.annotations_superset.who
        assert [(e.text, e.dimension_id) for e in who] == [("customer", "dim_customer")]

    def test_entries_with_same_dimension_collapse_to_first(self):
        e1, e2 = _event("one"), _event("two")
        svc.add_annotation_entry(e1.id, "who", "buyer", dimension_id="dim_customer")
        svc.add_annotation_entry(e2.id, "who", "client", dimension_id="dim_customer")

        process = _process([e1.id, e2.id])

        assert _texts(process.annotations_superset.who) == ["buyer"]

    def test_unlinked_entry_matching_linked_text_is_dropped(self):
        e1, e2 = _event("one"), _event("two")
        svc.add_annotation_entry(e1.id, "who", "customer", dimension_id="dim_customer")
        svc.add_annotation_entry(e2.id, "who", "customer")

        process = _process([e1.id, e2.id])

        assert [(e.text, e.dimension_id) for e in process.annotations_superset.who] == [
            ("customer", "dim_customer")
        ]

    def test_same_text_in_different_categories_is_kept_in_both(self):
        event = _event()
        svc.add_annotation_entry(event.id, "who", "store")
        svc.add_annotation_entry(event.id, "where", "store")

        process = _process([event.id])

        assert _texts(process.annotations_superset.who) == ["store"]
        assert _texts(process.annotations_superset.where) == ["store"]

    def test_unknown_process_raises_not_found(self):
        with pytest.raises(NotFoundError, match="proc_missing"):
            svc.recompute_process_superset("proc_missing")

    def test_resolved_process_is_returned_without_recompute(self):
        event = _event()
        process = _process([event.id])
        svc.resolve_process(process.id)

        result = svc.recompute_process_superset(process.id)

        assert result.annotations_superset is None
        assert result.resolved_at is not None

    def test_recompute_all_refreshes_active_and_skips_resolved(self):
        e1, e2 = _event("one"), _event("two")
        active = _process([e1.id], name="active")
        done = _process([e2.id], name="done")
        svc.resolve_process(done.id)
        svc.update_process(active.id, {"annotations_superset": None})

        svc.recompute_all_process_supersets()

        assert _stored_process(active.id).annotations_superset is not None
        assert _stored_process(done.id).annotations_superset is None

    def test_recompute_all_without_processes_is_a_no_op(self):
        svc.recompute_all_process_supersets()

        assert svc.load_processes() == []
