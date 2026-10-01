import pytest

from trellis_datamodel.utils.column_metadata import (
    resolve_column_metadata,
    resolve_column_origin,
    split_description_origin,
)

META = [{"System": "CRM"}]
RESOLVED = [{"System": "ERP"}]


@pytest.mark.parametrize(
    "raw, expected",
    [
        (None, (None, None)),
        ("", ("", None)),
        ("plain", ("plain", None)),
        ("desc | Origin: A: B", ("desc", "A: B")),
        ("Origin: A: B", (None, "A: B")),
        ("desc | Origin: ", ("desc", None)),
        ("Origin: ", (None, None)),
        (" | Origin: A: B", (None, "A: B")),
    ],
)
def test_split_description_origin(raw, expected):
    assert split_description_origin(raw) == expected


def test_precedence_meta_over_resolved_over_description():
    col = {
        "meta": {"origin": META},
        "origin": RESOLVED,
        "description": "d | Origin: X: Y",
    }
    assert resolve_column_origin(col) == META
    del col["meta"]
    assert resolve_column_origin(col) == RESOLVED
    del col["origin"]
    assert resolve_column_origin(col) == [{"X": "Y"}]


def test_neither_present_returns_none():
    assert resolve_column_origin({"description": "plain"}) is None
    assert resolve_column_origin({}) is None


@pytest.mark.parametrize("empty", [None, [], "", {}])
def test_empty_values_fall_through(empty):
    col = {"meta": {"origin": empty}, "origin": empty, "description": "Origin: A: B"}
    assert resolve_column_origin(col) == [{"A": "B"}]
    assert resolve_column_origin({"meta": {"origin": empty}, "origin": empty}) is None


def test_meta_none_is_tolerated():
    assert resolve_column_origin({"meta": None, "origin": RESOLVED}) == RESOLVED


def test_tuple_origin_from_frozen_manifest():
    col = {"meta": {"origin": ({"System": "CRM"},)}}
    assert resolve_column_origin(col) == META


def test_string_origin_is_parsed():
    assert resolve_column_origin({"origin": "A: B | C: D"}) == [{"A": "B"}, {"C": "D"}]


def test_metadata_cleans_description_and_accepts_override():
    col = {"description": "ignored", "meta": {"origin": META}}
    assert resolve_column_metadata(col, "d | Origin: X: Y") == ("d", META)
    assert resolve_column_metadata({"description": "d | Origin: X: Y"}) == (
        "d",
        [{"X": "Y"}],
    )
