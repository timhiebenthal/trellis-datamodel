"""Tests for the dbt reconciliation service."""

import pytest
from trellis_datamodel.services.reconciliation import (
    reconcile_entity_fields,
    reconcile_data_model,
)


class TestReconcileEntityFields:
    """Unit tests for the pure reconcile_entity_fields function."""

    def test_materializes_manifest_columns(self):
        """Manifest columns become source=dbt fields with name/datatype/description."""
        result = reconcile_entity_fields(
            existing_fields=[],
            manifest_columns=[
                {"name": "id", "type": "integer", "description": "Primary key"},
                {"name": "email", "type": "text", "description": "Email address"},
            ],
        )
        assert len(result) == 2
        assert result[0]["name"] == "id"
        assert result[0]["source"] == "dbt"
        assert result[0]["description"] == "Primary key"
        assert result[1]["name"] == "email"
        assert result[1]["source"] == "dbt"
        assert result[1]["description"] == "Email address"

    def test_maps_dbt_type_to_datatype(self):
        """Manifest types are mapped to the DraftedField datatype enum."""
        result = reconcile_entity_fields(
            existing_fields=[],
            manifest_columns=[
                {"name": "count", "type": "bigint"},
                {"name": "ratio", "type": "float8"},
                {"name": "flag", "type": "boolean"},
                {"name": "created", "type": "date"},
                {"name": "updated", "type": "timestamp without time zone"},
                {"name": "label", "type": "varchar"},
                {"name": "weird", "type": "bytea"},
            ],
        )
        assert result[0]["datatype"] == "int"
        assert result[1]["datatype"] == "float"
        assert result[2]["datatype"] == "bool"
        assert result[3]["datatype"] == "date"
        assert result[4]["datatype"] == "timestamp"
        assert result[5]["datatype"] == "text"
        assert result[6]["datatype"] == "unknown"

    def test_promotes_matching_draft(self):
        """A draft whose name matches a manifest column is promoted to source=dbt,
        with manifest metadata overwriting the draft's values."""
        result = reconcile_entity_fields(
            existing_fields=[
                {"name": "revenue", "datatype": "float", "description": "Old draft desc", "source": "draft"},
            ],
            manifest_columns=[
                {"name": "revenue", "type": "numeric", "description": "Manifest desc"},
            ],
        )
        assert len(result) == 1
        assert result[0]["name"] == "revenue"
        assert result[0]["source"] == "dbt"
        assert result[0]["description"] == "Manifest desc"

    def test_preserves_unmatched_draft(self):
        """A drafted field with no matching manifest column is kept unchanged."""
        result = reconcile_entity_fields(
            existing_fields=[
                {"name": "forecast", "datatype": "float", "description": "Future metric"},
            ],
            manifest_columns=[
                {"name": "revenue", "type": "numeric"},
            ],
        )
        names = [f["name"] for f in result]
        assert "forecast" in names
        draft = next(f for f in result if f["name"] == "forecast")
        assert draft.get("source") in (None, "draft")
        assert draft["description"] == "Future metric"

    def test_non_destructive_when_model_absent(self):
        """manifest_columns=None means the model is absent from the manifest;
        existing fields must be returned unchanged (non-destructive invariant)."""
        existing = [
            {"name": "id", "datatype": "int", "source": "dbt"},
            {"name": "draft_col", "datatype": "text", "source": "draft"},
        ]
        result = reconcile_entity_fields(existing_fields=existing, manifest_columns=None)
        assert result == existing

    def test_deterministic_order(self):
        """dbt fields appear in manifest order, then drafts in original order."""
        result = reconcile_entity_fields(
            existing_fields=[
                {"name": "draft_a", "datatype": "text"},
                {"name": "draft_b", "datatype": "text"},
            ],
            manifest_columns=[
                {"name": "col_z", "type": "text"},
                {"name": "col_a", "type": "text"},
            ],
        )
        names = [f["name"] for f in result]
        assert names == ["col_z", "col_a", "draft_a", "draft_b"]

    def test_empty_existing_empty_manifest(self):
        """Both empty — result is empty, not an error."""
        result = reconcile_entity_fields(existing_fields=[], manifest_columns=[])
        assert result == []

    def test_existing_source_dbt_fields_overwritten(self):
        """Previously reconciled source=dbt fields are overwritten from manifest (dbt is right)."""
        result = reconcile_entity_fields(
            existing_fields=[
                {"name": "id", "datatype": "text", "description": "Stale description", "source": "dbt"},
            ],
            manifest_columns=[
                {"name": "id", "type": "integer", "description": "Fresh from manifest"},
            ],
        )
        assert len(result) == 1
        assert result[0]["description"] == "Fresh from manifest"
        assert result[0]["datatype"] == "int"
        assert result[0]["source"] == "dbt"

    def test_origin_field_preserved_on_promoted_draft(self):
        """The free-text origin field on a drafted field is preserved after promotion."""
        result = reconcile_entity_fields(
            existing_fields=[
                {"name": "revenue", "datatype": "float", "origin": "DH1: SCHEMA.TABLE.COL"},
            ],
            manifest_columns=[
                {"name": "revenue", "type": "numeric"},
            ],
        )
        assert result[0].get("origin") == "DH1: SCHEMA.TABLE.COL"


