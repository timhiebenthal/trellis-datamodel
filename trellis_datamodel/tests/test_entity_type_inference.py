"""Tests for entity type inference logic."""

import json
import os
import pytest
from trellis_datamodel.adapters.dbt_core import DbtCoreAdapter
from trellis_datamodel import config as cfg
from trellis_datamodel.routes.data_model import _infer_type_from_name, _apply_entity_type_inference


class TestEntityTypeInference:
    """Test entity type inference based on model naming patterns."""

    @pytest.fixture(autouse=True)
    def setup_config(self):
        """Set up dimensional modeling config for tests."""
        # Save original config
        original_enabled = cfg.DIMENSIONAL_MODELING_CONFIG.enabled
        original_dim_prefix = cfg.DIMENSIONAL_MODELING_CONFIG.dimension_prefix
        original_fact_prefix = cfg.DIMENSIONAL_MODELING_CONFIG.fact_prefix

        # Enable dimensional modeling with standard prefixes
        cfg.DIMENSIONAL_MODELING_CONFIG.enabled = True
        cfg.DIMENSIONAL_MODELING_CONFIG.dimension_prefix = ["dim_", "d_"]
        cfg.DIMENSIONAL_MODELING_CONFIG.fact_prefix = ["fct_", "fact_"]

        yield

        # Restore original config
        cfg.DIMENSIONAL_MODELING_CONFIG.enabled = original_enabled
        cfg.DIMENSIONAL_MODELING_CONFIG.dimension_prefix = original_dim_prefix
        cfg.DIMENSIONAL_MODELING_CONFIG.fact_prefix = original_fact_prefix
        # Clear inference cache after tests
        DbtCoreAdapter.reset_inference_cache()

    def _create_manifest_with_models(self, tmp_path, model_names):
        """Helper to create a manifest.json with the given model names."""
        manifest = {
            "nodes": {
                f"model.test.{name}": {
                    "resource_type": "model",
                    "name": name,
                    "unique_id": f"model.test.{name}",
                    "schema": "public",
                    "alias": name,
                    "columns": {},
                }
                for name in model_names
            }
        }

        manifest_path = tmp_path / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)

        return str(manifest_path)

    def test_dimension_prefix(self, tmp_path):
        """Test dimension inference with dim_ prefix."""
        manifest_path = self._create_manifest_with_models(
            tmp_path, ["dim_customer", "dim_product"]
        )

        adapter = DbtCoreAdapter(
            manifest_path=manifest_path,
            catalog_path=str(tmp_path / "catalog.json"),
            project_path=str(tmp_path),
            data_model_path=str(tmp_path / "data_model.yml"),
            model_paths=[]
        )

        entity_types = adapter.infer_entity_types()

        assert entity_types["dim_customer"] == "dimension"
        assert entity_types["dim_product"] == "dimension"

    def test_dimension_short_prefix(self, tmp_path):
        """Test dimension inference with d_ prefix."""
        manifest_path = self._create_manifest_with_models(
            tmp_path, ["d_customer", "d_product"]
        )

        adapter = DbtCoreAdapter(
            manifest_path=manifest_path,
            catalog_path=str(tmp_path / "catalog.json"),
            project_path=str(tmp_path),
            data_model_path=str(tmp_path / "data_model.yml"),
            model_paths=[]
        )

        entity_types = adapter.infer_entity_types()

        assert entity_types["d_customer"] == "dimension"
        assert entity_types["d_product"] == "dimension"

    def test_fact_prefix(self, tmp_path):
        """Test fact inference with fct_ prefix."""
        manifest_path = self._create_manifest_with_models(
            tmp_path, ["fct_orders", "fct_sales"]
        )

        adapter = DbtCoreAdapter(
            manifest_path=manifest_path,
            catalog_path=str(tmp_path / "catalog.json"),
            project_path=str(tmp_path),
            data_model_path=str(tmp_path / "data_model.yml"),
            model_paths=[]
        )

        entity_types = adapter.infer_entity_types()

        assert entity_types["fct_orders"] == "fact"
        assert entity_types["fct_sales"] == "fact"

    def test_fact_full_word(self, tmp_path):
        """Test fact inference with fact_ prefix."""
        cfg.DIMENSIONAL_MODELING_CONFIG.fact_prefix = ["fact_", "fct_"]

        manifest_path = self._create_manifest_with_models(
            tmp_path, ["fact_orders", "fact_sales"]
        )

        adapter = DbtCoreAdapter(
            manifest_path=manifest_path,
            catalog_path=str(tmp_path / "catalog.json"),
            project_path=str(tmp_path),
            data_model_path=str(tmp_path / "data_model.yml"),
            model_paths=[]
        )

        entity_types = adapter.infer_entity_types()

        assert entity_types["fact_orders"] == "fact"
        assert entity_types["fact_sales"] == "fact"

    def test_case_insensitive(self, tmp_path):
        """Test case-insensitive pattern matching."""
        manifest_path = self._create_manifest_with_models(
            tmp_path, ["Dim_Customer", "FCT_ORDERS", "D_Product"]
        )

        adapter = DbtCoreAdapter(
            manifest_path=manifest_path,
            catalog_path=str(tmp_path / "catalog.json"),
            project_path=str(tmp_path),
            data_model_path=str(tmp_path / "data_model.yml"),
            model_paths=[]
        )

        entity_types = adapter.infer_entity_types()

        assert entity_types["Dim_Customer"] == "dimension"
        assert entity_types["FCT_ORDERS"] == "fact"
        assert entity_types["D_Product"] == "dimension"

    def test_multiple_prefixes(self, tmp_path):
        """Test multiple prefixes per entity type."""
        # Set up multiple prefixes
        cfg.DIMENSIONAL_MODELING_CONFIG.dimension_prefix = ["dim_", "d_", "dimension_"]
        cfg.DIMENSIONAL_MODELING_CONFIG.fact_prefix = ["fct_", "fact_", "f_"]

        manifest_path = self._create_manifest_with_models(
            tmp_path, ["dim_customer", "d_product", "dimension_location", "fct_orders", "fact_sales", "f_revenue"]
        )

        adapter = DbtCoreAdapter(
            manifest_path=manifest_path,
            catalog_path=str(tmp_path / "catalog.json"),
            project_path=str(tmp_path),
            data_model_path=str(tmp_path / "data_model.yml"),
            model_paths=[]
        )

        entity_types = adapter.infer_entity_types()

        # All dimension prefixes should work
        assert entity_types["dim_customer"] == "dimension"
        assert entity_types["d_product"] == "dimension"
        assert entity_types["dimension_location"] == "dimension"

        # All fact prefixes should work
        assert entity_types["fct_orders"] == "fact"
        assert entity_types["fact_sales"] == "fact"
        assert entity_types["f_revenue"] == "fact"

    def test_no_match_returns_unclassified(self, tmp_path):
        """Test unclassified for non-matching names."""
        manifest_path = self._create_manifest_with_models(
            tmp_path, ["orders", "customers", "raw_data", "staging_users"]
        )

        adapter = DbtCoreAdapter(
            manifest_path=manifest_path,
            catalog_path=str(tmp_path / "catalog.json"),
            project_path=str(tmp_path),
            data_model_path=str(tmp_path / "data_model.yml"),
            model_paths=[]
        )

        entity_types = adapter.infer_entity_types()

        assert entity_types["orders"] == "unclassified"
        assert entity_types["customers"] == "unclassified"
        assert entity_types["raw_data"] == "unclassified"
        assert entity_types["staging_users"] == "unclassified"

    def test_empty_manifest(self, tmp_path):
        """Test behavior with empty manifest."""
        manifest_path = self._create_manifest_with_models(tmp_path, [])

        adapter = DbtCoreAdapter(
            manifest_path=manifest_path,
            catalog_path=str(tmp_path / "catalog.json"),
            project_path=str(tmp_path),
            data_model_path=str(tmp_path / "data_model.yml"),
            model_paths=[]
        )

        entity_types = adapter.infer_entity_types()

        assert entity_types == {}

    def test_only_runs_when_dimensional_modeling_enabled(self, tmp_path):
        """Test inference only runs when dimensional modeling is enabled."""
        # Disable dimensional modeling
        cfg.DIMENSIONAL_MODELING_CONFIG.enabled = False

        manifest_path = self._create_manifest_with_models(
            tmp_path, ["dim_customer", "fct_orders"]
        )

        adapter = DbtCoreAdapter(
            manifest_path=manifest_path,
            catalog_path=str(tmp_path / "catalog.json"),
            project_path=str(tmp_path),
            data_model_path=str(tmp_path / "data_model.yml"),
            model_paths=[]
        )

        entity_types = adapter.infer_entity_types()

        # Should return empty dict when disabled
        assert entity_types == {}

    def test_dimension_prefix_takes_precedence(self, tmp_path):
        """Test dimension prefixes checked before fact prefixes."""
        # Create a model that could match both (if we had overlapping prefixes)
        # In practice, dim_ is checked before fct_, so dim_test should be dimension
        manifest_path = self._create_manifest_with_models(
            tmp_path, ["dim_test", "d_test"]
        )

        adapter = DbtCoreAdapter(
            manifest_path=manifest_path,
            catalog_path=str(tmp_path / "catalog.json"),
            project_path=str(tmp_path),
            data_model_path=str(tmp_path / "data_model.yml"),
            model_paths=[]
        )

        entity_types = adapter.infer_entity_types()

        # Should be classified as dimension, not fact
        assert entity_types["dim_test"] == "dimension"
        assert entity_types["d_test"] == "dimension"

    def test_mixed_entity_types(self, tmp_path):
        """Test that mixed entity types are all classified correctly."""
        manifest_path = self._create_manifest_with_models(
            tmp_path, [
                "dim_customer",
                "fct_orders",
                "staging_data",
                "d_product",
                "fact_sales",
                "raw_users"
            ]
        )

        # Add fact_ to prefixes
        cfg.DIMENSIONAL_MODELING_CONFIG.fact_prefix = ["fct_", "fact_"]

        adapter = DbtCoreAdapter(
            manifest_path=manifest_path,
            catalog_path=str(tmp_path / "catalog.json"),
            project_path=str(tmp_path),
            data_model_path=str(tmp_path / "data_model.yml"),
            model_paths=[]
        )

        entity_types = adapter.infer_entity_types()

        assert entity_types["dim_customer"] == "dimension"
        assert entity_types["d_product"] == "dimension"
        assert entity_types["fct_orders"] == "fact"
        assert entity_types["fact_sales"] == "fact"
        assert entity_types["staging_data"] == "unclassified"
        assert entity_types["raw_users"] == "unclassified"


