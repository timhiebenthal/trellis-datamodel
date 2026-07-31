def test_entity_typeddict_uses_generic_model_ref():
    from trellis_datamodel.adapters.base import Entity

    hints = Entity.__annotations__
    assert "model_ref" in hints
    assert "dbt_model" not in hints
