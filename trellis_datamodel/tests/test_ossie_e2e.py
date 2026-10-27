"""End-to-end test for the Ossie export through the HTTP surface.

A real `POST /api/sync-tests` runs the same code path the Push button does: it
reads `data_model.yml`, asks the adapter for models and schemas, writes the
semantic model, and reports the file and any warnings in the response. The
document is validated against the vendored `0.2.0.dev0` schema.
"""

import json
from pathlib import Path

import jsonschema
import pytest
import yaml

import trellis_datamodel.config as cfg
import trellis_datamodel.services.schema as schema_service
from trellis_datamodel.tests.conftest import FakeAdapter

SCHEMA_PATH = Path(__file__).parent / "fixtures" / "ossie" / "ossie-schema.json"
OSSIE_FILENAME = "semantic_model.yml"

MODELS = [
    {
        "unique_id": "model.fake.dim_customer",
        "name": "dim_customer",
        "version": None,
        "schema": "marts",
        "table": "dim_customer",
        "columns": [
            {"name": "customer_id", "type": "varchar", "description": "Customer ID"},
            {"name": "customer_name", "type": "varchar", "description": None},
        ],
        "description": "One row per customer.",
        "materialization": "table",
        "file_path": "models/dim_customer.sql",
        "tags": [],
    },
    {
        "unique_id": "model.fake.fct_sale",
        "name": "fct_sale",
        "version": None,
        "schema": "marts",
        "table": "fct_sale",
        "columns": [
            {"name": "sale_id", "type": "varchar", "description": None},
            {"name": "customer_id", "type": "varchar", "description": None},
            {"name": "amount", "type": "numeric", "description": None},
        ],
        "description": "Sales at order-line grain.",
        "materialization": "table",
        "file_path": "models/fct_sale.sql",
        "tags": [],
    },
    {
        "unique_id": "model.fake.fct_order",
        "name": "fct_order",
        "version": None,
        "schema": "marts",
        "table": "fct_order",
        "columns": [
            {"name": "order_id", "type": "varchar", "description": None},
            {"name": "customer_id", "type": "varchar", "description": None},
        ],
        "description": "One row per order.",
        "materialization": "table",
        "file_path": "models/fct_order.sql",
        "tags": [],
    },
]

ENTITIES = [
    {
        "id": "customer",
        "label": "Customer",
        "description": "Customer records",
        "model_ref": "model.fake.dim_customer",
        "entity_type": "dimension",
    },
    {
        "id": "sale",
        "label": "Sale",
        "description": "Sales records",
        "model_ref": "model.fake.fct_sale",
        "entity_type": "fact",
    },
    {
        "id": "order",
        "label": "Order",
        "description": "Order records",
        "model_ref": "model.fake.fct_order",
        "entity_type": "fact",
    },
    {
        "id": "procurement",
        "label": "Procurement",
        "description": "",
        "model_ref": None,
        "entity_type": "fact",
    },
]

# One dimension referenced by two facts; the FK sits on the fact side.
RELATIONSHIPS = [
    {
        "source": "customer",
        "target": "sale",
        "type": "one_to_many",
        "source_field": "customer_id",
        "target_field": "customer_id",
    },
    {
        "source": "customer",
        "target": "order",
        "type": "one_to_many",
        "source_field": "customer_id",
        "target_field": "customer_id",
    },
]


@pytest.fixture(scope="module")
def validator():
    with open(SCHEMA_PATH) as f:
        schema = json.load(f)
    return jsonschema.Draft202012Validator(schema)


def validate(validator, document):
    errors = sorted(validator.iter_errors(document), key=lambda e: list(e.path))
    if errors:
        messages = "\n".join(f"  - {e.message} at {list(e.path)}" for e in errors)
        raise AssertionError(f"Ossie document does not validate:\n{messages}")


class E2EAdapter(FakeAdapter):
    """A fake adapter carrying the metadata the export reads.

    `get_model_schema` marks `customer_id` as a primary key so the key rules run
    against the same ColumnSchema shape a real framework produces.
    """

    def get_model_schema(self, model_name, version=None):
        schema = super().get_model_schema(model_name, version=version)
        if model_name == "dim_customer":
            for column in schema["columns"]:
                if column["name"] == "customer_id":
                    column["primary_key"] = True
        return schema

    def get_project_status(self):
        status = super().get_project_status()
        status["project_name"] = "company_dummy"
        return status


def write_data_model(path):
    Path(path).write_text(
        yaml.safe_dump(
            {
                "version": 0.1,
                "entities": ENTITIES,
                "relationships": RELATIONSHIPS,
            }
        )
    )


def install(monkeypatch, tmp_path, *, enabled):
    """Point the push at a temp data model, a temp Ossie file, and the adapter."""
    data_model_path = tmp_path / "data_model.yml"
    ossie_path = tmp_path / OSSIE_FILENAME
    monkeypatch.setattr(cfg, "DATA_MODEL_PATH", str(data_model_path))
    monkeypatch.setattr(
        cfg,
        "OSSIE_CONFIG",
        cfg.OssieConfig(enabled=enabled, file=str(ossie_path)),
    )
    # Fresh dicts per test so a mutation in one push cannot leak into the next.
    adapter = E2EAdapter(models=[dict(m) for m in MODELS])
    monkeypatch.setattr(schema_service, "get_adapter", lambda: adapter)
    write_data_model(data_model_path)
    return data_model_path, ossie_path


