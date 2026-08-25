from __future__ import annotations

from math import ceil

from .models import ServiceState, SimulationResult


def simulate_checkout(state: ServiceState) -> SimulationResult:
    """Deterministic checkout capacity model used by the reproducible demo.

    One connection processes ten requests per second when both dependency and
    code latency factors are 1.0.  The separate factors let the evaluation
    corpus represent configuration, dependency and code-regression causes
    without inferring behavior from a version-name string.
    The model is intentionally simple: it makes every intervention auditable
    and keeps the demo independent from external infrastructure.
    """

    effective_pool = state.pool_size
    if state.adaptive_min_pool:
        required = ceil(
            state.traffic_rps
            * state.dependency_latency_factor
            * state.code_latency_factor
            / 10.0
        )
        effective_pool = max(effective_pool, min(required, 32))

    combined_latency_factor = state.dependency_latency_factor * state.code_latency_factor
    capacity = effective_pool * 10.0 / combined_latency_factor
    failed = max(0.0, state.traffic_rps - capacity)
    failure_rate = failed / state.traffic_rps if state.traffic_rps else 0.0
    p99_ms = 110.0 + combined_latency_factor * 45.0 + failure_rate * 900.0
    healthy = failure_rate <= 0.08 and p99_ms <= 300.0
    return SimulationResult(
        effective_pool_size=effective_pool,
        capacity_rps=round(capacity, 2),
        failure_rate=round(failure_rate, 4),
        p99_ms=round(p99_ms, 2),
        healthy=healthy,
    )
