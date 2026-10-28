"""Characterization tests for POST/GET /api/data-model save-merge behaviour.

All assertions go through the HTTP interface (POST then GET).
"""

import os

import pytest

from trellis_datamodel import config as cfg


def _save(client, entities, relationships=None, **extra):
    payload = {
        "version": 0.1,
        "entities": entities,
        "relationships": relationships or [],
        **extra,
    }
    response = client.post("/api/data-model", json=payload)
    assert response.status_code == 200, response.text
    return response


def _load(client):
    response = client.get("/api/data-model")
    assert response.status_code == 200, response.text
    return response.json()


def _entity(client, entity_id):
    return next(e for e in _load(client)["entities"] if e["id"] == entity_id)


class TestEntityFiltering:
    def test_entity_without_id_is_dropped(self, test_client):
        _save(test_client, [{"label": "No id"}, {"id": "a", "label": "A"}])
        assert [e["id"] for e in _load(test_client)["entities"]] == ["a"]

    def test_duplicate_entity_id_keeps_first_occurrence(self, test_client):
        _save(
            test_client,
            [{"id": "a", "label": "First"}, {"id": "a", "label": "Second"}],
        )
        entities = _load(test_client)["entities"]
        assert len(entities) == 1
        assert entities[0]["label"] == "First"

    def test_missing_label_defaults_to_empty_string(self, test_client):
        _save(test_client, [{"id": "a"}])
        assert _entity(test_client, "a")["label"] == ""

    def test_relationship_without_source_or_target_is_dropped(self, test_client):
        _save(
            test_client,
            [{"id": "a"}, {"id": "b"}],
            [
                {"source": "a"},
                {"target": "b"},
                {"source": "a", "target": "b", "type": "one_to_many"},
            ],
        )
        rels = _load(test_client)["relationships"]
        assert len(rels) == 1
        assert (rels[0]["source"], rels[0]["target"]) == ("a", "b")

    def test_relationship_fields_round_trip(self, test_client):
        _save(
            test_client,
            [{"id": "a"}, {"id": "b"}],
            [
                {
                    "source": "a",
                    "target": "b",
                    "label": "has",
                    "type": "one_to_many",
                    "source_field": "id",
                    "target_field": "a_id",
                    "label_dx": 5,
                    "label_dy": -7,
                }
            ],
        )
        rel = _load(test_client)["relationships"][0]
        assert rel["label"] == "has"
        assert rel["type"] == "one_to_many"
        assert rel["source_field"] == "id"
        assert rel["target_field"] == "a_id"
        assert rel["label_dx"] == 5
        assert rel["label_dy"] == -7


class TestLayoutSplit:
    def test_layout_fields_round_trip_via_get(self, test_client):
        _save(
            test_client,
            [
                {
                    "id": "a",
                    "position": {"x": 1, "y": 2},
                    "width": 250,
                    "panel_height": 120,
                    "collapsed": True,
                }
            ],
        )
        entity = _entity(test_client, "a")
        assert entity["position"] == {"x": 1, "y": 2}
        assert entity["width"] == 250
        assert entity["panel_height"] == 120
        assert entity["collapsed"] is True

    def test_source_colors_round_trip(self, test_client):
        _save(test_client, [{"id": "a"}], source_colors={"crm": "#ff0000"})
        assert _load(test_client)["source_colors"] == {"crm": "#ff0000"}

    def test_source_colors_dropped_when_omitted_on_later_save(self, test_client):
        _save(test_client, [{"id": "a"}], source_colors={"crm": "#ff0000"})
        _save(test_client, [{"id": "a"}])
        assert _load(test_client)["source_colors"] == {}

    def test_source_colors_available_without_data_model_file(
        self, test_client, temp_canvas_layout_path
    ):
        with open(temp_canvas_layout_path, "w") as f:
            f.write("version: 0.1\nsource_colors:\n  erp: '#00ff00'\n")
        data = _load(test_client)
        assert data["entities"] == []
        assert data["source_colors"] == {"erp": "#00ff00"}

    def test_null_source_colors_in_layout_file_read_as_empty(
        self, test_client, temp_data_model_path, temp_canvas_layout_path
    ):
        with open(temp_data_model_path, "w") as f:
            f.write("version: 0.1\nentities:\n  - id: a\n")
        with open(temp_canvas_layout_path, "w") as f:
            f.write("version: 0.1\nsource_colors:\n")
        assert _load(test_client)["source_colors"] == {}

    def test_unreadable_layout_file_is_ignored_on_get(
        self, test_client, temp_data_model_path, temp_canvas_layout_path
    ):
        with open(temp_data_model_path, "w") as f:
            f.write("version: 0.1\nentities:\n  - id: a\n    label: A\n")
        with open(temp_canvas_layout_path, "w") as f:
            f.write("entities: [unclosed\n  : : :")
        data = _load(test_client)
        assert data["entities"][0]["id"] == "a"
        assert "position" not in data["entities"][0]
        assert data["source_colors"] == {}


