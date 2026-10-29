"""One SQL type vocabulary shared by reconciliation and the Ossie exporter.

A warehouse type is normalised once (`split_column_type`) and matched against a
single table of families (`_FAMILIES`). Each family carries both projections,
the Trellis bucket stored in `data_model.yml` and the portable Ossie type, so a
new warehouse type is one edit here and the two consumers cannot disagree about
what it is.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SqlType:
    """What a recognised warehouse type means to each consumer."""

    bucket: str  # Trellis DraftedField datatype: text/int/float/bool/date/timestamp/unknown
    ossie: str | None  # Ossie DataType, or None when no portable equivalent exists


@dataclass(frozen=True)
class _Family:
    type: SqlType
    names: tuple[str, ...] = ()  # matched exactly
    prefixes: tuple[str, ...] = ()  # matched as a prefix of the base name
    scale_zero_bucket: str | None = None  # bucket override when declared scale is 0


# Order matters: the first family that matches wins, so specific families sit
# before the broader prefix families they would otherwise fall into.
_FAMILIES: tuple[_Family, ...] = (
    # Fixed-point. A scale of 0 is an integer bucket (Snowflake's NUMBER(38,0)),
    # anything else, including an unparameterized NUMBER whose scale the catalog
    # does not report, is float, the wider of the two. Ossie has one Decimal.
    _Family(
        SqlType("float", "Decimal"),
        names=("number", "numeric", "decimal", "dec", "bignumeric"),
        scale_zero_bucket="int",
    ),
    _Family(SqlType("float", "Decimal"), names=("money",)),
    _Family(SqlType("date", "Date"), names=("date",)),
    # Reconciliation has no bucket for a bare time-of-day.
    _Family(SqlType("unknown", "Time"), names=("time",)),
    _Family(
        SqlType("timestamp", "DateTimeTz"),
        prefixes=("timestamp_tz", "timestamptz", "timestamp_ltz"),
    ),
    _Family(SqlType("timestamp", "DateTime"), prefixes=("timestamp", "datetime")),
    _Family(SqlType("bool", "Boolean"), prefixes=("bool",)),
    # Must precede the integer prefixes, which would claim it through "int".
    _Family(SqlType("unknown", None), prefixes=("interval",)),
    _Family(
        SqlType("int", "Integer"),
        prefixes=(
            "int",
            "bigint",
            "smallint",
            "tinyint",
            "byteint",
            "serial",
            "bigserial",
            "smallserial",
            "integer",
        ),
    ),
    _Family(SqlType("float", "Float"), prefixes=("float", "double", "real")),
    _Family(
        SqlType("text", "String"),
        prefixes=(
            "varchar",
            "char",
            "text",
            "string",
            "nvarchar",
            "nchar",
            "clob",
            "uuid",
        ),
    ),
)

# Trellis buckets, for drafted fields without a usable physical type. `unknown`
# is intentionally absent: no portable type is better than a guessed one.
_BUCKET_OSSIE: dict[str, str] = {
    "text": "String",
    "int": "Integer",
    "float": "Float",
    "bool": "Boolean",
    "date": "Date",
    "timestamp": "DateTime",
}


def split_column_type(column_type: str) -> tuple[str, list[str]]:
    """Split a raw warehouse type into its lowercase base name and parameters.

    "NUMBER(38,0)" -> ("number", ["38", "0"])
    "VARCHAR(16777216)" -> ("varchar", ["16777216"])
    "TIMESTAMP_NTZ" -> ("timestamp_ntz", [])

    Collection wrappers (ARRAY, STRUCT<...>, "int[]") are deliberately left
    intact so they fall through to unrecognised rather than being flattened to
    the bucket of their element type.
    """
    t = column_type.lower().strip()
    open_paren = t.find("(")
    if open_paren == -1:
        return t, []
    base = t[:open_paren].strip()
    inner = t[open_paren + 1 :].rstrip().removesuffix(")")
    return base, [arg.strip() for arg in inner.split(",") if arg.strip()]


def classify_sql_type(column_type: str | None) -> SqlType | None:
    """Resolve a raw warehouse type, or None when it is not in the vocabulary."""
    if not column_type:
        return None
    base, args = split_column_type(column_type)
    if base.endswith("[]") or base.startswith(("array", "struct", "map")) or "<" in base:
        # Collection / nested types have no scalar equivalent.
        return None
    for family in _FAMILIES:
        if base in family.names or base.startswith(family.prefixes):
            if family.scale_zero_bucket and len(args) >= 2 and args[1] == "0":
                return SqlType(family.scale_zero_bucket, family.type.ossie)
            return family.type
    return None


def ossie_type_for_bucket(bucket: str | None) -> str | None:
    """Portable type for a Trellis bucket, e.g. "text" -> "String"."""
    return _BUCKET_OSSIE.get((bucket or "").strip().lower())
