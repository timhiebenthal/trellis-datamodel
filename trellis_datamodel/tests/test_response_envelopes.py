"""Response shapes that the declared response models must not strip or pad."""


def test_save_data_model_returns_bare_success_envelope(test_client):
    response = test_client.post(
        "/api/data-model",
        json={"version": 0.1, "entities": [{"id": "a"}], "relationships": []},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "success"}


def test_get_data_model_passes_through_unknown_top_level_keys(
    test_client, temp_data_model_path
):
    with open(temp_data_model_path, "w") as f:
        f.write(
            "version: 0.1\n"
            "entities:\n  - id: a\n"
            "relationships: []\n"
            "domains:\n  - id: sales\n    label: Sales\n"
        )

    body = test_client.get("/api/data-model").json()

    assert body["domains"] == [{"id": "sales", "label": "Sales"}]
    assert [e["id"] for e in body["entities"]] == ["a"]


def test_health_returns_ok(test_client):
    assert test_client.get("/health").json() == {"status": "ok"}
