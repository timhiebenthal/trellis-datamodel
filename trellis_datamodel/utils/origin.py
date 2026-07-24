"""Parse and stringify origin metadata for entity attributes."""

from __future__ import annotations

OriginEntry = dict[str, str]


def parse_origin(raw: object) -> list[OriginEntry]:
    if raw is None:
        return []
    if isinstance(raw, list):
        result: list[OriginEntry] = []
        for entry in raw:
            if isinstance(entry, dict):
                result.append({str(k): str(v) for k, v in entry.items()})
            elif isinstance(entry, str):
                result.extend(_parse_origin_string(entry))
        return result
    if isinstance(raw, str):
        return _parse_origin_string(raw)
    return []


def _parse_origin_string(value: str) -> list[OriginEntry]:
    stripped = value.strip()
    if not stripped:
        return []

    entries: list[OriginEntry] = []
    for part in stripped.split(" | "):
        segment = part.strip()
        if not segment:
            continue
        if ": " in segment:
            key, val = segment.split(": ", 1)
            entries.append({key: val})
        else:
            entries.append({"": segment})
    return entries


def stringify_origin(entries: list[OriginEntry]) -> str:
    parts: list[str] = []
    for entry in entries:
        if not entry:
            continue
        for key, value in entry.items():
            parts.append(f"{key}: {value}" if key else value)
    return " | ".join(parts)
