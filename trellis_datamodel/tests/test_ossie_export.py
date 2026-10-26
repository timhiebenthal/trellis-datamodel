"""Tests for the Apache Ossie exporter (Tasks 4-5: datasets, fields, keys).

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
from trellis_datamodel.adapters.base import ColumnInfo, ModelInfo
from trellis_datamodel.adapters.bruin import BruinAdapter
from trellis_datamodel.services.ossie import (
    DEFAULT_FILENAME,
    FIELD_DIALECT,
    OSSIE_VERSION,
    OssieExport,
    export_ossie,
)

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
):
    return ModelInfo(
        unique_id=unique_id,
        name=name,
        version=None,
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

        # The phantom candidate is dropped before counting, so one remains.
        assert dataset["primary_key"] == ["product_id"]
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
        validate(validator, read_yaml(single))

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
        validate(validator, read_yaml(multiple))


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
