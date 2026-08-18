"""Request-scoped, low-cardinality backend phase timing."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from time import perf_counter
from typing import Iterator


PHASE_NAMES = (
    "request",
    "artifact_read",
    "artifact_parse",
    "reconciliation",
    "model_index",
    "data_model_read",
    "layout_read",
    "entity_inference",
    "source_lineage",
    "schema_read",
    "relationship_scan",
)

_PHASE_DESCRIPTIONS = {
    "request": "request",
    "artifact_read": "artifact read",
    "artifact_parse": "artifact parse",
    "reconciliation": "reconciliation",
    "model_index": "model index",
    "data_model_read": "data model read",
    "layout_read": "layout read",
    "entity_inference": "entity inference",
    "source_lineage": "source lineage",
    "schema_read": "schema read",
    "relationship_scan": "relationship scan",
}
_VALID_PHASE_NAMES = frozenset(PHASE_NAMES)


@dataclass
class PhaseRecord:
    """Aggregated timing for one fixed phase."""

    duration_ms: float = 0.0
    call_count: int = 0

    @property
    def duration(self) -> float:
        """Return the aggregated duration in milliseconds."""
        return self.duration_ms


class PhaseCollector:
    """Mutable timing state scoped to one request context."""

    def __init__(self) -> None:
        self.records: dict[str, PhaseRecord] = {}

    def add(self, name: str, duration_ms: float) -> None:
        """Aggregate one completed invocation of a fixed phase."""
        _validate_phase_name(name)
        record = self.records.setdefault(name, PhaseRecord())
        record.duration_ms += duration_ms
        record.call_count += 1


_collector: ContextVar[PhaseCollector | None] = ContextVar(
    "trellis_observability_collector",
    default=None,
)
_active_phases: ContextVar[tuple[str, ...]] = ContextVar(
    "trellis_observability_active_phases",
    default=(),
)
# Public alias makes the request-scoped storage available to middleware without
# exposing any mutable global collector.
collector_var = _collector


def _validate_phase_name(name: str) -> None:
    if not isinstance(name, str) or name not in _VALID_PHASE_NAMES:
        raise ValueError(f"unsupported observability phase: {name!r}")


def get_collector() -> PhaseCollector | None:
    """Return the collector bound to the current execution context."""
    return _collector.get()


def set_collector(collector: PhaseCollector | None) -> Token[PhaseCollector | None]:
    """Bind a collector to the current execution context."""
    if collector is not None and not isinstance(collector, PhaseCollector):
        raise TypeError("collector must be a PhaseCollector or None")
    return _collector.set(collector)


def reset_collector(token: Token[PhaseCollector | None]) -> None:
    """Restore the collector state represented by a ContextVar token."""
    _collector.reset(token)


@contextmanager
def collector_scope(
    collector: PhaseCollector | None = None,
) -> Iterator[PhaseCollector]:
    """Temporarily bind and yield a new or supplied request collector."""
    active_collector = collector or PhaseCollector()
    phase_token = _active_phases.set(())
    token = set_collector(active_collector)
    try:
        yield active_collector
    finally:
        try:
            reset_collector(token)
        finally:
            _active_phases.reset(phase_token)


@contextmanager
def timed_phase(name: str) -> Iterator[None]:
    """Measure a fixed phase when a collector is bound to the context."""
    _validate_phase_name(name)
    collector = get_collector()
    if collector is None:
        yield
        return

    active_phases = _active_phases.get()
    if name in active_phases:
        # A route boundary may surround an adapter-owned phase. Keep one
        # aggregate for the operation rather than double-counting the same
        # fixed phase name.
        yield
        return

    phase_token = _active_phases.set((*active_phases, name))
    started_at = perf_counter()
    try:
        yield
    finally:
        try:
            collector.add(name, (perf_counter() - started_at) * 1000)
        finally:
            _active_phases.reset(phase_token)


def phase_description(name: str) -> str:
    """Return the fixed, safe description for a phase."""
    _validate_phase_name(name)
    return _PHASE_DESCRIPTIONS[name]


def serialize_server_timing(collector: PhaseCollector | None = None) -> str:
    """Serialize collected phases in vocabulary order for a Server-Timing header."""
    active_collector = collector if collector is not None else get_collector()
    if active_collector is None:
        return ""

    metrics = []
    for name in PHASE_NAMES:
        record = active_collector.records.get(name)
        if record is None or record.call_count == 0:
            continue
        metrics.append(
            f'{name};dur={record.duration_ms:.3f};desc="{phase_description(name)}"'
        )
    return ",".join(metrics)
