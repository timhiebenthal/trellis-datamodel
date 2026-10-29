"""Backend responses must match the TypeScript types the frontend declares.

``/config-status`` and ``/config-info`` serialize their response models with
``exclude_unset``, so the keys on the wire depend on the project; ``ConfigStatus``
and ``ConfigInfo`` in ``frontend/src/lib/types.ts`` are the frontend's side of
those contracts. This parses the interfaces from ``types.ts`` and compares
their keys with real responses: every required key must be present and no key
may be undeclared.
"""

import re
from pathlib import Path

import pytest

import trellis_datamodel.config as cfg
from trellis_datamodel.models.business_event import (
    AnnotationEntry,
    BusinessEvent,
    BusinessEventAnnotations,
)

TYPES_TS = Path(__file__).parents[2] / "frontend" / "src" / "lib" / "types.ts"

_INTERFACE = re.compile(r"export interface (\w+)(?:\s+extends\s+(\w+))?\s*\{")
_KEY = re.compile(r"^\s*(\w+)(\?)?\s*:")
_COMMENT = re.compile(r"/\*.*?\*/|//[^\n]*", re.DOTALL)


def _interface_keys(name: str) -> tuple[set[str], set[str]]:
    """Return (required, optional) top-level keys of ``export interface name``."""
    source = _COMMENT.sub("", TYPES_TS.read_text())
    match = next(m for m in _INTERFACE.finditer(source) if m[1] == name)
    required: set[str] = set()
    optional: set[str] = set()
    if match[2]:
        required, optional = _interface_keys(match[2])
    depth = 1
    line = ""
    for char in source[match.end() :]:
        if char == "\n":
            key = _KEY.match(line) if depth == 1 else None
            if key:
                (optional if key[2] else required).add(key[1])
            line = ""
            continue
        if depth == 1:
            line += char
        depth += (char == "{") - (char == "}")
        if depth == 0:
            break
    return required, optional


def _assert_matches(body: dict, interface: str) -> None:
    required, optional = _interface_keys(interface)
    keys = set(body)
    assert not required - keys, f"{interface}: missing from response: {required - keys}"
    assert not keys - required - optional, (
        f"{interface}: response keys undeclared in types.ts: {keys - required - optional}"
    )


def test_parser_finds_interface_keys():
    """Guard the guard: a parser that finds nothing would pass vacuously."""
    required, optional = _interface_keys("ConfigStatus")
    assert {"framework", "capabilities", "data_model_exists"} <= required
    assert {"error", "manifest_path"} <= optional
    required, optional = _interface_keys("ConfigInfo")
    assert {"data_model_path", "model_paths_resolved"} <= required
    assert "start_page" in optional
    # Nested object keys must not leak into the parent.
    assert "dataset" not in _interface_keys("MetricEntry")[1]
    # Inherited keys are included.
    assert {"catalog", "metrics", "influences"} <= _interface_keys("MetricTreeResponse")[0]


@pytest.mark.parametrize(
    "path, interface",
    [
        ("/api/config-status", "ConfigStatus"),
        ("/api/config-info", "ConfigInfo"),
    ],
)
def test_response_keys_match_types_ts(test_client, path, interface):
    response = test_client.get(path)
    assert response.status_code == 200
    _assert_matches(response.json(), interface)


def test_capabilities_and_artifacts_match_types_ts(test_client):
    body = test_client.get("/api/config-info").json()
    _assert_matches(body["capabilities"], "FrameworkCapabilities")
    for artifact in body["artifacts"].values():
        _assert_matches(artifact, "FrameworkArtifact")


def test_metric_tree_matches_types_ts(test_client, monkeypatch, tmp_path):
    monkeypatch.setattr(
        cfg,
        "METRICS_CONFIG",
        cfg.MetricsConfig(enabled=True, file=str(tmp_path / "metric_tree.yml")),
    )
    draft = {
        "id": "revenue",
        "label": "Revenue",
        "description": "Booked revenue.",
        "expression": "sum(amount) from fct__order",
        "dataset_ref": "fct__order",
    }
    payload = {"version": 0.1, "metrics": [draft], "influences": []}
    assert test_client.post("/api/metric-tree", json=payload).status_code == 200

    body = test_client.get("/api/metric-tree").json()
    _assert_matches(body, "MetricTreeResponse")
    for metric in body["metrics"]:
        _assert_matches(metric, "MetricEntry")


@pytest.mark.parametrize(
    "model, interface",
    [
        (AnnotationEntry, "AnnotationEntry"),
        (BusinessEvent, "BusinessEvent"),
        (BusinessEventAnnotations, "BusinessEventAnnotations"),
    ],
)
def test_business_event_models_match_types_ts(model, interface):
    """These endpoints serialize their pydantic models as-is, so compare fields."""
    _assert_matches(dict.fromkeys(model.model_fields), interface)
