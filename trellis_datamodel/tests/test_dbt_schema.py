"""Tests for dbt schema API endpoints."""

import os
import shutil
import yaml
import json
import pytest

from trellis_datamodel.adapters.base import ColumnInfo


def test_columninfo_allows_origin_key():
    """ColumnInfo accepts structured origin metadata."""
    column: ColumnInfo = {
        "name": "sales_amount",
        "type": "numeric",
        "origin": [{"DH1": "CORE.A"}],
    }
    assert column["origin"] == [{"DH1": "CORE.A"}]


@pytest.mark.parametrize(
    "origin_input",
    [
        [{"DH1": "CORE.T_SALES.AMOUNT"}, {"DH2": "CBUS.AMOUNT"}],
        "DH1: CORE.T_SALES.AMOUNT | DH2: CBUS.AMOUNT",
    ],
)
def test_materialize_writes_meta_origin(test_client, temp_dir, mock_manifest, origin_input):
    """Materialization writes meta.origin and keeps description free of | Origin: suffix."""
    sql_dir = os.path.join(temp_dir, "models", "3_core")
    os.makedirs(sql_dir, exist_ok=True)
    with open(os.path.join(sql_dir, "sales.yml"), "w") as f:
        yaml.dump({"version": 2, "models": [{"name": "sales", "columns": []}]}, f)

    expected_origin = [
        {"DH1": "CORE.T_SALES.AMOUNT"},
        {"DH2": "CBUS.AMOUNT"},
    ]

    # Site 2: POST /api/dbt-schema
    response = test_client.post(
        "/api/dbt-schema",
        json={
            "entity_id": "sales",
            "model_name": "sales",
            "fields": [
                {
                    "name": "amount",
                    "datatype": "numeric",
                    "description": "Net sales",
                    "origin": origin_input,
                }
            ],
        },
    )
    assert response.status_code == 200
    with open(response.json()["file_path"], "r") as f:
        schema = yaml.safe_load(f)
    col = schema["models"][0]["columns"][0]
    assert col["meta"]["origin"] == expected_origin
    assert col["description"] == "Net sales"
    assert "| Origin:" not in (col.get("description") or "")


def test_sync_dbt_tests_writes_meta_origin(
    test_client, temp_dir, temp_data_model_path, mock_manifest
):
    """Batch sync writes meta.origin for drafted fields (site 1)."""
    sql_dir = os.path.join(temp_dir, "models", "3_core")
    os.makedirs(sql_dir, exist_ok=True)
    with open(os.path.join(sql_dir, "users.sql"), "w") as f:
        f.write("SELECT 1")
    with open(os.path.join(sql_dir, "users.yml"), "w") as f:
        yaml.dump({"version": 2, "models": [{"name": "users", "columns": []}]}, f)

    data_model = {
        "version": 0.1,
        "entities": [
            {
                "id": "users",
                "label": "Users",
                "dbt_model": "model.project.users",
                "drafted_fields": [
                    {
                        "name": "amount",
                        "datatype": "numeric",
                        "description": "Net sales",
                        "origin": "DH1: CORE.T_SALES.AMOUNT | DH2: CBUS.AMOUNT",
                    }
                ],
            }
        ],
        "relationships": [],
    }
    with open(temp_data_model_path, "w") as f:
        yaml.dump(data_model, f)

    response = test_client.post("/api/sync-dbt-tests")
    assert response.status_code == 200

    yml_path = os.path.join(sql_dir, "users.yml")
    with open(yml_path, "r") as f:
        schema = yaml.safe_load(f)
    col = next(c for c in schema["models"][0]["columns"] if c["name"] == "amount")
    assert col["meta"]["origin"] == [
        {"DH1": "CORE.T_SALES.AMOUNT"},
        {"DH2": "CBUS.AMOUNT"},
    ]
    assert col["description"] == "Net sales"
    assert "| Origin:" not in (col.get("description") or "")


def test_push_to_dbt_preserves_native_column_type(
    test_client, temp_dir, temp_data_model_path, mock_manifest
):
    """Push to dbt must keep the dbt-native column type (e.g. varchar) instead of
    overwriting it with Trellis's internal UI bucket type (e.g. text).

    Regression test for GitHub issue #111: a bound entity's field type is
    "varchar" in the compiled dbt project, but Trellis's data model only
    tracks the coarse UI bucket ("text") for that field. Triggering
    "Push to dbt" must not clobber the more precise, existing schema.yml
    data_type with that bucket value.
    """
    sql_dir = os.path.join(temp_dir, "models", "3_core")
    os.makedirs(sql_dir, exist_ok=True)
    with open(os.path.join(sql_dir, "users.sql"), "w") as f:
        f.write("SELECT 1")
    with open(os.path.join(sql_dir, "users.yml"), "w") as f:
        yaml.dump(
            {
                "version": 2,
                "models": [
                    {
                        "name": "users",
                        "columns": [
                            {
                                "name": "name",
                                "data_type": "varchar",
                                "description": "Full name",
                            }
                        ],
                    }
                ],
            },
            f,
        )

    # Mirrors what reconciliation writes to data_model.yml: the bucketed UI
    # datatype ("text") alongside the preserved native dbt type ("varchar").
    data_model = {
        "version": 0.1,
        "entities": [
            {
                "id": "users",
                "label": "Users",
                "dbt_model": "model.project.users",
                "drafted_fields": [
                    {
                        "name": "name",
                        "datatype": "text",
                        "dbt_data_type": "varchar",
                        "description": "Full name",
                        "source": "dbt",
                    }
                ],
            }
        ],
        "relationships": [],
    }
    with open(temp_data_model_path, "w") as f:
        yaml.dump(data_model, f)

    response = test_client.post("/api/sync-dbt-tests")
    assert response.status_code == 200

    yml_path = os.path.join(sql_dir, "users.yml")
    with open(yml_path, "r") as f:
        schema = yaml.safe_load(f)
    col = next(c for c in schema["models"][0]["columns"] if c["name"] == "name")
    assert col["data_type"] == "varchar", (
        "Push to dbt overwrote the native dbt column type with the internal "
        f"UI bucket type: {col['data_type']!r} (expected 'varchar')"
    )


def test_push_to_dbt_does_not_overwrite_with_catalog_normalized_type(
    test_client, temp_dir, temp_data_model_path, mock_manifest
):
    """dbt/the warehouse can normalize a declared type to a synonym (e.g.
    Snowflake reports a "varchar" column as "TEXT" in the catalog). Push to
    dbt must not use that normalized value to clobber the type already
    declared in schema.yml, even though it now differs from the field's
    reconciled dbt_data_type.
    """
    sql_dir = os.path.join(temp_dir, "models", "3_core")
    os.makedirs(sql_dir, exist_ok=True)
    with open(os.path.join(sql_dir, "users.sql"), "w") as f:
        f.write("SELECT 1")
    with open(os.path.join(sql_dir, "users.yml"), "w") as f:
        yaml.dump(
            {
                "version": 2,
                "models": [
                    {
                        "name": "users",
                        "columns": [
                            {
                                "name": "name",
                                "data_type": "varchar",
                                "description": "Full name",
                            }
                        ],
                    }
                ],
            },
            f,
        )

    data_model = {
        "version": 0.1,
        "entities": [
            {
                "id": "users",
                "label": "Users",
                "dbt_model": "model.project.users",
                "drafted_fields": [
                    {
                        "name": "name",
                        "datatype": "text",
                        "dbt_data_type": "TEXT",
                        "description": "Full name",
                        "source": "dbt",
                    }
                ],
            }
        ],
        "relationships": [],
    }
    with open(temp_data_model_path, "w") as f:
        yaml.dump(data_model, f)

    response = test_client.post("/api/sync-dbt-tests")
    assert response.status_code == 200

    yml_path = os.path.join(sql_dir, "users.yml")
    with open(yml_path, "r") as f:
        schema = yaml.safe_load(f)
    col = next(c for c in schema["models"][0]["columns"] if c["name"] == "name")
    assert col["data_type"] == "varchar", (
        "Push to dbt overwrote the declared type with the catalog-normalized "
        f"type: {col['data_type']!r} (expected 'varchar')"
    )


