"""
Characterization tests for DbtCoreAdapter relationship inference.

Everything is observed through ``adapter.infer_relationships()``: which
relationships come back, which entity ids they resolve to, and which are
filtered out. Fixtures are tiny dbt projects written into ``tmp_path``.
"""

import json
from pathlib import Path

import pytest
import yaml

import trellis_datamodel.config as cfg
from trellis_datamodel.adapters.dbt_core import DbtCoreAdapter
from trellis_datamodel.exceptions import ConfigurationError, FileOperationError


def _model_node(name, columns=None, version=None):
    node = {
        "unique_id": f"model.proj.{name}",
        "resource_type": "model",
        "name": name,
        "original_file_path": f"models/3_core/{name}.sql",
        "columns": columns or {},
        "depends_on": {"nodes": []},
    }
    if version is not None:
        node["unique_id"] = f"model.proj.{name}.v{version}"
        node["version"] = version
    return node


def _fk_column(to, field="id", key="data_tests", args=False):
    rel = {"arguments": {"to": to, "field": field}} if args else {"to": to, "field": field}
    return {key: [{"relationships": rel}]}


def _build(tmp_path: Path, nodes, entities, yml_files=None):
    """Write a dbt project and return an adapter over it."""
    project = tmp_path / "dbt_project"
    models = project / "models" / "3_core"
    models.mkdir(parents=True)
    (project / "target").mkdir()
    manifest_path = project / "target" / "manifest.json"
    manifest_path.write_text(
        json.dumps({"nodes": {n["unique_id"]: n for n in nodes}, "sources": {}})
    )
    data_model_path = project / "data_model.yml"
    data_model_path.write_text(yaml.safe_dump({"entities": entities, "relationships": []}))
    for filename, content in (yml_files or {}).items():
        (models / filename).parent.mkdir(parents=True, exist_ok=True)
        (models / filename).write_text(content)
    return DbtCoreAdapter(
        manifest_path=str(manifest_path),
        catalog_path=str(project / "target" / "catalog.json"),
        project_path=str(project),
        data_model_path=str(data_model_path),
        model_paths=["3_core"],
    )


EMPTY_SCHEMA = {"schema.yml": "version: 2\nmodels: []\n"}

BOUND_ENTITIES = [
    {"id": "customer", "model_ref": "model.proj.dim_customer"},
    {"id": "orders", "model_ref": "model.proj.fct_orders"},
]


def _customer_orders_nodes(fk_column=None):
    return [
        _model_node("dim_customer", {"id": {"name": "id"}}),
        _model_node(
            "fct_orders",
            {"customer_id": {"name": "customer_id", **(fk_column or _fk_column("ref('dim_customer')"))}},
        ),
    ]


