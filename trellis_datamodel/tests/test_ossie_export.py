"""Tests for the Apache Ossie exporter (Tasks 4-6: datasets, fields, keys,
relationships) and its push integration (Task 7).

Every emitted document is validated against the vendored official
`0.2.0.dev0` schema, so a stale schema cannot silently pass everything.
"""

import json
import os
from pathlib import Path

import jsonschema
import pytest
import yaml

import trellis_datamodel.config as cfg
import trellis_datamodel.services.schema as schema_service
from trellis_datamodel.adapters.base import ColumnInfo, ModelInfo
from trellis_datamodel.adapters.bruin import BruinAdapter
from trellis_datamodel.exceptions import FileOperationError
from trellis_datamodel.models.metric import MetricEntry, MetricTreeFile
from trellis_datamodel.services.ossie import (
    DEFAULT_FILENAME,
    FIELD_DIALECT,
    OSSIE_VERSION,
    OssieExport,
    export_ossie,
)
from trellis_datamodel.tests.conftest import FakeAdapter

SCHEMA_PATH = Path(__file__).parent / "fixtures" / "ossie" / "ossie-schema.json"


@pytest.fixture(scope="module")
def validator():
    with open(SCHEMA_PATH) as f:
        schema = json.load(f)
    return jsonschema.Draft202012Validator(schema)


def validate(validator, document):
    """Raise (with every error) if the document is not schema-valid."""
    errors = sorted(validator.iter_errors(document), key=lambda e: list(e.path))
    if errors:
        messages = "\n".join(f"  - {e.message} at {list(e.path)}" for e in errors)
        raise AssertionError(f"Ossie document does not validate:\n{messages}")


def configure(monkeypatch, path, **overrides):
    """Point the exporter at `path` with optional OssieConfig overrides."""
    monkeypatch.setattr(
        cfg,
        "OSSIE_CONFIG",
        cfg.OssieConfig(file=str(path), **overrides),
    )
    return Path(path)


def column(name, type_=None, description=None):
    return ColumnInfo(name=name, type=type_, description=description)


def model(
    unique_id="model.company.dim_product",
    name="dim_product",
    schema="main",
    table=None,
    columns=None,
    description=None,
    version=None,
):
    return ModelInfo(
        unique_id=unique_id,
        name=name,
        version=version,
        schema=schema,
        table=table if table is not None else name,
        columns=columns or [],
        description=description,
        materialization="table",
        file_path=f"models/{name}.sql",
        tags=[],
    )


def read_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f)


def model_schema(*columns):
    """A ModelSchema-shaped dict, as an adapter's get_model_schema returns."""
    return {"model_name": "dim_product", "columns": list(columns)}


def bruin_column(name, primary_key=False):
    """A ColumnSchema as `_asset_to_model_schema` shapes it for Bruin."""
    entry = {"name": name, "data_type": "varchar", "description": ""}
    if primary_key:
        entry["primary_key"] = True
    return entry


def dbt_column(name, tests):
    """A ColumnSchema as `YamlHandler.get_columns` shapes it for dbt."""
    return {"name": name, "data_type": "varchar", "data_tests": list(tests)}


UNIQUE_AND_NOT_NULL = [{"unique": {}}, {"not_null": {}}]


def relationship(
    source, target, type_="many_to_one", source_field="id", target_field="id"
):
    """A relationship as `data_model.yml` stores it: source/target are entity ids."""
    return {
        "source": source,
        "target": target,
        "type": type_,
        "source_field": source_field,
        "target_field": target_field,
    }


PRODUCT_MODEL = model(
    unique_id="model.company.dim_product",
    name="dim_product",
    columns=[column("product_id", "varchar"), column("product_name", "text")],
)
SALE_MODEL = model(
    unique_id="model.company.fct_sale",
    name="fct_sale",
    columns=[column("sale_id", "varchar"), column("product_id", "varchar")],
)
PRODUCT_ENTITY = {"id": "product", "model_ref": "model.company.dim_product"}
SALE_ENTITY = {"id": "sale", "model_ref": "model.company.fct_sale"}


class TestHandBuiltDocument:
    def test_exports_bound_entity_and_skips_draft(
        self, validator, tmp_path, monkeypatch
    ):
        path = configure(monkeypatch, tmp_path / DEFAULT_FILENAME)
        entities = [
            {
                "id": "product",
                "description": "Product catalog",
                "model_ref": "model.company.dim_product",
            },
            {
                "id": "procurement",
                "description": "",
                "model_ref": None,
                "drafted_fields": [{"name": "po_number", "datatype": "text"}],
            },
        ]
        models = [
            model(
                columns=[
                    column("product_id", "varchar", "unique product ID"),
                    column("product_name", "text"),
                ]
            )
        ]

        result = export_ossie(entities, [], "company", models)

        assert isinstance(result, OssieExport)
        assert result.path == path
        assert path.exists()

        document = read_yaml(path)
        validate(validator, document)

        assert list(document) == [
            "version",
            "name",
            "datasets",
            "relationships",
            "metrics",
        ]
        assert document["version"] == OSSIE_VERSION == "0.2.0.dev0"
        assert document["name"] == "company"
        assert document["relationships"] == []
        assert document["metrics"] == []

        assert len(document["datasets"]) == 1
        dataset = document["datasets"][0]
        assert dataset["name"] == "dim_product"
        assert dataset["description"] == "Product catalog"
        assert "metrics" not in dataset

        assert any(
            'entity "procurement"' in warning and "not bound" in warning
            for warning in result.warnings
        )
        assert all(
            dataset["name"] != "procurement" for dataset in document["datasets"]
        )

    def test_empty_project_name_falls_back_to_data_model_stem(
        self, monkeypatch, tmp_path
    ):
        path = configure(monkeypatch, tmp_path / DEFAULT_FILENAME)
        data_model = tmp_path / "my_model.yml"
        data_model.write_text("version: 0.1\nentities: []\n")
        monkeypatch.setattr(cfg, "DATA_MODEL_PATH", str(data_model))

        result = export_ossie(
            [{"id": "product", "model_ref": "model.company.dim_product"}],
            [],
            "",
            [model()],
        )

        assert read_yaml(path)["name"] == "my_model"
        assert result.path == path


class TestFieldMapping:
    def test_maps_sql_types_and_marks_time(
        self, validator, tmp_path, monkeypatch
    ):
        path = configure(monkeypatch, tmp_path / DEFAULT_FILENAME)
        entities = [{"id": "product", "model_ref": "model.company.dim_product"}]
        models = [
            model(
                columns=[
                    column("product_id", "varchar"),
                    column("price", "numeric"),
                    column("created_at", "timestamp"),
                    column("location", "geography"),
                ]
            )
        ]

        export_ossie(entities, [], "company", models)

        document = read_yaml(path)
        validate(validator, document)
        fields = {f["name"]: f for f in document["datasets"][0]["fields"]}

        assert fields["product_id"]["datatype"] == "String"
        assert fields["product_id"]["dimension"]["is_time"] is False
        assert fields["price"]["datatype"] == "Decimal"
        assert fields["created_at"]["datatype"] == "DateTime"
        assert fields["created_at"]["dimension"]["is_time"] is True
        assert "datatype" not in fields["location"]
        assert fields["location"]["dimension"]["is_time"] is False

        for field in fields.values():
            assert field["expression"] == {
                "dialects": [
                    {"dialect": FIELD_DIALECT, "expression": field["name"]}
                ]
            }

    def test_omits_empty_field_description(self, validator, tmp_path, monkeypatch):
        path = configure(monkeypatch, tmp_path / DEFAULT_FILENAME)
        export_ossie(
            [{"id": "product", "model_ref": "model.company.dim_product"}],
            [],
            "company",
            [model(columns=[column("product_id", "varchar", "")])],
        )

        field = read_yaml(path)["datasets"][0]["fields"][0]
        assert "description" not in field