class TestReconcileDataModel:
    """Unit tests for the reconcile_data_model function."""

    def _make_manifest_models(self, name, columns):
        return [{"name": name, "unique_id": f"model.project.{name}", "columns": columns}]

    def test_reconciles_bound_entity(self):
        """A bound entity present in the manifest gets its dbt fields reconciled."""
        data_model = {
            "entities": [
                {
                    "id": "users",
                    "dbt_model": "model.project.users",
                    "drafted_fields": [],
                }
            ]
        }
        manifest_models = [
            {
                "unique_id": "model.project.users",
                "name": "users",
                "columns": [{"name": "id", "type": "integer", "description": "PK"}],
            }
        ]
        result, changed = reconcile_data_model(data_model, manifest_models)
        assert changed is True
        entity = result["entities"][0]
        assert len(entity["drafted_fields"]) == 1
        assert entity["drafted_fields"][0]["source"] == "dbt"
        assert entity["drafted_fields"][0]["name"] == "id"

    def test_unbound_entity_untouched(self):
        """An entity without dbt_model is not modified."""
        data_model = {
            "entities": [
                {"id": "sketch", "drafted_fields": [{"name": "col", "datatype": "text"}]}
            ]
        }
        result, changed = reconcile_data_model(data_model, [])
        assert changed is False
        assert result["entities"][0]["drafted_fields"] == [{"name": "col", "datatype": "text"}]

    def test_absent_model_non_destructive(self):
        """A bound entity whose model is absent from the manifest is left untouched."""
        data_model = {
            "entities": [
                {
                    "id": "users",
                    "dbt_model": "model.project.users",
                    "drafted_fields": [{"name": "id", "datatype": "int", "source": "dbt"}],
                }
            ]
        }
        # manifest_models does NOT contain users
        result, changed = reconcile_data_model(data_model, [])
        assert changed is False
        assert result["entities"][0]["drafted_fields"] == [
            {"name": "id", "datatype": "int", "source": "dbt"}
        ]

    def test_changed_false_when_already_reconciled(self):
        """Reconciling an already-reconciled model returns changed=False (idempotency)."""
        manifest_models = [
            {
                "unique_id": "model.project.users",
                "name": "users",
                "columns": [{"name": "id", "type": "integer", "description": "PK"}],
            }
        ]
        data_model = {
            "entities": [
                {
                    "id": "users",
                    "dbt_model": "model.project.users",
                    "drafted_fields": [
                        {"name": "id", "datatype": "int", "description": "PK", "source": "dbt"}
                    ],
                }
            ]
        }
        result, changed = reconcile_data_model(data_model, manifest_models)
        assert changed is False

    def test_multiple_entities_mixed(self):
        """Bound entity reconciled, unbound entity untouched."""
        data_model = {
            "entities": [
                {
                    "id": "users",
                    "dbt_model": "model.project.users",
                    "drafted_fields": [],
                },
                {
                    "id": "sketch",
                    "drafted_fields": [{"name": "future_col", "datatype": "text"}],
                },
            ]
        }
        manifest_models = [
            {
                "unique_id": "model.project.users",
                "name": "users",
                "columns": [{"name": "id", "type": "integer"}],
            }
        ]
        result, changed = reconcile_data_model(data_model, manifest_models)
        assert changed is True
        users = next(e for e in result["entities"] if e["id"] == "users")
        sketch = next(e for e in result["entities"] if e["id"] == "sketch")
        assert users["drafted_fields"][0]["source"] == "dbt"
        assert sketch["drafted_fields"] == [{"name": "future_col", "datatype": "text"}]