def read_yaml(path):
    with open(path) as f:
        return yaml.safe_load(f)


def install_metrics(monkeypatch, tmp_path, *, enabled, metrics):
    """Point the metric tree at tmp_path so the push can read the drafts."""
    tree_path = tmp_path / "metric_tree.yml"
    tree_path.write_text(
        yaml.safe_dump({"version": 0.1, "metrics": list(metrics), "influences": []})
    )
    monkeypatch.setattr(
        cfg,
        "METRICS_CONFIG",
        cfg.MetricsConfig(
            enabled=enabled,
            file=str(tree_path),
            layout_file=str(tmp_path / "metric_layout.yml"),
        ),
    )
    return tree_path


class TestOssiePushEndToEnd:
    def test_one_push_writes_only_the_bound_entities(
        self, test_client, validator, monkeypatch, tmp_path
    ):
        _, ossie_path = install(monkeypatch, tmp_path, enabled=True)

        response = test_client.post("/api/sync-tests")

        assert response.status_code == 200
        body = response.json()

        assert ossie_path.exists()
        document = read_yaml(ossie_path)
        validate(validator, document)

        assert document["version"] == "0.2.0.dev0"
        assert document["name"] == "company_dummy"
        assert document["metrics"] == []

        # Exactly the three bound entities, sorted by dataset name.
        assert [dataset["name"] for dataset in document["datasets"]] == [
            "dim_customer",
            "fct_order",
            "fct_sale",
        ]
        assert all(
            dataset["name"] != "procurement" for dataset in document["datasets"]
        )

        datasets = {dataset["name"]: dataset for dataset in document["datasets"]}
        assert datasets["dim_customer"]["source"] == "marts.dim_customer"
        assert datasets["dim_customer"]["primary_key"] == ["customer_id"]

        assert document["relationships"] == [
            {
                "name": "fct_order_to_dim_customer",
                "from": "fct_order",
                "to": "dim_customer",
                "from_columns": ["customer_id"],
                "to_columns": ["customer_id"],
            },
            {
                "name": "fct_sale_to_dim_customer",
                "from": "fct_sale",
                "to": "dim_customer",
                "from_columns": ["customer_id"],
                "to_columns": ["customer_id"],
            },
        ]

        assert str(ossie_path) in body["files"]
        assert any("procurement" in warning for warning in body["warnings"])

    def test_message_counts_framework_files_and_reports_warnings(
        self, test_client, monkeypatch, tmp_path
    ):
        """The Ossie document is named separately, not counted as a schema file."""
        install(monkeypatch, tmp_path, enabled=True)

        body = test_client.post("/api/sync-tests").json()

        # FakeAdapter writes no framework files; the Ossie document is the only
        # entry in `files`, and counting it would say "1 file(s)".
        assert body["message"].startswith("Updated 0 file(s)")
        assert "wrote semantic_model.yml" in body["message"]
        assert body["warnings"]
        assert body["message"].endswith(", 1 warning")

    def test_disabled_push_leaves_the_existing_document_untouched(
        self, test_client, monkeypatch, tmp_path
    ):
        _, ossie_path = install(monkeypatch, tmp_path, enabled=True)
        assert test_client.post("/api/sync-tests").status_code == 200
        assert ossie_path.exists()

        before_bytes = ossie_path.read_bytes()
        before_mtime = ossie_path.stat().st_mtime_ns

        monkeypatch.setattr(
            cfg,
            "OSSIE_CONFIG",
            cfg.OssieConfig(enabled=False, file=str(ossie_path)),
        )
        response = test_client.post("/api/sync-tests")

        assert response.status_code == 200
        assert ossie_path.read_bytes() == before_bytes
        assert ossie_path.stat().st_mtime_ns == before_mtime
        assert str(ossie_path) not in response.json()["files"]

    def test_push_emits_the_drafted_metrics(
        self, test_client, validator, monkeypatch, tmp_path
    ):
        _, ossie_path = install(monkeypatch, tmp_path, enabled=True)
        install_metrics(
            monkeypatch,
            tmp_path,
            enabled=True,
            metrics=[
                {
                    "id": "revenue",
                    "label": "Revenue",
                    "description": "Booked revenue.",
                    "expression": "sum(amount)",
                    "dataset_ref": "sale",
                },
                {
                    "id": "avg_order_value",
                    "label": "Average order value",
                    "expression": "sum(amount) / count(*)",
                },
            ],
        )

        response = test_client.post("/api/sync-tests")

        assert response.status_code == 200
        document = read_yaml(ossie_path)
        validate(validator, document)

        datasets = {dataset["name"]: dataset for dataset in document["datasets"]}
        assert [m["name"] for m in datasets["fct_sale"]["metrics"]] == ["revenue"]
        assert datasets["fct_sale"]["metrics"][0]["expression"] == {
            "dialects": [{"dialect": "ANSI_SQL", "expression": "sum(amount)"}]
        }
        assert [m["name"] for m in document["metrics"]] == ["avg_order_value"]
        assert "metrics" not in datasets["dim_customer"]
        assert str(ossie_path) in response.json()["files"]
