from trellis_datamodel.models.entity_keys import (
    get_model_ref, set_model_ref, get_framework_tags, set_framework_tags, has_legacy_keys,
    get_native_data_type, set_native_data_type,
)

def test_get_model_ref_reads_new_key():
    assert get_model_ref({"model_ref": "model.x.y"}) == "model.x.y"

def test_get_model_ref_reads_legacy_dbt_model_key():
    assert get_model_ref({"dbt_model": "model.x.y"}) == "model.x.y"

def test_get_model_ref_prefers_new_key_even_when_new_key_is_none():
    assert get_model_ref({"model_ref": None, "dbt_model": "stale"}) is None

def test_get_model_ref_none_when_unbound():
    assert get_model_ref({}) is None

def test_set_model_ref_writes_only_new_key_and_drops_legacy():
    entity = {"dbt_model": "old", "label": "keep me"}
    set_model_ref(entity, "model.x.y")
    assert entity == {"model_ref": "model.x.y", "label": "keep me"}

def test_set_model_ref_none_clears_both_keys():
    entity = {"dbt_model": "old", "model_ref": "newer"}
    set_model_ref(entity, None)
    assert entity == {}

def test_get_framework_tags_reads_new_key():
    assert get_framework_tags({"framework_tags": ["a"]}) == ["a"]

def test_get_framework_tags_reads_legacy_dbt_tags_key():
    assert get_framework_tags({"dbt_tags": ["a"]}) == ["a"]

def test_get_framework_tags_prefers_new_key_even_when_empty():
    assert get_framework_tags({"framework_tags": [], "dbt_tags": ["stale"]}) == []

def test_get_framework_tags_returns_new_list_not_alias():
    source = ["a"]
    result = get_framework_tags({"framework_tags": source})
    result.append("b")
    assert source == ["a"]

def test_set_framework_tags_writes_only_new_key_and_drops_legacy():
    entity = {"dbt_tags": ["old"]}
    set_framework_tags(entity, ["a", "b"])
    assert entity == {"framework_tags": ["a", "b"]}

def test_has_legacy_keys_detects_migration_need():
    assert has_legacy_keys({"dbt_model": "x"}) is True
    assert has_legacy_keys({"model_ref": "x"}) is False

def test_get_native_data_type_reads_new_key():
    assert get_native_data_type({"native_data_type": "varchar"}) == "varchar"

def test_get_native_data_type_reads_legacy_dbt_data_type_key():
    assert get_native_data_type({"dbt_data_type": "varchar"}) == "varchar"

def test_get_native_data_type_prefers_new_key_even_when_new_key_is_none():
    assert get_native_data_type({"native_data_type": None, "dbt_data_type": "stale"}) is None

def test_get_native_data_type_none_when_absent():
    assert get_native_data_type({}) is None

def test_set_native_data_type_writes_only_new_key_and_drops_legacy():
    field = {"dbt_data_type": "old", "name": "keep me"}
    set_native_data_type(field, "varchar")
    assert field == {"native_data_type": "varchar", "name": "keep me"}

def test_set_native_data_type_none_clears_both_keys():
    field = {"dbt_data_type": "old", "native_data_type": "newer"}
    set_native_data_type(field, None)
    assert field == {}
