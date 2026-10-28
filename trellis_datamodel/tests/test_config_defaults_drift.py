"""The runtime config dataclasses and the pydantic ConfigSchema each carry
their own defaults for the same trellis.yml keys. These tests pin that the
two agree, so a default changed in one place cannot silently diverge (#178).
"""

from trellis_datamodel import config
from trellis_datamodel.models.schemas import ConfigSchema


def test_entity_creation_guidance_defaults_match():
    runtime = config.GuidanceConfig()
    schema = ConfigSchema().entity_creation_guidance

    assert runtime.entity_wizard_enabled == schema.enabled
    assert runtime.push_warning_enabled == schema.push_warning_enabled
    assert runtime.min_description_length == schema.min_description_length
    assert runtime.disabled_guidance == schema.disabled_guidance


def test_dimensional_modeling_prefix_defaults_match():
    runtime = config.DimensionalModelingConfig()
    schema = ConfigSchema()
    patterns = schema.dimensional_modeling or type(schema).model_fields[
        "dimensional_modeling"
    ].annotation.__args__[0]()

    assert runtime.dimension_prefix == patterns.inference_patterns.dimension_prefix
    assert runtime.fact_prefix == patterns.inference_patterns.fact_prefix


def test_entity_modeling_prefix_default_matches():
    runtime = config.EntityModelingConfig()
    schema = ConfigSchema()
    patterns = schema.entity_modeling or type(schema).model_fields[
        "entity_modeling"
    ].annotation.__args__[0]()

    assert runtime.entity_prefix == patterns.inference_patterns.prefix


def test_ossie_defaults_match():
    runtime = config.OssieConfig()
    schema = ConfigSchema().ossie

    assert runtime.enabled == schema.enabled
    assert runtime.file == schema.file
    assert runtime.database == schema.source.database
    assert runtime.schema == schema.source.schema_name


def test_metrics_defaults_match():
    runtime = config.MetricsConfig()
    schema = ConfigSchema().metrics

    assert runtime.enabled == schema.enabled
    assert runtime.file == schema.file
    assert runtime.expression_dialect == schema.expression_dialect


def test_config_ui_metadata_reports_the_runtime_wizard_default():
    from trellis_datamodel.services.config_service import _FIELD_DEFINITIONS

    ui_default = _FIELD_DEFINITIONS["entity_creation_guidance.enabled"].default

    assert ui_default == config.GuidanceConfig().entity_wizard_enabled


def test_config_ui_prefix_defaults_are_members_of_the_schema_defaults():
    """The config page edits one prefix as a string while the schema holds a
    list, so the UI default can't equal the schema default. It must at least
    be one of the prefixes the runtime actually applies."""
    from trellis_datamodel.models.schemas import (
        DimensionalInferencePatterns,
        EntityInferencePatterns,
    )
    from trellis_datamodel.services.config_service import _FIELD_DEFINITIONS

    dimensional = DimensionalInferencePatterns()
    key = "dimensional_modeling.inference_patterns"

    assert _FIELD_DEFINITIONS[f"{key}.dimension_prefix"].default in dimensional.dimension_prefix
    assert _FIELD_DEFINITIONS[f"{key}.fact_prefix"].default in dimensional.fact_prefix
    # An empty entity prefix list means "no prefix", shown as an empty string.
    entity_default = _FIELD_DEFINITIONS["entity_modeling.inference_patterns.prefix"].default
    assert EntityInferencePatterns().prefix == [] and entity_default == ""


def test_company_dummy_path_default_matches_the_ui():
    from trellis_datamodel.services.config_service import _FIELD_DEFINITIONS

    assert _FIELD_DEFINITIONS["dbt_company_dummy_path"].default == ConfigSchema().dbt_company_dummy_path