class TestInferTypeFromName:
    """Unit tests for the _infer_type_from_name helper."""

    DIM_PREFIXES = ["dim_", "d_"]
    FACT_PREFIXES = ["fct_", "fact_"]

    def test_dim_prefix_returns_dimension(self):
        assert _infer_type_from_name("dim_customer", self.DIM_PREFIXES, self.FACT_PREFIXES) == "dimension"

    def test_d_prefix_returns_dimension(self):
        assert _infer_type_from_name("d_product", self.DIM_PREFIXES, self.FACT_PREFIXES) == "dimension"

    def test_fct_prefix_returns_fact(self):
        assert _infer_type_from_name("fct_orders", self.DIM_PREFIXES, self.FACT_PREFIXES) == "fact"

    def test_fact_prefix_returns_fact(self):
        assert _infer_type_from_name("fact_revenue", self.DIM_PREFIXES, self.FACT_PREFIXES) == "fact"

    def test_case_insensitive(self):
        assert _infer_type_from_name("DIM_Customer", self.DIM_PREFIXES, self.FACT_PREFIXES) == "dimension"
        assert _infer_type_from_name("FCT_Orders", self.DIM_PREFIXES, self.FACT_PREFIXES) == "fact"

    def test_no_match_returns_none(self):
        assert _infer_type_from_name("staging_data", self.DIM_PREFIXES, self.FACT_PREFIXES) is None
        assert _infer_type_from_name("raw_users", self.DIM_PREFIXES, self.FACT_PREFIXES) is None

    def test_double_underscore_id_matches(self):
        """Entity IDs like dim__account (generated with double underscore) still match dim_ prefix."""
        assert _infer_type_from_name("dim__account", self.DIM_PREFIXES, self.FACT_PREFIXES) == "dimension"


