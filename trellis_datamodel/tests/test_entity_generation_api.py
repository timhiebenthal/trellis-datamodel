"""HTTP-level characterization tests for entity generation from events and processes."""

import pytest
from starlette.testclient import TestClient

from trellis_datamodel import config as cfg
from trellis_datamodel.services import business_events_service


@pytest.fixture
def client(tmp_path, monkeypatch):
    """TestClient in dimensional modeling style with storage redirected to tmp_path."""
    events_file = str(tmp_path / "business_events.yml")
    monkeypatch.setattr(
        business_events_service, "_get_business_events_path", lambda: events_file
    )
    monkeypatch.setattr(cfg, "BUSINESS_EVENTS_ENABLED", True)
    monkeypatch.setattr(cfg, "MODELING_STYLE", "dimensional_model")
    monkeypatch.setattr(
        cfg,
        "DIMENSIONAL_MODELING_CONFIG",
        cfg.DimensionalModelingConfig(
            enabled=True, dimension_prefix=["dim_"], fact_prefix=["fct_"]
        ),
    )

    from trellis_datamodel.server import app

    with TestClient(app) as test_client:
        yield test_client


def _event_with_annotations(client, text, annotations, **extra):
    """Create an event and add (annotation_type, text) entries to it."""
    response = client.post("/api/business-events", json={"text": text, **extra})
    assert response.status_code == 201, response.text
    event = response.json()
    for annotation_type, entry_text in annotations:
        added = client.post(
            f"/api/business-events/{event['id']}/annotations",
            json={"annotation_type": annotation_type, "text": entry_text},
        )
        assert added.status_code == 200, added.text
    return event


