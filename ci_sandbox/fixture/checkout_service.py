from __future__ import annotations

from dataclasses import dataclass


DEFAULT_POOL_SIZE = 20


@dataclass(frozen=True)
class CheckoutHealth:
    traffic_rps: float
    pool_size: int
    capacity_rps: float
    failure_rate: float


def simulate_checkout(traffic_rps: float, pool_size: int = DEFAULT_POOL_SIZE) -> CheckoutHealth:
    capacity_rps = pool_size * 8.0
    overload = max(0.0, traffic_rps - capacity_rps)
    failure_rate = min(1.0, overload / max(traffic_rps, 1.0))
    return CheckoutHealth(traffic_rps, pool_size, capacity_rps, round(failure_rate, 4))
