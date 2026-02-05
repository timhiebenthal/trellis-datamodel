"""Tests for entity type inference logic."""

import json
import os
import pytest
from trellis_datamodel.adapters.dbt_core import DbtCoreAdapter
from trellis_datamodel import config as cfg


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