class TestDraftedFieldMerging:
    def test_model_column_wins_and_remaining_drafts_sort_by_name(
        self, validator, tmp_path, monkeypatch
    ):
        path = configure(monkeypatch, tmp_path / DEFAULT_FILENAME)
        entities = [
            {
                "id": "product",
                "model_ref": "model.company.dim_product",
                "drafted_fields": [
                    {
                        "name": "product_id",
                        "datatype": "int",
                        "description": "must lose to the model column",
                    },
                    {
                        "name": "reorder_point",
                        "datatype": "int",
                        "physical_datatype": "numeric(38,0)",
                        "description": "Reorder threshold",
                    },
                    {"name": "active", "datatype": "bool"},
                    {"name": "   ", "datatype": "text"},
                    {"datatype": "text"},
                    {"name": "mystery", "datatype": "unknown"},
                ],
            }
        ]
        models = [model(columns=[column("product_id", "varchar", "model wins")])]

        export_ossie(entities, [], "company", models)

        document = read_yaml(path)
        validate(validator, document)
        fields = document["datasets"][0]["fields"]

        assert [f["name"] for f in fields] == [
            "product_id",
            "active",
            "mystery",
            "reorder_point",
        ]
        by_name = {f["name"]: f for f in fields}
        assert by_name["product_id"]["datatype"] == "String"
        assert by_name["product_id"]["description"] == "model wins"
        assert by_name["active"]["datatype"] == "Boolean"
        assert by_name["reorder_point"]["datatype"] == "Decimal"
        assert by_name["reorder_point"]["description"] == "Reorder threshold"
        assert "datatype" not in by_name["mystery"]


class TestKeyInference:
    def test_bruin_primary_key_column_becomes_the_primary_key(
        self, validator, tmp_path, monkeypatch
    ):
        path = configure(monkeypatch, tmp_path / DEFAULT_FILENAME)
        entities = [
            {
                "id": "product",
                "description": "Product catalog",
                "model_ref": "model.company.dim_product",
            }
        ]
        models = [
            model(
                columns=[
                    column("product_id", "varchar"),
                    column("product_name", "text"),
                ]
            )
        ]
        schemas = {
            "model.company.dim_product": model_schema(
                bruin_column("product_id", primary_key=True),
                bruin_column("product_name"),
            )
        }

        export_ossie(entities, [], "company", models, schemas)

        document = read_yaml(path)
        validate(validator, document)
        dataset = document["datasets"][0]

        assert dataset["primary_key"] == ["product_id"]
        assert "unique_keys" not in dataset
        # Key sits after source/description and before fields.
        assert list(dataset) == [
            "name",
            "source",
            "description",
            "primary_key",
            "fields",
        ]

    def test_two_candidates_become_independent_unique_keys(
        self, validator, tmp_path, monkeypatch
    ):
        path = configure(monkeypatch, tmp_path / DEFAULT_FILENAME)
        entities = [{"id": "product", "model_ref": "model.company.dim_product"}]
        models = [
            model(
                columns=[
                    column("product_id", "varchar"),
                    column("sku", "varchar"),
                ]
            )
        ]
        schemas = {
            "model.company.dim_product": model_schema(
                dbt_column("product_id", UNIQUE_AND_NOT_NULL),
                dbt_column("sku", UNIQUE_AND_NOT_NULL),
            )
        }

        export_ossie(entities, [], "company", models, schemas)

        document = read_yaml(path)
        validate(validator, document)
        dataset = document["datasets"][0]

        assert dataset["unique_keys"] == [["product_id"], ["sku"]]
        assert "primary_key" not in dataset

    def test_unique_test_alone_is_not_a_candidate(
        self, validator, tmp_path, monkeypatch
    ):
        path = configure(monkeypatch, tmp_path / DEFAULT_FILENAME)
        entities = [{"id": "product", "model_ref": "model.company.dim_product"}]
        models = [
            model(
                columns=[
                    column("product_id", "varchar"),
                    column("sku", "varchar"),
                ]
            )
        ]
        schemas = {
            "model.company.dim_product": model_schema(
                dbt_column("product_id", [{"unique": {}}]),
                bruin_column("sku"),
            )
        }

        export_ossie(entities, [], "company", models, schemas)

        document = read_yaml(path)
        validate(validator, document)
        dataset = document["datasets"][0]

        assert "primary_key" not in dataset
        assert "unique_keys" not in dataset

    def test_bare_string_test_entries_count_as_key_candidates(
        self, validator, tmp_path, monkeypatch
    ):
        path = configure(monkeypatch, tmp_path / DEFAULT_FILENAME)
        entities = [{"id": "product", "model_ref": "model.company.dim_product"}]
        models = [model(columns=[column("product_id", "varchar")])]
        schemas = {
            "model.company.dim_product": model_schema(
                dbt_column("product_id", ["unique", "not_null"]),
            )
        }

        export_ossie(entities, [], "company", models, schemas)

        document = read_yaml(path)
        validate(validator, document)
        assert document["datasets"][0]["primary_key"] == ["product_id"]

    def test_relationship_reference_side_is_the_fallback_key(
        self, validator, tmp_path, monkeypatch
    ):
        path = configure(monkeypatch, tmp_path / DEFAULT_FILENAME)
        entities = [
            {"id": "customer", "model_ref": "model.company.dim_customer"},
            {"id": "sale", "model_ref": "model.company.fct_sale"},
        ]
        models = [
            model(
                unique_id="model.company.dim_customer",
                name="dim_customer",
                columns=[column("customer_id", "varchar")],
            ),
            model(
                unique_id="model.company.fct_sale",
                name="fct_sale",
                columns=[column("customer_id", "varchar")],
            ),
        ]
        relationships = [
            {
                "source": "sale",
                "target": "customer",
                "type": "many_to_one",
                "source_field": "customer_id",
                "target_field": "customer_id",
            }
        ]

        export_ossie(entities, relationships, "company", models)

        document = read_yaml(path)
        validate(validator, document)
        datasets = {d["name"]: d for d in document["datasets"]}

        assert datasets["dim_customer"]["primary_key"] == ["customer_id"]
        assert "primary_key" not in datasets["fct_sale"]
        assert "unique_keys" not in datasets["fct_sale"]

    def test_metadata_wins_over_the_relationship_fallback(
        self, validator, tmp_path, monkeypatch
    ):
        path = configure(monkeypatch, tmp_path / DEFAULT_FILENAME)
        entities = [
            {"id": "customer", "model_ref": "model.company.dim_customer"},
            {"id": "sale", "model_ref": "model.company.fct_sale"},
        ]
        models = [
            model(
                unique_id="model.company.dim_customer",
                name="dim_customer",
                columns=[
                    column("customer_key", "varchar"),
                    column("customer_id", "varchar"),
                ],
            ),
            model(
                unique_id="model.company.fct_sale",
                name="fct_sale",
                columns=[column("customer_id", "varchar")],
            ),
        ]
        relationships = [
            {
                "source": "sale",
                "target": "customer",
                "type": "many_to_one",
                "source_field": "customer_id",
                "target_field": "customer_id",
            }
        ]
        schemas = {
            "model.company.dim_customer": model_schema(
                bruin_column("customer_key", primary_key=True),
                bruin_column("customer_id"),
            )
        }

        export_ossie(entities, relationships, "company", models, schemas)

        document = read_yaml(path)
        validate(validator, document)
        datasets = {d["name"]: d for d in document["datasets"]}

        assert datasets["dim_customer"]["primary_key"] == ["customer_key"]

    def test_two_inbound_relationships_yield_one_primary_key(
        self, validator, tmp_path, monkeypatch
    ):
        """Two inbound relationships are two claims, not two unique keys."""
        path = configure(monkeypatch, tmp_path / DEFAULT_FILENAME)
        entities = [
            {"id": "customer", "model_ref": "model.company.dim_customer"},
            {"id": "sale", "model_ref": "model.company.fct_sale"},
            {"id": "shipment", "model_ref": "model.company.fct_shipment"},
        ]
        models = [
            model(
                unique_id="model.company.dim_customer",
                name="dim_customer",
                columns=[
                    column("customer_id", "varchar"),
                    column("legacy_customer_id", "varchar"),
                ],
            ),
            model(
                unique_id="model.company.fct_sale",
                name="fct_sale",
                columns=[column("legacy_customer_id", "varchar")],
            ),
            model(
                unique_id="model.company.fct_shipment",
                name="fct_shipment",
                columns=[column("customer_id", "varchar")],
            ),
        ]
        # Input order puts the shipment first; the sorted `from` puts fct_sale
        # first, so that relationship is the deterministic single candidate.
        relationships = [
            relationship(
                "shipment", "customer", "many_to_one", "customer_id", "customer_id"
            ),
            relationship(
                "sale",
                "customer",
                "many_to_one",
                "legacy_customer_id",
                "legacy_customer_id",
            ),
        ]

        export_ossie(entities, relationships, "company", models)

        document = read_yaml(path)
        validate(validator, document)
        dataset = next(d for d in document["datasets"] if d["name"] == "dim_customer")

        assert len(document["relationships"]) == 2
        assert dataset["primary_key"] == ["legacy_customer_id"]
        assert "unique_keys" not in dataset

    def test_skipped_relationship_contributes_no_key(
        self, validator, tmp_path, monkeypatch
    ):
        """A relationship the exporter drops is not evidence of uniqueness."""
        path = configure(monkeypatch, tmp_path / DEFAULT_FILENAME)
        entities = [
            {"id": "customer", "model_ref": "model.company.dim_customer"},
            {"id": "sale", "model_ref": "model.company.fct_sale"},
        ]
        models = [
            model(
                unique_id="model.company.dim_customer",
                name="dim_customer",
                columns=[column("customer_id", "varchar")],
            ),
            model(
                unique_id="model.company.fct_sale",
                name="fct_sale",
                columns=[column("customer_id", "varchar")],
            ),
        ]
        relationships = [
            relationship(
                "sale", "customer", "many_to_one", "customer_id", "missing_id"
            )
        ]

        export_ossie(entities, relationships, "company", models)

        document = read_yaml(path)
        validate(validator, document)
        dataset = next(d for d in document["datasets"] if d["name"] == "dim_customer")

        assert document["relationships"] == []
        assert "primary_key" not in dataset
        assert "unique_keys" not in dataset

    @pytest.mark.parametrize("rel_type", ["many_to_many", "zero_or_many_to_many"])
    def test_many_to_many_contributes_no_key(
        self, validator, tmp_path, monkeypatch, rel_type
    ):
        """Both sides many: neither endpoint's field identifies a row."""
        path = configure(monkeypatch, tmp_path / DEFAULT_FILENAME)
        entities = [
            {"id": "customer", "model_ref": "model.company.dim_customer"},
            {"id": "sale", "model_ref": "model.company.fct_sale"},
        ]
        models = [
            model(
                unique_id="model.company.dim_customer",
                name="dim_customer",
                columns=[column("customer_id", "varchar")],
            ),
            model(
                unique_id="model.company.fct_sale",
                name="fct_sale",
                columns=[column("customer_id", "varchar")],
            ),
        ]
        relationships = [
            relationship("sale", "customer", rel_type, "customer_id", "customer_id")
        ]

        export_ossie(entities, relationships, "company", models)

        document = read_yaml(path)
        validate(validator, document)

        # The relationship itself still survives; only the key claim is withheld.
        assert len(document["relationships"]) == 1
        for dataset in document["datasets"]:
            assert "primary_key" not in dataset
            assert "unique_keys" not in dataset

    def test_absent_metadata_candidate_falls_through_to_relationship_evidence(
        self, validator, tmp_path, monkeypatch
    ):
        path = configure(monkeypatch, tmp_path / DEFAULT_FILENAME)
        entities = [
            {"id": "customer", "model_ref": "model.company.dim_customer"},
            {"id": "sale", "model_ref": "model.company.fct_sale"},
        ]
        models = [
            model(
                unique_id="model.company.dim_customer",
                name="dim_customer",
                columns=[column("customer_id", "varchar")],
            ),
            model(
                unique_id="model.company.fct_sale",
                name="fct_sale",
                columns=[column("customer_id", "varchar")],
            ),
        ]
        # The metadata flags a column the dataset does not declare, so it cannot
        # be a key; the surviving relationship still can.
        schemas = {
            "model.company.dim_customer": model_schema(
                bruin_column("legacy_id", primary_key=True),
            )
        }
        relationships = [
            relationship(
                "sale", "customer", "many_to_one", "customer_id", "customer_id"
            )
        ]

        export_ossie(entities, relationships, "company", models, schemas)

        document = read_yaml(path)
        validate(validator, document)
        dataset = next(d for d in document["datasets"] if d["name"] == "dim_customer")

        assert dataset["primary_key"] == ["customer_id"]
        assert "unique_keys" not in dataset

    def test_candidate_absent_from_fields_is_dropped(
        self, validator, tmp_path, monkeypatch
    ):
        path = configure(monkeypatch, tmp_path / DEFAULT_FILENAME)
        entities = [{"id": "product", "model_ref": "model.company.dim_product"}]
        models = [model(columns=[column("product_id", "varchar")])]
        schemas = {
            "model.company.dim_product": model_schema(
                bruin_column("product_id", primary_key=True),
                bruin_column("legacy_id", primary_key=True),
            )
        }

        export_ossie(entities, [], "company", models, schemas)

        document = read_yaml(path)
        validate(validator, document)
        dataset = document["datasets"][0]

        # One member of the flagged composite is not a declared field, so the
        # composite is incomplete and neither column identifies a row alone.
        assert "primary_key" not in dataset
        assert "unique_keys" not in dataset

    def test_only_absent_candidates_leave_both_keys_off(
        self, validator, tmp_path, monkeypatch
    ):
        path = configure(monkeypatch, tmp_path / DEFAULT_FILENAME)
        entities = [{"id": "product", "model_ref": "model.company.dim_product"}]
        models = [model(columns=[column("product_id", "varchar")])]
        schemas = {
            "model.company.dim_product": model_schema(
                bruin_column("legacy_id", primary_key=True),
            )
        }

        export_ossie(entities, [], "company", models, schemas)

        document = read_yaml(path)
        validate(validator, document)
        dataset = document["datasets"][0]

        assert "primary_key" not in dataset
        assert "unique_keys" not in dataset

    def test_nothing_available_omits_both_keys(self, validator, tmp_path, monkeypatch):
        path = configure(monkeypatch, tmp_path / DEFAULT_FILENAME)
        entities = [{"id": "product", "model_ref": "model.company.dim_product"}]
        models = [model(columns=[column("product_id", "varchar")])]

        export_ossie(entities, [], "company", models)

        document = read_yaml(path)
        validate(validator, document)
        dataset = document["datasets"][0]

        assert "primary_key" not in dataset
        assert "unique_keys" not in dataset

    def test_both_key_shapes_validate(self, validator, tmp_path, monkeypatch):
        """Single metadata candidate vs Bruin's composite flag, both validated."""
        entities = [{"id": "product", "model_ref": "model.company.dim_product"}]
        models = [
            model(
                columns=[
                    column("product_id", "varchar"),
                    column("sku", "varchar"),
                ]
            )
        ]

        single = configure(monkeypatch, tmp_path / "single.yml")
        export_ossie(
            entities,
            [],
            "company",
            models,
            {
                "model.company.dim_product": model_schema(
                    bruin_column("product_id", primary_key=True),
                    bruin_column("sku"),
                )
            },
        )
        document = read_yaml(single)
        validate(validator, document)
        assert document["datasets"][0]["primary_key"] == ["product_id"]
        assert "unique_keys" not in document["datasets"][0]

        # Bruin flags every column of a composite key, so two flags are one
        # multi-element primary key, never two independent unique keys.
        multiple = configure(monkeypatch, tmp_path / "multiple.yml")
        export_ossie(
            entities,
            [],
            "company",
            models,
            {
                "model.company.dim_product": model_schema(
                    bruin_column("product_id", primary_key=True),
                    bruin_column("sku", primary_key=True),
                )
            },
        )
        document = read_yaml(multiple)
        validate(validator, document)
        dataset = document["datasets"][0]
        assert dataset["primary_key"] == ["product_id", "sku"]
        assert "unique_keys" not in dataset


