"""Resource budget: turn five sliders into hard limits, and turn those limits into money.

Rates are derived from the commercial model: a fully shared 4-core / 8 GB node earns about ฿2.50 per hour
(`commercial/token_model.py`, credit rate 2.5 THB per node-hour). The per-resource split below keeps that total
for a reference machine and scales linearly with what the user actually offers.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

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
    lim = limits(share, cores, ram_gb, disk_free_gb, mbps, vram_gb)
    cpu = lim['cpu_cores'] * RATE_PER_CORE_H
    ram = lim['ram_gb'] * RATE_PER_GB_RAM_H
    gpu = (lim['gpu_hours_share'] * RATE_PER_GPU_HOUR * max(1.0, vram_gb / 2)) if share.gpu_pct else 0.0
    disk = lim['disk_gb'] * (RATE_PER_GB_DISK_MONTH / 730) if lim['disk_gb'] else 0.0
    net = lim['mbps'] * 3600 / 8 / 1024 * (share.network_pct / 100) * 0  # traffic is metered on delivery
    net = 0.0
    total = cpu + ram + gpu + disk + net
    return {
        'hourly_thb': round(total, 3),
        'daily_thb': round(total * 24, 2),
        'monthly_thb': round(total * 24 * 30, 0),
        'breakdown': {'cpu': round(cpu, 3), 'ram': round(ram, 3), 'gpu': round(gpu, 3), 'disk': round(disk, 3)},
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
