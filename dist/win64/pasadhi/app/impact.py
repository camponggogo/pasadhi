"""Value a contribution by the measured impact of each resource, not by a flat rate.

The weights come from `bench/results/resource_impact.json` (measured on an i7-8550U):
    CPU 98.0 % · RAM 0.4 % · DISK 1.0 % · NET 0.6 %            (no NVIDIA GPU)
    CPU 56.6 % · GPU 42.2 % · RAM 0.2 % · DISK 0.6 % · NET 0.4 % (with a GTX 1050)

A node-hour is worth `pool` THB, and the user receives `pool × Σ(share_i × weight_i)`.
Sharing 100 % of a 4-thread reference node therefore pays exactly 2.50 THB/hour, which is the credit rate
used by the commercial model. Two other profiles exist because the weights are workload-dependent: when jobs
are large, RAM becomes the gate; when the fleet is GPU-heavy, the card dominates.
"""
from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dataclasses import dataclass

# Measured shares (this host / with a card) and two workload-dependent assumptions.
PROFILES = {
    'small_jobs': {'CPU': 0.980, 'GPU': 0.000, 'RAM': 0.004, 'DISK': 0.010, 'NET': 0.006},
    'with_gpu': {'CPU': 0.566, 'GPU': 0.422, 'RAM': 0.002, 'DISK': 0.006, 'NET': 0.004},
    'large_jobs': {'CPU': 0.550, 'GPU': 0.000, 'RAM': 0.300, 'DISK': 0.100, 'NET': 0.050},
}

POOL_THB_PER_REFERENCE_HOUR = 2.50   # 4 threads, fully shared
REFERENCE_THREADS = 4
GPU_POOL_THB_PER_HOUR = 3.00         # a 2 GB class card at 100 %


@dataclass
class Share:
    cpu_pct: int = 20
    gpu_pct: int = 0
    ram_pct: int = 10
    disk_pct: int = 5
    network_pct: int = 10

    def fractions(self) -> dict:
        return {'CPU': self.cpu_pct / 100, 'GPU': self.gpu_pct / 100, 'RAM': self.ram_pct / 100,
                'DISK': self.disk_pct / 100, 'NET': self.network_pct / 100}


def weights(profile: str = 'auto', has_gpu: bool = False) -> dict:
    if profile == 'auto':
        profile = 'with_gpu' if has_gpu else 'small_jobs'
    return PROFILES[profile]


def node_value(share: Share, threads: int = 4, ram_gb: float = 8.0, vram_gb: float = 0.0,
               profile: str = 'auto') -> dict:
    has_gpu = vram_gb > 0 and share.gpu_pct > 0
    weight = weights(profile, has_gpu)

    cpu_pool = POOL_THB_PER_REFERENCE_HOUR * max(threads, 1) / REFERENCE_THREADS
    fractions = share.fractions()
    contribution = {name: fractions[name] * weight.get(name, 0.0) for name in fractions}
    cpu_hourly = cpu_pool * sum(value for name, value in contribution.items() if name != 'GPU')

    gpu_hourly = 0.0
    if has_gpu:
        gpu_hourly = GPU_POOL_THB_PER_HOUR * max(vram_gb, 1.0) / 2.0 * fractions['GPU']

    hourly = cpu_hourly + gpu_hourly
    return {
        'profile': profile,
        'weights': weight,
        'weighted_fraction': round(sum(contribution.values()), 4),
        'contribution': {name: round(value, 4) for name, value in contribution.items()},
        'hourly_thb': round(hourly, 3),
        'daily_thb': round(hourly * 24, 2),
        'monthly_thb': round(hourly * 24 * 30, 0),
        'detail': {'cpu_pool_thb': round(cpu_pool, 2), 'cpu_part': round(cpu_hourly, 3),
                   'gpu_part': round(gpu_hourly, 3)},
    }


def explain(result: dict) -> str:
    lines = [f"profile {result['profile']} → weighted {result['weighted_fraction']*100:.2f} % of the pool"]
    for name, value in result['contribution'].items():
        if value:
            lines.append(f'  {name:<5} {value*100:6.2f} % of pool → {result["detail"]["cpu_pool_thb"]*value:.3f} ฿/h')
    lines.append(f"total {result['hourly_thb']} ฿/h ≈ {result['monthly_thb']:,.0f} ฿/month")
    return '\n'.join(lines)


if __name__ == '__main__':
    for profile in ('small_jobs', 'with_gpu'):
        for share in (Share(20, 0, 10, 5, 10), Share(35, 0, 20, 10, 20), Share(90, 100, 40, 20, 40)):
            result = node_value(share, threads=8, ram_gb=16, vram_gb=2 if profile == 'with_gpu' else 0,
                                profile=profile)
            print(f'--- {profile} · CPU {share.cpu_pct}% GPU {share.gpu_pct}% RAM {share.ram_pct}% '
                  f'DISK {share.disk_pct}% NET {share.network_pct}%')
            print(explain(result))