class TestManifestIndexedRelationships:
    def test_fk_test_becomes_one_to_many_from_referenced_to_owning_entity(self, tmp_path):
        adapter = _build(tmp_path, _customer_orders_nodes(), BOUND_ENTITIES, EMPTY_SCHEMA)

        assert adapter.infer_relationships() == [
            {
                "source": "customer",
                "target": "orders",
                "label": "",
                "type": "one_to_many",
                "source_field": "id",
                "target_field": "customer_id",
                "source_model_name": "dim_customer",
                "source_model_version": None,
                "target_model_name": "fct_orders",
                "target_model_version": None,
            }
        ]

    def test_legacy_tests_key_is_read_like_data_tests(self, tmp_path):
        nodes = _customer_orders_nodes(_fk_column("ref('dim_customer')", key="tests"))
        adapter = _build(tmp_path, nodes, BOUND_ENTITIES, EMPTY_SCHEMA)

        assert [(r["source"], r["target"]) for r in adapter.infer_relationships()] == [
            ("customer", "orders")
        ]

    def test_arguments_block_form_is_read_like_top_level_keys(self, tmp_path):
        nodes = _customer_orders_nodes(_fk_column("ref('dim_customer')", "id", args=True))
        adapter = _build(tmp_path, nodes, BOUND_ENTITIES, EMPTY_SCHEMA)

        rels = adapter.infer_relationships()

        assert [(r["source_field"], r["target_field"]) for r in rels] == [("id", "customer_id")]

    def test_test_without_field_yields_no_relationship(self, tmp_path):
        nodes = _customer_orders_nodes(
            {"data_tests": [{"relationships": {"to": "ref('dim_customer')"}}]}
        )
        adapter = _build(tmp_path, nodes, BOUND_ENTITIES, EMPTY_SCHEMA)

        assert adapter.infer_relationships() == []

    def test_unbound_entities_are_filtered_by_default(self, tmp_path):
        entities = [{"id": "customer"}, {"id": "orders", "model_ref": "model.proj.fct_orders"}]
        adapter = _build(tmp_path, _customer_orders_nodes(), entities, EMPTY_SCHEMA)

        assert adapter.infer_relationships() == []

    def test_include_unbound_returns_relationship_with_raw_model_names(self, tmp_path):
        adapter = _build(tmp_path, _customer_orders_nodes(), [], EMPTY_SCHEMA)

        rels = adapter.infer_relationships(include_unbound=True)

        assert [(r["source"], r["target"]) for r in rels] == [("dim_customer", "fct_orders")]

    def test_entity_bound_only_through_additional_models_counts_as_bound(self, tmp_path):
        entities = [
            {"id": "customer", "model_ref": "model.proj.dim_customer"},
            {"id": "orders", "additional_models": ["model.proj.fct_orders"]},
        ]
        adapter = _build(tmp_path, _customer_orders_nodes(), entities, EMPTY_SCHEMA)

        rels = adapter.infer_relationships()

        assert [(r["source"], r["target"]) for r in rels] == [("customer", "orders")]

    def test_versioned_ref_resolves_to_entity_bound_to_that_version(self, tmp_path):
        nodes = [
            _model_node("dim_customer", {"id": {"name": "id"}}, version=2),
            _model_node(
                "fct_orders",
                {"customer_id": {"name": "customer_id", **_fk_column("ref('dim_customer', v=2)")}},
            ),
        ]
        entities = [
            {"id": "customer", "model_ref": "model.proj.dim_customer.v2"},
            {"id": "orders", "model_ref": "model.proj.fct_orders"},
        ]
        adapter = _build(tmp_path, nodes, entities, EMPTY_SCHEMA)

        rels = adapter.infer_relationships()

        assert [(r["source"], r["source_model_version"]) for r in rels] == [("customer", 2)]

    def test_owning_model_version_is_reported_as_target_version(self, tmp_path):
        nodes = [
            _model_node("dim_customer", {"id": {"name": "id"}}),
            _model_node(
                "fct_orders",
                {"customer_id": {"name": "customer_id", **_fk_column("ref('dim_customer')")}},
                version=3,
            ),
        ]
        entities = [
            {"id": "customer", "model_ref": "model.proj.dim_customer"},
            {"id": "orders", "model_ref": "model.proj.fct_orders.v3"},
        ]
        adapter = _build(tmp_path, nodes, entities, EMPTY_SCHEMA)

        rels = adapter.infer_relationships()

        assert [(r["target"], r["target_model_version"]) for r in rels] == [("orders", 3)]

    def test_entity_prefix_maps_prefixed_model_names_back_to_unbound_entity(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(
            cfg,
            "ENTITY_MODELING_CONFIG",
            cfg.EntityModelingConfig(enabled=True, entity_prefix=["entity_"]),
        )
        nodes = [
            _model_node("entity_customer", {"id": {"name": "id"}}),
            _model_node(
                "entity_orders",
                {"customer_id": {"name": "customer_id", **_fk_column("ref('entity_customer')")}},
            ),
        ]
        adapter = _build(
            tmp_path, nodes, [{"id": "customer"}, {"id": "orders"}], EMPTY_SCHEMA
        )

        rels = adapter.infer_relationships(include_unbound=True)

        assert [(r["source"], r["target"]) for r in rels] == [("customer", "orders")]

    def test_dimensional_prefixes_map_model_names_back_to_unbound_entities(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(
            cfg,
            "DIMENSIONAL_MODELING_CONFIG",
            cfg.DimensionalModelingConfig(
                enabled=True, dimension_prefix=["dim_"], fact_prefix=["fct_"]
            ),
        )
        adapter = _build(
            tmp_path,
            _customer_orders_nodes(),
            [{"id": "customer"}, {"id": "orders"}],
            EMPTY_SCHEMA,
        )

        rels = adapter.infer_relationships(include_unbound=True)

        assert [(r["source"], r["target"]) for r in rels] == [("customer", "orders")]

    def test_prefixed_name_stays_raw_when_dimensional_modeling_disabled(self, tmp_path):
        adapter = _build(
            tmp_path,
            _customer_orders_nodes(),
            [{"id": "customer"}, {"id": "orders"}],
            EMPTY_SCHEMA,
        )

        rels = adapter.infer_relationships(include_unbound=True)

        assert [(r["source"], r["target"]) for r in rels] == [("dim_customer", "fct_orders")]

    def test_yaml_documented_name_differing_from_file_name_resolves_to_bound_entity(
        self, tmp_path
    ):
        """fct_procurement.yml documents model `entity_procurement`; refs to that name map to the entity bound to fct_procurement."""
        nodes = [
            _model_node("fct_procurement", {"id": {"name": "id"}}),
            _model_node(
                "fct_orders",
                {"procurement_id": {"name": "procurement_id", **_fk_column("ref('entity_procurement')")}},
            ),
        ]
        entities = [
            {"id": "procurement", "model_ref": "model.proj.fct_procurement"},
            {"id": "orders", "model_ref": "model.proj.fct_orders"},
        ]
        yml = {
            "fct_procurement.yml": "version: 2\nmodels:\n  - name: entity_procurement\n",
        }
        adapter = _build(tmp_path, nodes, entities, yml)

        rels = adapter.infer_relationships()

        assert [(r["source"], r["target"]) for r in rels] == [("procurement", "orders")]

    def test_bound_entity_resolves_by_documented_yaml_name_of_its_own_model(self, tmp_path):
        """The bound model's yml documents a different name; refs using it resolve to the entity."""
        nodes = [
            _model_node("dim_customer", {"id": {"name": "id"}}),
            _model_node(
                "fct_orders",
                {"customer_id": {"name": "customer_id", **_fk_column("ref('Customer_Doc')")}},
            ),
        ]
        yml = {"dim_customer.yml": "version: 2\nmodels:\n  - name: dim_customer\n  - name: Customer_Doc\n"}
        adapter = _build(tmp_path, nodes, BOUND_ENTITIES, yml)

        rels = adapter.infer_relationships()

        assert [(r["source"], r["target"]) for r in rels] == [("customer", "orders")]

    def test_missing_schema_files_raise_when_relationships_exist(self, tmp_path):
        adapter = _build(tmp_path, _customer_orders_nodes(), BOUND_ENTITIES, {})

        with pytest.raises(ConfigurationError, match="No schema yml files"):
            adapter.infer_relationships()

    def test_missing_manifest_raises_file_operation_error(self, tmp_path):
        adapter = _build(tmp_path, _customer_orders_nodes(), BOUND_ENTITIES, EMPTY_SCHEMA)
        Path(adapter.manifest_path).unlink()

        with pytest.raises(FileOperationError, match="Manifest not found"):
            adapter.infer_relationships()


# --- YAML fallback: manifest carries no relationship tests -------------------

PLAIN_NODES = [_model_node("dim_customer"), _model_node("fct_orders")]

DIM_CUSTOMER_YML = "version: 2\nmodels:\n  - name: dim_customer\n    columns:\n      - name: id\n"

FCT_ORDERS_YML = """\
version: 2
models:
  - name: fct_orders
    columns:
      - name: customer_id
        {key}:
          - relationships:
              {to_block}
"""


def _fk_yaml(key="data_tests", args=False, to="ref('dim_customer')"):
    """One schema file per model, named after the model (dbt convention for per-model yml)."""
    if args:
        to_block = f"arguments:\n                to: \"{to}\"\n                field: id"
    else:
        to_block = f"to: \"{to}\"\n              field: id"
    return {
        "dim_customer.yml": DIM_CUSTOMER_YML,
        "fct_orders.yml": FCT_ORDERS_YML.format(key=key, to_block=to_block),
    }


class TestYamlScannedRelationships:
    def test_schema_yaml_fk_test_resolves_to_bound_entities(self, tmp_path):
        adapter = _build(tmp_path, PLAIN_NODES, BOUND_ENTITIES, _fk_yaml())

        assert adapter.infer_relationships() == [
            {
                "source": "customer",
                "target": "orders",
                "label": "",
                "type": "one_to_many",
                "source_field": "id",
                "target_field": "customer_id",
                "source_model_name": "dim_customer",
                "source_model_version": None,
                "target_model_name": "fct_orders",
                "target_model_version": None,
            }
        ]

    @pytest.mark.parametrize("key", ["tests", "data_tests"])
    def test_both_test_keys_are_scanned(self, tmp_path, key):
        adapter = _build(tmp_path, PLAIN_NODES, BOUND_ENTITIES, _fk_yaml(key=key))

        assert len(adapter.infer_relationships()) == 1

    def test_arguments_block_is_scanned(self, tmp_path):
        adapter = _build(tmp_path, PLAIN_NODES, BOUND_ENTITIES, _fk_yaml(args=True))

        assert [r["source_field"] for r in adapter.infer_relationships()] == ["id"]

    def test_unbound_entities_are_filtered_by_default(self, tmp_path):
        adapter = _build(tmp_path, PLAIN_NODES, [], _fk_yaml())

        assert adapter.infer_relationships() == []

    def test_include_unbound_returns_raw_model_names(self, tmp_path):
        adapter = _build(tmp_path, PLAIN_NODES, [], _fk_yaml())

        rels = adapter.infer_relationships(include_unbound=True)

        assert [(r["source"], r["target"]) for r in rels] == [("dim_customer", "fct_orders")]

    def test_duplicate_relationships_across_files_are_returned_once(self, tmp_path):
        yml = _fk_yaml()
        yml["copy/fct_orders.yml"] = yml["fct_orders.yml"]
        adapter = _build(tmp_path, PLAIN_NODES, BOUND_ENTITIES, yml)

        assert len(adapter.infer_relationships()) == 1

    def test_test_without_to_or_field_is_ignored(self, tmp_path):
        yml = {
            "fct_orders.yml": (
                "models:\n"
                "  - name: fct_orders\n"
                "    columns:\n"
                "      - name: customer_id\n"
                "        data_tests:\n"
                "          - relationships:\n"
                "              field: id\n"
                "          - not_null\n"
            )
        }
        adapter = _build(tmp_path, PLAIN_NODES, BOUND_ENTITIES, yml)

        assert adapter.infer_relationships() == []

    def test_unparseable_yaml_file_is_skipped_while_others_are_still_scanned(self, tmp_path):
        yml = _fk_yaml()
        yml["broken.yml"] = "models: [unclosed\n"
        adapter = _build(tmp_path, PLAIN_NODES, BOUND_ENTITIES, yml)

        assert len(adapter.infer_relationships()) == 1

    def test_no_schema_files_raise_configuration_error(self, tmp_path):
        adapter = _build(tmp_path, PLAIN_NODES, BOUND_ENTITIES, {})

        with pytest.raises(ConfigurationError, match="No schema yml files"):
            adapter.infer_relationships()

    def test_versioned_model_in_yaml_reports_its_version_on_the_target_side(self, tmp_path):
        yml = {
            "dim_customer.yml": DIM_CUSTOMER_YML,
            "fct_orders.yml": (
                "models:\n"
                "  - name: fct_orders\n"
                "    versions:\n"
                "      - v: 1\n"
                "      - v: 2\n"
                "        columns:\n"
                "          - name: customer_id\n"
                "            data_tests:\n"
                "              - relationships:\n"
                "                  to: ref('dim_customer', v=1)\n"
                "                  field: id\n"
            ),
        }
        entities = [
            {"id": "customer_v1", "model_ref": "model.proj.dim_customer.v1"},
            {"id": "orders_v2", "model_ref": "model.proj.fct_orders.v2"},
        ]
        adapter = _build(tmp_path, PLAIN_NODES, entities, yml)

        rels = adapter.infer_relationships()

        assert [
            (r["source"], r["source_model_version"], r["target"], r["target_model_version"])
            for r in rels
        ] == [("customer_v1", 1, "orders_v2", 2)]

    def test_each_model_version_resolves_to_the_entity_bound_to_that_version(self, tmp_path):
        yml = {
            "dim_customer.yml": DIM_CUSTOMER_YML,
            "fct_orders.yml": (
                "models:\n"
                "  - name: fct_orders\n"
                "    columns:\n"
                "      - name: customer_id\n"
                "        data_tests:\n"
                "          - relationships:\n"
                "              to: ref('dim_customer')\n"
                "              field: id\n"
                "    versions:\n"
                "      - v: 1\n"
                "      - v: 2\n"
                "        columns:\n"
                "          - include: all\n"
                "          - name: extra\n"
            ),
        }
        entities = [
            {"id": "customer", "model_ref": "model.proj.dim_customer"},
            {"id": "orders_v1", "model_ref": "model.proj.fct_orders.v1"},
            {"id": "orders_v2", "model_ref": "model.proj.fct_orders.v2"},
        ]
        adapter = _build(tmp_path, PLAIN_NODES, entities, yml)

        rels = adapter.infer_relationships()

        assert sorted((r["target"], r["target_model_version"]) for r in rels) == [
            ("orders_v1", 1),
            ("orders_v2", 2),
        ]

    def test_models_documented_in_one_shared_schema_file_still_resolve_to_their_entities(
        self, tmp_path
    ):
        yml = {
            "schema.yml": (
                "models:\n"
                "  - name: dim_customer\n"
                "    columns:\n"
                "      - name: id\n"
                "  - name: fct_orders\n"
                "    columns:\n"
                "      - name: customer_id\n"
                "        data_tests:\n"
                "          - relationships:\n"
                "              to: ref('dim_customer')\n"
                "              field: id\n"
            )
        }
        adapter = _build(tmp_path, PLAIN_NODES, BOUND_ENTITIES, yml)

        rels = adapter.infer_relationships()

        assert [(r["source"], r["target"]) for r in rels] == [("customer", "orders")]


class TestYamlScanEdgeCases:
    def test_missing_configured_model_dir_is_skipped(self, tmp_path):
        adapter = _build(tmp_path, PLAIN_NODES, BOUND_ENTITIES, _fk_yaml())
        adapter.model_paths = ["3_core", "does_not_exist"]

        assert [(r["source"], r["target"]) for r in adapter.infer_relationships()] == [
            ("customer", "orders")
        ]

    def test_model_entry_without_name_is_skipped(self, tmp_path):
        yml = _fk_yaml()
        yml["fct_orders.yml"] = yml["fct_orders.yml"].replace(
            "models:\n", "models:\n  - columns:\n      - name: orphan\n", 1
        )
        adapter = _build(tmp_path, PLAIN_NODES, BOUND_ENTITIES, yml)

        assert len(adapter.infer_relationships()) == 1

    def test_non_numeric_model_version_is_reported_as_none(self, tmp_path):
        yml = {
            "fct_orders.yml": (
                "models:\n"
                "  - name: fct_orders\n"
                "    versions:\n"
                "      - v: beta\n"
                "        columns:\n"
                "          - name: customer_id\n"
                "            data_tests:\n"
                "              - relationships:\n"
                "                  to: ref('dim_customer')\n"
                "                  field: id\n"
            )
        }
        adapter = _build(tmp_path, PLAIN_NODES, [], yml)

        rels = adapter.infer_relationships(include_unbound=True)

        assert [(r["target"], r["target_model_version"]) for r in rels] == [
            ("fct_orders", None)
        ]

    def test_model_bound_to_entity_without_id_falls_back_to_model_name(self, tmp_path):
        entities = [
            {"model_ref": "model.proj.dim_customer"},
            {"model_ref": "model.proj.fct_orders"},
        ]
        adapter = _build(tmp_path, PLAIN_NODES, entities, _fk_yaml())

        rels = adapter.infer_relationships(include_unbound=True)

        assert [(r["source"], r["target"]) for r in rels] == [("dim_customer", "fct_orders")]

    def test_relationships_read_before_a_malformed_model_entry_are_kept(self, tmp_path):
        yml = _fk_yaml()
        yml["fct_orders.yml"] += "  - not_a_mapping\n"
        adapter = _build(tmp_path, PLAIN_NODES, BOUND_ENTITIES, yml)

        assert [(r["source"], r["target"]) for r in adapter.infer_relationships()] == [
            ("customer", "orders")
        ]


class TestModelToEntityMapEdgeCases:
    def test_versioned_additional_model_resolves_to_its_entity(self, tmp_path):
        nodes = [
            _model_node("dim_customer", {"id": {"name": "id"}}),
            _model_node(
                "fct_orders",
                {"customer_id": {"name": "customer_id", **_fk_column("ref('dim_customer')")}},
                version=2,
            ),
        ]
        entities = [
            {"id": "customer", "model_ref": "model.proj.dim_customer"},
            {"id": "orders", "additional_models": ["model.proj.fct_orders.v2"]},
        ]
        adapter = _build(tmp_path, nodes, entities, EMPTY_SCHEMA)

        rels = adapter.infer_relationships()

        assert [(r["source"], r["target"], r["target_model_version"]) for r in rels] == [
            ("customer", "orders", 2)
        ]

    def test_unparseable_yaml_of_a_bound_model_does_not_break_resolution(self, tmp_path):
        yml = {**EMPTY_SCHEMA, "dim_customer.yml": "models: [unclosed\n"}
        adapter = _build(tmp_path, _customer_orders_nodes(), BOUND_ENTITIES, yml)

        assert [(r["source"], r["target"]) for r in adapter.infer_relationships()] == [
            ("customer", "orders")
        ]

    def test_single_model_yaml_without_name_is_ignored(self, tmp_path):
        yml = {**EMPTY_SCHEMA, "nameless.yml": "models:\n  - columns: []\n"}
        adapter = _build(tmp_path, _customer_orders_nodes(), BOUND_ENTITIES, yml)

        assert [(r["source"], r["target"]) for r in adapter.infer_relationships()] == [
            ("customer", "orders")
        ]
