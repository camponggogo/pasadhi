"""GPU layer: capability model, VRAM-aware tile planning, and fleet arithmetic.

Nothing here needs a GPU to run — the model is arithmetic over published specs, and it is labelled as such
wherever it is reported. The CPU numbers it is compared against are measured (see bench/run.py).

Reference card: NVIDIA GTX 1050 2 GB (GP107, SM_61, 640 CUDA cores, 1.86 TFLOPS fp32, DP4A int8,
112 GB/s, PCIe 3.0 x16, 75 W).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Device:
    name: str
    vram_gb: float
    tflops_f32: float
    tops_int8: float
    bandwidth_gbps: float
    watts: float

    @property
    def usable_vram_gb(self) -> float:
        """Drivers, context and fragmentation eat ~10 % of a small card."""
        return self.vram_gb * 0.9


GTX1050 = Device('GTX 1050 2GB', 2.0, 1.862, 3.72, 112.0, 75.0)
RTX3060 = Device('RTX 3060 12GB', 12.0, 12.74, 25.5, 360.0, 170.0)
CPU_NODE = Device('i7-8550U (measured)', 16.0, 0.074, 0.0, 35.0, 45.0)


def network_bytes_per_second(link_gbps: float, utilisation: float = 0.94) -> float:
    """1 GbE in practice: ~118 MB/s of payload after framing and TCP overhead."""
    return link_gbps * 1e9 / 8 * utilisation


def gemm_seconds(n: int, device: Device, efficiency: float = 0.70, dtype_bytes: int = 4) -> float:
    flops = 2.0 * n ** 3
    peak = device.tops_int8 * 1e12 if dtype_bytes == 1 else device.tflops_f32 * 1e12
    return flops / (peak * efficiency)


def transfer_seconds(n: int, link_gbps: float, dtype_bytes: int = 4) -> float:
    """Two operands, each n×n, over the link. The result is small enough to ignore here."""
    return 2 * n * n * dtype_bytes / network_bytes_per_second(link_gbps)


def shard_efficiency(n: int, device: Device, link_gbps: float, dtype_bytes: int = 4, efficiency: float = 0.70) -> float:
    """Fraction of the card's compute that survives the network for one sharded GEMM."""
    compute = gemm_seconds(n, device, efficiency, dtype_bytes)
    move = transfer_seconds(n, link_gbps, dtype_bytes)
    return compute / (compute + move)


def crossover_n(device: Device, link_gbps: float, dtype_bytes: int = 4, efficiency: float = 0.70) -> float:
    """Matrix size at which compute time equals transfer time (the useful threshold)."""
    peak = device.tops_int8 * 1e12 if dtype_bytes == 1 else device.tflops_f32 * 1e12
    return 4 * peak * efficiency * dtype_bytes / network_bytes_per_second(link_gbps)


def vram_max_square(device: Device, dtype_bytes: int = 4, operands: int = 2) -> int:
    """Largest square matrix that fits when two operands share the card."""
    bytes_total = device.usable_vram_gb * 1024 ** 3
    return int((bytes_total / (operands * dtype_bytes)) ** 0.5)


def plan_bins(sizes_gb: list[float], devices: list[Device]) -> list[dict]:
    """First-fit-decreasing packing of jobs into cards, largest job first."""
    bins = [{'device': device, 'used': 0.0, 'jobs': []} for device in devices]
    for index, size in enumerate(sorted(sizes_gb, reverse=True)):
        placed = False
        for slot in bins:
            if slot['used'] + size <= slot['device'].usable_vram_gb:
                slot['used'] += size
                slot['jobs'].append(index)
                placed = True
                break
        if not placed:
            bins.append({'device': devices[0], 'used': size, 'jobs': [index], 'overflow': True})
    return bins


def fleet(device: Device, count: int, mode: str, n: int = 4096, link_gbps: float = 1.0,
          dtype_bytes: int = 4) -> dict:
    """Two modes that behave completely differently.

    independent: every card works on its own job; the network only carries results.
    sharded:     one big GEMM split across cards; the network carries operands.
    """
    peak = device.tops_int8 if dtype_bytes == 1 else device.tflops_f32
    if mode == 'independent':
        efficiency = 0.70
        aggregate = count * peak * efficiency
        network_dependency = 0.0
    else:
        efficiency = shard_efficiency(n, device, link_gbps, dtype_bytes)
        aggregate = count * peak * efficiency
        network_dependency = 1 - efficiency
    return {
        'mode': mode,
        'cards': count,
        'dtype_bytes': dtype_bytes,
        'n': n,
        'link_gbps': link_gbps,
        'per_card_efficiency': round(efficiency, 3),
        'aggregate_tflops': round(aggregate, 1),
        'aggregate_pflops': round(aggregate / 1000, 2),
        'network_dependency': round(network_dependency, 3),
        'total_vram_gb': round(device.vram_gb * count, 0),
        'power_kw': round(device.watts * count / 1000, 1),
    }


def cost_per_tflop_hour(device: Device, card_cost_thb: float, count: int, hours: int = 36 * 730,
                        kwh_thb: float = 4.2, host_cost_thb: float = 9_000) -> float:
    """Depreciation + electricity + one host per card, per delivered TFLOP-hour at 60 % duty."""
    capital = (card_cost_thb + host_cost_thb) * count
    depreciation = capital / hours
    energy = device.watts * count / 1000 * kwh_thb
    delivered_tflops_per_hour = count * device.tflops_f32 * 0.70 * 0.60 * 3600
    return (depreciation + energy) / delivered_tflops_per_hour