def test_push_to_dbt_backfills_missing_type_for_new_dbt_column(
    test_client, temp_dir, temp_data_model_path, mock_manifest
):
    """A dbt-sourced column synced for the first time (no prior schema.yml
    entry) has no existing value to preserve, so it should be backfilled
    with the native dbt_data_type rather than left blank or set to the
    coarse UI bucket. The catalog's "TEXT" spelling is canonicalized to
    "varchar" so freshly-backfilled columns don't mix spellings with
    hand-declared ones across schema.yml files.
    """
    sql_dir = os.path.join(temp_dir, "models", "3_core")
    os.makedirs(sql_dir, exist_ok=True)
    with open(os.path.join(sql_dir, "users.sql"), "w") as f:
        f.write("SELECT 1")
    with open(os.path.join(sql_dir, "users.yml"), "w") as f:
        yaml.dump({"version": 2, "models": [{"name": "users", "columns": []}]}, f)

    data_model = {
        "version": 0.1,
        "entities": [
            {
                "id": "users",
                "label": "Users",
                "dbt_model": "model.project.users",
                "drafted_fields": [
                    {
                        "name": "name",
                        "datatype": "text",
                        "dbt_data_type": "TEXT",
                        "description": "Full name",
                        "source": "dbt",
                    }
                ],
            }
        ],
        "relationships": [],
    }
    with open(temp_data_model_path, "w") as f:
        yaml.dump(data_model, f)

    response = test_client.post("/api/sync-dbt-tests")
    assert response.status_code == 200

    yml_path = os.path.join(sql_dir, "users.yml")
    with open(yml_path, "r") as f:
        schema = yaml.safe_load(f)
    col = next(c for c in schema["models"][0]["columns"] if c["name"] == "name")
    assert col["data_type"] == "varchar"


def test_push_to_dbt_does_not_canonicalize_ambiguous_number_type(
    test_client, temp_dir, temp_data_model_path, mock_manifest
):
    """NUMBER collapses int/integer/decimal/numeric and the catalog doesn't
    expose precision/scale, so backfilling must not guess a declared
    spelling for it — the raw catalog value is written as-is.
    """
    sql_dir = os.path.join(temp_dir, "models", "3_core")
    os.makedirs(sql_dir, exist_ok=True)
    with open(os.path.join(sql_dir, "users.sql"), "w") as f:
        f.write("SELECT 1")
    with open(os.path.join(sql_dir, "users.yml"), "w") as f:
        yaml.dump({"version": 2, "models": [{"name": "users", "columns": []}]}, f)

    data_model = {
        "version": 0.1,
        "entities": [
            {
                "id": "users",
                "label": "Users",
                "dbt_model": "model.project.users",
                "drafted_fields": [
                    {
                        "name": "age",
                        "datatype": "number",
                        "dbt_data_type": "NUMBER",
                        "description": "Age",
                        "source": "dbt",
                    }
                ],
            }
        ],
        "relationships": [],
    }
    with open(temp_data_model_path, "w") as f:
        yaml.dump(data_model, f)

    response = test_client.post("/api/sync-dbt-tests")
    assert response.status_code == 200

    yml_path = os.path.join(sql_dir, "users.yml")
    with open(yml_path, "r") as f:
        schema = yaml.safe_load(f)
    col = next(c for c in schema["models"][0]["columns"] if c["name"] == "age")
    assert col["data_type"] == "NUMBER"


def test_round_trip_demo_origin(monkeypatch, temp_dir):
    """Demo-style project: materialize structured origin to schema.yml and read back via get_models."""
    from trellis_datamodel import config as cfg
    from trellis_datamodel.adapters.dbt_core import DbtCoreAdapter

    model_name = "fact__campaign_management"
    model_uid = "model.demo.fact__campaign_management"
    entity_id = "fact__campaign_management"
    origin_list = [
        {"DH1": "CORE.T_SALES.AMOUNT"},
        {"DH2": "CBUS.AMOUNT"},
    ]

    models_dir = os.path.join(temp_dir, "models", "3-entity")
    os.makedirs(models_dir, exist_ok=True)
    with open(os.path.join(models_dir, f"{model_name}.sql"), "w") as f:
        f.write("select 1 as sales_amount_dc")

    manifest_path = os.path.join(temp_dir, "manifest.json")
    manifest_data = {
        "nodes": {
            model_uid: {
                "unique_id": model_uid,
                "resource_type": "model",
                "name": model_name,
                "schema": "main",
                "alias": model_name,
                "original_file_path": f"models/3-entity/{model_name}.sql",
                "columns": {},
                "description": "Campaign management fact",
                "config": {"materialized": "table"},
                "tags": [],
            }
        }
    }
    with open(manifest_path, "w") as f:
        json.dump(manifest_data, f)

    data_model_path = os.path.join(temp_dir, "data_model.yml")
    data_model = {
        "version": 0.1,
        "entities": [
            {
                "id": entity_id,
                "label": "Campaign Management",
                "dbt_model": model_uid,
                "drafted_fields": [
                    {
                        "name": "sales_amount_dc",
                        "datatype": "numeric",
                        "description": "Net sales",
                        "origin": origin_list,
                    }
                ],
            }
        ],
        "relationships": [],
    }
    with open(data_model_path, "w") as f:
        yaml.dump(data_model, f)

    monkeypatch.setattr(cfg, "DBT_PROJECT_PATH", temp_dir)
    monkeypatch.setattr(cfg, "MANIFEST_PATH", manifest_path)
    monkeypatch.setattr(cfg, "CATALOG_PATH", "")
    monkeypatch.setattr(cfg, "DATA_MODEL_PATH", data_model_path)
    monkeypatch.setattr(cfg, "DBT_MODEL_PATHS", ["3-entity"])

    adapter = DbtCoreAdapter(
        manifest_path=manifest_path,
        catalog_path="",
        project_path=temp_dir,
        data_model_path=data_model_path,
        model_paths=["3-entity"],
    )

    yml_path = adapter.save_dbt_schema(
        entity_id=entity_id,
        model_name=model_name,
        fields=[
            {
                "name": "sales_amount_dc",
                "datatype": "numeric",
                "description": "Net sales",
                "origin": origin_list,
            }
        ],
    )

    with open(yml_path, "r") as f:
        schema = yaml.safe_load(f)
    col = schema["models"][0]["columns"][0]
    assert col["meta"]["origin"] == origin_list
    assert col["description"] == "Net sales"
    assert "| Origin:" not in (col.get("description") or "")

    manifest_data["nodes"][model_uid]["columns"]["sales_amount_dc"] = {
        "name": "sales_amount_dc",
        "data_type": "numeric",
        "description": "Net sales",
        "meta": {"origin": origin_list},
    }
    with open(manifest_path, "w") as f:
        json.dump(manifest_data, f)

    models = adapter.get_models()
    model = next(m for m in models if m["name"] == model_name)
    read_col = next(c for c in model["columns"] if c["name"] == "sales_amount_dc")
    assert read_col["origin"] == origin_list
    assert read_col.get("description") == "Net sales"


