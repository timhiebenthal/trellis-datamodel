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
    # GET still emits both spellings via the response-only alias shim.
    assert entity["dbt_model"] == "model.proj.orders"
    assert entity["dbt_tags"] == ["nightly"]
    assert entity["model_ref"] == "model.proj.orders"
    assert entity["framework_tags"] == ["nightly"]


def test_get_data_model_emits_both_legacy_and_new_keys(test_client, temp_data_model_path):
    """GET /api/data-model must emit both the legacy dbt_model/dbt_tags keys and
    the generic model_ref/framework_tags keys so unmigrated frontend clients
    keep resolving bindings while consumers can start migrating to the new
    spelling."""
    model_data = {
        "version": 0.1,
        "entities": [
            {
                "id": "customers",
                "label": "Customers",
                "dbt_model": "model.proj.customers",
                "dbt_tags": ["nightly", "customer_360"],
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
    entities = {e["id"]: e for e in response.json()["entities"]}

    bound = entities["customers"]
    assert bound["model_ref"] == bound["dbt_model"]
    assert bound["model_ref"] == "model.proj.customers"
    assert bound["framework_tags"] == bound["dbt_tags"]
    assert bound["framework_tags"] == ["nightly", "customer_360"]


def test_dual_key_emission_is_response_only_not_persisted(test_client, temp_data_model_path):
    """The GET-time legacy-key alias shim must decorate the response only; the
    on-disk YAML must never gain the shim-added keys. This is checked by
    seeding disk with the new-key spelling directly (bypassing the API) and
    confirming the legacy keys the response adds never leak back to disk."""
    model_data = {
        "version": 0.1,
        "entities": [
            {
                "id": "products",
                "label": "Products",
                "model_ref": "model.proj.products",
                "framework_tags": ["nightly"],
                "ui_tags": ["core"],
            }
        ],
        "relationships": [],
    }
    with open(temp_data_model_path, "w") as f:
        yaml.dump(model_data, f)

    response = test_client.get("/api/data-model")
    assert response.status_code == 200
    entity = response.json()["entities"][0]
    # Shim adds both spellings to the response...
    assert entity["model_ref"] == "model.proj.products"
    assert entity["dbt_model"] == "model.proj.products"
    assert entity["framework_tags"] == ["nightly"]
    assert entity["dbt_tags"] == ["nightly"]

    # ...but the on-disk file is untouched: no legacy keys were persisted.
    with open(temp_data_model_path, "r") as f:
        saved = yaml.safe_load(f)
    saved_entity = saved["entities"][0]
    for key in LEGACY_KEYS:
        assert key not in saved_entity, (
            f"legacy key '{key}' must not be persisted to disk by the "
            "response-only shim"
        )
    assert saved_entity["model_ref"] == "model.proj.products"
    assert saved_entity["framework_tags"] == ["nightly"]
