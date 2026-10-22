"""Latency physics for a public, eventually interplanetary network.

The speed of light is the one constant no amount of engineering removes. This module turns it into a
scheduling rule: what can be sharded, what must run locally, and what only works as store-and-forward.

    python pasadhi/bench/orbit_model.py
"""
from __future__ import annotations

from dataclasses import dataclass

C_KM_S = 299_792.458
FIBER_FACTOR = 0.68   # light in glass, ~2/3 c


@dataclass(frozen=True)
class Link:
    name: str
    one_way_ms: float
    bandwidth_mbps: float
    note: str

    @property
    def rtt_ms(self) -> float:
        return self.one_way_ms * 2


def fiber(distance_km: float) -> float:
    """One-way latency over glass, in milliseconds."""
    return distance_km / (C_KM_S * FIBER_FACTOR) * 1000


def radio(distance_km: float) -> float:
    """One-way latency over free space, in milliseconds."""
    return distance_km / C_KM_S * 1000


EARTH_FIBER = Link('Earth · fibre (antipodal)', fiber(20_000), 10_000, 'two thirds of c in glass')
LEO = Link('LEO satellite · 550 km', radio(2_200) + 8, 200, 'path ~4x altitude, plus ground segment')
GEO = Link('GEO satellite · 35 786 km', radio(2 * 35_786) + 20, 50, 'one hop up and down')
MOON = Link('Earth–Moon', radio(384_400), 10, '1.28 s one way, unavoidable')
MARS_MIN = Link('Earth–Mars · closest', radio(54_600_000), 2, '3 min one way')
MARS_MAX = Link('Earth–Mars · farthest', radio(401_000_000), 2, '22 min one way')

LINKS = [EARTH_FIBER, LEO, GEO, MOON, MARS_MIN, MARS_MAX]


def sharded_efficiency(n: int, card_tflops: float, link: Link, steps: int = 10,
                       efficiency: float = 0.70) -> float:
    """A big GEMM needs `steps` collective rounds; each round costs a full RTT."""
    compute = 2 * n ** 3 / (card_tflops * 1e12 * efficiency)
    communication = steps * link.rtt_ms / 1000
    return compute / (compute + communication)


def batch_efficiency(job_seconds: float, link: Link) -> float:
    """Independent jobs pay one round trip per job: dispatch out, result back."""
    return job_seconds / (job_seconds + link.rtt_ms / 1000)


def minimum_job_seconds(link: Link, target: float = 0.90) -> float:
    """Shortest job that still keeps `target` of its wall time doing work."""
    rtt = link.rtt_ms / 1000
    return target * rtt / (1 - target)


def table(n: int = 4096, card_tflops: float = 1.34, job_seconds: float = 600.0) -> list[dict]:
    rows = []
    for link in LINKS:
        rows.append({
            'link': link.name,
            'rtt_ms': round(link.rtt_ms, 1),
            'mbps': link.bandwidth_mbps,
            'gemm_eff': round(sharded_efficiency(n, card_tflops, link), 6),
            'batch_eff_10min': round(batch_efficiency(job_seconds, link), 4),
            'min_job_s_for_90pct': round(minimum_job_seconds(link), 1),
            'note': link.note,
        })
    return rows