class TestOptionalFieldPersistence:
    def test_descriptive_fields_round_trip(self, test_client):
        _save(
            test_client,
            [
                {
                    "id": "a",
                    "label": "A",
                    "description": "An entity",
                    "domain": "sales",
                    "domains": ["sales", "finance"],
                    "annotation_type": "note",
                    "additional_models": ["model.p.b"],
                }
            ],
        )
        entity = _entity(test_client, "a")
        assert entity["description"] == "An entity"
        assert entity["domain"] == "sales"
        assert entity["domains"] == ["sales", "finance"]
        assert entity["annotation_type"] == "note"
        assert entity["additional_models"] == ["model.p.b"]

    def test_unbound_entity_keeps_source_system_and_tags(self, test_client):
        _save(
            test_client,
            [{"id": "a", "tags": ["x"], "source_system": ["crm"]}],
        )
        entity = _entity(test_client, "a")
        assert entity["tags"] == ["x"]
        assert entity["source_system"] == ["crm"]

    def test_bound_entity_tags_are_derived_from_ui_tags_not_payload_tags(
        self, test_client
    ):
        _save(
            test_client,
            [
                {
                    "id": "a",
                    "model_ref": "model.p.a",
                    "tags": ["stale"],
                    "ui_tags": ["pii"],
                }
            ],
        )
        assert _entity(test_client, "a")["tags"] == ["pii"]

    def test_bound_entity_does_not_keep_payload_source_system(self, test_client):
        _save(
            test_client,
            [{"id": "a", "model_ref": "model.p.a", "source_system": ["crm"]}],
        )
        assert "source_system" not in _entity(test_client, "a")

    def test_drafted_field_origin_string_is_parsed_and_blank_origin_removed(
        self, test_client
    ):
        _save(
            test_client,
            [
                {
                    "id": "a",
                    "drafted_fields": [
                        {"name": "good", "origin": "source: crm | table: customers"},
                        {"name": "bad", "origin": ""},
                    ],
                }
            ],
        )
        fields = {f["name"]: f for f in _entity(test_client, "a")["drafted_fields"]}
        assert fields["good"]["origin"] == [{"source": "crm"}, {"table": "customers"}]
        assert "origin" not in fields["bad"]


class TestModelRefPreservation:
    def test_omitted_model_ref_keeps_existing_binding(self, test_client):
        _save(test_client, [{"id": "a", "model_ref": "model.p.a"}])
        _save(test_client, [{"id": "a", "label": "Renamed"}])
        entity = _entity(test_client, "a")
        assert entity["model_ref"] == "model.p.a"
        assert entity["label"] == "Renamed"

    def test_explicit_null_model_ref_unbinds(self, test_client):
        _save(test_client, [{"id": "a", "model_ref": "model.p.a"}])
        _save(test_client, [{"id": "a", "model_ref": None}])
        assert not _entity(test_client, "a").get("model_ref")


