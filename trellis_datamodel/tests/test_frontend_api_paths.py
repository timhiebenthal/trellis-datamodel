"""Every endpoint ``frontend/src/lib/api.ts`` calls must exist on the backend.

The frontend once called ``/business-events/{id}/seven-entries`` while the
backend only exposed ``/annotations``; the frontend unit tests mock ``fetch``,
so nothing noticed. This compares the (method, path) pairs found in ``api.ts``
with the routes in the FastAPI OpenAPI schema.
"""

import re
from pathlib import Path

API_TS = Path(__file__).parents[2] / "frontend" / "src" / "lib" / "api.ts"

# `${API_BASE}` followed by path segments; a `${...}` only counts as a path
# parameter when it is a whole segment, so `bus-matrix${queryString}` stops at
# `bus-matrix`.
_CALL = re.compile(r"\$\{API_BASE\}((?:/[\w-]+|/\$\{[^}]+\})*)")
_METHOD = re.compile(r"method:\s*'(\w+)'")
_PARAM = re.compile(r"\$\{[^}]+\}|\{[^}]+\}")
# Lines after the URL in which the request options (and `method`) may appear.
_OPTIONS_WINDOW = 4


def _normalize(path: str) -> str:
    return _PARAM.sub("{}", path)


def _frontend_calls() -> set[tuple[str, str]]:
    lines = API_TS.read_text().splitlines()
    calls = set()
    for i, line in enumerate(lines):
        for match in _CALL.finditer(line):
            window = "\n".join(lines[i : i + _OPTIONS_WINDOW])
            method = _METHOD.search(window)
            calls.add(
                (method.group(1).upper() if method else "GET", _normalize(match[1]))
            )
    return calls


def _backend_routes() -> set[tuple[str, str]]:
    from trellis_datamodel.server import app

    http = {"get", "post", "put", "patch", "delete"}
    return {
        (method.upper(), _normalize(path.removeprefix("/api")))
        for path, ops in app.openapi()["paths"].items()
        for method in ops
        if method in http
    }


def test_extractor_finds_calls():
    """Guard the guard: a regex that matches nothing would pass vacuously."""
    calls = _frontend_calls()
    assert ("GET", "/data-model") in calls
    assert ("POST", "/models/{}/schema") in calls
    assert ("GET", "/bus-matrix") in calls
    assert len(calls) >= 25


def test_every_frontend_call_has_a_backend_route(test_client):
    missing = sorted(_frontend_calls() - _backend_routes())
    assert not missing, (
        "api.ts calls endpoints the backend does not expose: "
        + ", ".join(f"{m} {p}" for m, p in missing)
    )