class TestDatasetNaming:
    def test_duplicate_dataset_name_exports_first_and_warns(
        self, validator, tmp_path, monkeypatch
    ):
        """Two entities on one model would make the dataset reference ambiguous."""
        path = configure(monkeypatch, tmp_path / DEFAULT_FILENAME)
        entities = [
            {"id": "a", "model_ref": "model.company.dim_customer"},
            {"id": "b", "model_ref": "model.company.dim_customer"},
        ]
        models = [
            model(
                unique_id="model.company.dim_customer",
                name="dim_customer",
                columns=[column("customer_id", "varchar")],
            )
        ]

        result = export_ossie(entities, [], "company", models)

        document = read_yaml(path)
        validate(validator, document)
        assert [d["name"] for d in document["datasets"]] == ["dim_customer"]
        assert result.warnings == [
            'entities "a" and "b" both map to dataset "dim_customer"; only "a" '
            "was exported (a dataset name must be unique)"
        ]

    def test_relationship_to_a_duplicate_dataset_blames_the_duplicate(
        self, tmp_path, monkeypatch
    ):
        """The adapter did report the model, so the warning must not say it didn't."""
        configure(monkeypatch, tmp_path / DEFAULT_FILENAME)
        entities = [
            {"id": "a", "model_ref": "model.company.dim_customer"},
            {"id": "b", "model_ref": "model.company.dim_customer"},
        ]
        relationships = [
            {
                "source": "a",
                "target": "b",
                "type": "one_to_many",
                "source_field": "customer_id",
                "target_field": "customer_id",
            }
        ]
        models = [
            model(
                unique_id="model.company.dim_customer",
                name="dim_customer",
                columns=[column("customer_id", "varchar")],
            )
        ]

        result = export_ossie(entities, relationships, "company", models)

        skipped = [w for w in result.warnings if "skipped" in w]
        assert len(skipped) == 1
        assert 'target entity "b" maps to dataset "dim_customer"' in skipped[0]
        assert "does not report" not in skipped[0]

    def test_versioned_model_names_the_dataset_with_the_version(
        self, validator, tmp_path, monkeypatch
    ):
        path = configure(monkeypatch, tmp_path / DEFAULT_FILENAME)
        entities = [
            {"id": "player_v1", "model_ref": "model.company.player.v1"},
            {"id": "player_v2", "model_ref": "model.company.player.v2"},
        ]
        models = [
            model(
                unique_id="model.company.player.v1",
                name="player",
                version=1,
                table="player_v1",
                columns=[column("player_id", "varchar")],
            ),
            model(
                unique_id="model.company.player.v2",
                name="player",
                version=2,
                table="player_v2",
                columns=[column("player_id", "varchar")],
            ),
        ]

        export_ossie(entities, [], "company", models)

        document = read_yaml(path)
        validate(validator, document)
        datasets = {d["name"]: d for d in document["datasets"]}

        assert list(datasets) == ["player_v1", "player_v2"]
        assert datasets["player_v1"]["source"] == "main.player_v1"
        assert datasets["player_v2"]["source"] == "main.player_v2"