class TestTagPreservation:
    def test_omitted_framework_tags_kept_for_bound_entity(self, test_client):
        _save(
            test_client,
            [{"id": "a", "model_ref": "model.p.a", "framework_tags": ["nightly"]}],
        )
        _save(test_client, [{"id": "a", "model_ref": "model.p.a", "ui_tags": ["pii"]}])
        assert _entity(test_client, "a")["tags"] == ["nightly", "pii"]

    def test_omitted_framework_tags_not_kept_for_unbound_entity(self, test_client):
        _save(test_client, [{"id": "a", "framework_tags": ["nightly"]}])
        _save(test_client, [{"id": "a", "tags": ["mine"]}])
        assert _entity(test_client, "a")["tags"] == ["mine"]

    def test_omitted_ui_tags_after_push_record_clears_ui_tags(
        self, test_client, temp_data_model_path
    ):
        # pushed_tags is backend-owned, so seed it the way a push would.
        with open(temp_data_model_path, "w") as f:
            f.write(
                "version: 0.1\nentities:\n"
                "  - id: a\n    model_ref: model.p.a\n"
                "    ui_tags: [pii]\n    pushed_tags: [pii]\n"
            )
        _save(test_client, [{"id": "a", "model_ref": "model.p.a"}])
        assert _entity(test_client, "a")["tags"] == []

    def test_push_record_is_dropped_when_entity_rebound_to_other_model(
        self, test_client, temp_data_model_path
    ):
        with open(temp_data_model_path, "w") as f:
            f.write(
                "version: 0.1\nentities:\n"
                "  - id: a\n    model_ref: model.p.a\n"
                "    ui_tags: [pii]\n    pushed_tags: [pii]\n"
            )
        _save(test_client, [{"id": "a", "model_ref": "model.p.other"}])
        # On a different model the push record no longer applies, so the
        # previously stored ui_tags are not carried over either.
        assert _entity(test_client, "a")["tags"] == []


class TestEntityTypePreservation:
    def test_omitted_entity_type_keeps_existing_value(self, test_client):
        _save(test_client, [{"id": "a", "entity_type": "dimension"}])
        _save(test_client, [{"id": "a", "label": "A"}])
        assert _entity(test_client, "a")["entity_type"] == "dimension"

    def test_explicit_entity_type_overrides_existing_value(self, test_client):
        _save(test_client, [{"id": "a", "entity_type": "dimension"}])
        _save(test_client, [{"id": "a", "entity_type": "fact"}])
        assert _entity(test_client, "a")["entity_type"] == "fact"

    def test_omitted_entity_type_on_new_entity_stays_absent(self, test_client):
        _save(test_client, [{"id": "a"}])
        assert "entity_type" not in _entity(test_client, "a")

    @pytest.mark.parametrize("value", ["fact", "dimension", "unclassified", "entity"])
    def test_accepts_each_valid_entity_type(self, test_client, value):
        _save(test_client, [{"id": "a", "entity_type": value}])
        assert _entity(test_client, "a")["entity_type"] == value

    def test_rejects_invalid_entity_type_with_422(self, test_client):
        response = test_client.post(
            "/api/data-model",
            json={
                "version": 0.1,
                "entities": [{"id": "a", "entity_type": "bogus"}],
                "relationships": [],
            },
        )
        assert response.status_code == 422
        assert response.json()["error"] == "validation_error"
        assert "bogus" in response.json()["detail"]

    def test_rejected_save_does_not_change_stored_model(self, test_client):
        _save(test_client, [{"id": "keep", "label": "Keep"}])
        test_client.post(
            "/api/data-model",
            json={
                "version": 0.1,
                "entities": [{"id": "new", "entity_type": "bogus"}],
                "relationships": [],
            },
        )
        assert [e["id"] for e in _load(test_client)["entities"]] == ["keep"]