class TestSaveDbtSchema:
    """Tests for POST /api/dbt-schema endpoint."""

    def test_creates_schema_file(self, test_client, temp_dir):
        request_data = {
            "entity_id": "users",
            "model_name": "users",
            "fields": [
                {"name": "id", "datatype": "int"},
                {"name": "email", "datatype": "text", "description": "User email"},
            ],
            "description": "User entity",
        }
        response = test_client.post("/api/dbt-schema", json=request_data)
        assert response.status_code == 200

        result = response.json()
        assert result["status"] == "success"
        assert "file_path" in result

        # Verify file content
        with open(result["file_path"], "r") as f:
            schema = yaml.safe_load(f)

        assert schema["version"] == 2
        assert len(schema["models"]) == 1
        model = schema["models"][0]
        assert model["name"] == "users"
        assert model["description"] == "User entity"
        assert len(model["columns"]) == 2

    def test_push_is_non_destructive_for_unlisted_columns(
        self, test_client, temp_dir, mock_manifest
    ):
        """Pushing a subset of fields must not delete columns already in schema.yml
        that are absent from the incoming field list (e.g. added by a developer directly)."""
        sql_dir = os.path.join(temp_dir, "models", "3_core")
        os.makedirs(sql_dir, exist_ok=True)
        with open(os.path.join(sql_dir, "users.sql"), "w") as f:
            f.write("SELECT 1")

        yml_path = os.path.join(sql_dir, "users.yml")
        with open(yml_path, "w") as f:
            yaml.dump(
                {
                    "version": 2,
                    "models": [
                        {
                            "name": "users",
                            "columns": [
                                {"name": "id", "data_type": "int"},
                                {"name": "name", "data_type": "text"},
                                {"name": "legacy_col", "data_type": "text"},
                            ],
                        }
                    ],
                },
                f,
            )

        # Push only id + name — legacy_col must survive
        response = test_client.post(
            "/api/dbt-schema",
            json={
                "entity_id": "users",
                "model_name": "users",
                "fields": [
                    {"name": "id", "datatype": "int"},
                    {"name": "name", "datatype": "text"},
                ],
            },
        )
        assert response.status_code == 200

        with open(yml_path, "r") as f:
            saved = yaml.safe_load(f)

        col_names = [c["name"] for c in saved["models"][0]["columns"]]
        assert "legacy_col" in col_names, (
            f"legacy_col was deleted by push; got columns: {col_names}"
        )
        assert "id" in col_names
        assert "name" in col_names

    def test_preserves_versioned_models_and_versions(
        self, test_client, temp_dir, temp_data_model_path
    ):
        # Overwrite manifest with versioned model pointing to player_v2.sql
        manifest_path = os.path.join(temp_dir, "manifest.json")
        manifest_data = {
            "nodes": {
                "model.project.player.v1": {
                    "unique_id": "model.project.player.v1",
                    "resource_type": "model",
                    "name": "player",
                    "version": 1,
                    "schema": "public",
                    "alias": "player",
                    "original_file_path": "models/3_core/all/player_v1.sql",
                    "columns": {},
                    "description": "Player v1",
                    "config": {"materialized": "table"},
                    "tags": [],
                },
                "model.project.player.v2": {
                    "unique_id": "model.project.player.v2",
                    "resource_type": "model",
                    "name": "player",
                    "version": 2,
                    "schema": "public",
                    "alias": "player",
                    "original_file_path": "models/3_core/all/player_v2.sql",
                    "columns": {},
                    "description": "Player v2",
                    "config": {"materialized": "table"},
                    "tags": [],
                },
            }
        }
        with open(manifest_path, "w") as f:
            json.dump(manifest_data, f)

        # Existing schema with v1 definition (stored in player.yml)
        models_dir = os.path.join(temp_dir, "models", "3_core", "all")
        os.makedirs(models_dir, exist_ok=True)
        yml_path = os.path.join(models_dir, "player.yml")
        existing_schema = {
            "version": 2,
            "models": [
                {
                    "name": "player",
                    "latest_version": 1,
                    "versions": [
                        {
                            "v": 1,
                            "description": "v1 description",
                            "columns": [{"name": "player_id", "data_type": "text"}],
                        }
                    ],
                }
            ],
        }
        with open(yml_path, "w") as f:
            yaml.dump(existing_schema, f)

        # Data model binds entity to v2
        data_model = {
            "version": 0.1,
            "entities": [
                {
                    "id": "player",
                    "label": "Player",
                    "description": "Players competing in the NBA",
                    "dbt_model": "model.project.player.v2",
                }
            ],
            "relationships": [],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data_model, f)

        request_data = {
            "entity_id": "player",
            "model_name": "player",
            "fields": [
                {
                    "name": "player_uuid",
                    "datatype": "text",
                    "description": "New PK",
                }
            ],
            "description": "Players v2",
            "tags": ["core"],
        }

        response = test_client.post("/api/dbt-schema", json=request_data)
        assert response.status_code == 200

        with open(yml_path, "r") as f:
            schema = yaml.safe_load(f)

        model = schema["models"][0]
        assert model["latest_version"] == 2

        versions = {v["v"]: v for v in model["versions"]}
        assert 1 in versions  # keep existing v1
        assert 2 in versions  # add/update v2

        # v1 is unchanged
        assert versions[1]["columns"][0]["name"] == "player_id"

        # v2 reflects new request
        v2_columns = versions[2]["columns"]
        assert v2_columns[0]["name"] == "player_uuid"
        assert versions[2].get("config", {}).get("tags") == ["core"]

    def test_writes_relationship_test_for_many_to_one(
        self, test_client, temp_dir, temp_data_model_path
    ):
        """
        Regression: save_dbt_schema must write a relationship test when the entity
        holds the FK in a many_to_one relationship.
        """
        data_model = {
            "version": 0.1,
            "entities": [
                {"id": "orders", "label": "Orders", "position": {"x": 100, "y": 0}},
                {"id": "customers", "label": "Customers", "position": {"x": 0, "y": 0}},
            ],
            "relationships": [
                {
                    "source": "orders",
                    "target": "customers",
                    "type": "many_to_one",
                    "source_field": "customer_id",
                    "target_field": "id",
                }
            ],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data_model, f)

        response = test_client.post(
            "/api/dbt-schema",
            json={
                "entity_id": "orders",
                "model_name": "orders",
                "fields": [{"name": "customer_id", "datatype": "int"}],
            },
        )
        assert response.status_code == 200

        with open(response.json()["file_path"]) as f:
            schema = yaml.safe_load(f)

        rel_tests = schema["models"][0]["columns"][0]["data_tests"]
        assert rel_tests == [
            {
                "relationships": {
                    "arguments": {"to": "ref('customers')", "field": "id"},
                }
            }
        ]

    def test_writes_relationship_test_for_one_to_one(
        self, test_client, temp_dir, temp_data_model_path
    ):
        """
        save_dbt_schema must write a relationship test when the entity holds
        the FK in a one_to_one relationship.
        """
        data_model = {
            "version": 0.1,
            "entities": [
                {"id": "passports", "label": "Passports", "position": {"x": 0, "y": 0}},
                {"id": "persons", "label": "Persons", "position": {"x": 100, "y": 0}},
            ],
            "relationships": [
                {
                    "source": "passports",
                    "target": "persons",
                    "type": "one_to_one",
                    "source_field": "person_id",
                    "target_field": "id",
                }
            ],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data_model, f)

        response = test_client.post(
            "/api/dbt-schema",
            json={
                "entity_id": "passports",
                "model_name": "passports",
                "fields": [{"name": "person_id", "datatype": "int"}],
            },
        )
        assert response.status_code == 200

        with open(response.json()["file_path"]) as f:
            schema = yaml.safe_load(f)

        rel_tests = schema["models"][0]["columns"][0]["data_tests"]
        assert rel_tests == [
            {
                "relationships": {
                    "arguments": {"to": "ref('persons')", "field": "id"},
                }
            }
        ]


    def test_save_dbt_schema_removes_stale_relationship_test(
        self, test_client, temp_dir, temp_data_model_path
    ):
        """save_dbt_schema must remove a relationship test from a field that was
        previously an FK but is no longer one (relationship removed or type changed)."""
        # First push: orders.customer_id has a many_to_one FK → customers
        data_model_with_rel = {
            "version": 0.1,
            "entities": [
                {"id": "orders", "label": "Orders"},
                {"id": "customers", "label": "Customers"},
            ],
            "relationships": [
                {
                    "source": "orders",
                    "target": "customers",
                    "type": "many_to_one",
                    "source_field": "customer_id",
                    "target_field": "id",
                }
            ],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data_model_with_rel, f)

        response = test_client.post(
            "/api/dbt-schema",
            json={
                "entity_id": "orders",
                "model_name": "orders",
                "fields": [{"name": "customer_id", "datatype": "int"}],
            },
        )
        assert response.status_code == 200
        yml_path = response.json()["file_path"]

        with open(yml_path) as f:
            schema = yaml.safe_load(f)
        rel_tests = schema["models"][0]["columns"][0].get("data_tests", [])
        assert any("relationships" in t for t in rel_tests), "Relationship test not written in first push"

        # Second push: relationship removed — customer_id is no longer an FK
        data_model_no_rel = {
            "version": 0.1,
            "entities": [
                {"id": "orders", "label": "Orders"},
                {"id": "customers", "label": "Customers"},
            ],
            "relationships": [],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data_model_no_rel, f)

        response2 = test_client.post(
            "/api/dbt-schema",
            json={
                "entity_id": "orders",
                "model_name": "orders",
                "fields": [{"name": "customer_id", "datatype": "int"}],
            },
        )
        assert response2.status_code == 200

        with open(yml_path) as f:
            schema2 = yaml.safe_load(f)
        remaining_tests = schema2["models"][0]["columns"][0].get("data_tests", [])
        has_rel_test = any("relationships" in t for t in remaining_tests)
        assert not has_rel_test, (
            f"Stale relationship test not removed; data_tests: {remaining_tests}"
        )


