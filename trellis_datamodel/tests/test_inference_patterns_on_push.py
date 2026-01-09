"""Tests for inference pattern application on push operations."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from trellis_datamodel.adapters.dbt_core import DbtCoreAdapter
from trellis_datamodel import config as cfg
from pathlib import Path


class TestInferencePatternsOnPush:
    """Test that inference patterns are applied when pushing entities to dbt."""

    @pytest.fixture(autouse=True)
    def setup_config(self):
        """Ensure dimensional modeling config is loaded."""
        cfg.DIMENSIONAL_MODELING_CONFIG.enabled = True
        cfg.DIMENSIONAL_MODELING_CONFIG.dimension_prefix = ["dim_", "d_"]
        cfg.DIMENSIONAL_MODELING_CONFIG.fact_prefix = ["fct_", "fact_"]
        yield
        cfg.DIMENSIONAL_MODELING_CONFIG.enabled = False

    def test_dimension_entity_gets_prefix(self, tmp_path):
        """Test that dimension entities get dim_ prefix when unbound."""
        adapter = DbtCoreAdapter(
            manifest_path=str(tmp_path / "manifest.json"),
            catalog_path=str(tmp_path / "catalog.json"),
            project_path=str(tmp_path),
            data_model_path=str(tmp_path / "data_model.yml"),
            model_paths=[str(tmp_path / "models")]
        )
        
        entity = {
            "id": "customer",
            "entity_type": "dimension",
        }
        
        model_name = adapter._entity_to_model_name(entity)
        
        assert model_name == "dim_customer", f"Expected 'dim_customer', got '{model_name}'"

    def test_fact_entity_gets_prefix(self, tmp_path):
        """Test that fact entities get fct_ prefix when unbound."""
        adapter = DbtCoreAdapter(
            manifest_path=str(tmp_path / "manifest.json"),
            catalog_path=str(tmp_path / "catalog.json"),
            project_path=str(tmp_path),
            data_model_path=str(tmp_path / "data_model.yml"),
            model_paths=[str(tmp_path / "models")]
        )
        
        entity = {
            "id": "orders",
            "entity_type": "fact",
        }
        
        model_name = adapter._entity_to_model_name(entity)
        
        assert model_name == "fct_orders", f"Expected 'fct_orders', got '{model_name}'"

    def test_unclassified_entity_no_prefix(self, tmp_path):
        """Test that unclassified entities don't get any prefix."""
        adapter = DbtCoreAdapter(
            manifest_path=str(tmp_path / "manifest.json"),
            catalog_path=str(tmp_path / "catalog.json"),
            project_path=str(tmp_path),
            data_model_path=str(tmp_path / "data_model.yml"),
            model_paths=[str(tmp_path / "models")]
        )
        
        entity = {
            "id": "raw_data",
            "entity_type": "unclassified",
        }
        
        model_name = adapter._entity_to_model_name(entity)
        
        assert model_name == "raw_data", f"Expected 'raw_data', got '{model_name}'"

    def test_bound_entity_prefix_not_changed(self, tmp_path):
        """Test that bound entities keep their original model name."""
        adapter = DbtCoreAdapter(
            manifest_path=str(tmp_path / "manifest.json"),
            catalog_path=str(tmp_path / "catalog.json"),
            project_path=str(tmp_path),
            data_model_path=str(tmp_path / "data_model.yml"),
            model_paths=[str(tmp_path / "models")]
        )
        
        entity = {
            "id": "customer",
            "entity_type": "dimension",
            "dbt_model": "model.myproject.dim_customer"
        }
        
        model_name = adapter._entity_to_model_name(entity)
        
        assert model_name == "dim_customer", f"Expected 'dim_customer', got '{model_name}'"

    def test_entity_with_existing_prefix_not_doubled(self, tmp_path):
        """Test that entities already having a prefix don't get it doubled."""
        adapter = DbtCoreAdapter(
            manifest_path=str(tmp_path / "manifest.json"),
            catalog_path=str(tmp_path / "catalog.json"),
            project_path=str(tmp_path),
            data_model_path=str(tmp_path / "data_model.yml"),
            model_paths=[str(tmp_path / "models")]
        )
        
        entity = {
            "id": "dim_customer",  # Already has prefix
            "entity_type": "dimension",
        }
        
        model_name = adapter._entity_to_model_name(entity)
        
        assert model_name == "dim_customer", f"Expected 'dim_customer', got '{model_name}'"

    def test_dimensional_modeling_disabled_no_prefix(self, tmp_path):
        """Test that when dimensional modeling is disabled, no prefix is applied."""
        cfg.DIMENSIONAL_MODELING_CONFIG.enabled = False
        
        adapter = DbtCoreAdapter(
            manifest_path=str(tmp_path / "manifest.json"),
            catalog_path=str(tmp_path / "catalog.json"),
            project_path=str(tmp_path),
            data_model_path=str(tmp_path / "data_model.yml"),
            model_paths=[str(tmp_path / "models")]
        )
        
        entity = {
            "id": "customer",
            "entity_type": "dimension",
        }
        
        model_name = adapter._entity_to_model_name(entity)
        
        assert model_name == "customer", f"Expected 'customer' (no prefix), got '{model_name}'"

    def test_custom_prefixes_from_config(self, tmp_path):
        """Test that custom prefixes from config are respected."""
        cfg.DIMENSIONAL_MODELING_CONFIG.dimension_prefix = ["d"]
        cfg.DIMENSIONAL_MODELING_CONFIG.fact_prefix = ["f"]
        
        adapter = DbtCoreAdapter(
            manifest_path=str(tmp_path / "manifest.json"),
            catalog_path=str(tmp_path / "catalog.json"),
            project_path=str(tmp_path),
            data_model_path=str(tmp_path / "data_model.yml"),
            model_paths=[str(tmp_path / "models")]
        )
        
        dimension_entity = {
            "id": "customer",
            "entity_type": "dimension",
        }
        fact_entity = {
            "id": "orders",
            "entity_type": "fact",
        }
        
        dim_model_name = adapter._entity_to_model_name(dimension_entity)
        fact_model_name = adapter._entity_to_model_name(fact_entity)
        
        assert dim_model_name == "dcustomer", f"Expected 'dcustomer', got '{dim_model_name}'"
        assert fact_model_name == "forders", f"Expected 'forders', got '{fact_model_name}'"

    def test_first_prefix_from_list_used(self, tmp_path):
        """Test that first prefix from the list is used."""
        cfg.DIMENSIONAL_MODELING_CONFIG.dimension_prefix = ["dim_", "d_"]
        cfg.DIMENSIONAL_MODELING_CONFIG.fact_prefix = ["fct_", "fact_"]
        
        adapter = DbtCoreAdapter(
            manifest_path=str(tmp_path / "manifest.json"),
            catalog_path=str(tmp_path / "catalog.json"),
            project_path=str(tmp_path),
            data_model_path=str(tmp_path / "data_model.yml"),
            model_paths=[str(tmp_path / "models")]
        )
        
        entity = {
            "id": "customer",
            "entity_type": "dimension",
        }
        
        model_name = adapter._entity_to_model_name(entity)
        
        assert model_name == "dim_customer", f"Expected 'dim_customer' (first prefix), got '{model_name}'"

    def test_case_insensitive_prefix_detection(self, tmp_path):
        """Test that prefix detection is case-insensitive."""
        adapter = DbtCoreAdapter(
            manifest_path=str(tmp_path / "manifest.json"),
            catalog_path=str(tmp_path / "catalog.json"),
            project_path=str(tmp_path),
            data_model_path=str(tmp_path / "data_model.yml"),
            model_paths=[str(tmp_path / "models")]
        )
        
        entity = {
            "id": "DIM_customer",  # Mixed case with prefix
            "entity_type": "dimension",
        }
        
        model_name = adapter._entity_to_model_name(entity)
        
        assert model_name == "DIM_customer", f"Expected 'DIM_customer' (unchanged), got '{model_name}'"

    def test_versioned_model_name_extraction(self, tmp_path):
        """Test that versioned model names are extracted correctly."""
        adapter = DbtCoreAdapter(
            manifest_path=str(tmp_path / "manifest.json"),
            catalog_path=str(tmp_path / "catalog.json"),
            project_path=str(tmp_path),
            data_model_path=str(tmp_path / "data_model.yml"),
            model_paths=[str(tmp_path / "models")]
        )
        
        entity = {
            "id": "customer",
            "entity_type": "dimension",
            "dbt_model": "model.myproject.dim_customer.v2"
        }
        
        model_name = adapter._entity_to_model_name(entity)
        
        assert model_name == "dim_customer", f"Expected 'dim_customer', got '{model_name}'"

