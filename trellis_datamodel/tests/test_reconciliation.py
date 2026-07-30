"""Tests for the dbt reconciliation service."""

import pytest
from trellis_datamodel.services.reconciliation import (
    reconcile_entity_fields,
    reconcile_entity_tags,
    reconcile_data_model,
    compute_display_tags,
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

    def test_preserves_native_dbt_type_alongside_bucket(self):
        """The raw dbt/warehouse type is preserved in dbt_data_type, not just
        collapsed into the coarse datatype bucket (#111)."""
        result = reconcile_entity_fields(
            existing_fields=[],
            manifest_columns=[
                {"name": "label", "type": "varchar"},
            ],
        )
        assert result[0]["datatype"] == "text"
        assert result[0]["dbt_data_type"] == "varchar"

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
        assert result[0]["origin"] == "DH1: SCHEMA.TABLE.COL"

    def test_reconcile_preserves_list_origin(self):
        """Structured list origin on a draft field passes through unchanged."""
        origin_list = [{"DH1": "CORE.A"}, {"DH2": "CBUS.B"}]
        result = reconcile_entity_fields(
            existing_fields=[
                {"name": "revenue", "datatype": "float", "origin": origin_list},
            ],
            manifest_columns=[],
        )
        assert result[0]["origin"] == origin_list

    def test_origin_parsed_from_manifest_description(self):
        """Origin embedded in manifest description is parsed into separate field."""
        result = reconcile_entity_fields(
            existing_fields=[],
            manifest_columns=[
                {"name": "revenue", "type": "numeric", "description": "Total revenue | Origin: DH1: SCHEMA.TABLE.COL"},
            ],
        )
        assert result[0]["description"] == "Total revenue"
        assert result[0]["origin"] == "DH1: SCHEMA.TABLE.COL"

    def test_origin_only_parsed_from_manifest_description(self):
        """Origin-only description (no preceding text) is parsed correctly."""
        result = reconcile_entity_fields(
            existing_fields=[],
            manifest_columns=[
                {"name": "revenue", "type": "numeric", "description": "Origin: DH1: SCHEMA.TABLE.COL"},
            ],
        )
        assert result[0]["description"] is None
        assert result[0]["origin"] == "DH1: SCHEMA.TABLE.COL"

    def test_stale_origin_removed_when_description_changes(self):
        """If manifest description no longer contains origin, stale origin is removed."""
        result = reconcile_entity_fields(
            existing_fields=[
                {"name": "revenue", "datatype": "float", "description": "Old desc", "origin": "OLD_ORIGIN"},
            ],
            manifest_columns=[
                {"name": "revenue", "type": "numeric", "description": "New desc without origin"},
            ],
        )
        assert result[0]["description"] == "New desc without origin"
        assert "origin" not in result[0]


class TestReconcileEntityTags:
    def test_dbt_tags_overwrite_existing_tags_field(self):
        """dbt is authoritative for the mirrored `tags` field — always overwritten."""
        result = reconcile_entity_tags(existing_tags=["stale"], manifest_tags=["nightly", "core"])
        assert result == ["nightly", "core"]

    def test_absent_from_manifest_is_non_destructive(self):
        """Model absent from manifest (partial compile) — existing tags untouched."""
        result = reconcile_entity_tags(existing_tags=["nightly"], manifest_tags=None)
        assert result == ["nightly"]

    def test_empty_manifest_tags_clears_mirrored_tags(self):
        """Model present in manifest with no tags — mirrored tags become empty,
        distinct from 'absent from manifest' (None)."""
        result = reconcile_entity_tags(existing_tags=["stale"], manifest_tags=[])
        assert result == []


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
                        {
                            "name": "id",
                            "datatype": "int",
                            "dbt_data_type": "integer",
                            "description": "PK",
                            "source": "dbt",
                        }
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

    def test_reconcile_data_model_refreshes_entity_dbt_tags_from_manifest(self):
        data_model = {
            "entities": [
                {"id": "users", "dbt_model": "model.proj.users", "dbt_tags": ["old"]},
            ]
        }
        manifest_models = [
            {"unique_id": "model.proj.users", "columns": [], "tags": ["nightly", "core"]},
        ]
        result, changed = reconcile_data_model(data_model, manifest_models)
        assert result["entities"][0]["dbt_tags"] == ["nightly", "core"]
        assert changed is True

    def test_reconcile_data_model_leaves_ui_tags_untouched(self):
        data_model = {
            "entities": [
                {
                    "id": "users",
                    "dbt_model": "model.proj.users",
                    "dbt_tags": ["old"],
                    "ui_tags": ["pii"],
                },
            ]
        }
        manifest_models = [
            {"unique_id": "model.proj.users", "columns": [], "tags": ["nightly"]},
        ]
        result, _ = reconcile_data_model(data_model, manifest_models)
        assert result["entities"][0]["ui_tags"] == ["pii"]


class TestTagMigrationSeed:
    def test_legacy_tags_seed_ui_tags_once_and_retire_legacy_key(self):
        """An entity with a pre-existing legacy `tags` value (from before the
        dbt_tags/ui_tags split existed) and no `ui_tags` key is seeded once so
        its tags aren't lost, and the legacy `tags` key is retired — bound
        entities never persist `tags` going forward."""
        data_model = {
            "entities": [
                {"id": "users", "dbt_model": "model.proj.users", "tags": ["pii"]},
            ]
        }
        manifest_models = [
            {"unique_id": "model.proj.users", "columns": [], "tags": ["nightly"]},
        ]
        result, _ = reconcile_data_model(data_model, manifest_models)
        entity = result["entities"][0]
        assert entity["ui_tags"] == ["pii"]
        assert entity["dbt_tags"] == ["nightly"]
        assert "tags" not in entity

    def test_seed_does_not_reapply_once_ui_tags_exists(self):
        """The one-time seed never runs again once ui_tags is present,
        even if it's empty (explicit user removal must stick), but the
        legacy tags key is still retired."""
        data_model = {
            "entities": [
                {
                    "id": "users",
                    "dbt_model": "model.proj.users",
                    "tags": ["pii"],
                    "ui_tags": [],
                },
            ]
        }
        manifest_models = [
            {"unique_id": "model.proj.users", "columns": [], "tags": ["nightly"]},
        ]
        result, _ = reconcile_data_model(data_model, manifest_models)
        entity = result["entities"][0]
        assert entity["ui_tags"] == []
        assert "tags" not in entity

    def test_does_not_seed_already_dbt_reconciled_tags_into_ui_tags(self):
        """If legacy `tags` already exactly matches what the manifest says
        (i.e. it was already mirrored by the old pre-rename code, not legacy
        pre-fix data), a later reconcile must NOT seed the entire dbt tag list
        into ui_tags — that would wrongly treat dbt's own tags as
        user-added, and defeat the read-only/removable distinction in the UI.
        The legacy key is still retired either way."""
        data_model = {
            "entities": [
                {"id": "users", "dbt_model": "model.proj.users", "tags": ["sdh", "entity", "customer_360"]},
            ]
        }
        manifest_models = [
            {"unique_id": "model.proj.users", "columns": [], "tags": ["sdh", "entity", "customer_360"]},
        ]
        result, _ = reconcile_data_model(data_model, manifest_models)
        entity = result["entities"][0]
        assert "ui_tags" not in entity, (
            f"dbt-mirrored tags were wrongly seeded into ui_tags; got: {entity.get('ui_tags')}"
        )
        assert entity["dbt_tags"] == ["sdh", "entity", "customer_360"]
        assert "tags" not in entity


class TestComputeDisplayTags:
    def test_bound_entity_unions_dbt_and_ui_tags(self):
        entity = {"dbt_model": "model.proj.users", "dbt_tags": ["nightly"], "ui_tags": ["pii"]}
        assert compute_display_tags(entity) == ["nightly", "pii"]

    def test_bound_entity_dedupes_overlap(self):
        entity = {"dbt_model": "model.proj.users", "dbt_tags": ["nightly", "core"], "ui_tags": ["core", "pii"]}
        assert compute_display_tags(entity) == ["nightly", "core", "pii"]

    def test_unbound_entity_uses_plain_tags(self):
        entity = {"tags": ["draft-tag"]}
        assert compute_display_tags(entity) == ["draft-tag"]

    def test_bound_entity_with_no_tags_at_all(self):
        entity = {"dbt_model": "model.proj.users"}
        assert compute_display_tags(entity) == []


class TestReconcileIdempotency:
    def test_repeated_reconcile_produces_no_further_change(self):
        data_model = {
            "entities": [
                {"id": "users", "dbt_model": "model.proj.users", "dbt_tags": ["nightly"], "ui_tags": ["pii"]},
            ]
        }
        manifest_models = [
            {"unique_id": "model.proj.users", "columns": [], "tags": ["nightly"]},
        ]
        once, changed_once = reconcile_data_model(data_model, manifest_models)
        twice, changed_twice = reconcile_data_model(once, manifest_models)
        assert changed_twice is False
        assert twice == once
