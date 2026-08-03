"""
The last strict-xfail contract pinning work deferred to the BruinAdapter spec.

The four adapter-surface gaps this file used to hold (get_lineage,
get_exposures, get_source_systems_for_model, get_project_status) are now
declared on TransformationAdapter and live-tested in
test_adapter_protocol_surface.py.

What remains is the end state those methods exist to enable: services and
routes must obtain framework data through the adapter rather than reading
manifest.json / catalog.json off disk themselves. Declaring the methods was
the first half; rewiring the callers is the second. Marked `strict=True` so
the moment the rewiring lands, this turns into a hard failure and has to be
deleted deliberately.
"""

import re
from pathlib import Path

import pytest

FUTURE_REASON = (
    "Deferred to the BruinAdapter spec: routes and services still read dbt "
    "artifacts directly instead of going through TransformationAdapter. "
    "When implemented, delete this file — strict=True makes an unexpected "
    "pass a hard failure so this cannot be silently skipped."
)

# Config declaration sites legitimately name the artifacts: something has to
# hold the paths and describe them to the user. The contract is about *reading*
# artifacts, so the gate covers the consumers — routes and services.
ARTIFACT_PATTERN = re.compile(r"manifest\.json|catalog\.json|MANIFEST_PATH|CATALOG_PATH")


@pytest.mark.xfail(strict=True, reason=FUTURE_REASON)
def test_no_route_or_service_reads_framework_artifacts_directly():
    """The end state: only adapters/ may name manifest.json / catalog.json."""
    package_root = Path(__file__).resolve().parents[1]
    offenders = sorted(
        str(path.relative_to(package_root))
        for directory in ("routes", "services")
        for path in package_root.joinpath(directory).rglob("*.py")
        if ARTIFACT_PATTERN.search(path.read_text())
    )
    assert offenders == []
