"""One SQL type vocabulary feeds both reconciliation and the Ossie exporter."""

import pytest

from trellis_datamodel.services.ossie import _ossie_datatype
from trellis_datamodel.services.reconciliation import _map_column_type
from trellis_datamodel.utils.sql_types import (
    classify_sql_type,
    ossie_type_for_bucket,
    split_column_type,
)


def test_split_column_type():
    assert split_column_type("NUMBER(38,0)") == ("number", ["38", "0"])
    assert split_column_type(" VARCHAR(16777216) ") == ("varchar", ["16777216"])
    assert split_column_type("TIMESTAMP_NTZ") == ("timestamp_ntz", [])


@pytest.mark.parametrize(
    "raw, bucket, ossie",
    [
        # Families that used to be known to reconciliation only (#163)
        ("uuid", "text", "String"),
        ("nvarchar(40)", "text", "String"),
        ("tinyint", "int", "Integer"),
        ("serial", "int", "Integer"),
        ("bigserial", "int", "Integer"),
        ("money", "float", "Decimal"),
        ("bignumeric", "float", "Decimal"),
        # Known to both
        ("varchar(50)", "text", "String"),
        ("BIGINT", "int", "Integer"),
        ("TIMESTAMP_NTZ(9)", "timestamp", "DateTime"),
        ("timestamptz", "timestamp", "DateTimeTz"),
        ("boolean", "bool", "Boolean"),
        ("date", "date", "Date"),
        ("FLOAT64", "float", "Float"),
        # Scale decides the Trellis bucket, never the Ossie type
        ("NUMBER(38,0)", "int", "Decimal"),
        ("NUMBER(10,2)", "float", "Decimal"),
        ("numeric", "float", "Decimal"),
        # Known to Ossie only: no Trellis bucket for a time of day
        ("time", "unknown", "Time"),
        # No portable equivalent: must not fall into the "int" prefix
        ("interval", "unknown", None),
    ],
)
def test_one_vocabulary_projects_to_both_consumers(raw, bucket, ossie):
    assert _map_column_type(raw) == bucket
    assert _ossie_datatype(raw) == ossie


@pytest.mark.parametrize("raw", ["VARIANT", "ARRAY", "int[]", "struct<a int>", "", None])
def test_unrecognised_types_are_not_guessed(raw):
    assert classify_sql_type(raw) is None
    assert _map_column_type(raw) == "unknown"
    assert _ossie_datatype(raw) is None


def test_bucket_projection_omits_unknown():
    assert ossie_type_for_bucket("TEXT") == "String"
    assert ossie_type_for_bucket("unknown") is None
    assert ossie_type_for_bucket(None) is None