class TestRolesMerge:
    ROLE_A = {"label": "Buyer", "role": "customer", "source": "orders"}
    ROLE_B = {"label": "Seller", "role": "vendor", "source": "orders"}

    def test_new_entity_stores_incoming_roles(self, test_client):
        _save(test_client, [{"id": "a", "roles": [self.ROLE_A]}])
        assert _entity(test_client, "a")["roles"] == [self.ROLE_A]

    def test_incoming_roles_are_unioned_with_existing(self, test_client):
        _save(test_client, [{"id": "a", "roles": [self.ROLE_A]}])
        _save(test_client, [{"id": "a", "roles": [self.ROLE_B]}])
        assert _entity(test_client, "a")["roles"] == [self.ROLE_A, self.ROLE_B]

    def test_roles_with_same_label_and_source_are_not_duplicated(self, test_client):
        _save(test_client, [{"id": "a", "roles": [self.ROLE_A]}])
        _save(
            test_client,
            [{"id": "a", "roles": [self.ROLE_A, {**self.ROLE_B}]}],
        )
        assert _entity(test_client, "a")["roles"] == [self.ROLE_A, self.ROLE_B]

    def test_same_label_different_source_is_kept_as_separate_role(self, test_client):
        other_source = {**self.ROLE_A, "source": "invoices"}
        _save(test_client, [{"id": "a", "roles": [self.ROLE_A]}])
        _save(test_client, [{"id": "a", "roles": [other_source]}])
        assert _entity(test_client, "a")["roles"] == [self.ROLE_A, other_source]

    def test_omitted_roles_keep_existing(self, test_client):
        _save(test_client, [{"id": "a", "roles": [self.ROLE_A]}])
        _save(test_client, [{"id": "a", "label": "A"}])
        assert _entity(test_client, "a")["roles"] == [self.ROLE_A]

    def test_null_roles_keep_existing(self, test_client):
        _save(test_client, [{"id": "a", "roles": [self.ROLE_A]}])
        _save(test_client, [{"id": "a", "roles": None}])
        assert _entity(test_client, "a")["roles"] == [self.ROLE_A]

    def test_empty_incoming_roles_keep_existing(self, test_client):
        _save(test_client, [{"id": "a", "roles": [self.ROLE_A]}])
        _save(test_client, [{"id": "a", "roles": []}])
        assert _entity(test_client, "a")["roles"] == [self.ROLE_A]

    def test_null_roles_on_new_entity_stores_no_roles(self, test_client):
        _save(test_client, [{"id": "a", "roles": None}])
        assert "roles" not in _entity(test_client, "a")

    def test_flat_string_roles_in_payload_are_ignored_when_merging(
        self, test_client
    ):
        _save(test_client, [{"id": "a", "roles": [self.ROLE_A]}])
        _save(test_client, [{"id": "a", "roles": ["legacy", self.ROLE_B]}])
        assert _entity(test_client, "a")["roles"] == [self.ROLE_A, self.ROLE_B]

    def test_only_flat_string_roles_over_existing_leave_existing_unchanged(
        self, test_client
    ):
        _save(test_client, [{"id": "a", "roles": [self.ROLE_A]}])
        _save(test_client, [{"id": "a", "roles": ["legacy"]}])
        assert _entity(test_client, "a")["roles"] == [self.ROLE_A]

    def test_rejects_non_list_roles_with_422(self, test_client):
        response = test_client.post(
            "/api/data-model",
            json={
                "version": 0.1,
                "entities": [{"id": "a", "roles": "customer"}],
                "relationships": [],
            },
        )
        assert response.status_code == 422
        assert "roles must be a list" in response.json()["detail"]

    def test_rejects_roles_with_non_string_non_dict_item_with_422(self, test_client):
        response = test_client.post(
            "/api/data-model",
            json={
                "version": 0.1,
                "entities": [{"id": "a", "roles": [42]}],
                "relationships": [],
            },
        )
        assert response.status_code == 422
        assert "roles must be a list" in response.json()["detail"]


class TestEntityTypeInferenceOnRead:
    @pytest.fixture
    def dimensional(self, monkeypatch):
        monkeypatch.setattr(
            cfg,
            "DIMENSIONAL_MODELING_CONFIG",
            cfg.DimensionalModelingConfig(
                enabled=True, dimension_prefix=["dim_"], fact_prefix=["fct_"]
            ),
        )

    def test_unbound_entity_type_inferred_from_dimension_prefix(
        self, test_client, dimensional
    ):
        _save(test_client, [{"id": "dim_customer"}])
        assert _entity(test_client, "dim_customer")["entity_type"] == "dimension"

    def test_unbound_entity_type_inferred_from_fact_prefix(
        self, test_client, dimensional
    ):
        _save(test_client, [{"id": "FCT_orders"}])
        assert _entity(test_client, "FCT_orders")["entity_type"] == "fact"

    def test_unclassified_entity_is_reinferred(self, test_client, dimensional):
        _save(test_client, [{"id": "dim_x", "entity_type": "unclassified"}])
        assert _entity(test_client, "dim_x")["entity_type"] == "dimension"

    def test_entity_without_matching_prefix_gets_no_type(
        self, test_client, dimensional
    ):
        _save(test_client, [{"id": "customer"}])
        assert "entity_type" not in _entity(test_client, "customer")

    def test_manually_set_type_is_not_overridden(self, test_client, dimensional):
        _save(test_client, [{"id": "dim_x", "entity_type": "fact"}])
        assert _entity(test_client, "dim_x")["entity_type"] == "fact"

    def test_no_inference_when_dimensional_modeling_disabled(self, test_client):
        _save(test_client, [{"id": "dim_customer"}])
        assert "entity_type" not in _entity(test_client, "dim_customer")