class TestSyncDbtTests:
    """Tests for POST /api/sync-dbt-tests endpoint."""

    def test_syncs_relationship_tests(
        self, test_client, temp_dir, temp_data_model_path
    ):
        # Create data model with entities and relationships
        data_model = {
            "version": 0.1,
            "entities": [
                {"id": "users", "label": "Users", "position": {"x": 0, "y": 0}},
                {
                    "id": "orders",
                    "label": "Orders",
                    "position": {"x": 100, "y": 0},
                    "drafted_fields": [{"name": "user_id", "datatype": "int"}],
                },
            ],
            "relationships": [
                {
                    "source": "users",
                    "target": "orders",
                    "type": "one_to_many",
                    "source_field": "id",
                    "target_field": "user_id",
                }
            ],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data_model, f)

        response = test_client.post("/api/sync-dbt-tests")
        assert response.status_code == 200

        result = response.json()
        assert result["status"] == "success"
        assert len(result["files"]) == 2  # One for each entity

    def test_sync_dbt_tests_removes_stale_drafted_fields(
        self, test_client, temp_dir, temp_data_model_path, mock_manifest
    ):
        """Regression for #98: when a drafted_field is renamed/removed in
        data_model.yml, the corresponding column must disappear from schema.yml
        on the next "push to dbt" run instead of accumulating alongside the new
        name."""
        sql_dir = os.path.join(temp_dir, "models", "3_core")
        os.makedirs(sql_dir, exist_ok=True)
        with open(os.path.join(sql_dir, "users.sql"), "w") as f:
            f.write("SELECT 1")

        yml_path = os.path.join(sql_dir, "users.yml")
        with open(yml_path, "w") as f:
            yaml.dump(
                {
                    "version": 2,
                    "models": [
                        {
                            "name": "users",
                            "columns": [
                                {"name": "id", "data_type": "int"},
                                {"name": "old_email", "data_type": "text"},
                                {"name": "to_delete", "data_type": "text"},
                            ],
                        }
                    ],
                },
                f,
            )

        data_model = {
            "version": 0.1,
            "entities": [
                {
                    "id": "users",
                    "label": "Users",
                    "dbt_model": "model.test_project.users",
                    "drafted_fields": [
                        {"name": "id", "datatype": "int"},
                        {"name": "new_email", "datatype": "text"},
                    ],
                }
            ],
            "relationships": [],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data_model, f)

        response = test_client.post("/api/sync-dbt-tests")
        assert response.status_code == 200

        with open(yml_path, "r") as f:
            saved = yaml.safe_load(f)
        names = [c["name"] for c in saved["models"][0]["columns"]]
        assert names == ["id", "new_email"]

    def test_syncs_relationship_tests_with_entity_type(
        self, test_client, temp_dir, temp_data_model_path
    ):
        """
        Regression test: relationship type should be determined by entity_type when
        relationship has no explicit type set (or defaults incorrectly).

        When source is fact and target is dimension (e.g., orders -> customers),
        the FK is typically on the fact side (source), making it many_to_one.
        When source is dimension and target is fact (e.g., customers -> orders),
        the FK is typically on the fact side (target), making it one_to_many.

        This test ensures the backend correctly writes relationship tests based on
        the relationship type, not based on entity_type inference.
        """
        # Test case 1: fact -> dimension should result in FK on source (many_to_one)
        data_model = {
            "version": 0.1,
            "entities": [
                {
                    "id": "dim_customers",
                    "label": "Customers",
                    "entity_type": "dimension",
                    "position": {"x": 0, "y": 0},
                },
                {
                    "id": "fct_orders",
                    "label": "Orders",
                    "entity_type": "fact",
                    "position": {"x": 100, "y": 0},
                    "drafted_fields": [{"name": "customer_id", "datatype": "int"}],
                },
            ],
            # Relationship from dimension (source) to fact (target)
            # With one_to_many, FK should be on target (fact/fct_orders)
            "relationships": [
                {
                    "source": "dim_customers",
                    "target": "fct_orders",
                    "type": "one_to_many",
                    "source_field": "id",
                    "target_field": "customer_id",
                }
            ],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data_model, f)

        response = test_client.post("/api/sync-dbt-tests")
        assert response.status_code == 200

        # fct_orders.yml should have the relationship test (FK on target)
        orders_yml = os.path.join(temp_dir, "models", "3_core", "fct_orders.yml")
        assert os.path.exists(orders_yml)
        with open(orders_yml, "r") as f:
            schema = yaml.safe_load(f)

        # Find customer_id column
        customer_id_col = None
        for col in schema["models"][0]["columns"]:
            if col["name"] == "customer_id":
                customer_id_col = col
                break

        assert customer_id_col is not None, "customer_id column not found"
        assert "data_tests" in customer_id_col, "FK test not written"
        # Should reference dim_customers
        assert any(
            "dim_customers" in str(test.get("relationships", {}).get("arguments", {}))
            for test in customer_id_col["data_tests"]
        ), "Relationship test should reference dim_customers"

    def test_syncs_using_dbt_model_names(
        self, test_client, temp_dir, temp_data_model_path
    ):
        """
        Ensure relationship tests reference bound dbt model names, not raw entity IDs.
        """
        data_model = {
            "version": 0.1,
            "entities": [
                {
                    "id": "customer_entity",
                    "label": "Customers",
                    "dbt_model": "model.project.customers",
                    "position": {"x": 0, "y": 0},
                },
                {
                    "id": "order_entity",
                    "label": "Orders",
                    "dbt_model": "model.project.orders",
                    "drafted_fields": [{"name": "customer_id", "datatype": "int"}],
                },
            ],
            "relationships": [
                {
                    "source": "customer_entity",
                    "target": "order_entity",
                    "type": "one_to_many",
                    "source_field": "id",
                    "target_field": "customer_id",
                }
            ],
        }

        # Persist data model
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data_model, f)

        response = test_client.post("/api/sync-dbt-tests")
        assert response.status_code == 200

        # orders.yml should contain a relationship test pointing to customers (dbt model name)
        orders_yml = os.path.join(temp_dir, "models", "3_core", "orders.yml")
        assert os.path.exists(orders_yml)
        with open(orders_yml, "r") as f:
            schema = yaml.safe_load(f)

        rel_tests = schema["models"][0]["columns"][0]["data_tests"]
        assert rel_tests == [
            {
                "relationships": {
                    "arguments": {"to": "ref('customers')", "field": "id"},
                }
            }
        ]

    def test_syncs_many_to_one_relationship(
        self, test_client, temp_dir, temp_data_model_path
    ):
        """
        Ensure many_to_one relationships write FK test to source entity (the "many" side).
        """
        data_model = {
            "version": 0.1,
            "entities": [
                {
                    "id": "customer_entity",
                    "label": "Customers",
                    "dbt_model": "model.project.customers",
                    "position": {"x": 0, "y": 0},
                },
                {
                    "id": "order_entity",
                    "label": "Orders",
                    "dbt_model": "model.project.orders",
                    "drafted_fields": [{"name": "customer_id", "datatype": "int"}],
                    "position": {"x": 100, "y": 0},
                },
            ],
            "relationships": [
                {
                    "source": "order_entity",  # Source is "many" side, so FK should be here
                    "target": "customer_entity",  # Target is "one" side (PK)
                    "type": "many_to_one",
                    "source_field": "customer_id",  # FK field
                    "target_field": "id",  # PK field
                }
            ],
        }

        # Persist data model
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data_model, f)

        response = test_client.post("/api/sync-dbt-tests")
        assert response.status_code == 200

        # orders.yml should contain a relationship test (FK is on source/orders)
        orders_yml = os.path.join(temp_dir, "models", "3_core", "orders.yml")
        assert os.path.exists(orders_yml)
        with open(orders_yml, "r") as f:
            schema = yaml.safe_load(f)

        rel_tests = schema["models"][0]["columns"][0]["data_tests"]
        assert rel_tests == [
            {
                "relationships": {
                    "arguments": {"to": "ref('customers')", "field": "id"},
                }
            }
        ]

        # customers.yml should NOT have a relationship test (PK is on target/customers)
        customers_yml = os.path.join(temp_dir, "models", "3_core", "customers.yml")
        if os.path.exists(customers_yml):
            with open(customers_yml, "r") as f:
                customer_schema = yaml.safe_load(f)
            # If customers.yml exists, it shouldn't have relationship tests for this relationship
            if "models" in customer_schema and len(customer_schema["models"]) > 0:
                if "columns" in customer_schema["models"][0]:
                    for col in customer_schema["models"][0]["columns"]:
                        if col.get("name") == "id":
                            # PK field shouldn't have relationship test pointing back
                            tests = col.get("data_tests", [])
                            for test in tests:
                                if "relationships" in test:
                                    rel = test["relationships"]
                                    ref = rel.get("arguments", {}).get(
                                        "to", ""
                                    ) or rel.get("to", "")
                                    assert "ref('orders')" not in ref

    def test_removes_stale_relationship_tests_when_type_changes(
        self, test_client, temp_dir, temp_data_model_path
    ):
        """
        When relationship type changes (e.g., one_to_many -> many_to_one),
        stale relationship tests should be removed from old FK location and
        added to new FK location.
        """
        # Start with one_to_many relationship (FK on target/orders)
        data_model = {
            "version": 0.1,
            "entities": [
                {
                    "id": "customers",
                    "label": "Customers",
                    "dbt_model": "model.project.customers",
                    "position": {"x": 0, "y": 0},
                },
                {
                    "id": "orders",
                    "label": "Orders",
                    "dbt_model": "model.project.orders",
                    "drafted_fields": [{"name": "customer_id", "datatype": "int"}],
                    "position": {"x": 100, "y": 0},
                },
            ],
            "relationships": [
                {
                    "source": "customers",
                    "target": "orders",
                    "type": "one_to_many",  # FK on target (orders)
                    "source_field": "id",
                    "target_field": "customer_id",
                }
            ],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data_model, f)

        # First sync: FK should be on orders
        response = test_client.post("/api/sync-dbt-tests")
        assert response.status_code == 200

        orders_yml = os.path.join(temp_dir, "models", "3_core", "orders.yml")
        assert os.path.exists(orders_yml)
        with open(orders_yml, "r") as f:
            schema = yaml.safe_load(f)

        # Verify FK test is on orders.customer_id
        rel_tests = schema["models"][0]["columns"][0]["data_tests"]
        assert len(rel_tests) == 1
        assert "relationships" in rel_tests[0]
        assert rel_tests[0]["relationships"]["arguments"]["to"] == "ref('customers')"

        # Now change relationship type to many_to_one (FK should move to source/customers)
        data_model["relationships"][0]["type"] = "many_to_one"
        # Swap fields: FK now on source (customers), PK on target (orders)
        data_model["relationships"][0]["source_field"] = "customer_id"
        data_model["relationships"][0]["target_field"] = "id"
        # Swap source/target to reflect new direction
        data_model["relationships"][0]["source"] = "orders"
        data_model["relationships"][0]["target"] = "customers"

        with open(temp_data_model_path, "w") as f:
            yaml.dump(data_model, f)

        # Second sync: FK should move to orders, old FK on customers should be removed
        response = test_client.post("/api/sync-dbt-tests")
        assert response.status_code == 200

        # Verify orders.yml still has the test (FK is still on orders, just different semantics)
        with open(orders_yml, "r") as f:
            schema = yaml.safe_load(f)

        rel_tests = schema["models"][0]["columns"][0]["data_tests"]
        assert len(rel_tests) == 1
        assert "relationships" in rel_tests[0]
        assert rel_tests[0]["relationships"]["arguments"]["to"] == "ref('customers')"

        # Verify customers.yml does NOT have a relationship test
        # (even if it exists, it shouldn't have a test pointing back to orders)
        customers_yml = os.path.join(temp_dir, "models", "3_core", "customers.yml")
        if os.path.exists(customers_yml):
            with open(customers_yml, "r") as f:
                customer_schema = yaml.safe_load(f)
            if "models" in customer_schema and len(customer_schema["models"]) > 0:
                if "columns" in customer_schema["models"][0]:
                    for col in customer_schema["models"][0]["columns"]:
                        if col.get("name") == "id":
                            tests = col.get("data_tests", [])
                            for test in tests:
                                if "relationships" in test:
                                    rel = test["relationships"]
                                    ref = rel.get("arguments", {}).get(
                                        "to", ""
                                    ) or rel.get("to", "")
                                    assert "ref('orders')" not in ref

    def test_removes_stale_tests_when_swapping_one_to_many_to_many_to_one(
        self, test_client, temp_dir, temp_data_model_path
    ):
        """
        Test the specific bug scenario: swapping one_to_many to many_to_one
        should move FK from target to source and remove stale test from target.
        """
        # Create initial state: one_to_many with FK on target
        data_model = {
            "version": 0.1,
            "entities": [
                {
                    "id": "department",
                    "label": "Department",
                    "dbt_model": "model.project.department",
                    "drafted_fields": [{"name": "department_id", "datatype": "text"}],
                },
                {
                    "id": "cool_stuff",
                    "label": "Cool Stuff",
                    "dbt_model": "model.project.cool_stuff",
                    "drafted_fields": [{"name": "department_id", "datatype": "text"}],
                },
            ],
            "relationships": [
                {
                    "source": "department",
                    "target": "cool_stuff",
                    "type": "one_to_many",  # FK on target (cool_stuff)
                    "source_field": "department_id",
                    "target_field": "department_id",
                }
            ],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data_model, f)

        # Initial sync: FK should be on cool_stuff
        response = test_client.post("/api/sync-dbt-tests")
        assert response.status_code == 200

        cool_stuff_yml = os.path.join(temp_dir, "models", "3_core", "cool_stuff.yml")
        assert os.path.exists(cool_stuff_yml)
        with open(cool_stuff_yml, "r") as f:
            schema = yaml.safe_load(f)

        # Verify FK test exists on cool_stuff.department_id
        rel_tests = schema["models"][0]["columns"][0]["data_tests"]
        assert len(rel_tests) == 1
        assert "relationships" in rel_tests[0]

        # Now swap to many_to_one (FK should move to department)
        data_model["relationships"][0]["type"] = "many_to_one"
        # Note: source/target stay the same, only type changes (as per fixed swap logic)
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data_model, f)

        # Second sync: FK should move to department, stale test removed from cool_stuff
        response = test_client.post("/api/sync-dbt-tests")
        assert response.status_code == 200

        # Verify cool_stuff.yml no longer has the relationship test
        with open(cool_stuff_yml, "r") as f:
            schema = yaml.safe_load(f)

        # cool_stuff.department_id should NOT have relationship test anymore
        if "columns" in schema["models"][0]:
            for col in schema["models"][0]["columns"]:
                if col.get("name") == "department_id":
                    tests = col.get("data_tests", [])
                    # Should have no relationship tests (or no tests at all)
                    for test in tests:
                        assert "relationships" not in test

        # Verify department.yml now has the relationship test
        department_yml = os.path.join(temp_dir, "models", "3_core", "department.yml")
        assert os.path.exists(department_yml)
        with open(department_yml, "r") as f:
            dept_schema = yaml.safe_load(f)

        # department.department_id should have relationship test pointing to cool_stuff
        rel_tests = dept_schema["models"][0]["columns"][0]["data_tests"]
        assert len(rel_tests) == 1
        assert "relationships" in rel_tests[0]
        assert rel_tests[0]["relationships"]["arguments"]["to"] == "ref('cool_stuff')"