class TestApplyEntityTypeInferenceUnbound:
    """Tests for the unbound-entity ID-prefix fallback in _apply_entity_type_inference."""

    @pytest.fixture(autouse=True)
    def setup_config(self):
        original_enabled = cfg.DIMENSIONAL_MODELING_CONFIG.enabled
        original_dim = cfg.DIMENSIONAL_MODELING_CONFIG.dimension_prefix
        original_fact = cfg.DIMENSIONAL_MODELING_CONFIG.fact_prefix
        cfg.DIMENSIONAL_MODELING_CONFIG.enabled = True
        cfg.DIMENSIONAL_MODELING_CONFIG.dimension_prefix = ["dim_", "d_"]
        cfg.DIMENSIONAL_MODELING_CONFIG.fact_prefix = ["fct_", "fact_"]
        yield
        cfg.DIMENSIONAL_MODELING_CONFIG.enabled = original_enabled
        cfg.DIMENSIONAL_MODELING_CONFIG.dimension_prefix = original_dim
        cfg.DIMENSIONAL_MODELING_CONFIG.fact_prefix = original_fact
        DbtCoreAdapter.reset_inference_cache()

    def _make_model_data(self, entities):
        return {"entities": entities, "relationships": []}

    def _mock_adapter(self, inferred_types):
        from unittest.mock import MagicMock, patch
        adapter = MagicMock()
        adapter.infer_entity_types.return_value = inferred_types
        return patch("trellis_datamodel.routes.data_model.get_adapter", return_value=adapter)

    def test_unbound_dim_entity_inferred_as_dimension(self):
        """Unbound entity whose ID starts with dim_ is inferred as dimension."""
        with self._mock_adapter({}):
            model_data = self._make_model_data([
                {"id": "dim__account", "label": "Account", "entity_type": "unclassified"},
            ])
            result = _apply_entity_type_inference(model_data)
        assert result["entities"][0]["entity_type"] == "dimension"

    def test_unbound_fact_entity_inferred_as_fact(self):
        """Unbound entity whose ID starts with fct_ is inferred as fact."""
        with self._mock_adapter({}):
            model_data = self._make_model_data([
                {"id": "fct_transactions", "label": "Transactions"},
            ])
            result = _apply_entity_type_inference(model_data)
        assert result["entities"][0]["entity_type"] == "fact"

    def test_manually_set_type_not_overridden(self):
        """A manually saved entity_type is never overwritten by inference."""
        with self._mock_adapter({}):
            model_data = self._make_model_data([
                {"id": "dim__account", "label": "Account", "entity_type": "fact"},
            ])
            result = _apply_entity_type_inference(model_data)
        assert result["entities"][0]["entity_type"] == "fact"

    def test_no_prefix_match_stays_unclassified(self):
        """Unbound entity with a random/timestamp ID stays unclassified."""
        with self._mock_adapter({}):
            model_data = self._make_model_data([
                {"id": "1684123456789", "label": "New Entity"},
            ])
            result = _apply_entity_type_inference(model_data)
        assert result["entities"][0].get("entity_type") is None

    def test_manifest_inference_takes_precedence(self):
        """Bound entity classified via manifest is not re-evaluated by ID fallback."""
        with self._mock_adapter({"dim_customer": "dimension"}):
            model_data = self._make_model_data([
                {"id": "dim_customer", "label": "Customer", "entity_type": "unclassified"},
            ])
            result = _apply_entity_type_inference(model_data)
        assert result["entities"][0]["entity_type"] == "dimension"
