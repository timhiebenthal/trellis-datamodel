"""HTTP-level tests for the business events and processes routes."""

import pytest
from starlette.testclient import TestClient

from trellis_datamodel import config as cfg
from trellis_datamodel.services import business_events_service


@pytest.fixture
def client(tmp_path, monkeypatch):
    """TestClient with the feature enabled and storage redirected to tmp_path."""
    events_file = str(tmp_path / "business_events.yml")
    monkeypatch.setattr(
        business_events_service, "_get_business_events_path", lambda: events_file
    )
    monkeypatch.setattr(cfg, "BUSINESS_EVENTS_ENABLED", True)

    from trellis_datamodel.server import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def disabled_client(tmp_path, monkeypatch):
    """TestClient with the feature flag off."""
    events_file = str(tmp_path / "business_events.yml")
    monkeypatch.setattr(
        business_events_service, "_get_business_events_path", lambda: events_file
    )
    monkeypatch.setattr(cfg, "BUSINESS_EVENTS_ENABLED", False)

    from trellis_datamodel.server import app

    with TestClient(app) as test_client:
        yield test_client


def _create_event(client, text="customer buys product", **extra):
    response = client.post("/api/business-events", json={"text": text, **extra})
    assert response.status_code == 201, response.text
    return response.json()


def _create_process(client, event_ids, name="Order to cash", type="discrete"):
    response = client.post(
        "/api/processes",
        json={"name": name, "type": type, "domain": "Sales", "event_ids": event_ids},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _event_from_list(client, event_id):
    events = client.get("/api/business-events").json()
    return next(e for e in events if e["id"] == event_id)


def _process_from_list(client, process_id):
    processes = client.get("/api/processes").json()
    return next(p for p in processes if p["id"] == process_id)


# ---------------------------------------------------------------------------
# Feature flag
# ---------------------------------------------------------------------------


class TestFeatureDisabled:
    @pytest.mark.parametrize(
        "method,url,body",
        [
            ("get", "/api/business-events", None),
            ("get", "/api/business-events/domains", None),
            ("post", "/api/business-events", {"text": "x"}),
            ("put", "/api/business-events/evt_1", {"text": "x"}),
            ("delete", "/api/business-events/evt_1", None),
            ("get", "/api/processes", None),
            (
                "post",
                "/api/processes",
                {"name": "p", "type": "discrete", "domain": "d", "event_ids": ["e"]},
            ),
            ("post", "/api/processes/proc_1/resolve", None),
        ],
    )
    def test_endpoint_returns_403_when_feature_disabled(
        self, disabled_client, method, url, body
    ):
        response = getattr(disabled_client, method)(
            url, **({"json": body} if body is not None else {})
        )

        assert response.status_code == 403
        assert response.json()["error"] == "feature_disabled"


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


class TestListEvents:
    def test_list_is_empty_when_nothing_created(self, client):
        response = client.get("/api/business-events")

        assert response.status_code == 200
        assert response.json() == []

    def test_created_event_is_listed(self, client):
        created = _create_event(client, "customer buys product")

        events = client.get("/api/business-events").json()

        assert [e["id"] for e in events] == [created["id"]]
        assert events[0]["text"] == "customer buys product"


class TestCreateEvent:
    def test_returns_201_with_generated_id_and_defaults(self, client):
        response = client.post("/api/business-events", json={"text": "order placed"})

        assert response.status_code == 201
        body = response.json()
        assert body["id"].startswith("evt_")
        assert body["id"].endswith("_001")
        assert body["text"] == "order placed"
        assert body["type"] == "discrete"

    def test_text_is_stripped(self, client):
        created = _create_event(client, "  order placed  ")

        assert created["text"] == "order placed"

    def test_type_domain_and_description_are_stored(self, client):
        created = _create_event(
            client,
            "subscription runs",
            type="recurring",
            domain="Billing",
            description="monthly",
        )

        listed = _event_from_list(client, created["id"])
        assert listed["type"] == "recurring"
        assert listed["domain"] == "Billing"
        assert listed["description"] == "monthly"

    def test_second_event_gets_next_sequence_number(self, client):
        _create_event(client, "first")
        second = _create_event(client, "second")

        assert second["id"].endswith("_002")

    def test_annotations_in_request_are_persisted(self, client):
        created = _create_event(
            client,
            "customer buys product",
            annotations={"who": [{"id": "who_1", "text": "Customer"}]},
        )

        listed = _event_from_list(client, created["id"])
        assert [e["text"] for e in listed["annotations"]["who"]] == ["Customer"]

    def test_missing_text_is_rejected_with_422(self, client):
        response = client.post("/api/business-events", json={})

        assert response.status_code == 422

    def test_blank_text_is_rejected_with_422(self, client):
        response = client.post("/api/business-events", json={"text": "   "})

        assert response.status_code == 422
        assert "text" in response.json()["detail"].lower()

    def test_invalid_type_is_rejected_with_422(self, client):
        response = client.post(
            "/api/business-events", json={"text": "x", "type": "bogus"}
        )

        assert response.status_code == 422
        assert "Invalid event type" in response.json()["detail"]

    def test_invalid_type_is_not_persisted(self, client):
        client.post("/api/business-events", json={"text": "x", "type": "bogus"})

        assert client.get("/api/business-events").json() == []


class TestUpdateEvent:
    def test_updated_text_is_visible_in_list(self, client):
        created = _create_event(client, "old text")

        response = client.put(
            f"/api/business-events/{created['id']}", json={"text": "new text"}
        )

        assert response.status_code == 200
        assert response.json()["text"] == "new text"
        assert _event_from_list(client, created["id"])["text"] == "new text"

    def test_update_keeps_fields_not_in_request(self, client):
        created = _create_event(client, "keep me", domain="Sales")

        client.put(f"/api/business-events/{created['id']}", json={"type": "evolving"})

        listed = _event_from_list(client, created["id"])
        assert listed["text"] == "keep me"
        assert listed["domain"] == "Sales"
        assert listed["type"] == "evolving"

    def test_update_annotations_replaces_them(self, client):
        created = _create_event(client)

        client.put(
            f"/api/business-events/{created['id']}",
            json={"annotations": {"who": [{"id": "who_1", "text": "Customer"}]}},
        )

        listed = _event_from_list(client, created["id"])
        assert [e["text"] for e in listed["annotations"]["who"]] == ["Customer"]

    def test_unknown_event_returns_404(self, client):
        response = client.put("/api/business-events/evt_missing", json={"text": "x"})

        assert response.status_code == 404
        assert "evt_missing" in response.json()["detail"]

    def test_blank_text_returns_422(self, client):
        created = _create_event(client)

        response = client.put(
            f"/api/business-events/{created['id']}", json={"text": "  "}
        )

        assert response.status_code == 422

    def test_invalid_type_returns_422(self, client):
        created = _create_event(client)

        response = client.put(
            f"/api/business-events/{created['id']}", json={"type": "bogus"}
        )

        assert response.status_code == 422
        assert "Invalid event type" in response.json()["detail"]


class TestDeleteEvent:
    def test_returns_204_and_event_is_gone(self, client):
        created = _create_event(client)

        response = client.delete(f"/api/business-events/{created['id']}")

        assert response.status_code == 204
        assert client.get("/api/business-events").json() == []

    def test_only_the_targeted_event_is_removed(self, client):
        keep = _create_event(client, "keep")
        drop = _create_event(client, "drop")

        client.delete(f"/api/business-events/{drop['id']}")

        assert [e["id"] for e in client.get("/api/business-events").json()] == [
            keep["id"]
        ]

    def test_unknown_event_returns_404(self, client):
        response = client.delete("/api/business-events/evt_missing")

        assert response.status_code == 404

    def test_deleting_twice_returns_404_the_second_time(self, client):
        created = _create_event(client)
        client.delete(f"/api/business-events/{created['id']}")

        response = client.delete(f"/api/business-events/{created['id']}")

        assert response.status_code == 404


class TestDomains:
    def test_domains_empty_when_no_events(self, client):
        response = client.get("/api/business-events/domains")

        assert response.status_code == 200
        assert response.json() == []

    def test_domains_are_unique_and_sorted(self, client):
        _create_event(client, "a", domain="Sales")
        _create_event(client, "b", domain="Billing")
        _create_event(client, "c", domain="Sales")
        _create_event(client, "d")

        response = client.get("/api/business-events/domains")

        assert response.json() == ["Billing", "Sales"]


# ---------------------------------------------------------------------------
# Annotations
# ---------------------------------------------------------------------------


def _add_annotation(client, event_id, annotation_type="who", text="Customer", **extra):
    return client.post(
        f"/api/business-events/{event_id}/annotations",
        json={"annotation_type": annotation_type, "text": text, **extra},
    )


class TestAddAnnotation:
    def test_added_entry_appears_in_requested_category(self, client):
        event = _create_event(client)

        response = _add_annotation(client, event["id"], "what", "Product")

        assert response.status_code == 200
        entries = _event_from_list(client, event["id"])["annotations"]["what"]
        assert [e["text"] for e in entries] == ["Product"]

    def test_added_entry_gets_an_id(self, client):
        event = _create_event(client)

        body = _add_annotation(client, event["id"]).json()

        assert body["annotations"]["who"][0]["id"]

    def test_description_and_dimension_id_are_kept(self, client):
        event = _create_event(client)

        _add_annotation(
            client,
            event["id"],
            "who",
            "Customer",
            dimension_id="dim_customer",
            description="the buyer",
        )

        entry = _event_from_list(client, event["id"])["annotations"]["who"][0]
        assert entry["dimension_id"] == "dim_customer"
        assert entry["description"] == "the buyer"

    def test_two_entries_get_distinct_ids(self, client):
        event = _create_event(client)
        _add_annotation(client, event["id"], "who", "Customer")
        body = _add_annotation(client, event["id"], "who", "Seller").json()

        ids = [e["id"] for e in body["annotations"]["who"]]
        assert len(set(ids)) == 2

    def test_invalid_annotation_type_returns_422(self, client):
        event = _create_event(client)

        response = _add_annotation(client, event["id"], "bogus")

        assert response.status_code == 422
        assert "Invalid annotation_type" in response.json()["detail"]

    def test_blank_text_returns_422(self, client):
        event = _create_event(client)

        response = _add_annotation(client, event["id"], "who", "  ")

        assert response.status_code == 422

    def test_unknown_event_returns_404(self, client):
        response = _add_annotation(client, "evt_missing")

        assert response.status_code == 404


class TestUpdateAnnotation:
    def test_updated_text_is_visible_in_list(self, client):
        event = _create_event(client)
        entry_id = _add_annotation(client, event["id"]).json()["annotations"]["who"][
            0
        ]["id"]

        response = client.put(
            f"/api/business-events/{event['id']}/annotations/{entry_id}",
            json={"text": "Client"},
        )

        assert response.status_code == 200
        entries = _event_from_list(client, event["id"])["annotations"]["who"]
        assert [e["text"] for e in entries] == ["Client"]

    def test_update_keeps_entry_id(self, client):
        event = _create_event(client)
        entry_id = _add_annotation(client, event["id"]).json()["annotations"]["who"][
            0
        ]["id"]

        client.put(
            f"/api/business-events/{event['id']}/annotations/{entry_id}",
            json={"description": "the buyer"},
        )

        entry = _event_from_list(client, event["id"])["annotations"]["who"][0]
        assert entry["id"] == entry_id
        assert entry["description"] == "the buyer"
        assert entry["text"] == "Customer"

    def test_blank_text_returns_422(self, client):
        event = _create_event(client)
        entry_id = _add_annotation(client, event["id"]).json()["annotations"]["who"][
            0
        ]["id"]

        response = client.put(
            f"/api/business-events/{event['id']}/annotations/{entry_id}",
            json={"text": " "},
        )

        assert response.status_code == 422

    def test_unknown_entry_returns_404(self, client):
        event = _create_event(client)
        _add_annotation(client, event["id"])

        response = client.put(
            f"/api/business-events/{event['id']}/annotations/nope",
            json={"text": "x"},
        )

        assert response.status_code == 404

    def test_unknown_event_returns_404(self, client):
        response = client.put(
            "/api/business-events/evt_missing/annotations/x", json={"text": "x"}
        )

        assert response.status_code == 404


class TestRemoveAnnotation:
    def test_removed_entry_is_no_longer_listed(self, client):
        event = _create_event(client)
        entry_id = _add_annotation(client, event["id"]).json()["annotations"]["who"][
            0
        ]["id"]

        response = client.delete(
            f"/api/business-events/{event['id']}/annotations/{entry_id}"
        )

        assert response.status_code == 200
        assert _event_from_list(client, event["id"])["annotations"]["who"] == []

    def test_other_entries_survive_removal(self, client):
        event = _create_event(client)
        first = _add_annotation(client, event["id"], "who", "Customer").json()
        entry_id = first["annotations"]["who"][0]["id"]
        _add_annotation(client, event["id"], "who", "Seller")

        client.delete(f"/api/business-events/{event['id']}/annotations/{entry_id}")

        entries = _event_from_list(client, event["id"])["annotations"]["who"]
        assert [e["text"] for e in entries] == ["Seller"]

    def test_unknown_entry_returns_404(self, client):
        event = _create_event(client)
        _add_annotation(client, event["id"])

        response = client.delete(
            f"/api/business-events/{event['id']}/annotations/nope"
        )

        assert response.status_code == 404

    def test_unknown_event_returns_404(self, client):
        response = client.delete("/api/business-events/evt_missing/annotations/x")

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Processes
# ---------------------------------------------------------------------------


class TestCreateProcess:
    def test_returns_201_with_generated_id_and_members(self, client):
        event = _create_event(client)

        response = client.post(
            "/api/processes",
            json={
                "name": "Order to cash",
                "type": "evolving",
                "domain": "Sales",
                "event_ids": [event["id"]],
                "description": "end to end",
            },
        )

        assert response.status_code == 201
        body = response.json()
        assert body["id"].startswith("proc_")
        assert body["name"] == "Order to cash"
        assert body["type"] == "evolving"
        assert body["domain"] == "Sales"
        assert body["event_ids"] == [event["id"]]

    def test_created_process_is_listed(self, client):
        event = _create_event(client)
        process = _create_process(client, [event["id"]])

        assert [p["id"] for p in client.get("/api/processes").json()] == [
            process["id"]
        ]

    def test_member_event_links_back_to_process(self, client):
        event = _create_event(client)
        process = _create_process(client, [event["id"]])

        assert _event_from_list(client, event["id"])["process_id"] == process["id"]

    def test_domain_is_stripped(self, client):
        event = _create_event(client)

        response = client.post(
            "/api/processes",
            json={
                "name": "p",
                "type": "discrete",
                "domain": "  Sales  ",
                "event_ids": [event["id"]],
            },
        )

        assert response.json()["domain"] == "Sales"

    def test_missing_required_fields_returns_422(self, client):
        response = client.post("/api/processes", json={"name": "p"})

        assert response.status_code == 422

    def test_blank_domain_returns_422(self, client):
        event = _create_event(client)

        response = client.post(
            "/api/processes",
            json={
                "name": "p",
                "type": "discrete",
                "domain": "  ",
                "event_ids": [event["id"]],
            },
        )

        assert response.status_code == 422

    def test_blank_name_returns_422(self, client):
        event = _create_event(client)

        response = client.post(
            "/api/processes",
            json={
                "name": " ",
                "type": "discrete",
                "domain": "Sales",
                "event_ids": [event["id"]],
            },
        )

        assert response.status_code == 422

    def test_no_event_ids_returns_422(self, client):
        response = client.post(
            "/api/processes",
            json={"name": "p", "type": "discrete", "domain": "Sales"},
        )

        assert response.status_code == 422

    def test_invalid_type_returns_422(self, client):
        event = _create_event(client)

        response = client.post(
            "/api/processes",
            json={
                "name": "p",
                "type": "bogus",
                "domain": "Sales",
                "event_ids": [event["id"]],
            },
        )

        assert response.status_code == 422

    def test_unknown_event_id_returns_404(self, client):
        response = client.post(
            "/api/processes",
            json={
                "name": "p",
                "type": "discrete",
                "domain": "Sales",
                "event_ids": ["evt_missing"],
            },
        )

        assert response.status_code == 404

    def test_event_already_in_another_process_returns_422(self, client):
        event = _create_event(client)
        _create_process(client, [event["id"]])

        response = client.post(
            "/api/processes",
            json={
                "name": "second",
                "type": "discrete",
                "domain": "Sales",
                "event_ids": [event["id"]],
            },
        )

        assert response.status_code == 422


class TestListProcesses:
    def test_empty_when_none_created(self, client):
        response = client.get("/api/processes")

        assert response.status_code == 200
        assert response.json() == []


class TestUpdateProcess:
    def test_updated_name_is_visible_in_list(self, client):
        event = _create_event(client)
        process = _create_process(client, [event["id"]])

        response = client.put(
            f"/api/processes/{process['id']}", json={"name": "Renamed"}
        )

        assert response.status_code == 200
        assert _process_from_list(client, process["id"])["name"] == "Renamed"

    def test_update_keeps_fields_not_in_request(self, client):
        event = _create_event(client)
        process = _create_process(client, [event["id"]], type="recurring")

        client.put(f"/api/processes/{process['id']}", json={"name": "Renamed"})

        listed = _process_from_list(client, process["id"])
        assert listed["type"] == "recurring"
        assert listed["domain"] == "Sales"
        assert listed["event_ids"] == [event["id"]]

    def test_event_ids_update_relinks_events(self, client):
        first = _create_event(client, "first")
        second = _create_event(client, "second")
        process = _create_process(client, [first["id"]])

        client.put(
            f"/api/processes/{process['id']}", json={"event_ids": [second["id"]]}
        )

        assert _event_from_list(client, first["id"])["process_id"] is None
        assert _event_from_list(client, second["id"])["process_id"] == process["id"]

    def test_unknown_process_returns_404(self, client):
        response = client.put("/api/processes/proc_missing", json={"name": "x"})

        assert response.status_code == 404

    def test_empty_body_returns_422(self, client):
        event = _create_event(client)
        process = _create_process(client, [event["id"]])

        response = client.put(f"/api/processes/{process['id']}", json={})

        assert response.status_code == 422

    def test_blank_domain_returns_422(self, client):
        event = _create_event(client)
        process = _create_process(client, [event["id"]])

        response = client.put(f"/api/processes/{process['id']}", json={"domain": " "})

        assert response.status_code == 422

    def test_invalid_type_returns_422(self, client):
        event = _create_event(client)
        process = _create_process(client, [event["id"]])

        response = client.put(f"/api/processes/{process['id']}", json={"type": "x"})

        assert response.status_code == 422

    def test_empty_event_ids_returns_422(self, client):
        event = _create_event(client)
        process = _create_process(client, [event["id"]])

        response = client.put(f"/api/processes/{process['id']}", json={"event_ids": []})

        assert response.status_code == 422

    def test_resolved_process_cannot_be_updated(self, client):
        event = _create_event(client)
        process = _create_process(client, [event["id"]])
        client.post(f"/api/processes/{process['id']}/resolve")

        response = client.put(f"/api/processes/{process['id']}", json={"name": "x"})

        assert response.status_code == 422
        assert "resolved" in response.json()["detail"].lower()


class TestResolveProcess:
    def test_resolved_process_has_resolved_at_set(self, client):
        event = _create_event(client)
        process = _create_process(client, [event["id"]])

        response = client.post(f"/api/processes/{process['id']}/resolve")

        assert response.status_code == 200
        assert response.json()["resolved_at"] is not None
        assert _process_from_list(client, process["id"])["resolved_at"] is not None

    def test_resolving_frees_member_events(self, client):
        event = _create_event(client)
        process = _create_process(client, [event["id"]])

        client.post(f"/api/processes/{process['id']}/resolve")

        assert _event_from_list(client, event["id"])["process_id"] is None

    def test_resolving_twice_returns_422(self, client):
        event = _create_event(client)
        process = _create_process(client, [event["id"]])
        client.post(f"/api/processes/{process['id']}/resolve")

        response = client.post(f"/api/processes/{process['id']}/resolve")

        assert response.status_code == 422
        assert "already resolved" in response.json()["detail"]

    def test_unknown_process_returns_404(self, client):
        response = client.post("/api/processes/proc_missing/resolve")

        assert response.status_code == 404


class TestAttachEvents:
    def test_attached_event_becomes_a_member(self, client):
        member = _create_event(client, "member")
        extra = _create_event(client, "extra")
        process = _create_process(client, [member["id"]])

        response = client.post(
            f"/api/processes/{process['id']}/attach", json={"event_ids": [extra["id"]]}
        )

        assert response.status_code == 200
        assert _process_from_list(client, process["id"])["event_ids"] == [
            member["id"],
            extra["id"],
        ]
        assert _event_from_list(client, extra["id"])["process_id"] == process["id"]

    def test_attaching_event_owned_by_other_process_returns_422(self, client):
        first = _create_event(client, "first")
        second = _create_event(client, "second")
        _create_process(client, [first["id"]], name="one")
        other = _create_process(client, [second["id"]], name="two")

        response = client.post(
            f"/api/processes/{other['id']}/attach", json={"event_ids": [first["id"]]}
        )

        assert response.status_code == 422
        assert "already attached" in response.json()["detail"]

    def test_unknown_process_returns_404(self, client):
        event = _create_event(client)

        response = client.post(
            "/api/processes/proc_missing/attach", json={"event_ids": [event["id"]]}
        )

        assert response.status_code == 404

    def test_attaching_to_resolved_process_returns_422(self, client):
        member = _create_event(client, "member")
        extra = _create_event(client, "extra")
        process = _create_process(client, [member["id"]])
        client.post(f"/api/processes/{process['id']}/resolve")

        response = client.post(
            f"/api/processes/{process['id']}/attach", json={"event_ids": [extra["id"]]}
        )

        assert response.status_code == 422
        assert "resolved" in response.json()["detail"]

    def test_unknown_event_returns_404(self, client):
        member = _create_event(client)
        process = _create_process(client, [member["id"]])

        response = client.post(
            f"/api/processes/{process['id']}/attach",
            json={"event_ids": ["evt_missing"]},
        )

        assert response.status_code == 404

    def test_empty_event_ids_returns_422(self, client):
        member = _create_event(client)
        process = _create_process(client, [member["id"]])

        response = client.post(
            f"/api/processes/{process['id']}/attach", json={"event_ids": []}
        )

        assert response.status_code == 422


class TestDetachEvents:
    def test_detached_event_is_no_longer_a_member(self, client):
        first = _create_event(client, "first")
        second = _create_event(client, "second")
        process = _create_process(client, [first["id"], second["id"]])

        response = client.post(
            f"/api/processes/{process['id']}/detach", json={"event_ids": [second["id"]]}
        )

        assert response.status_code == 200
        assert _process_from_list(client, process["id"])["event_ids"] == [first["id"]]
        assert _event_from_list(client, second["id"])["process_id"] is None

    def test_other_members_keep_their_link(self, client):
        first = _create_event(client, "first")
        second = _create_event(client, "second")
        process = _create_process(client, [first["id"], second["id"]])

        client.post(
            f"/api/processes/{process['id']}/detach", json={"event_ids": [second["id"]]}
        )

        assert _event_from_list(client, first["id"])["process_id"] == process["id"]

    def test_unknown_process_returns_404(self, client):
        response = client.post(
            "/api/processes/proc_missing/detach", json={"event_ids": ["evt_1"]}
        )

        assert response.status_code == 404

    def test_empty_event_ids_returns_422(self, client):
        member = _create_event(client)
        process = _create_process(client, [member["id"]])

        response = client.post(
            f"/api/processes/{process['id']}/detach", json={"event_ids": []}
        )

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Entity generation (error mapping)
# ---------------------------------------------------------------------------


class TestGenerateEntitiesErrors:
    def test_unknown_event_returns_404(self, client):
        response = client.post("/api/business-events/evt_missing/generate-entities")

        assert response.status_code == 404

    def test_unknown_process_returns_404(self, client):
        response = client.post("/api/processes/proc_missing/generate-entities")

        assert response.status_code == 404

    def test_generate_is_forbidden_when_feature_disabled(self, disabled_client):
        response = disabled_client.post("/api/business-events/evt_1/generate-entities")

        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Error mapping (global handlers in server.py)
# ---------------------------------------------------------------------------


class TestErrorMapping:
    def test_validation_error_is_422_with_message_and_error_code(self, client):
        response = client.post(
            "/api/processes",
            json={"name": "p", "type": "bogus", "domain": "Sales", "event_ids": []},
        )

        assert response.status_code == 422
        assert response.json() == {
            "detail": "Invalid process type: bogus. Must be one of: discrete, evolving, recurring",
            "error": "validation_error",
        }

    def test_request_checks_run_before_the_process_lookup(self, client):
        response = client.put("/api/processes/proc_missing", json={})

        assert response.status_code == 422
        assert response.json()["detail"] == "No fields provided to update"

    def test_unknown_event_ids_are_listed_together(self, client):
        response = client.post(
            "/api/processes",
            json={
                "name": "p",
                "type": "discrete",
                "domain": "Sales",
                "event_ids": ["evt_a", "evt_b"],
            },
        )

        assert response.status_code == 404
        assert response.json() == {
            "detail": "Events not found: evt_a, evt_b",
            "error": "not_found",
        }

    def test_unexpected_error_is_500_without_leaking_the_exception(
        self, client, monkeypatch
    ):
        from trellis_datamodel.routes import business_events as routes
        from trellis_datamodel.server import app

        def boom():
            raise RuntimeError("private failure detail")

        monkeypatch.setattr(routes, "load_business_events", boom)

        with TestClient(app, raise_server_exceptions=False) as raw_client:
            response = raw_client.get("/api/business-events")

        assert response.status_code == 500
        assert response.json() == {
            "detail": "Internal Server Error",
            "error": "internal_error",
        }
        assert "private failure detail" not in response.text