class TestRelationships:
    def _export(
        self,
        tmp_path,
        monkeypatch,
        relationships,
        entities=None,
        models=None,
        filename=DEFAULT_FILENAME,
    ):
        path = configure(monkeypatch, tmp_path / filename)
        result = export_ossie(
            [PRODUCT_ENTITY, SALE_ENTITY] if entities is None else entities,
            relationships,
            "company",
            [PRODUCT_MODEL, SALE_MODEL] if models is None else models,
        )
        return path, result

    def test_one_to_many_puts_from_on_the_many_side(
        self, validator, tmp_path, monkeypatch
    ):
        """The canvas stores `product -> sale`; the sale side holds the FK."""
        path, _ = self._export(
            tmp_path,
            monkeypatch,
            [
                relationship(
                    "product", "sale", "one_to_many", "product_id", "product_id"
                )
            ],
        )

        document = read_yaml(path)
        validate(validator, document)

        assert document["relationships"] == [
            {
                "name": "fct_sale_to_dim_product",
                "from": "fct_sale",
                "to": "dim_product",
                "from_columns": ["product_id"],
                "to_columns": ["product_id"],
            }
        ]
        assert list(document["relationships"][0]) == [
            "name",
            "from",
            "to",
            "from_columns",
            "to_columns",
        ]

    def test_many_to_one_keeps_from_on_the_source(
        self, validator, tmp_path, monkeypatch
    ):
        """The FK sits on the source, so `from` is the source dataset."""
        path, _ = self._export(
            tmp_path,
            monkeypatch,
            [
                relationship(
                    "sale", "product", "many_to_one", "product_id", "product_id"
                )
            ],
        )

        document = read_yaml(path)
        validate(validator, document)

        entry = document["relationships"][0]
        assert entry["name"] == "fct_sale_to_dim_product"
        assert entry["from"] == "fct_sale"
        assert entry["to"] == "dim_product"

    def test_one_to_one_puts_from_on_the_source(
        self, validator, tmp_path, monkeypatch
    ):
        """`one_to_one` places the FK on the source, matching place_foreign_key."""
        path, _ = self._export(
            tmp_path,
            monkeypatch,
            [relationship("sale", "product", "one_to_one", "product_id", "product_id")],
        )

        document = read_yaml(path)
        validate(validator, document)

        entry = document["relationships"][0]
        assert entry["from"] == "fct_sale"
        assert entry["to"] == "dim_product"

    def test_draft_endpoint_is_skipped_with_a_warning(
        self, validator, tmp_path, monkeypatch
    ):
        path, result = self._export(
            tmp_path,
            monkeypatch,
            [
                relationship(
                    "sale", "product", "many_to_one", "product_id", "product_id"
                )
            ],
            entities=[{"id": "product", "model_ref": None}, SALE_ENTITY],
        )

        document = read_yaml(path)
        validate(validator, document)
        assert document["relationships"] == []

        warning = next(
            w for w in result.warnings if "relationship" in w and '"product"' in w
        )
        assert '"sale"' in warning
        assert "draft" in warning

    def test_unresolvable_endpoint_is_skipped_with_a_warning(
        self, validator, tmp_path, monkeypatch
    ):
        path, result = self._export(
            tmp_path,
            monkeypatch,
            [relationship("sale", "ghost", "many_to_one", "product_id", "product_id")],
            entities=[
                PRODUCT_ENTITY,
                SALE_ENTITY,
                {"id": "ghost", "model_ref": "model.company.ghost"},
            ],
        )

        document = read_yaml(path)
        validate(validator, document)
        assert document["relationships"] == []

        warning = next(
            w for w in result.warnings if "relationship" in w and '"ghost"' in w
        )
        assert "model.company.ghost" in warning
        assert "does not report" in warning

    def test_empty_source_field_is_skipped_with_a_warning(
        self, validator, tmp_path, monkeypatch
    ):
        path, result = self._export(
            tmp_path,
            monkeypatch,
            [relationship("sale", "product", "many_to_one", "", "product_id")],
        )

        document = read_yaml(path)
        validate(validator, document)
        assert document["relationships"] == []

        warning = next(w for w in result.warnings if '"sale"' in w and '"product"' in w)
        assert "source_field" in warning

    def test_empty_target_field_is_skipped_with_a_warning(
        self, validator, tmp_path, monkeypatch
    ):
        path, result = self._export(
            tmp_path,
            monkeypatch,
            [relationship("sale", "product", "many_to_one", "product_id", "")],
        )

        document = read_yaml(path)
        validate(validator, document)
        assert document["relationships"] == []

        warning = next(w for w in result.warnings if '"sale"' in w and '"product"' in w)
        assert "target_field" in warning

    def test_empty_field_warning_uses_the_plural_verb_for_two_fields(
        self, validator, tmp_path, monkeypatch
    ):
        path, result = self._export(
            tmp_path,
            monkeypatch,
            [relationship("sale", "product", "many_to_one", "", "")],
        )

        document = read_yaml(path)
        validate(validator, document)
        assert document["relationships"] == []
        assert result.warnings == [
            'relationship "sale" -> "product" (many_to_one) skipped: '
            "source_field and target_field are empty"
        ]

    def test_duplicate_skipped_relationship_warns_once(
        self, validator, tmp_path, monkeypatch
    ):
        duplicate = relationship("sale", "product", "many_to_one", "", "product_id")
        path, result = self._export(tmp_path, monkeypatch, [duplicate, dict(duplicate)])

        document = read_yaml(path)
        validate(validator, document)
        assert document["relationships"] == []
        assert result.warnings == [
            'relationship "sale" -> "product" (many_to_one) skipped: '
            "source_field is empty"
        ]

    def test_referenced_field_absent_from_the_dataset_is_skipped(
        self, validator, tmp_path, monkeypatch
    ):
        path, result = self._export(
            tmp_path,
            monkeypatch,
            [
                relationship(
                    "sale", "product", "many_to_one", "product_id", "missing_id"
                )
            ],
        )

        document = read_yaml(path)
        validate(validator, document)
        assert document["relationships"] == []

        warning = next(w for w in result.warnings if "missing_id" in w)
        assert "dim_product" in warning
        assert '"sale"' in warning

    def test_fk_field_absent_from_the_dataset_is_skipped(
        self, validator, tmp_path, monkeypatch
    ):
        path, result = self._export(
            tmp_path,
            monkeypatch,
            [relationship("sale", "product", "many_to_one", "legacy_id", "product_id")],
        )

        document = read_yaml(path)
        validate(validator, document)
        assert document["relationships"] == []

        warning = next(w for w in result.warnings if "legacy_id" in w)
        assert "fct_sale" in warning

    def test_duplicate_tuples_collapse_to_one_entry(
        self, validator, tmp_path, monkeypatch
    ):
        duplicate = relationship(
            "sale", "product", "many_to_one", "product_id", "product_id"
        )
        path, _ = self._export(tmp_path, monkeypatch, [duplicate, dict(duplicate)])

        document = read_yaml(path)
        validate(validator, document)
        assert len(document["relationships"]) == 1

    def test_same_dataset_pair_gets_distinct_names(
        self, validator, tmp_path, monkeypatch
    ):
        customer = model(
            unique_id="model.company.dim_customer",
            name="dim_customer",
            columns=[
                column("customer_id", "varchar"),
                column("shipping_customer_id", "varchar"),
            ],
        )
        sale = model(
            unique_id="model.company.fct_sale",
            name="fct_sale",
            columns=[
                column("customer_id", "varchar"),
                column("shipping_customer_id", "varchar"),
            ],
        )
        relationships = [
            relationship(
                "sale",
                "customer",
                "many_to_one",
                "shipping_customer_id",
                "shipping_customer_id",
            ),
            relationship(
                "sale", "customer", "many_to_one", "customer_id", "customer_id"
            ),
        ]

        path, _ = self._export(
            tmp_path,
            monkeypatch,
            relationships,
            entities=[
                {"id": "customer", "model_ref": "model.company.dim_customer"},
                SALE_ENTITY,
            ],
            models=[customer, sale],
        )

        document = read_yaml(path)
        validate(validator, document)

        assert [entry["name"] for entry in document["relationships"]] == [
            "fct_sale_to_dim_customer",
            "fct_sale_to_dim_customer_shipping_customer_id",
        ]
        assert [entry["from_columns"] for entry in document["relationships"]] == [
            ["customer_id"],
            ["shipping_customer_id"],
        ]

    def test_surviving_collision_gets_a_numeric_suffix(
        self, validator, tmp_path, monkeypatch
    ):
        customer = model(
            unique_id="model.company.dim_customer",
            name="dim_customer",
            columns=[
                column("customer_id", "varchar"),
                column("legacy_customer_id", "varchar"),
                column("old_customer_id", "varchar"),
            ],
        )
        sale = model(
            unique_id="model.company.fct_sale",
            name="fct_sale",
            columns=[column("customer_id", "varchar")],
        )
        # Same dataset pair and same foreign-key column, three referenced columns.
        relationships = [
            relationship(
                "sale", "customer", "many_to_one", "customer_id", "old_customer_id"
            ),
            relationship(
                "sale", "customer", "many_to_one", "customer_id", "customer_id"
            ),
            relationship(
                "sale", "customer", "many_to_one", "customer_id", "legacy_customer_id"
            ),
        ]

        path, _ = self._export(
            tmp_path,
            monkeypatch,
            relationships,
            entities=[
                {"id": "customer", "model_ref": "model.company.dim_customer"},
                SALE_ENTITY,
            ],
            models=[customer, sale],
        )

        document = read_yaml(path)
        validate(validator, document)

        assert [entry["name"] for entry in document["relationships"]] == [
            "fct_sale_to_dim_customer",
            "fct_sale_to_dim_customer_customer_id",
            "fct_sale_to_dim_customer_customer_id_2",
        ]

    def test_order_is_stable_and_document_validates(
        self, validator, tmp_path, monkeypatch
    ):
        customer = model(
            unique_id="model.company.dim_customer",
            name="dim_customer",
            columns=[column("customer_id", "varchar")],
        )
        sale = model(
            unique_id="model.company.fct_sale",
            name="fct_sale",
            columns=[
                column("customer_id", "varchar"),
                column("product_id", "varchar"),
            ],
        )
        relationships = [
            relationship("sale", "product", "many_to_one", "product_id", "product_id"),
            relationship(
                "sale", "customer", "many_to_one", "customer_id", "customer_id"
            ),
        ]

        first, _ = self._export(
            tmp_path,
            monkeypatch,
            relationships,
            entities=[
                PRODUCT_ENTITY,
                SALE_ENTITY,
                {"id": "customer", "model_ref": "model.company.dim_customer"},
            ],
            models=[PRODUCT_MODEL, sale, customer],
            filename="first.yml",
        )
        second, _ = self._export(
            tmp_path,
            monkeypatch,
            relationships,
            entities=[
                PRODUCT_ENTITY,
                SALE_ENTITY,
                {"id": "customer", "model_ref": "model.company.dim_customer"},
            ],
            models=[PRODUCT_MODEL, sale, customer],
            filename="second.yml",
        )

        document = read_yaml(first)
        validate(validator, document)
        assert [entry["name"] for entry in document["relationships"]] == [
            "fct_sale_to_dim_customer",
            "fct_sale_to_dim_product",
        ]
        assert first.read_bytes() == second.read_bytes()

    def test_bruin_foreign_key_blocks_orient_from_the_referencing_asset(
        self, validator, tmp_path, monkeypatch, bruin_pipeline
    ):
        path = configure(monkeypatch, tmp_path / DEFAULT_FILENAME)
        adapter = BruinAdapter(
            pipeline_path=bruin_pipeline,
            data_model_path="",
            asset_paths=[],
        )
        models = adapter.get_models()
        # Unbound inference keeps asset short names, which become entity ids.
        relationships = adapter.infer_relationships(include_unbound=True)
        by_name = {m["name"]: m for m in models}
        entity_ids = sorted(
            {r["source"] for r in relationships}
            | {r["target"] for r in relationships}
        )
        entities = [
            {"id": entity_id, "model_ref": by_name[entity_id]["unique_id"]}
            for entity_id in entity_ids
        ]

        result = export_ossie(entities, relationships, "trellis_test_pipeline", models)

        assert result.path == path
        document = read_yaml(path)
        validate(validator, document)

        by_pair = {(e["from"], e["to"]): e for e in document["relationships"]}
        entry = by_pair[("fct__order", "dim__customer")]
        assert entry["from"] == "fct__order"
        assert entry["to"] == "dim__customer"
        assert entry["from_columns"] == ["customer_id"]
        assert entry["to_columns"] == ["customer_id"]


