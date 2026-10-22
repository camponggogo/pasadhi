"""Resource budget: turn five sliders into hard limits, and turn those limits into money.

Rates are derived from the commercial model: a fully shared 4-core / 8 GB node earns about ฿2.50 per hour
(`commercial/token_model.py`, credit rate 2.5 THB per node-hour). The per-resource split below keeps that total
for a reference machine and scales linearly with what the user actually offers.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, asdict
from pathlib import Path

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

REFERENCE = {'cores': 4, 'ram_gb': 8, 'disk_gb': 64, 'mbps': 100, 'gpu': 0.0}
REFERENCE_HOURLY_THB = 2.5

RATE_PER_CORE_H = 0.55
RATE_PER_GB_RAM_H = 0.035
RATE_PER_GB_DISK_MONTH = 0.05
RATE_PER_GB_TRAFFIC = 0.02
RATE_PER_GPU_HOUR = 0.90        # a 2 GB class card; scaled by VRAM below


@dataclass
class Share:
    cpu_pct: int = 20
    gpu_pct: int = 0
    ram_pct: int = 10
    disk_pct: int = 5
    network_pct: int = 10

    autostart: bool = True
    night_only: bool = False     # contribute only outside 08:00–18:00

    def clamp(self) -> 'Share':
        self.cpu_pct = max(0, min(90, int(self.cpu_pct)))
        self.gpu_pct = max(0, min(100, int(self.gpu_pct)))
        self.ram_pct = max(0, min(80, int(self.ram_pct)))
        self.disk_pct = max(0, min(50, int(self.disk_pct)))
        self.network_pct = max(0, min(80, int(self.network_pct)))
        return self

    def to_dict(self) -> dict:
        return asdict(self)


def limits(share: Share, cores: int, ram_gb: float, disk_free_gb: float, mbps: float,
           vram_gb: float = 0.0) -> dict:
    return {
        'cpu_cores': round(max(0.1, cores * share.cpu_pct / 100), 2) if share.cpu_pct else 0.0,
        'gpu_hours_share': round(share.gpu_pct / 100, 2),
        'vram_gb': round(vram_gb * share.gpu_pct / 100, 2),
        'ram_gb': round(ram_gb * share.ram_pct / 100, 2),
        'disk_gb': round(disk_free_gb * share.disk_pct / 100, 1),
        'mbps': round(mbps * share.network_pct / 100, 1) if mbps else 0.0,
    }


def hourly_earnings(share: Share, cores: int, ram_gb: float, disk_free_gb: float, mbps: float,
                    vram_gb: float = 0.0) -> dict:
    """Payout follows the measured impact of each resource (`app/impact.py`), not a flat rate."""
    from pasadhi.app import impact

    result = impact.node_value(
        impact.Share(cpu_pct=share.cpu_pct, gpu_pct=share.gpu_pct, ram_pct=share.ram_pct,
                     disk_pct=share.disk_pct, network_pct=share.network_pct),
        threads=cores, ram_gb=ram_gb, vram_gb=vram_gb * (share.gpu_pct / 100))
    pool = result['detail']['cpu_pool_thb']
    contribution = result['contribution']
    return {
        'hourly_thb': result['hourly_thb'],
        'daily_thb': result['daily_thb'],
        'monthly_thb': result['monthly_thb'],
        'breakdown': {
            'cpu': round(contribution['CPU'] * pool, 3),
            'ram': round(contribution['RAM'] * pool, 3),
            'gpu': result['detail']['gpu_part'],
            'disk': round(contribution['DISK'] * pool, 3),
            'net': round(contribution['NET'] * pool, 3),
        },
        'weights': result['weights'],
        'weighted_fraction': result['weighted_fraction'],
    }


def reference_check() -> float:
    """The rates should reproduce the commercial credit rate for the reference machine."""
    share = Share(cpu_pct=100, gpu_pct=0, ram_pct=100, disk_pct=100, network_pct=100)
    result = hourly_earnings(share, REFERENCE['cores'], REFERENCE['ram_gb'],
                             REFERENCE['disk_gb'], REFERENCE['mbps'])
    return result['hourly_thb']


if __name__ == '__main__':
    print('reference hourly:', reference_check(), 'THB (target', REFERENCE_HOURLY_THB, ')')
    print(hourly_earnings(Share(), 8, 16, 200, 1000))
