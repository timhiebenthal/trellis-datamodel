"""Single source of truth for decoding a column's origin.

A column's origin can reach us from three places:
  1. structured ``meta.origin`` (what push writes to schema.yml),
  2. an already-resolved ``origin`` key (e.g. a column from ``get_models()``),
  3. legacy text embedded in the description: ``"desc | Origin: value"`` or
     ``"Origin: value"``.

Everything that needs to read origin goes through this module so the
decoders cannot disagree.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from trellis_datamodel.utils.origin import OriginEntry, parse_origin

_ORIGIN_SEPARATOR = " | Origin: "
_ORIGIN_PREFIX = "Origin: "


def split_description_origin(
    raw_description: str | None,
) -> tuple[str | None, str | None]:
    """Split a description into (clean_description, embedded_origin_text).

    Legacy encoding of origin inside the description:
      - "desc | Origin: value"  (both present)
      - "Origin: value"         (only origin, no description)

    Descriptions without embedded origin are returned unchanged.
    """
    if not raw_description:
        return raw_description, None

    sep_idx = raw_description.find(_ORIGIN_SEPARATOR)
    if sep_idx != -1:
        desc = raw_description[:sep_idx]
        origin = raw_description[sep_idx + len(_ORIGIN_SEPARATOR) :]
        return (desc or None), (origin or None)

    if raw_description.startswith(_ORIGIN_PREFIX):
        origin = raw_description[len(_ORIGIN_PREFIX) :]
        return None, (origin or None)

    return raw_description, None


def _as_parseable(raw: object) -> object:
    """Frozen manifest snapshots hold tuples/mappings; make them list/dict."""
    if isinstance(raw, tuple):
        return [dict(e) if isinstance(e, Mapping) else e for e in raw]
    return raw


def resolve_column_metadata(
    col: Mapping[str, Any], description: str | None = None
) -> tuple[str | None, list[OriginEntry] | None]:
    """Return (clean_description, origin) for a column.

    ``description`` defaults to ``col["description"]``. Origin precedence:
    structured ``meta.origin`` -> already-resolved ``col["origin"]`` ->
    origin embedded in the description. Origin is the list format of
    ``utils/origin.py``, or None when no source carries one. The returned
    description never contains embedded origin text.
    """
    if description is None:
        description = col.get("description")
    clean_desc, embedded = split_description_origin(description)

    meta = col.get("meta") or {}
    origin = parse_origin(_as_parseable(meta.get("origin")))
    if not origin:
        origin = parse_origin(_as_parseable(col.get("origin")))
    if not origin and embedded:
        origin = parse_origin(embedded)
    return clean_desc, (origin or None)


def resolve_column_origin(col: Mapping[str, Any]) -> list[OriginEntry] | None:
    """Origin of a column from any source (see ``resolve_column_metadata``)."""
    return resolve_column_metadata(col)[1]