class TestReadRobustness:
    def test_bound_entity_with_non_list_additional_models_still_loads(
        self, test_client, temp_data_model_path
    ):
        with open(temp_data_model_path, "w") as f:
            f.write(
                "version: 0.1\nentities:\n"
                "  - id: a\n    model_ref: model.p.a\n"
                "    additional_models: not-a-list\n"
            )
        entity = _entity(test_client, "a")
        assert entity["model_ref"] == "model.p.a"

    def test_malformed_data_model_file_returns_500(
        self, test_client, temp_data_model_path
    ):
        with open(temp_data_model_path, "w") as f:
            f.write("entities: [unclosed\n  : : :")
        response = test_client.get("/api/data-model")
        assert response.status_code == 500
        assert "Error reading data model" in response.json()["detail"]


class TestSaveFailure:
    def test_unwritable_data_model_path_returns_500(
        self, test_client, temp_dir, monkeypatch
    ):
        blocker = os.path.join(temp_dir, "blocker")
        with open(blocker, "w") as f:
            f.write("not a directory")
        monkeypatch.setattr(
            cfg, "DATA_MODEL_PATH", os.path.join(blocker, "data_model.yml")
        )
        response = test_client.post(
            "/api/data-model",
            json={"version": 0.1, "entities": [{"id": "a"}], "relationships": []},
        )
        assert response.status_code == 500
        assert "Error saving data model" in response.json()["detail"]


class TestSourceSystemSuggestions:
    def test_empty_when_no_data_model(self, test_client):
        response = test_client.get("/api/source-systems/suggestions")
        assert response.status_code == 200
        assert response.json() == {"suggestions": []}

    def test_collects_sorted_deduplicated_stripped_sources_from_unbound_entities(
        self, test_client
    ):
        _save(
            test_client,
            [
                {"id": "a", "source_system": ["zeta", " crm "]},
                {"id": "b", "source_system": ["crm", "alpha"]},
            ],
        )
        response = test_client.get("/api/source-systems/suggestions")
        assert response.json() == {"suggestions": ["alpha", "crm", "zeta"]}

    def test_bound_entity_payload_source_system_is_not_suggested(self, test_client):
        _save(
            test_client,
            [{"id": "a", "model_ref": "model.p.a", "source_system": ["hidden"]}],
        )
        response = test_client.get("/api/source-systems/suggestions")
        assert "hidden" not in response.json()["suggestions"]

    def test_non_list_source_system_is_ignored(
        self, test_client, temp_data_model_path
    ):
        with open(temp_data_model_path, "w") as f:
            f.write("version: 0.1\nentities:\n  - id: a\n    source_system: crm\n")
        response = test_client.get("/api/source-systems/suggestions")
        assert response.json() == {"suggestions": []}

    def test_malformed_data_model_yields_empty_suggestions(
        self, test_client, temp_data_model_path
    ):
        with open(temp_data_model_path, "w") as f:
            f.write("entities: [unclosed\n  : : :")
        response = test_client.get("/api/source-systems/suggestions")
        assert response.status_code == 200
        assert response.json() == {"suggestions": []}

    def test_bound_entities_with_additional_models_do_not_break_suggestions(
        self, test_client, temp_data_model_path
    ):
        with open(temp_data_model_path, "w") as f:
            f.write(
                "version: 0.1\nentities:\n"
                "  - id: a\n    model_ref: model.p.a\n"
                "    additional_models: [model.p.b, model.p.a]\n"
                "  - id: c\n    model_ref: model.p.c\n    additional_models: x\n"
            )
        response = test_client.get("/api/source-systems/suggestions")
        assert response.status_code == 200
        assert isinstance(response.json()["suggestions"], list)