class TestGetModelSchema:
    """Tests for GET /api/models/{model_name}/schema endpoint."""

    def test_returns_empty_for_missing_yml(self, test_client, temp_dir, mock_manifest):
        # Create SQL file path structure (manifest points to this)
        sql_dir = os.path.join(temp_dir, "models", "3_core")
        os.makedirs(sql_dir, exist_ok=True)
        with open(os.path.join(sql_dir, "users.sql"), "w") as f:
            f.write("SELECT 1")

        response = test_client.get("/api/models/users/schema")
        assert response.status_code == 200

        data = response.json()
        assert data["model_name"] == "users"
        assert data["columns"] == []

    def test_returns_404_for_unknown_model(self, test_client):
        response = test_client.get("/api/models/nonexistent/schema")
        assert response.status_code == 404


class TestUpdateModelSchema:
    """Tests for POST /api/models/{model_name}/schema endpoint."""

    def test_updates_schema(self, test_client, temp_dir, mock_manifest):
        # Create the SQL file that manifest points to
        sql_dir = os.path.join(temp_dir, "models", "3_core")
        os.makedirs(sql_dir, exist_ok=True)
        with open(os.path.join(sql_dir, "users.sql"), "w") as f:
            f.write("SELECT 1")

        request_data = {
            "columns": [
                {"name": "id", "data_type": "int", "description": "Primary key"},
            ],
            "description": "Updated description",
        }
        response = test_client.post("/api/models/users/schema", json=request_data)
        assert response.status_code == 200

        result = response.json()
        assert result["status"] == "success"

        # Verify the YML file was created
        yml_path = os.path.join(sql_dir, "users.yml")
        assert os.path.exists(yml_path)

    def test_removes_renamed_and_deleted_columns(
        self, test_client, temp_dir, mock_manifest
    ):
        """Regression: renaming or deleting fields in data_model.yml must
        propagate to schema.yml instead of leaving stale columns behind.
        See issue #98."""
        sql_dir = os.path.join(temp_dir, "models", "3_core")
        os.makedirs(sql_dir, exist_ok=True)
        with open(os.path.join(sql_dir, "users.sql"), "w") as f:
            f.write("SELECT 1")

        yml_path = os.path.join(sql_dir, "users.yml")
        with open(yml_path, "w") as f:
            yaml.dump(
                {
                    "version": 2,
                    "models": [
                        {
                            "name": "users",
                            "columns": [
                                {"name": "id", "data_type": "int"},
                                {"name": "old_email", "data_type": "text"},
                                {"name": "to_delete", "data_type": "text"},
                            ],
                        }
                    ],
                },
                f,
            )

        request_data = {
            "columns": [
                {"name": "id", "data_type": "int"},
                {"name": "new_email", "data_type": "text"},
            ],
        }
        response = test_client.post("/api/models/users/schema", json=request_data)
        assert response.status_code == 200

        with open(yml_path, "r") as f:
            saved = yaml.safe_load(f)
        names = [c["name"] for c in saved["models"][0]["columns"]]
        assert names == ["id", "new_email"]


