from __future__ import annotations

from ..models import ExperimentResult, FaultVariant, ServiceState


def evolve_fault_family(
    baseline: ServiceState,
    experiments: list[ExperimentResult],
    seed_mutations: list[dict],
) -> list[FaultVariant]:
    """Turn one reproduced incident into a small fault family.

    The goal is not random fuzzing. The variants preserve the proven causal
    mechanism and then perturb traffic, latency, and capacity pressure so a
    candidate patch must prove broader immunity.
    """

    primary = next((item for item in experiments if item.classification == "primary-cause"), None)
    lineage = primary.hypothesis_id if primary else "unknown"
    variants: list[FaultVariant] = []
    for item in seed_mutations:
        variants.append(
            FaultVariant(
                name=item["name"],
                lineage=lineage,
                trigger="从事故证据中复现的种子场景",
                changes=item["changes"],
                expected_risk="known",
            )
        )

    variants.extend(
        [
            FaultVariant(
                name="pool-borderline",
                lineage=lineage,
                trigger="中等流量下容量接近饱和边界",
                changes={
                    "traffic_rps": max(130.0, baseline.traffic_rps * 1.08),
                    "dependency_latency_factor": baseline.dependency_latency_factor,
                    "pool_size": max(6, baseline.pool_size + 2),
                },
                expected_risk="medium",
            ),
            FaultVariant(
                name="recovery-spike",
                lineage=lineage,
                trigger="恢复窗口出现流量尖峰",
                changes={
                    "traffic_rps": baseline.traffic_rps * 1.48,
                    "dependency_latency_factor": baseline.dependency_latency_factor,
                },
                expected_risk="high",
            ),
            FaultVariant(
                name="downstream-jitter",
                lineage=lineage,
                trigger="中等流量叠加间歇性下游延迟抖动",
                changes={
                    "traffic_rps": baseline.traffic_rps * 1.10,
                    "dependency_latency_factor": 1.6,
                },
                expected_risk="medium",
            ),
            FaultVariant(
                name="silent-config-drift",
                lineage=lineage,
                trigger="午间峰值前容量配置发生隐性漂移",
                changes={
                    "traffic_rps": baseline.traffic_rps * 0.98,
                    "dependency_latency_factor": 1.5,
                    "pool_size": max(4, baseline.pool_size - 2),
                },
                expected_risk="high",
            ),
        ]
    )
    return variants
