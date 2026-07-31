"""Snapshot of the data-model API wire format before key generalization.

Sprint 0 tripwire: these tests deliberately hard-code the *current*
`dbt_model`/`dbt_tags` spelling. When the wire format is later renamed to
`model_ref`/`framework_tags`, this file must fail loudly so the rename is
never silently missed.
"""

import yaml

LEGACY_KEYS = ("dbt_model", "dbt_tags")


def test_get_data_model_response_shape(test_client, temp_data_model_path):
    """GET /api/data-model exposes the binding and mirrored tags under the
    legacy `dbt_model`/`dbt_tags` keys today."""
    model_data = {
        "version": 0.1,
        "entities": [
            {
                "id": "users",
                "label": "Users",
                "dbt_model": "model.proj.users",
                "dbt_tags": ["nightly", "customer_360"],
                "ui_tags": ["pii"],
            }
        ],
        "relationships": [],
    }
    with open(temp_data_model_path, "w") as f:
        yaml.dump(model_data, f)

    response = test_client.get("/api/data-model")
    assert response.status_code == 200
    entity = response.json()["entities"][0]

    for key in LEGACY_KEYS:
        assert key in entity, f"expected legacy key '{key}' in GET response entity"

    assert entity["dbt_model"] == "model.proj.users"
    assert entity["dbt_tags"] == ["nightly", "customer_360"]
    # Computed display tags mirror dbt_tags + ui_tags for bound entities.
    assert entity["tags"] == ["nightly", "customer_360", "pii"]


def test_post_data_model_accepts_legacy_payload(test_client, temp_data_model_path):
    """POST /api/data-model accepts a payload keyed by `dbt_model`/`dbt_tags`
    and a subsequent GET resolves the binding from what was persisted.

    Post-rename (Sprint 2 Stream C): the internal read/write path now
    persists the generic `model_ref`/`framework_tags` keys to disk, never the
    legacy spelling — this is the tripwire firing as documented above.
    """
    payload = {
        "version": 0.1,
        "entities": [
            {
                "id": "orders",
                "label": "Orders",
                "dbt_model": "model.proj.orders",
                "dbt_tags": ["nightly"],
            }
        ],
        "relationships": [],
    }
    response = test_client.post("/api/data-model", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    with open(temp_data_model_path, "r") as f:
        saved = yaml.safe_load(f)
    saved_entity = saved["entities"][0]
    for key in LEGACY_KEYS:
        assert key not in saved_entity, (
            f"legacy key '{key}' must not be persisted to disk"
        )
    assert saved_entity["model_ref"] == "model.proj.orders"
    assert saved_entity["framework_tags"] == ["nightly"]

    response = test_client.get("/api/data-model")
    assert response.status_code == 200
    entity = response.json()["entities"][0]
    # Sprint 6: the GET-time dual-key alias shim was retired now that the
    # frontend reads model_ref/framework_tags exclusively. The persisted
    # (generic) keys are what GET reflects back.
    assert entity["model_ref"] == "model.proj.orders"
    assert entity["framework_tags"] == ["nightly"]


def test_get_data_model_no_longer_emits_legacy_keys(test_client, temp_data_model_path):
    """Sprint 6: the transitional GET-time dual-key alias shim has been
    removed. When the data model is stored in the current model_ref/
    framework_tags spelling, the response must not gain dbt_model/dbt_tags
    keys for any entity."""
    model_data = {
        "version": 0.1,
        "entities": [
            {
                "id": "customers",
                "label": "Customers",
                "model_ref": "model.proj.customers",
                "framework_tags": ["nightly", "customer_360"],
                "ui_tags": ["pii"],
            },
            {
                "id": "notes",
                "label": "Notes",
            },
        ],
        "relationships": [],
    }
    with open(temp_data_model_path, "w") as f:
        yaml.dump(model_data, f)

    response = test_client.get("/api/data-model")
    assert response.status_code == 200
    entities = response.json()["entities"]

    for entity in entities:
        for key in LEGACY_KEYS:
            assert key not in entity, (
                f"legacy key '{key}' must no longer be emitted in GET response "
                f"for entity '{entity.get('id')}'"
            )