class TestInferRelationships:
    """Tests for GET /api/infer-relationships endpoint."""

    def test_returns_empty_for_no_yml_files(self, test_client, temp_dir):
        response = test_client.get("/api/infer-relationships")
        assert response.status_code == 400
        assert "No schema yml files found" in response.json()["detail"]

    def test_infers_relationships_from_tests(
        self, test_client, temp_dir, temp_data_model_path
    ):
        # Data model with bound entities
        data_model = {
            "version": 0.1,
            "entities": [
                {"id": "users", "dbt_model": "model.project.users"},
                {"id": "orders", "dbt_model": "model.project.orders"},
            ],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data_model, f)

        # Create a YML file with relationship tests
        models_dir = os.path.join(temp_dir, "models", "3_core")
        os.makedirs(models_dir, exist_ok=True)

        schema = {
            "version": 2,
            "models": [
                {
                    "name": "orders",
                    "columns": [
                        {
                            "name": "user_id",
                            "data_type": "int",
                            "tests": [
                                {
                                    "relationships": {
                                        "arguments": {
                                            "to": "ref('users')",
                                            "field": "id",
                                        }
                                    }
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        with open(os.path.join(models_dir, "orders.yml"), "w") as f:
            yaml.dump(schema, f)

        response = test_client.get("/api/infer-relationships")
        assert response.status_code == 200

        rels = response.json()["relationships"]
        assert len(rels) == 1
        assert rels[0]["source"] == "users"
        assert rels[0]["target"] == "orders"
        assert rels[0]["source_field"] == "id"
        assert rels[0]["target_field"] == "user_id"

    def test_infers_relationships_from_nested_directories(
        self, test_client, temp_dir, temp_data_model_path
    ):
        # Ensure nested model directories are also scanned
        nested_dir = os.path.join(temp_dir, "models", "3_core", "all")
        os.makedirs(nested_dir, exist_ok=True)

        data_model = {
            "version": 0.1,
            "entities": [
                {"id": "team", "dbt_model": "model.project.team"},
                {"id": "game", "dbt_model": "model.project.game"},
            ],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data_model, f)

        schema = {
            "version": 2,
            "models": [
                {
                    "name": "game",
                    "columns": [
                        {
                            "name": "home_team_id",
                            "data_type": "text",
                            "data_tests": [
                                {
                                    "relationships": {
                                        "arguments": {
                                            "to": "ref('team')",
                                            "field": "team_id",
                                        },
                                    }
                                }
                            ],
                        },
                        {
                            "name": "away_team_id",
                            "data_type": "text",
                            "data_tests": [
                                {
                                    "relationships": {
                                        "arguments": {
                                            "to": "ref('team')",
                                            "field": "team_id",
                                        },
                                    }
                                }
                            ],
                        },
                    ],
                }
            ],
        }

        with open(os.path.join(nested_dir, "game.yml"), "w") as f:
            yaml.dump(schema, f)

        response = test_client.get("/api/infer-relationships")
        assert response.status_code == 200

        rels = response.json()["relationships"]
        assert len(rels) == 2
        assert {
            "source": "team",
            "target": "game",
            "source_field": "team_id",
            "target_field": "home_team_id",
        } in [
            {
                "source": r["source"],
                "target": r["target"],
                "source_field": r["source_field"],
                "target_field": r["target_field"],
            }
            for r in rels
        ]
        assert {
            "source": "team",
            "target": "game",
            "source_field": "team_id",
            "target_field": "away_team_id",
        } in [
            {
                "source": r["source"],
                "target": r["target"],
                "source_field": r["source_field"],
                "target_field": r["target_field"],
            }
            for r in rels
        ]

    def test_infers_relationships_across_multiple_model_paths(
        self, test_client, temp_dir, temp_data_model_path
    ):
        """
        When multiple dbt model paths are configured (including with a models/ prefix),
        all should be scanned.
        """
        from trellis_datamodel import config as cfg

        # Add an extra model path and point to a different directory
        extra_models_dir = os.path.join(temp_dir, "models", "3_entity")
        os.makedirs(extra_models_dir, exist_ok=True)

        original_paths = list(cfg.DBT_MODEL_PATHS)
        try:
            cfg.DBT_MODEL_PATHS = ["3_core", "models/3_entity"]

            data_model = {
                "version": 0.1,
                "entities": [
                    {"id": "product", "dbt_model": "model.project.product"},
                    {"id": "opportunity", "dbt_model": "model.project.opportunity"},
                ],
            }
            with open(temp_data_model_path, "w") as f:
                yaml.dump(data_model, f)

            schema = {
                "version": 2,
                "models": [
                    {
                        "name": "opportunity",
                        "columns": [
                            {
                                "name": "product_id",
                                "data_tests": [
                                    {
                                        "relationships": {
                                            "arguments": {
                                                "to": "ref('product')",
                                                "field": "product_id",
                                            }
                                        }
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }

            with open(os.path.join(extra_models_dir, "opportunity.yml"), "w") as f:
                yaml.dump(schema, f)

            response = test_client.get("/api/infer-relationships")
            assert response.status_code == 200

            rels = response.json()["relationships"]
            assert {"source": "product", "target": "opportunity"} in [
                {"source": r["source"], "target": r["target"]} for r in rels
            ]
        finally:
            cfg.DBT_MODEL_PATHS = original_paths
            shutil.rmtree(extra_models_dir, ignore_errors=True)

    def test_infers_relationships_with_arguments_block(
        self, test_client, temp_dir, temp_data_model_path
    ):
        """
        The app should recognize dbt's arguments syntax for relationship tests.
        """
        models_dir = os.path.join(temp_dir, "models", "3_core")
        # Clean out prior test artifacts to avoid cross-test contamination
        shutil.rmtree(models_dir, ignore_errors=True)
        os.makedirs(models_dir, exist_ok=True)

        data_model = {
            "version": 0.1,
            "entities": [
                {"id": "customers", "dbt_model": "model.project.customers"},
                {"id": "orders", "dbt_model": "model.project.orders"},
            ],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data_model, f)

        schema = {
            "version": 2,
            "models": [
                {
                    "name": "orders",
                    "columns": [
                        {
                            "name": "customer_id",
                            "data_type": "int",
                            "data_tests": [
                                {
                                    "relationships": {
                                        "arguments": {
                                            "to": "ref('customers')",
                                            "field": "id",
                                        },
                                        "config": {"severity": "error"},
                                    }
                                }
                            ],
                        }
                    ],
                }
            ],
        }

        with open(os.path.join(models_dir, "orders.yml"), "w") as f:
            yaml.dump(schema, f)

        response = test_client.get("/api/infer-relationships")
        assert response.status_code == 200

        rels = response.json()["relationships"]
        assert len(rels) == 1
        assert rels[0]["source"] == "customers"
        assert rels[0]["target"] == "orders"
        assert rels[0]["source_field"] == "id"
        assert rels[0]["target_field"] == "customer_id"

    def test_can_include_unbound_entities_when_requested(
        self, test_client, temp_dir, temp_data_model_path
    ):
        """
        When include_unbound=true is passed, relationships are returned even if
        the entities have not yet been persisted with dbt_model bindings.
        """
        models_dir = os.path.join(temp_dir, "models", "3_core")
        os.makedirs(models_dir, exist_ok=True)

        # Data model without dbt_model bindings (e.g. right after a drag+drop)
        data_model = {
            "version": 0.1,
            "entities": [
                {"id": "customers"},
                {"id": "orders"},
            ],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data_model, f)

        # Relationship test between the two models
        schema = {
            "version": 2,
            "models": [
                {
                    "name": "orders",
                    "columns": [
                        {
                            "name": "customer_id",
                            "tests": [
                                {
                                    "relationships": {
                                        "arguments": {
                                            "to": "ref('customers')",
                                            "field": "id",
                                        }
                                    }
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        with open(os.path.join(models_dir, "orders.yml"), "w") as f:
            yaml.dump(schema, f)

        # Default behaviour should still filter unbound entities
        default_response = test_client.get("/api/infer-relationships")
        assert default_response.status_code == 200
        assert default_response.json()["relationships"] == []

        # With the flag enabled we should get the inferred relationship back
        response = test_client.get("/api/infer-relationships?include_unbound=true")
        assert response.status_code == 200
        rels = response.json()["relationships"]
        assert len(rels) == 1
        assert rels[0]["source"] == "customers"
        assert rels[0]["target"] == "orders"
        assert rels[0]["source_field"] == "id"
        assert rels[0]["target_field"] == "customer_id"

    def test_maps_additional_models_to_entity_ids(
        self, test_client, temp_dir, temp_data_model_path
    ):
        """
        Relationship inference should translate additional_models to their entity IDs.
        """
        # Data model maps additional model to entity
        data_model = {
            "version": 0.1,
            "entities": [
                {
                    "id": "customers",
                    "label": "Customers",
                    "additional_models": ["model.project.customers_alt"],
                },
                {
                    "id": "orders",
                    "label": "Orders",
                    "dbt_model": "model.project.orders",
                },
            ],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data_model, f)

        # Create YML for additional model name with relationship test
        models_dir = os.path.join(temp_dir, "models", "3_core")
        os.makedirs(models_dir, exist_ok=True)
        schema = {
            "version": 2,
            "models": [
                {
                    "name": "customers_alt",
                    "columns": [
                        {
                            "name": "id",
                            "data_type": "int",
                            "data_tests": [
                                {
                                    "relationships": {
                                        "arguments": {
                                            "to": "ref('orders')",
                                            "field": "order_id",
                                        },
                                    }
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        with open(os.path.join(models_dir, "customers_alt.yml"), "w") as f:
            yaml.dump(schema, f)

        response = test_client.get("/api/infer-relationships")
        assert response.status_code == 200

        rels = response.json()["relationships"]
        # Find the relationship coming from the additional model file
        rel = next(
            r
            for r in rels
            if r["source_field"] == "order_id"
            and r["target_field"] == "id"
            and r["target"] == "customers"
            and r["source"] == "orders"
        )
        assert rel

    def test_resolves_versioned_refs_to_existing_entity(
        self, test_client, temp_dir, temp_data_model_path
    ):
        """
        ref('model', v=1) should resolve to an entity bound to v2 (or vice-versa)
        instead of creating a duplicate entity.
        """
        # Bind player to v2 in the data model
        data_model = {
            "version": 0.1,
            "entities": [
                {
                    "id": "player",
                    "label": "Player",
                    "dbt_model": "model.test.player.v2",
                },
                {
                    "id": "game_stats",
                    "label": "Game Stats",
                    "dbt_model": "model.test.game_stats",
                },
            ],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data_model, f)

        # YML with versioned ref to player v1
        schema = {
            "version": 2,
            "models": [
                {
                    "name": "game_stats",
                    "columns": [
                        {
                            "name": "player_id",
                            "data_tests": [
                                {
                                    "relationships": {
                                        "arguments": {
                                            "to": "ref('player', v=1)",
                                            "field": "player_id",
                                        }
                                    }
                                }
                            ],
                        }
                    ],
                }
            ],
        }

        models_dir = os.path.join(temp_dir, "models", "3_core")
        os.makedirs(models_dir, exist_ok=True)
        with open(os.path.join(models_dir, "game_stats.yml"), "w") as f:
            yaml.dump(schema, f)

        response = test_client.get("/api/infer-relationships")
        assert response.status_code == 200

        rels = response.json()["relationships"]
        assert len(rels) == 1
        rel = rels[0]
        assert rel["source"] == "player"
        assert rel["target"] == "game_stats"
        assert rel["source_field"] == "player_id"
        assert rel["target_field"] == "player_id"


class TestEntityPrefixApplication:
    """Tests for entity prefix application in save endpoint."""

    def test_applies_prefix_to_unbound_entity(
        self, test_client, temp_dir, temp_data_model_path, monkeypatch
    ):
        """Test that entity prefix is applied when saving unbound entity."""
        from trellis_datamodel import config as cfg

        # Set up entity modeling config with prefix
        original_config = cfg.ENTITY_MODELING_CONFIG
        monkeypatch.setattr(
            cfg,
            "ENTITY_MODELING_CONFIG",
            type("obj", (object,), {"enabled": True, "entity_prefix": ["tbl_"]})(),
        )
        monkeypatch.setattr(cfg, "MODELING_STYLE", "entity_model")

        # Data model with unbound entity
        data_model = {
            "version": 0.1,
            "entities": [
                {
                    "id": "customer",
                    "label": "Customer",
                    "position": {"x": 0, "y": 0},
                }
            ],
            "relationships": [],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data_model, f)

        # Save schema
        request_data = {
            "entity_id": "customer",
            "model_name": "customer",
            "fields": [{"name": "id", "datatype": "int"}],
            "description": "Customer entity",
        }
        response = test_client.post("/api/dbt-schema", json=request_data)
        assert response.status_code == 200

        # Verify prefix was applied in saved schema
        result = response.json()
        with open(result["file_path"], "r") as f:
            schema = yaml.safe_load(f)

        assert schema["models"][0]["name"] == "tbl_customer"

        # Restore original config
        monkeypatch.setattr(cfg, "ENTITY_MODELING_CONFIG", original_config)

    def test_does_not_double_prefix_bound_entity(
        self, test_client, temp_dir, temp_data_model_path, monkeypatch
    ):
        """Test that bound entity with prefix doesn't get double-prefixed."""
        from trellis_datamodel import config as cfg

        # Set up entity modeling config with prefix
        original_config = cfg.ENTITY_MODELING_CONFIG
        monkeypatch.setattr(
            cfg,
            "ENTITY_MODELING_CONFIG",
            type("obj", (object,), {"enabled": True, "entity_prefix": ["tbl_"]})(),
        )
        monkeypatch.setattr(cfg, "MODELING_STYLE", "entity_model")

        # Create manifest with prefixed model
        manifest_path = os.path.join(temp_dir, "manifest.json")
        manifest_data = {
            "nodes": {
                "model.project.tbl_orders": {
                    "unique_id": "model.project.tbl_orders",
                    "resource_type": "model",
                    "name": "tbl_orders",
                    "schema": "public",
                    "alias": "tbl_orders",
                    "original_file_path": "models/3_core/tbl_orders.sql",
                    "columns": {},
                    "description": "Orders table",
                    "config": {"materialized": "table"},
                    "tags": [],
                }
            }
        }
        with open(manifest_path, "w") as f:
            json.dump(manifest_data, f)

        # Data model with bound entity (already has prefix)
        data_model = {
            "version": 0.1,
            "entities": [
                {
                    "id": "order",
                    "label": "Order",
                    "dbt_model": "model.project.tbl_orders",
                    "position": {"x": 0, "y": 0},
                }
            ],
            "relationships": [],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data_model, f)

        # Save schema - should not double prefix
        request_data = {
            "entity_id": "order",
            "model_name": "order",
            "fields": [{"name": "order_id", "datatype": "int"}],
            "description": "Order entity",
        }
        response = test_client.post("/api/dbt-schema", json=request_data)
        assert response.status_code == 200

        # Verify no double prefix in saved schema
        result = response.json()
        with open(result["file_path"], "r") as f:
            schema = yaml.safe_load(f)

        assert schema["models"][0]["name"] == "tbl_orders"  # Not "tbl_tbl_orders"

        # Restore original config
        monkeypatch.setattr(cfg, "ENTITY_MODELING_CONFIG", original_config)

    def test_case_insensitive_prefix_detection(
        self, test_client, temp_dir, temp_data_model_path, monkeypatch
    ):
        """Test that prefix detection is case-insensitive."""
        from trellis_datamodel import config as cfg

        # Set up entity modeling config with lowercase prefix
        original_config = cfg.ENTITY_MODELING_CONFIG
        monkeypatch.setattr(
            cfg,
            "ENTITY_MODELING_CONFIG",
            type("obj", (object,), {"enabled": True, "entity_prefix": ["tbl_"]})(),
        )
        monkeypatch.setattr(cfg, "MODELING_STYLE", "entity_model")

        # Data model with entity ID that has prefix in uppercase
        data_model = {
            "version": 0.1,
            "entities": [
                {
                    "id": "TBL_CUSTOMER",  # Uppercase prefix
                    "label": "Customer",
                    "position": {"x": 0, "y": 0},
                }
            ],
            "relationships": [],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data_model, f)

        # Save schema - should detect prefix and not double
        request_data = {
            "entity_id": "TBL_CUSTOMER",
            "model_name": "TBL_CUSTOMER",
            "fields": [{"name": "id", "datatype": "int"}],
            "description": "Customer entity",
        }
        response = test_client.post("/api/dbt-schema", json=request_data)
        assert response.status_code == 200

        # Verify no double prefix (case-insensitive match)
        result = response.json()
        with open(result["file_path"], "r") as f:
            schema = yaml.safe_load(f)

        assert schema["models"][0]["name"] == "TBL_CUSTOMER"  # Not "tbl_TBL_CUSTOMER"

        # Restore original config
        monkeypatch.setattr(cfg, "ENTITY_MODELING_CONFIG", original_config)

    def test_uses_first_prefix_from_multiple_configured(
        self, test_client, temp_dir, temp_data_model_path, monkeypatch
    ):
        """Test that first configured prefix is used when multiple are provided."""
        from trellis_datamodel import config as cfg

        # Set up entity modeling config with multiple prefixes
        original_config = cfg.ENTITY_MODELING_CONFIG
        monkeypatch.setattr(
            cfg,
            "ENTITY_MODELING_CONFIG",
            type(
                "obj",
                (object,),
                {"enabled": True, "entity_prefix": ["tbl_", "entity_", "t_"]},
            )(),
        )
        monkeypatch.setattr(cfg, "MODELING_STYLE", "entity_model")

        # Data model with unbound entity
        data_model = {
            "version": 0.1,
            "entities": [
                {
                    "id": "product",
                    "label": "Product",
                    "position": {"x": 0, "y": 0},
                }
            ],
            "relationships": [],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data_model, f)

        # Save schema - should use first prefix
        request_data = {
            "entity_id": "product",
            "model_name": "product",
            "fields": [{"name": "product_id", "datatype": "int"}],
            "description": "Product entity",
        }
        response = test_client.post("/api/dbt-schema", json=request_data)
        assert response.status_code == 200

        # Verify first prefix was applied
        result = response.json()
        with open(result["file_path"], "r") as f:
            schema = yaml.safe_load(f)

        assert schema["models"][0]["name"] == "tbl_product"  # Uses first prefix

        # Restore original config
        monkeypatch.setattr(cfg, "ENTITY_MODELING_CONFIG", original_config)

    def test_no_prefix_when_entity_modeling_disabled(
        self, test_client, temp_dir, temp_data_model_path, monkeypatch
    ):
        """Test that no prefix is applied when entity modeling is disabled."""
        from trellis_datamodel import config as cfg

        # Set up entity modeling config as disabled
        original_config = cfg.ENTITY_MODELING_CONFIG
        monkeypatch.setattr(
            cfg,
            "ENTITY_MODELING_CONFIG",
            type("obj", (object,), {"enabled": False, "entity_prefix": ["tbl_"]})(),
        )
        monkeypatch.setattr(cfg, "MODELING_STYLE", "dimensional_model")

        # Data model with unbound entity
        data_model = {
            "version": 0.1,
            "entities": [
                {
                    "id": "category",
                    "label": "Category",
                    "position": {"x": 0, "y": 0},
                }
            ],
            "relationships": [],
        }
        with open(temp_data_model_path, "w") as f:
            yaml.dump(data_model, f)

        # Save schema - should not apply prefix
        request_data = {
            "entity_id": "category",
            "model_name": "category",
            "fields": [{"name": "category_id", "datatype": "int"}],
            "description": "Category entity",
        }
        response = test_client.post("/api/dbt-schema", json=request_data)
        assert response.status_code == 200

        # Verify no prefix was applied
        result = response.json()
        with open(result["file_path"], "r") as f:
            schema = yaml.safe_load(f)

        assert schema["models"][0]["name"] == "category"  # Not "tbl_category"

        # Restore original config
        monkeypatch.setattr(cfg, "ENTITY_MODELING_CONFIG", original_config)


class TestModelSchemaVersionHandling:
    """Ensure schema read/write honors requested dbt model version."""

    def _write_versioned_manifest(self, temp_dir: str):
        manifest_data = {
            "nodes": {
                "model.project.player.v1": {
                    "unique_id": "model.project.player.v1",
                    "resource_type": "model",
                    "name": "player",
                    "version": 1,
                    "schema": "public",
                    "alias": "player",
                    "original_file_path": "models/3_core/all/player_v1.sql",
                    "columns": {},
                    "description": "Player v1",
                    "config": {"materialized": "table"},
                    "tags": [],
                },
                "model.project.player.v2": {
                    "unique_id": "model.project.player.v2",
                    "resource_type": "model",
                    "name": "player",
                    "version": 2,
                    "schema": "public",
                    "alias": "player",
                    "original_file_path": "models/3_core/all/player_v2.sql",
                    "columns": {},
                    "description": "Player v2",
                    "config": {"materialized": "table"},
                    "tags": [],
                },
            }
        }

        manifest_path = os.path.join(temp_dir, "manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(manifest_data, f)

    def _write_versioned_schema(self, temp_dir: str) -> str:
        models_dir = os.path.join(temp_dir, "models", "3_core", "all")
        os.makedirs(models_dir, exist_ok=True)
        yml_path = os.path.join(models_dir, "player.yml")

        existing_schema = {
            "version": 2,
            "models": [
                {
                    "name": "player",
                    "latest_version": 2,
                    "versions": [
                        {
                            "v": 1,
                            "description": "v1 description",
                            "columns": [{"name": "player_id", "data_type": "text"}],
                        },
                        {
                            "v": 2,
                            "description": "v2 description",
                            "columns": [{"name": "player_uuid", "data_type": "text"}],
                        },
                    ],
                }
            ],
        }

        with open(yml_path, "w") as f:
            yaml.dump(existing_schema, f)

        return yml_path

    def test_get_model_schema_uses_requested_version(self, test_client, temp_dir):
        self._write_versioned_manifest(temp_dir)
        self._write_versioned_schema(temp_dir)

        response = test_client.get("/api/models/player/schema", params={"version": 2})
        assert response.status_code == 200

        schema = response.json()
        col_names = [col["name"] for col in schema["columns"]]
        assert "player_uuid" in col_names
        assert "player_id" not in col_names
        assert schema["description"] == "v2 description"

    def test_save_model_schema_targets_requested_version(self, test_client, temp_dir):
        self._write_versioned_manifest(temp_dir)
        yml_path = self._write_versioned_schema(temp_dir)

        response = test_client.post(
            "/api/models/player/schema",
            json={
                "columns": [
                    {
                        "name": "player_uuid",
                        "data_type": "text",
                        "description": "Updated PK",
                    }
                ],
                "description": "Players v2 updated",
                "tags": ["core"],
                "version": 2,
            },
        )
        assert response.status_code == 200

        with open(yml_path, "r") as f:
            updated = yaml.safe_load(f)

        versions = {v["v"]: v for v in updated["models"][0]["versions"]}
        assert versions[1]["columns"][0]["name"] == "player_id"

        v2_cols = versions[2]["columns"]
        assert v2_cols[0]["name"] == "player_uuid"
        assert v2_cols[0]["description"] == "Updated PK"
        assert versions[2].get("config", {}).get("tags") == ["core"]
        assert updated["models"][0]["latest_version"] == 2