def _process_over(
    client, event_ids, name="Order to cash", type="discrete", domain="Sales", **extra
):
    response = client.post(
        "/api/processes",
        json={
            "name": name,
            "type": type,
            "domain": domain,
            "event_ids": event_ids,
            **extra,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _generate_for_event(client, event_id):
    response = client.post(f"/api/business-events/{event_id}/generate-entities")
    assert response.status_code == 200, response.text
    return response.json()


def _generate_for_process(client, process_id):
    response = client.post(f"/api/processes/{process_id}/generate-entities")
    assert response.status_code == 200, response.text
    return response.json()


def _by_type(result, entity_type):
    return [e for e in result["entities"] if e["entity_type"] == entity_type]


def _field_names(entity):
    return [f["name"] for f in entity["drafted_fields"]]


ORDER_ANNOTATIONS = [
    ("who", "customer"),
    ("what", "product"),
    ("how_many", "quantity"),
]


class TestGenerateFromEvent:
    def test_event_yields_prefixed_dimensions_and_one_fact(self, client):
        event = _event_with_annotations(
            client, "customer buys product", ORDER_ANNOTATIONS
        )

        result = _generate_for_event(client, event["id"])

        assert result["errors"] == []
        assert [e["id"] for e in _by_type(result, "dimension")] == [
            "dim_customer",
            "dim_product",
        ]
        assert [e["id"] for e in _by_type(result, "fact")] == [
            "fct_customer_buys_product"
        ]

    def test_every_dimension_relates_one_to_many_to_the_fact(self, client):
        event = _event_with_annotations(
            client, "customer buys product", ORDER_ANNOTATIONS
        )

        result = _generate_for_event(client, event["id"])

        assert [(r["source"], r["target"], r["type"]) for r in result["relationships"]] == [
            ("dim_customer", "fct_customer_buys_product", "one_to_many"),
            ("dim_product", "fct_customer_buys_product", "one_to_many"),
        ]

    def test_how_many_entries_become_fact_fields(self, client):
        event = _event_with_annotations(
            client,
            "customer buys product",
            ORDER_ANNOTATIONS + [("how_many", "unit price")],
        )

        result = _generate_for_event(client, event["id"])

        assert _field_names(_by_type(result, "fact")[0]) == ["quantity", "unit_price"]

    def test_event_domain_is_set_on_entities_and_slugified_into_tag(self, client):
        event = _event_with_annotations(
            client, "customer buys product", ORDER_ANNOTATIONS, domain="Customer Sales"
        )

        result = _generate_for_event(client, event["id"])

        for entity in result["entities"]:
            assert entity["domain"] == "Customer Sales"
            assert entity["tags"] == ["customer-sales"]

    def test_event_without_how_many_reports_an_error_and_no_entities(self, client):
        event = _event_with_annotations(client, "customer buys", [("who", "customer")])

        result = _generate_for_event(client, event["id"])

        assert result["entities"] == []
        assert result["errors"] == [
            "At least one 'How Many' entry is required for fact table"
        ]

    def test_event_with_only_how_many_reports_a_dimension_error(self, client):
        event = _event_with_annotations(client, "sale", [("how_many", "quantity")])

        result = _generate_for_event(client, event["id"])

        assert result["entities"] == []
        assert result["errors"] == [
            "At least one dimension entry (Who, What, When, Where, How, or Why) is required"
        ]

    def test_event_without_annotations_reports_an_error(self, client):
        event = _event_with_annotations(client, "nothing yet", [])

        result = _generate_for_event(client, event["id"])

        assert result["entities"] == []
        assert result["errors"] == ["Event must have annotation entries"]

    def test_repeated_dimension_text_is_generated_once(self, client):
        event = _event_with_annotations(
            client,
            "customer buys product",
            [("who", "customer"), ("what", "customer"), ("how_many", "quantity")],
        )

        result = _generate_for_event(client, event["id"])

        assert [e["id"] for e in _by_type(result, "dimension")] == ["dim_customer"]
        assert len(result["relationships"]) == 1

    def test_dimension_text_already_carrying_prefix_is_not_double_prefixed(
        self, client
    ):
        event = _event_with_annotations(
            client,
            "customer buys",
            [("who", "dim_customer"), ("how_many", "quantity")],
        )

        result = _generate_for_event(client, event["id"])

        assert [e["id"] for e in _by_type(result, "dimension")] == ["dim_customer"]


class TestGenerateFromDiscreteProcess:
    @pytest.fixture
    def process(self, client):
        first = _event_with_annotations(
            client,
            "customer places order",
            [("who", "customer"), ("how_many", "quantity")],
            domain="Sales",
        )
        second = _event_with_annotations(
            client,
            "customer pays invoice",
            [("who", "customer"), ("what", "invoice"), ("how_many", "amount")],
        )
        return _process_over(client, [first["id"], second["id"]], name="Order to cash")

    def test_fact_is_named_after_the_process(self, client, process):
        result = _generate_for_process(client, process["id"])

        assert result["errors"] == []
        fact = _by_type(result, "fact")[0]
        assert fact["id"] == "fct_order_to_cash"
        assert fact["label"] == "Order To Cash"

    def test_dimensions_come_from_the_union_of_member_events(self, client, process):
        result = _generate_for_process(client, process["id"])

        assert [e["id"] for e in _by_type(result, "dimension")] == [
            "dim_customer",
            "dim_invoice",
        ]

    def test_fact_carries_measures_plus_event_and_process_id_columns(
        self, client, process
    ):
        result = _generate_for_process(client, process["id"])

        assert _field_names(_by_type(result, "fact")[0]) == [
            "quantity",
            "amount",
            "event_id",
            "process_id",
        ]

    def test_fact_metadata_describes_the_process(self, client, process):
        result = _generate_for_process(client, process["id"])

        metadata = _by_type(result, "fact")[0]["metadata"]
        assert metadata["process_id"] == process["id"]
        assert metadata["process_name"] == "Order to cash"
        assert metadata["process_type"] == "discrete"
        assert metadata["event_ids"] == process["event_ids"]
        assert metadata["event_count"] == 2

    def test_fact_description_defaults_to_discrete_wording(self, client, process):
        result = _generate_for_process(client, process["id"])

        assert (
            _by_type(result, "fact")[0]["description"]
            == "Fact: Order To Cash (discrete process)"
        )

    def test_process_description_overrides_default_fact_description(self, client):
        event = _event_with_annotations(client, "order", ORDER_ANNOTATIONS)
        process = _process_over(
            client, [event["id"]], description="Tracks every order"
        )

        result = _generate_for_process(client, process["id"])

        assert _by_type(result, "fact")[0]["description"] == "Tracks every order"

    def test_every_dimension_relates_to_the_process_fact(self, client, process):
        result = _generate_for_process(client, process["id"])

        assert [(r["source"], r["target"]) for r in result["relationships"]] == [
            ("dim_customer", "fct_order_to_cash"),
            ("dim_invoice", "fct_order_to_cash"),
        ]

    def test_process_domain_wins_over_member_event_domain(self, client):
        event = _event_with_annotations(
            client, "order", ORDER_ANNOTATIONS, domain="Sales"
        )
        process = _process_over(client, [event["id"]], domain="Finance")

        result = _generate_for_process(client, process["id"])

        for entity in result["entities"]:
            assert entity["domain"] == "Finance"
            assert entity["tags"] == ["finance"]

    def test_recurring_process_is_generated_like_a_discrete_one(self, client):
        event = _event_with_annotations(client, "order", ORDER_ANNOTATIONS)
        process = _process_over(client, [event["id"]], type="recurring")

        result = _generate_for_process(client, process["id"])

        assert _field_names(_by_type(result, "fact")[0])[-2:] == [
            "event_id",
            "process_id",
        ]


class TestGenerateFromEvolvingProcess:
    @pytest.fixture
    def process(self, client):
        event = _event_with_annotations(client, "order", ORDER_ANNOTATIONS)
        return _process_over(client, [event["id"]], name="Loan lifecycle", type="evolving")

    def test_fact_carries_measures_and_process_id_but_no_event_id(
        self, client, process
    ):
        result = _generate_for_process(client, process["id"])

        assert _field_names(_by_type(result, "fact")[0]) == ["quantity", "process_id"]

    def test_fact_description_defaults_to_evolving_wording(self, client, process):
        result = _generate_for_process(client, process["id"])

        assert (
            _by_type(result, "fact")[0]["description"]
            == "Fact: Loan Lifecycle (evolving process)"
        )

    def test_fact_metadata_reports_evolving_type(self, client, process):
        result = _generate_for_process(client, process["id"])

        assert _by_type(result, "fact")[0]["metadata"]["process_type"] == "evolving"

    def test_fact_id_does_not_repeat_an_existing_prefix(self, client):
        event = _event_with_annotations(client, "order", ORDER_ANNOTATIONS)
        process = _process_over(
            client, [event["id"]], name="fct loans", type="evolving"
        )

        result = _generate_for_process(client, process["id"])

        assert _by_type(result, "fact")[0]["id"] == "fct_loans"


class TestGenerateFromProcessErrors:
    def test_resolved_process_cannot_generate(self, client):
        event = _event_with_annotations(client, "order", ORDER_ANNOTATIONS)
        process = _process_over(client, [event["id"]])
        client.post(f"/api/processes/{process['id']}/resolve")

        result = _generate_for_process(client, process["id"])

        assert result["entities"] == []
        assert result["errors"] == ["Cannot generate entities from a resolved process"]

    def test_process_without_how_many_reports_an_error(self, client):
        event = _event_with_annotations(client, "order", [("who", "customer")])
        process = _process_over(client, [event["id"]])

        result = _generate_for_process(client, process["id"])

        assert result["entities"] == []
        assert result["errors"] == [
            "At least one 'How Many' entry is required for fact table"
        ]

    def test_process_with_only_how_many_reports_a_dimension_error(self, client):
        event = _event_with_annotations(client, "order", [("how_many", "quantity")])
        process = _process_over(client, [event["id"]])

        result = _generate_for_process(client, process["id"])

        assert result["entities"] == []
        assert result["errors"] == [
            "At least one dimension entry (Who, What, When, Where, How, or Why) is required"
        ]


class TestGenerateFromProcessEntityModel:
    @pytest.fixture
    def entity_client(self, client, monkeypatch):
        monkeypatch.setattr(cfg, "MODELING_STYLE", "entity_model")
        return client

    def test_process_becomes_a_single_entity_with_drafted_fields(self, entity_client):
        event = _event_with_annotations(
            entity_client,
            "customer places order",
            [("who", "customer"), ("how_many", "quantity")],
        )
        process = _process_over(entity_client, [event["id"]], name="Order to cash")

        result = _generate_for_process(entity_client, process["id"])

        assert result["errors"] == []
        assert result["relationships"] == []
        [entity] = result["entities"]
        assert entity["id"] == "order_to_cash"
        assert entity["entity_type"] == "entity"
        assert entity["metadata"]["process_id"] == process["id"]
        assert _field_names(entity) == ["customer", "quantity"]

    def test_linked_dimension_becomes_a_many_to_one_relationship(self, entity_client):
        event = entity_client.post(
            "/api/business-events", json={"text": "customer places order"}
        ).json()
        entity_client.post(
            f"/api/business-events/{event['id']}/annotations",
            json={
                "annotation_type": "who",
                "text": "customer",
                "dimension_id": "customer_entity",
            },
        )
        process = _process_over(entity_client, [event["id"]], name="Order to cash")

        result = _generate_for_process(entity_client, process["id"])

        assert [
            (r["source"], r["target"], r["type"], r["label"])
            for r in result["relationships"]
        ] == [("order_to_cash", "customer_entity", "many_to_one", "customer")]