class TestSourceQualification:
    def _source(self, tmp_path, monkeypatch, **overrides):
        path = configure(monkeypatch, tmp_path / DEFAULT_FILENAME, **overrides)
        export_ossie(
            [{"id": "product", "model_ref": "model.company.dim_product"}],
            [],
            "company",
            [model()],
        )
        return read_yaml(path)["datasets"][0]["source"]

    def test_default_omits_database(self, tmp_path, monkeypatch):
        assert self._source(tmp_path, monkeypatch) == "main.dim_product"

    def test_configured_database_prepends(self, tmp_path, monkeypatch):
        assert (
            self._source(tmp_path, monkeypatch, database="ANALYTICS")
            == "ANALYTICS.main.dim_product"
        )

    def test_configured_schema_overrides_model_schema(self, tmp_path, monkeypatch):
        assert (
            self._source(tmp_path, monkeypatch, schema="MARTS")
            == "MARTS.dim_product"
        )

    def test_model_table_falls_back_to_name(self, tmp_path, monkeypatch):
        path = configure(monkeypatch, tmp_path / DEFAULT_FILENAME)
        export_ossie(
            [{"id": "product", "model_ref": "model.company.dim_product"}],
            [],
            "company",
            [model(table="")],
        )
        assert read_yaml(path)["datasets"][0]["source"] == "main.dim_product"


