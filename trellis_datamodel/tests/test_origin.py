"""Tests for origin parse/stringify utilities."""

import pytest

from trellis_datamodel.utils.origin import parse_origin, stringify_origin


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, []),
        ([], []),
        (
            "DH1: CORE.T_SALES.AMOUNT | DH2: CBUS.AMOUNT",
            [{"DH1": "CORE.T_SALES.AMOUNT"}, {"DH2": "CBUS.AMOUNT"}],
        ),
        ("DH1: CORE.A", [{"DH1": "CORE.A"}]),
        ("SAP.SALES_AMOUNT_DC", [{"": "SAP.SALES_AMOUNT_DC"}]),
        ([{"DH1": "CORE.A"}], [{"DH1": "CORE.A"}]),
        ("DH1: schema.table:col", [{"DH1": "schema.table:col"}]),
        ("   ", []),
    ],
)
def test_parse_origin(raw, expected):
    assert parse_origin(raw) == expected


@pytest.mark.parametrize(
    ("entries", "expected"),
    [
        (
            [{"DH1": "CORE.A"}, {"DH2": "CBUS.B"}],
            "DH1: CORE.A | DH2: CBUS.B",
        ),
        ([{"": "SAP.X"}], "SAP.X"),
        ([], ""),
    ],
)
def test_stringify_origin(entries, expected):
    assert stringify_origin(entries) == expected


def test_stringify_origin_round_trip():
    structured = [{"DH1": "CORE.A"}, {"DH2": "CBUS.B"}]
    assert parse_origin(stringify_origin(structured)) == structured
