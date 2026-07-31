"""Tests for data model API endpoints."""

import os
import yaml
import pytest

from trellis_datamodel.tests._entity_compat import get_model_ref, get_framework_tags


class TestGetDataModel:
    """Tests for GET /api/data-model endpoint."""

    def test_returns_empty_model_when_file_missing(self, test_client):
        response = test_client.get("/api/data-model")
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == 0.1
        assert data["entities"] == []
        assert data["relationships"] == []

    def test_returns_existing_model(
        self, test_client, temp_data_model_path, temp_canvas_layout_path
    ):
        # Create a data model file (model-only)
        model_data = {
            "version": 0.1,
            "entities": [{"id": "users", "label": "Users"}],
            "relationships": [
                {"source": "orders", "target": "users", "type": "one_to_many"}
            ],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(model_data, f)

        # Create a canvas layout file (layout-only)
        layout_data = {
            "version": 0.1,
            "entities": {
                "users": {
                    "position": {"x": 0, "y": 0},
                    "width": 280,
                    "collapsed": False,
                }
            },
            "relationships": {"orders-users-0": {"label_dx": 10, "label_dy": 20}},
        }
        with open(temp_canvas_layout_path, "w") as f:
            yaml.dump(layout_data, f)

        response = test_client.get("/api/data-model")
        assert response.status_code == 200
        data = response.json()
        assert len(data["entities"]) == 1
        assert data["entities"][0]["id"] == "users"
        # Verify layout is merged
        assert data["entities"][0]["position"] == {"x": 0, "y": 0}
        assert data["entities"][0]["width"] == 280
        assert data["relationships"][0]["label_dx"] == 10
        assert data["relationships"][0]["label_dy"] == 20

    def test_handles_file_with_missing_keys(self, test_client, temp_data_model_path):
        # Create a minimal data model file
        with open(temp_data_model_path, "w") as f:
            yaml.dump({"version": 0.1}, f)

        response = test_client.get("/api/data-model")
        assert response.status_code == 200
        data = response.json()
        assert data["entities"] == []

    def test_computes_display_tags_for_bound_entity(
        self, test_client, temp_data_model_path
    ):
        """GET /api/data-model injects a computed `tags` union (dbt_tags +
        ui_tags) for bound entities, without persisting it back to disk."""
        model_data = {
            "version": 0.1,
            "entities": [
                {
                    "id": "users",
                    "label": "Users",
                    "dbt_model": "model.proj.users",
                    "dbt_tags": ["nightly", "customer_360"],
                    "ui_tags": ["pii"],
                },
            ],
            "relationships": [],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(model_data, f)

        response = test_client.get("/api/data-model")
        assert response.status_code == 200
        entity = response.json()["entities"][0]
        assert entity["tags"] == ["nightly", "customer_360", "pii"]

        with open(temp_data_model_path, "r") as f:
            on_disk = yaml.safe_load(f)
        assert "tags" not in on_disk["entities"][0], (
            "computed display tags must never be written back to data_model.yml"
        )

    def test_unbound_entity_display_tags_are_its_own_tags_field(
        self, test_client, temp_data_model_path
    ):
        model_data = {
            "version": 0.1,
            "entities": [
                {"id": "draft", "label": "Draft", "tags": ["draft-tag"]},
            ],
            "relationships": [],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(model_data, f)

        response = test_client.get("/api/data-model")
        assert response.status_code == 200
        entity = response.json()["entities"][0]
        assert entity["tags"] == ["draft-tag"]


class TestSaveDataModel:
    """Tests for POST /api/data-model endpoint."""

    def test_saves_new_model(
        self, test_client, temp_data_model_path, temp_canvas_layout_path
    ):
        model_data = {
            "version": 0.1,
            "entities": [
                {
                    "id": "users",
                    "label": "Users",
                    "position": {"x": 100, "y": 200},
                    "width": 300,
                    "collapsed": False,
                }
            ],
            "relationships": [],
        }
        response = test_client.post("/api/data-model", json=model_data)
        assert response.status_code == 200
        assert response.json()["status"] == "success"

        # Verify model file was written (without visual properties)
        assert os.path.exists(temp_data_model_path)
        with open(temp_data_model_path, "r") as f:
            saved = yaml.safe_load(f)
        assert saved["entities"][0]["id"] == "users"
        assert "position" not in saved["entities"][0]
        assert "width" not in saved["entities"][0]

        # Verify layout file was written (with visual properties only)
        assert os.path.exists(temp_canvas_layout_path)
        with open(temp_canvas_layout_path, "r") as f:
            layout = yaml.safe_load(f)
        assert "users" in layout["entities"]
        assert layout["entities"]["users"]["position"] == {"x": 100, "y": 200}
        assert layout["entities"]["users"]["width"] == 300

    def test_overwrites_existing_model(
        self, test_client, temp_data_model_path, temp_canvas_layout_path
    ):
        # Create initial model and layout
        with open(temp_data_model_path, "w") as f:
            yaml.dump(
                {"version": 0.1, "entities": [{"id": "old"}], "relationships": []}, f
            )
        with open(temp_canvas_layout_path, "w") as f:
            yaml.dump(
                {
                    "version": 0.1,
                    "entities": {"old": {"position": {"x": 50, "y": 50}}},
                    "relationships": {},
                },
                f,
            )

        # Overwrite with new model
        model_data = {
            "version": 0.1,
            "entities": [{"id": "new", "label": "New", "position": {"x": 0, "y": 0}}],
            "relationships": [],
        }
        response = test_client.post("/api/data-model", json=model_data)
        assert response.status_code == 200

        # Verify old entity is removed from both files
        with open(temp_data_model_path, "r") as f:
            saved = yaml.safe_load(f)
        assert len(saved["entities"]) == 1
        assert saved["entities"][0]["id"] == "new"

        with open(temp_canvas_layout_path, "r") as f:
            layout = yaml.safe_load(f)
        assert "old" not in layout["entities"]
        assert "new" in layout["entities"]

    def test_validates_required_fields(self, test_client):
        # Missing required fields should fail validation
        response = test_client.post("/api/data-model", json={})
        assert response.status_code == 422  # Pydantic validation error

    def test_source_colors_roundtrip(
        self, test_client, temp_data_model_path, temp_canvas_layout_path
    ):
        """Test that source_colors from canvas_layout.yml are preserved."""
        # Create a canvas layout with source_colors
        layout_data = {
            "version": 0.1,
            "entities": {},
            "relationships": {},
            "source_colors": {
                "Salesforce": "#EF4444",
                "Snowflake": "#3B82F6",
            },
        }
        with open(temp_canvas_layout_path, "w") as f:
            yaml.dump(layout_data, f)

        # Verify source_colors are returned in GET
        response = test_client.get("/api/data-model")
        assert response.status_code == 200
        data = response.json()
        assert "source_colors" in data
        assert data["source_colors"]["Salesforce"] == "#EF4444"
        assert data["source_colors"]["Snowflake"] == "#3B82F6"

        # Save data model with source_colors included
        model_data = {
            "version": 0.1,
            "entities": [{"id": "users", "label": "Users"}],
            "relationships": [],
            "source_colors": {
                "Salesforce": "#EF4444",
                "Snowflake": "#3B82F6",
                "MongoDB": "#10B981",
            },
        }
        response = test_client.post("/api/data-model", json=model_data)
        assert response.status_code == 200

        # Verify source_colors are saved to canvas_layout.yml
        with open(temp_canvas_layout_path, "r") as f:
            saved = yaml.safe_load(f)
        assert "source_colors" in saved
        assert saved["source_colors"]["Salesforce"] == "#EF4444"
        assert saved["source_colors"]["Snowflake"] == "#3B82F6"
        assert saved["source_colors"]["MongoDB"] == "#10B981"

    def test_backward_compatibility_without_source_colors(
        self, test_client, temp_data_model_path, temp_canvas_layout_path
    ):
        """Test that models without source_colors work correctly."""
        # Create data model without source_colors
        model_data = {
            "version": 0.1,
            "entities": [{"id": "users", "label": "Users"}],
            "relationships": [],
        }
        response = test_client.post("/api/data-model", json=model_data)
        assert response.status_code == 200

        # Verify GET works without source_colors
        response = test_client.get("/api/data-model")
        assert response.status_code == 200
        data = response.json()
        # source_colors should be present but empty when not configured
        assert "source_colors" in data
        assert data["source_colors"] == {}

    def test_deduplicates_entities_with_same_id(
        self, test_client, temp_data_model_path
    ):
        """POST with duplicate entity IDs keeps only the first occurrence."""
        payload = {
            "version": 0.1,
            "entities": [
                {"id": "orders", "label": "Orders (first)"},
                {"id": "orders", "label": "Orders (duplicate — should be ignored)"},
                {"id": "users", "label": "Users"},
            ],
            "relationships": [],
        }
        response = test_client.post("/api/data-model", json=payload)
        assert response.status_code == 200
        assert response.json()["status"] == "success"

        with open(temp_data_model_path, "r") as f:
            saved = yaml.safe_load(f)

        entity_ids = [e["id"] for e in saved["entities"]]
        # Exactly one "orders" entry must be present
        assert entity_ids.count("orders") == 1
        # The first occurrence's label must be preserved
        orders_entity = next(e for e in saved["entities"] if e["id"] == "orders")
        assert orders_entity["label"] == "Orders (first)"
        # The other unique entity is unaffected
        assert "users" in entity_ids

    def test_save_writes_generic_keys_to_disk(self, test_client, temp_data_model_path):
        """POST persists model_ref/framework_tags to disk; no legacy dbt_* keys,
        even when the incoming payload uses the legacy dbt_model/dbt_tags names."""
        payload = {
            "version": 0.1,
            "entities": [
                {
                    "id": "users",
                    "label": "Users",
                    "dbt_model": "model.proj.users",
                    "dbt_tags": ["nightly", "customer_360"],
                }
            ],
            "relationships": [],
        }
        response = test_client.post("/api/data-model", json=payload)
        assert response.status_code == 200

        with open(temp_data_model_path, "r") as f:
            saved = yaml.safe_load(f)

        entity = saved["entities"][0]
        assert entity["model_ref"] == "model.proj.users"
        assert entity["framework_tags"] == ["nightly", "customer_360"]
        assert "dbt_model" not in entity, "legacy key must not be written to disk"
        assert "dbt_tags" not in entity, "legacy key must not be written to disk"

    def test_save_preserves_mirrored_tags_when_autosave_omits_them_legacy_payload(
        self, test_client, temp_data_model_path
    ):
        """A bound entity's reconcile-owned framework tags must survive an
        autosave that uses the legacy dbt_model/ui_tags payload shape (today's
        live frontend), even though the file on disk now stores
        model_ref/framework_tags."""
        with open(temp_data_model_path, "w") as f:
            yaml.safe_dump(
                {
                    "version": 0.1,
                    "entities": [
                        {
                            "id": "users",
                            "label": "Users",
                            "model_ref": "model.proj.users",
                            "framework_tags": ["nightly", "customer_360"],
                        }
                    ],
                    "relationships": [],
                },
                f,
            )

        # Legacy-shaped autosave payload: dbt_model + ui_tags only, no
        # dbt_tags/framework_tags key at all — exactly what auto-save.ts sends
        # today for a bound entity.
        payload = {
            "version": 0.1,
            "entities": [
                {
                    "id": "users",
                    "label": "Users",
                    "dbt_model": "model.proj.users",
                    "ui_tags": ["pii"],
                }
            ],
            "relationships": [],
        }
        response = test_client.post("/api/data-model", json=payload)
        assert response.status_code == 200

        with open(temp_data_model_path, "r") as f:
            saved = yaml.safe_load(f)

        entity = saved["entities"][0]
        assert get_model_ref(entity) == "model.proj.users"
        assert get_framework_tags(entity) == ["nightly", "customer_360"], (
            "bound entity's reconcile-owned framework tags were wiped by a "
            f"legacy-shaped autosave payload; got: {get_framework_tags(entity)}"
        )
        assert entity["ui_tags"] == ["pii"]

    def test_preserves_existing_roles_when_omitted_from_payload(
        self, test_client, temp_data_model_path
    ):
        with open(temp_data_model_path, "w") as f:
            yaml.safe_dump(
                {
                    "version": 0.1,
                    "entities": [
                        {
                            "id": "dim_employee",
                            "label": "Employee",
                            "entity_type": "dimension",
                            "roles": ["Sales Agent"],
                        }
                    ],
                    "relationships": [],
                },
                f,
                sort_keys=False,
            )

        # Simulate an older/stale client payload that does not include `roles`.
        payload = {
            "version": 0.1,
            "entities": [
                {
                    "id": "dim_employee",
                    "label": "Employee",
                    "entity_type": "dimension",
                }
            ],
            "relationships": [],
        }
        response = test_client.post("/api/data-model", json=payload)
        assert response.status_code == 200

        with open(temp_data_model_path, "r") as f:
            saved = yaml.safe_load(f)

        assert saved["entities"][0]["id"] == "dim_employee"
        assert saved["entities"][0]["roles"] == ["Sales Agent"]


def test_get_data_model_normalizes_origin(test_client, temp_data_model_path):
    """Legacy string origin in data_model.yml is returned as a structured list."""
    model_data = {
        "version": 0.1,
        "entities": [
            {
                "id": "sales",
                "label": "Sales",
                "drafted_fields": [
                    {
                        "name": "amount",
                        "datatype": "numeric",
                        "origin": "DH1: CORE.A | DH2: CBUS.B",
                    }
                ],
            }
        ],
        "relationships": [],
    }
    with open(temp_data_model_path, "w") as f:
        yaml.dump(model_data, f)

    response = test_client.get("/api/data-model")
    assert response.status_code == 200
    field = response.json()["entities"][0]["drafted_fields"][0]
    assert field["origin"] == [{"DH1": "CORE.A"}, {"DH2": "CBUS.B"}]


def test_save_data_model_writes_origin_list(test_client, temp_data_model_path):
    """Saved data_model.yml persists structured origin lists; legacy strings migrate."""
    legacy_payload = {
        "version": 0.1,
        "entities": [
            {
                "id": "sales",
                "label": "Sales",
                "drafted_fields": [
                    {
                        "name": "amount",
                        "datatype": "numeric",
                        "origin": "DH1: CORE.A",
                    }
                ],
            }
        ],
        "relationships": [],
    }
    response = test_client.post("/api/data-model", json=legacy_payload)
    assert response.status_code == 200

    with open(temp_data_model_path, "r") as f:
        saved = yaml.safe_load(f)
    assert saved["entities"][0]["drafted_fields"][0]["origin"] == [{"DH1": "CORE.A"}]

    structured_payload = {
        "version": 0.1,
        "entities": [
            {
                "id": "sales",
                "label": "Sales",
                "drafted_fields": [
                    {
                        "name": "amount",
                        "datatype": "numeric",
                        "origin": [{"DH1": "CORE.A"}, {"DH2": "CBUS.B"}],
                    }
                ],
            }
        ],
        "relationships": [],
    }
    response = test_client.post("/api/data-model", json=structured_payload)
    assert response.status_code == 200

    with open(temp_data_model_path, "r") as f:
        saved = yaml.safe_load(f)
    assert saved["entities"][0]["drafted_fields"][0]["origin"] == [
        {"DH1": "CORE.A"},
        {"DH2": "CBUS.B"},
    ]


def test_split_preserves_ui_tags_key():
    """ui_tags round-trips through the model/layout split the same way
    `dbt_tags` already does: present in the split-out model entity when the
    incoming entity carries the key, and simply absent (not raising, not
    defaulted) when the incoming entity omits it.
    """
    from trellis_datamodel.routes.data_model import _split_model_and_layout

    content = {
        "version": 0.1,
        "entities": [
            {
                "id": "users",
                "label": "Users",
                "dbt_model": "model.proj.users",
                "dbt_tags": ["nightly"],
                "ui_tags": ["pii"],
                "position": {"x": 0, "y": 0},
            },
            {
                "id": "orders",
                "label": "Orders",
                "dbt_model": "model.proj.orders",
                "dbt_tags": ["nightly"],
                # ui_tags intentionally omitted
            },
        ],
        "relationships": [],
    }

    model_data, _layout_data = _split_model_and_layout(content)

    users_entity = next(e for e in model_data["entities"] if e["id"] == "users")
    assert get_framework_tags(users_entity) == ["nightly"]
    assert users_entity["ui_tags"] == ["pii"]

    orders_entity = next(e for e in model_data["entities"] if e["id"] == "orders")
    assert get_framework_tags(orders_entity) == ["nightly"]
    assert "ui_tags" not in orders_entity


def test_split_preserves_bound_entity_dbt_tags_when_omitted_by_autosave():
    """`dbt_tags` on a bound entity is reconcile-owned: auto-save.ts deliberately
    never sends it (it only ever sends ui_tags for bound entities). Omitting the
    key must NOT wipe the previously-reconciled tags already on disk — it must be
    preserved from existing_model_data, mirroring the `roles` preservation pattern.
    """
    from trellis_datamodel.routes.data_model import _split_model_and_layout

    existing_model_data = {
        "entities": [
            {
                "id": "users",
                "dbt_model": "model.proj.users",
                "dbt_tags": ["nightly", "customer_360"],
            },
        ]
    }

    # Exactly what auto-save.ts sends today for a bound entity: ui_tags only,
    # no "dbt_tags" key at all.
    incoming_content = {
        "version": 0.1,
        "entities": [
            {
                "id": "users",
                "label": "Users",
                "dbt_model": "model.proj.users",
                "ui_tags": ["pii"],
                "position": {"x": 0, "y": 0},
            },
        ],
        "relationships": [],
    }

    model_data, _layout_data = _split_model_and_layout(
        incoming_content, existing_model_data
    )

    users_entity = model_data["entities"][0]
    assert get_framework_tags(users_entity) == ["nightly", "customer_360"], (
        f"bound entity's reconcile-owned dbt_tags were wiped on autosave; got: {get_framework_tags(users_entity)}"
    )
    assert users_entity["ui_tags"] == ["pii"]


def test_split_never_persists_tags_for_bound_entity_even_if_sent():
    """Bound entities never persist a `tags` key at all, even if a stale
    client sends one — only unbound entities use plain `tags`."""
    from trellis_datamodel.routes.data_model import _split_model_and_layout

    incoming_content = {
        "version": 0.1,
        "entities": [
            {
                "id": "users",
                "label": "Users",
                "dbt_model": "model.proj.users",
                "tags": ["legacy-stale-value"],
                "position": {"x": 0, "y": 0},
            },
        ],
        "relationships": [],
    }

    model_data, _layout_data = _split_model_and_layout(incoming_content)

    users_entity = model_data["entities"][0]
    assert "tags" not in users_entity


def test_split_does_not_preserve_tags_for_unbound_entity_when_omitted():
    """Unbound entities have no schema.yml to reconcile against — `tags` is their
    single freely-editable field. Clearing it to empty is sent as an omitted key
    (see auto-save.ts's `displayTags.length > 0 ? displayTags : undefined`), and
    that must genuinely clear it, not resurrect the old value from disk.
    """
    from trellis_datamodel.routes.data_model import _split_model_and_layout

    existing_model_data = {
        "entities": [
            {"id": "draft_entity", "tags": ["old-draft-tag"]},
        ]
    }

    # User cleared all tags in the UI for this unbound entity — auto-save.ts omits
    # the key entirely rather than sending an empty list.
    incoming_content = {
        "version": 0.1,
        "entities": [
            {"id": "draft_entity", "label": "Draft Entity", "position": {"x": 0, "y": 0}},
        ],
        "relationships": [],
    }

    model_data, _layout_data = _split_model_and_layout(
        incoming_content, existing_model_data
    )

    entity = model_data["entities"][0]
    assert "tags" not in entity, (
        f"unbound entity's intentionally-cleared tags were resurrected; got: {entity.get('tags')}"
    )


def test_autosave_omitting_mirrored_tags_does_not_clear_them():
    """A bound entity's framework-mirrored tags are reconcile-owned: auto-save
    never sends them (only ui_tags). Omitting the key on save must not clear
    the previously-reconciled tags already on disk."""
    from trellis_datamodel.routes.data_model import _split_model_and_layout

    existing_model_data = {
        "entities": [
            {
                "id": "users",
                "dbt_model": "model.proj.users",
                "dbt_tags": ["nightly", "customer_360"],
            },
        ]
    }

    # Exactly what auto-save.ts sends for a bound entity: ui_tags only, no
    # mirrored-tags key at all.
    incoming_content = {
        "version": 0.1,
        "entities": [
            {
                "id": "users",
                "label": "Users",
                "dbt_model": "model.proj.users",
                "ui_tags": ["pii"],
                "position": {"x": 0, "y": 0},
            },
        ],
        "relationships": [],
    }

    model_data, _layout_data = _split_model_and_layout(
        incoming_content, existing_model_data
    )

    entity = model_data["entities"][0]
    assert get_model_ref(entity) == "model.proj.users"
    assert get_framework_tags(entity) == ["nightly", "customer_360"], (
        "bound entity's reconcile-owned mirrored tags were wiped on autosave; "
        f"got: {get_framework_tags(entity)}"
    )
    assert entity["ui_tags"] == ["pii"]


def test_autosave_omitting_tags_does_clear_them():
    """An unbound entity's `tags` field is freely editable — there is no
    schema.yml to reconcile against. Omitting the key on save (how auto-save.ts
    signals the user cleared all tags) must genuinely clear it, not resurrect
    the previous value from disk."""
    from trellis_datamodel.routes.data_model import _split_model_and_layout

    existing_model_data = {
        "entities": [
            {"id": "draft_entity", "tags": ["old-draft-tag"]},
        ]
    }

    incoming_content = {
        "version": 0.1,
        "entities": [
            {"id": "draft_entity", "label": "Draft Entity", "position": {"x": 0, "y": 0}},
        ],
        "relationships": [],
    }

    model_data, _layout_data = _split_model_and_layout(
        incoming_content, existing_model_data
    )

    entity = model_data["entities"][0]
    assert get_model_ref(entity) is None
    assert "tags" not in entity, (
        f"unbound entity's intentionally-cleared tags were resurrected; got: {entity.get('tags')}"
    )


def test_get_data_model_computes_display_tags_for_bound_and_unbound(
    test_client, temp_data_model_path
):
    """GET /api/data-model computes display tags as the union of
    framework-mirrored tags + ui_tags for bound entities, and passes through
    the entity's own `tags` field unchanged for unbound entities — without
    persisting the computed value back to disk."""
    model_data = {
        "version": 0.1,
        "entities": [
            {
                "id": "users",
                "label": "Users",
                "dbt_model": "model.proj.users",
                "dbt_tags": ["nightly", "customer_360"],
                "ui_tags": ["pii"],
            },
            {"id": "draft", "label": "Draft", "tags": ["draft-tag"]},
        ],
        "relationships": [],
    }
    with open(temp_data_model_path, "w") as f:
        yaml.dump(model_data, f)

    response = test_client.get("/api/data-model")
    assert response.status_code == 200
    entities = response.json()["entities"]

    users = next(e for e in entities if e["id"] == "users")
    assert get_model_ref(users) == "model.proj.users"
    assert users["tags"] == ["nightly", "customer_360", "pii"]

    draft = next(e for e in entities if e["id"] == "draft")
    assert get_model_ref(draft) is None
    assert draft["tags"] == ["draft-tag"]

    with open(temp_data_model_path, "r") as f:
        on_disk = yaml.safe_load(f)
    on_disk_users = next(e for e in on_disk["entities"] if e["id"] == "users")
    on_disk_draft = next(e for e in on_disk["entities"] if e["id"] == "draft")
    assert "tags" not in on_disk_users, (
        "computed display tags must never be written back to data_model.yml"
    )
    assert on_disk_draft["tags"] == ["draft-tag"]