class TestOutputPathFallback:
    def test_unconfigured_path_is_absolute_in_the_working_directory(
        self, validator, tmp_path, monkeypatch
    ):
        """A bare filename would hand `save_file` an empty parent directory."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(cfg, "OSSIE_CONFIG", cfg.OssieConfig(file=""))
        monkeypatch.setattr(cfg, "DATA_MODEL_PATH", "")
        expected = tmp_path / DEFAULT_FILENAME

        result = export_ossie(
            [{"id": "product", "model_ref": "model.company.dim_product"}],
            [],
            "company",
            [model()],
        )

        assert expected.is_absolute()
        assert result.path is not None
        assert result.path.is_absolute()
        assert result.path.parent == Path.cwd()
        assert result.path.name == DEFAULT_FILENAME
        assert expected.exists()
        validate(validator, read_yaml(expected))


class TestUnresolvableModelRef:
    def test_skips_and_warns_naming_the_ref(
        self, validator, tmp_path, monkeypatch
    ):
        path = configure(monkeypatch, tmp_path / DEFAULT_FILENAME)
        entities = [
            {"id": "product", "model_ref": "model.company.dim_product"},
            {"id": "ghost", "model_ref": "model.company.ghost"},
        ]

        result = export_ossie(entities, [], "company", [model()])

        document = read_yaml(path)
        validate(validator, document)
        assert [d["name"] for d in document["datasets"]] == ["dim_product"]

        warning = next(w for w in result.warnings if "model.company.ghost" in w)
        assert 'entity "ghost"' in warning
        assert "dbt_model_paths" in warning
        assert "bruin_asset_paths" in warning


class TestZeroDatasets:
    def test_writes_no_file_and_returns_no_path(self, tmp_path, monkeypatch):
        path = configure(monkeypatch, tmp_path / DEFAULT_FILENAME)

        result = export_ossie(
            [{"id": "procurement", "model_ref": None}],
            [],
            "company",
            [],
        )

        assert result.path is None
        assert not path.exists()
        assert any("nothing was written" in w for w in result.warnings)


class TestDeterminism:
    def test_two_runs_are_byte_identical(self, tmp_path, monkeypatch):
        entities = [
            {
                "id": "product",
                "model_ref": "model.company.dim_product",
                "drafted_fields": [{"name": "b_field", "datatype": "text"}],
            }
        ]
        models = [
            model(
                columns=[
                    column("product_id", "varchar"),
                    column("created_at", "timestamp"),
                ]
            )
        ]

        first = configure(monkeypatch, tmp_path / "first.yml")
        export_ossie(entities, [], "company", models)

        second = configure(monkeypatch, tmp_path / "second.yml")
        export_ossie(entities, [], "company", models)

        assert first.read_bytes() == second.read_bytes()


class TestAtomicity:
    def test_dump_failure_leaves_no_partial_file(self, tmp_path, monkeypatch):
        import ruamel.yaml

        path = configure(monkeypatch, tmp_path / DEFAULT_FILENAME)
        path.write_text("original content\n")

        def boom(self, data, stream):
            raise RuntimeError("simulated dump failure")

        monkeypatch.setattr(ruamel.yaml.YAML, "dump", boom)

        with pytest.raises(RuntimeError, match="simulated dump failure"):
            export_ossie(
                [{"id": "product", "model_ref": "model.company.dim_product"}],
                [],
                "company",
                [model(columns=[column("product_id", "varchar")])],
            )

        assert path.read_text() == "original content\n"
        assert not os.path.exists(f"{path}.tmp")


class TestBruinGolden:
    def test_fixture_pipeline_exports_a_valid_document(
        self, validator, tmp_path, monkeypatch, bruin_pipeline
    ):
        path = configure(monkeypatch, tmp_path / DEFAULT_FILENAME)
        adapter = BruinAdapter(
            pipeline_path=bruin_pipeline,
            data_model_path="",
            asset_paths=[],
        )
        models = adapter.get_models()
        entities = [
            {
                "id": m["name"],
                "description": m["description"] or "",
                "model_ref": m["unique_id"],
            }
            for m in models
        ]

        result = export_ossie(entities, [], "trellis_test_pipeline", models)

        assert result.path == path
        document = read_yaml(path)
        validate(validator, document)

        assert document["name"] == "trellis_test_pipeline"
        names = [d["name"] for d in document["datasets"]]
        assert names == sorted(names)
        assert "dim__customer" in names

        customer = next(
            d for d in document["datasets"] if d["name"] == "dim__customer"
        )
        assert customer["source"] == "core.dim__customer"
        assert customer["description"] == "One row per customer."

    def test_fixture_pipeline_keys_come_from_column_metadata(
        self, validator, tmp_path, monkeypatch, bruin_pipeline
    ):
        path = configure(monkeypatch, tmp_path / DEFAULT_FILENAME)
        adapter = BruinAdapter(
            pipeline_path=bruin_pipeline,
            data_model_path="",
            asset_paths=[],
        )
        models = adapter.get_models()
        entities = [
            {
                "id": m["name"],
                "description": m["description"] or "",
                "model_ref": m["unique_id"],
            }
            for m in models
        ]
        schemas = {
            m["unique_id"]: adapter.get_model_schema(m["name"]) for m in models
        }

        export_ossie(entities, [], "trellis_test_pipeline", models, schemas)

        document = read_yaml(path)
        validate(validator, document)
        customer = next(
            d for d in document["datasets"] if d["name"] == "dim__customer"
        )
        assert customer["primary_key"] == ["customer_id"]
        assert "unique_keys" not in customer



class TestNegativeValidation:
    def test_validator_rejects_a_broken_document(self, validator):
        broken = {
            "version": "0.2.0.dev0",
            "name": "broken",
            "datasets": [
                {
                    "name": "dim_product",
                    "fields": [
                        {
                            "name": "product_id",
                            "expression": {
                                "dialects": [
                                    {
                                        "dialect": "ANSI_SQL",
                                        "expression": "product_id",
                                    }
                                ]
                            },
                            "datatype": "String",
                        }
                    ],
                }
            ],
            "relationships": [],
            "metrics": [],
        }
        # Missing the required `source` on the dataset.
        assert not validator.is_valid(broken)

        empty = {
            "version": "0.2.0.dev0",
            "name": "broken",
            "datasets": [],
        }
        # `datasets` has minItems: 1.
        assert not validator.is_valid(empty)


class PushAdapter(FakeAdapter):
    """A fake adapter that performs the framework write a real push performs.

    It keeps a written schema file so `SyncOutcome.files` can be told apart from
    the Ossie document, and can be told to fail a specific model's schema read.
    """

    def __init__(self, output_dir, models=None):
        super().__init__(models=models)
        self.output_dir = Path(output_dir)
        self.push_count = 0
        self.failing_schemas: set[str] = set()

    def sync_relationships(self, entities, relationships):
        self.push_count += 1
        path = self.output_dir / "framework_schema.yml"
        path.write_text(f"push: {self.push_count}\n")
        return [path]

    def get_model_schema(self, model_name, version=None):
        if model_name in self.failing_schemas:
            raise FileNotFoundError(f"no schema file for {model_name}")
        return super().get_model_schema(model_name, version=version)


CUSTOMER_MODEL = {
    "unique_id": "model.fake.customer",
    "name": "customer",
    "version": None,
    "schema": "main",
    "table": "dim_customer",
    "columns": [
        {"name": "customer_id", "type": "varchar", "description": "Customer ID"}
    ],
    "description": "Customers",
    "materialization": "table",
    "file_path": "models/dim_customer.sql",
    "tags": [],
}
CUSTOMER_ENTITY = {
    "id": "customer",
    "label": "Customer",
    "model_ref": "model.fake.customer",
}


def install_push(
    monkeypatch, output_dir, adapter, *, enabled=True, filename=DEFAULT_FILENAME
):
    """Point the Ossie output at `output_dir` and route the push at `adapter`."""
    path = Path(output_dir) / filename
    monkeypatch.setattr(
        cfg,
        "OSSIE_CONFIG",
        cfg.OssieConfig(enabled=enabled, file=str(path)),
    )
    monkeypatch.setattr(schema_service, "get_adapter", lambda: adapter)
    return path


def write_data_model(path, entities, relationships=()):
    Path(path).write_text(
        yaml.safe_dump(
            {
                "version": 0.1,
                "entities": list(entities),
                "relationships": list(relationships),
            }
        )
    )


class TestPushIntegration:
    def test_enabled_push_writes_a_valid_document(
        self, validator, monkeypatch, tmp_path, temp_data_model_path
    ):
        path = install_push(
            monkeypatch, tmp_path, PushAdapter(tmp_path, [dict(CUSTOMER_MODEL)])
        )
        write_data_model(temp_data_model_path, [dict(CUSTOMER_ENTITY)])

        result = schema_service.sync_framework_tests()

        assert isinstance(result, schema_service.SyncOutcome)
        assert result.ossie_path == path
        assert path.exists()
        assert path in result.files

        document = read_yaml(path)
        validate(validator, document)
        assert document["name"] == "fake"
        assert [d["name"] for d in document["datasets"]] == ["customer"]

    def test_disabled_push_leaves_an_existing_document_untouched(
        self, monkeypatch, tmp_path, temp_data_model_path
    ):
        path = install_push(
            monkeypatch,
            tmp_path,
            PushAdapter(tmp_path, [dict(CUSTOMER_MODEL)]),
            enabled=False,
        )
        path.write_text("name: previous\n")
        os.utime(path, (1_000_000_000, 1_000_000_000))
        before = path.stat()

        def boom(*args, **kwargs):
            raise AssertionError("the exporter must not run while disabled")

        monkeypatch.setattr(schema_service, "export_ossie_for_push", boom)
        write_data_model(temp_data_model_path, [dict(CUSTOMER_ENTITY)])

        result = schema_service.sync_framework_tests()

        assert result.ossie_path is None
        assert result.warnings == []
        assert path.read_bytes() == b"name: previous\n"
        after = path.stat()
        assert after.st_mtime_ns == before.st_mtime_ns
        assert after.st_size == before.st_size

    def test_zero_bound_entities_writes_nothing_and_says_why(
        self, monkeypatch, tmp_path, temp_data_model_path
    ):
        path = install_push(
            monkeypatch, tmp_path, PushAdapter(tmp_path, [dict(CUSTOMER_MODEL)])
        )
        write_data_model(temp_data_model_path, [{"id": "draft", "label": "Draft"}])

        result = schema_service.sync_framework_tests()

        assert result.ossie_path is None
        assert not path.exists()
        assert any("not bound" in w for w in result.warnings)
        assert any("nothing was written" in w for w in result.warnings)

    def test_export_failure_says_framework_files_were_updated(
        self, monkeypatch, tmp_path, temp_data_model_path
    ):
        adapter = PushAdapter(tmp_path, [dict(CUSTOMER_MODEL)])
        install_push(monkeypatch, tmp_path, adapter)
        write_data_model(temp_data_model_path, [dict(CUSTOMER_ENTITY)])

        def boom(*args, **kwargs):
            raise RuntimeError("disk full")

        monkeypatch.setattr(schema_service, "export_ossie_for_push", boom)

        with pytest.raises(FileOperationError) as excinfo:
            schema_service.sync_framework_tests()

        message = str(excinfo.value)
        assert adapter.push_count == 1
        assert "framework schema files were updated" in message.lower()
        assert "was not written" in message
        assert "disk full" in message

    def test_sync_tests_endpoint_returns_warnings_and_the_written_path(
        self, test_client, monkeypatch, tmp_path, temp_data_model_path
    ):
        path = install_push(
            monkeypatch, tmp_path, PushAdapter(tmp_path, [dict(CUSTOMER_MODEL)])
        )
        write_data_model(temp_data_model_path, [dict(CUSTOMER_ENTITY)])

        response = test_client.post("/api/sync-tests")

        assert response.status_code == 200
        body = response.json()
        assert body["warnings"] == []
        assert str(path) in body["files"]
        assert DEFAULT_FILENAME in body["message"]
        assert path.exists()

    def test_unreadable_model_schema_is_only_a_warning(
        self, validator, monkeypatch, tmp_path, temp_data_model_path
    ):
        adapter = PushAdapter(tmp_path, [dict(CUSTOMER_MODEL)])
        adapter.failing_schemas = {"customer"}
        path = install_push(monkeypatch, tmp_path, adapter)
        write_data_model(temp_data_model_path, [dict(CUSTOMER_ENTITY)])

        result = schema_service.sync_framework_tests()

        assert result.ossie_path == path
        assert path.exists()
        validate(validator, read_yaml(path))

        warning = next(w for w in result.warnings if 'model "customer"' in w)
        assert "schema" in warning


# The document today's exporter writes for one product and one sale dataset.
# Captured before metric emission landed; metric preservation must not alter it.
GOLDEN_NO_METRICS = """version: 0.2.0.dev0
name: company
datasets:
  - name: dim_product
    source: main.dim_product
    description: Product catalog
    primary_key:
      - product_id
    fields:
      - name: product_id
        expression:
          dialects:
            - dialect: ANSI_SQL
              expression: product_id
        datatype: String
        dimension:
          is_time: false
      - name: product_name
        expression:
          dialects:
            - dialect: ANSI_SQL
              expression: product_name
        datatype: String
        dimension:
          is_time: false
  - name: fct_sale
    source: main.fct_sale
    fields:
      - name: sale_id
        expression:
          dialects:
            - dialect: ANSI_SQL
              expression: sale_id
        datatype: String
        dimension:
          is_time: false
      - name: product_id
        expression:
          dialects:
            - dialect: ANSI_SQL
              expression: product_id
        datatype: String
        dimension:
          is_time: false
relationships:
  - name: fct_sale_to_dim_product
    from: fct_sale
    to: dim_product
    from_columns:
      - product_id
    to_columns:
      - product_id
metrics: []
"""


def draft(metric_id, expression="sum(amount)", dataset_ref=None, description=None):
    """A drafted metric as metric_tree.yml stores it."""
    entry = {
        "id": metric_id,
        "label": metric_id.replace("_", " ").title(),
        "expression": expression,
    }
    if description:
        entry["description"] = description
    if dataset_ref:
        entry["dataset_ref"] = dataset_ref
    return entry


def configure_metrics(
    monkeypatch, tmp_path, *, enabled=True, metrics=None, dialect="ANSI_SQL"
):
    """Point `metrics.*` at tmp_path, writing the tree there when one is given."""
    tree_path = Path(tmp_path) / "metric_tree.yml"
    if metrics is not None:
        tree_path.write_text(
            yaml.safe_dump(
                {"version": 0.1, "metrics": list(metrics), "influences": []}
            )
        )
    monkeypatch.setattr(
        cfg,
        "METRICS_CONFIG",
        cfg.MetricsConfig(
            enabled=enabled,
            file=str(tree_path),
            expression_dialect=dialect,
        ),
    )
    return tree_path


def export_product_and_sale(
    tmp_path,
    monkeypatch,
    *,
    metrics=None,
    enabled=True,
    existing=None,
    dialect="ANSI_SQL",
    tree=None,
    filename=DEFAULT_FILENAME,
):
    """Export a fixed two-dataset model with the given metric tree state."""
    path = Path(tmp_path) / filename
    monkeypatch.setattr(cfg, "OSSIE_CONFIG", cfg.OssieConfig(file=str(path)))
    configure_metrics(
        monkeypatch, tmp_path, enabled=enabled, metrics=metrics, dialect=dialect
    )
    if existing is not None:
        path.write_text(yaml.safe_dump(existing, sort_keys=False))
    result = export_ossie(
        [PRODUCT_ENTITY, SALE_ENTITY],
        [],
        "company",
        [PRODUCT_MODEL, SALE_MODEL],
        metric_tree=tree,
    )
    return path, result


FOREIGN_EXISTING = {
    "version": "0.2.0.dev0",
    "name": "company",
    "datasets": [
        {
            "name": "fct_sale",
            "source": "main.fct_sale",
            "fields": [],
            "metrics": [
                {
                    "name": "manual_orders",
                    "description": "Kept by hand",
                    "expression": {
                        "dialects": [
                            {"dialect": "ANSI_SQL", "expression": "count(*)"}
                        ]
                    },
                    "datatype": "Integer",
                    "ai_context": {"synonyms": ["orders"]},
                    "custom_extensions": [
                        {"vendor_name": "ACME", "data": "opaque"}
                    ],
                }
            ],
        },
        {"name": "dim_product", "source": "main.dim_product", "fields": []},
    ],
    "relationships": [],
    "metrics": [
        {
            "name": "model_margin",
            "expression": {
                "dialects": [
                    {"dialect": "ANSI_SQL", "expression": "sum(amount) - sum(cost)"}
                ]
            },
            "custom_extensions": [{"vendor_name": "ACME", "data": "opaque"}],
        }
    ],
}


class TestMetricEmission:
    def test_dataset_ref_lands_under_that_dataset(
        self, validator, tmp_path, monkeypatch
    ):
        path, _ = export_product_and_sale(
            tmp_path,
            monkeypatch,
            metrics=[
                draft("revenue", "sum(amount)", "fct_sale", "Booked revenue."),
                draft("orders", "count(*)", "fct_sale"),
            ],
        )

        document = read_yaml(path)
        validate(validator, document)

        datasets = {dataset["name"]: dataset for dataset in document["datasets"]}
        assert [m["name"] for m in datasets["fct_sale"]["metrics"]] == [
            "orders",
            "revenue",
        ]
        assert datasets["fct_sale"]["metrics"][1] == {
            "name": "revenue",
            "description": "Booked revenue.",
            "expression": {
                "dialects": [
                    {"dialect": "ANSI_SQL", "expression": "sum(amount)"}
                ]
            },
        }
        assert "description" not in datasets["fct_sale"]["metrics"][0]
        # The dataset carries metrics after its fields, and only when non-empty.
        assert list(datasets["fct_sale"])[-1] == "metrics"
        assert "metrics" not in datasets["dim_product"]
        assert document["metrics"] == []

    def test_draft_without_dataset_ref_lands_at_root_sorted_by_name(
        self, validator, tmp_path, monkeypatch
    ):
        path, _ = export_product_and_sale(
            tmp_path,
            monkeypatch,
            metrics=[draft("revenue"), draft("margin", "avg(price)")],
            dialect="OSSIE_SQL_2026",
        )

        document = read_yaml(path)
        validate(validator, document)

        assert [m["name"] for m in document["metrics"]] == ["margin", "revenue"]
        assert document["metrics"][0]["expression"] == {
            "dialects": [{"dialect": "OSSIE_SQL_2026", "expression": "avg(price)"}]
        }
        assert "datatype" not in document["metrics"][0]
        assert all("metrics" not in dataset for dataset in document["datasets"])

    def test_existing_metrics_survive_at_both_levels(self, validator, tmp_path, monkeypatch):
        path, _ = export_product_and_sale(
            tmp_path,
            monkeypatch,
            metrics=[draft("revenue", "sum(amount)", "fct_sale"), draft("margin")],
            existing=FOREIGN_EXISTING,
        )

        document = read_yaml(path)
        validate(validator, document)

        datasets = {dataset["name"]: dataset for dataset in document["datasets"]}
        assert [m["name"] for m in datasets["fct_sale"]["metrics"]] == [
            "revenue",
            "manual_orders",
        ]
        preserved = datasets["fct_sale"]["metrics"][1]
        assert list(preserved) == [
            "name",
            "description",
            "expression",
            "datatype",
            "ai_context",
            "custom_extensions",
        ]
        assert preserved["datatype"] == "Integer"
        assert preserved["ai_context"] == {"synonyms": ["orders"]}
        assert preserved["custom_extensions"] == [
            {"vendor_name": "ACME", "data": "opaque"}
        ]

        assert [m["name"] for m in document["metrics"]] == [
            "margin",
            "model_margin",
        ]
        root_preserved = document["metrics"][1]
        assert root_preserved["custom_extensions"] == [
            {"vendor_name": "ACME", "data": "opaque"}
        ]
        assert "datatype" not in root_preserved

    def test_disabled_emits_nothing_and_still_preserves(
        self, validator, tmp_path, monkeypatch
    ):
        path, _ = export_product_and_sale(
            tmp_path,
            monkeypatch,
            metrics=[draft("revenue", "sum(amount)", "fct_sale"), draft("margin")],
            enabled=False,
            existing=FOREIGN_EXISTING,
        )

        document = read_yaml(path)
        validate(validator, document)

        datasets = {dataset["name"]: dataset for dataset in document["datasets"]}
        assert [m["name"] for m in datasets["fct_sale"]["metrics"]] == [
            "manual_orders"
        ]
        assert [m["name"] for m in document["metrics"]] == ["model_margin"]
        assert "metrics" not in datasets["dim_product"]

    def test_unresolvable_dataset_ref_warns_and_falls_back_to_the_root(
        self, validator, tmp_path, monkeypatch
    ):
        path, result = export_product_and_sale(
            tmp_path,
            monkeypatch,
            metrics=[draft("orphan", "sum(x)", "ghost")],
        )

        document = read_yaml(path)
        validate(validator, document)

        assert [m["name"] for m in document["metrics"]] == ["orphan"]
        assert all("metrics" not in dataset for dataset in document["datasets"])

        warning = next(w for w in result.warnings if "orphan" in w)
        assert "ghost" in warning
        assert "root" in warning

    def test_dataset_ref_naming_an_entity_id_does_not_resolve(
        self, validator, tmp_path, monkeypatch
    ):
        """`dataset_ref` is the exported dataset name (`fct_sale`), not the entity id."""
        path, result = export_product_and_sale(
            tmp_path,
            monkeypatch,
            metrics=[draft("revenue", "sum(amount)", "sale")],
        )

        document = read_yaml(path)
        validate(validator, document)

        assert [m["name"] for m in document["metrics"]] == ["revenue"]
        assert all("metrics" not in dataset for dataset in document["datasets"])
        assert any('dataset_ref "sale"' in w for w in result.warnings)

    def test_preserved_metric_of_a_vanished_dataset_moves_to_the_root(
        self, validator, tmp_path, monkeypatch
    ):
        existing = {
            "version": "0.2.0.dev0",
            "name": "company",
            "datasets": [
                {
                    "name": "legacy",
                    "source": "main.legacy",
                    "fields": [],
                    "metrics": [
                        {
                            "name": "legacy_orders",
                            "expression": {
                                "dialects": [
                                    {"dialect": "ANSI_SQL", "expression": "count(*)"}
                                ]
                            },
                        }
                    ],
                }
            ],
            "relationships": [],
            "metrics": [],
        }

        path, result = export_product_and_sale(
            tmp_path, monkeypatch, existing=existing
        )

        document = read_yaml(path)
        validate(validator, document)

        assert "legacy" not in {dataset["name"] for dataset in document["datasets"]}
        assert [m["name"] for m in document["metrics"]] == ["legacy_orders"]
        warning = next(w for w in result.warnings if "legacy_orders" in w)
        assert "legacy" in warning
        assert "root" in warning

    def test_second_push_is_byte_identical(self, tmp_path, monkeypatch):
        metrics = [
            draft("revenue", "sum(amount)", "fct_sale", "Booked revenue."),
            draft("orders", "count(*)", "fct_sale"),
            draft("margin"),
        ]
        path, _ = export_product_and_sale(
            tmp_path, monkeypatch, metrics=metrics, existing=FOREIGN_EXISTING
        )
        first = path.read_bytes()

        export_product_and_sale(
            tmp_path, monkeypatch, metrics=metrics, existing=None
        )

        assert path.read_bytes() == first

    def test_explicit_tree_argument_wins_over_the_file(
        self, validator, tmp_path, monkeypatch
    ):
        path, _ = export_product_and_sale(
            tmp_path,
            monkeypatch,
            metrics=[draft("from_file")],
            tree=MetricTreeFile(
                metrics=[MetricEntry(id="from_argument", label="Arg", expression="sum(x)")]
            ),
        )

        document = read_yaml(path)
        validate(validator, document)
        assert [m["name"] for m in document["metrics"]] == ["from_argument"]

    def test_no_metric_tree_file_matches_the_pre_change_golden(
        self, tmp_path, monkeypatch
    ):
        path = Path(tmp_path) / DEFAULT_FILENAME
        monkeypatch.setattr(cfg, "OSSIE_CONFIG", cfg.OssieConfig(file=str(path)))
        configure_metrics(monkeypatch, tmp_path, enabled=False)

        export_ossie(
            [
                {
                    "id": "product",
                    "description": "Product catalog",
                    "model_ref": "model.company.dim_product",
                },
                SALE_ENTITY,
            ],
            [
                relationship(
                    "sale", "product", "many_to_one", "product_id", "product_id"
                )
            ],
            "company",
            [PRODUCT_MODEL, SALE_MODEL],
        )

        assert path.read_text() == GOLDEN_NO_METRICS


def test_collect_model_schemas_reads_bound_models_in_one_batch():
    """A push with N bound entities makes one batch call, not N adapter reads."""
    from trellis_datamodel.services.ossie import collect_model_schemas

    models = [
        {"unique_id": f"model.p.m{i}", "name": f"m{i}", "version": None}
        for i in range(5)
    ]
    entities = [
        {"id": f"e{i}", "model_ref": f"model.p.m{i}"} for i in range(4)
    ]

    class BatchAdapter:
        batches: list[list] = []

        def get_model_schema(self, *args, **kwargs):
            raise AssertionError("per-model read during a push")

        def get_model_schemas(self, requests):
            self.batches.append(requests)
            return [
                RuntimeError("boom") if name == "m2" else {"model_name": name}
                for name, _ in requests
            ]

    adapter = BatchAdapter()
    schemas, warnings = collect_model_schemas(adapter, entities, models)

    assert adapter.batches == [[(f"m{i}", None) for i in range(4)]]
    assert set(schemas) == {"model.p.m0", "model.p.m1", "model.p.m3"}
    assert len(warnings) == 1 and 'model "m2"' in warnings[0] and "boom" in warnings[0]
