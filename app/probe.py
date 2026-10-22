"""Probe the machine once, at install time and on every boot.

Everything here is best-effort and cross-platform: Windows, Linux, macOS, Android (Termux / Kotlin bridge).
"""
from __future__ import annotations

import platform
import shutil
import socket
import subprocess
import time
from dataclasses import asdict, dataclass, field

try:
    import psutil
except ImportError:  # pragma: no cover - the app ships psutil, the probe must still run without it
    psutil = None


@dataclass
class Hardware:
    os: str
    machine: str
    cpu_model: str
    cores_physical: int
    cores_logical: int
    ram_gb: float
    disk_free_gb: float
    disk_total_gb: float
    has_gpu: bool
    gpu_name: str
    gpu_vram_gb: float
    network_mbps: float
    wired: bool
    on_battery: bool
    uptime_hours: float
    hostname: str
    probe_ms: float
    notes: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _cpu_model() -> str:
    system = platform.system()
    try:
        if system == 'Windows':
            out = subprocess.run(['wmic', 'cpu', 'get', 'name'], capture_output=True, text=True, timeout=5).stdout
            lines = [line.strip() for line in out.splitlines() if line.strip() and 'Name' not in line]
            return lines[0] if lines else platform.processor()
        if system == 'Linux':
            with open('/proc/cpuinfo', encoding='utf-8') as handle:
                for line in handle:
                    if line.lower().startswith('model name'):
                        return line.split(':', 1)[1].strip()
        if system == 'Darwin':
            out = subprocess.run(['sysctl', '-n', 'machdep.cpu.brand_string'],
                                 capture_output=True, text=True, timeout=5).stdout
            return out.strip() or platform.processor()
    except Exception:
        pass
    return platform.processor() or 'unknown'


def _gpu() -> tuple[bool, str, float]:
    try:
        out = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader'],
                             capture_output=True, text=True, timeout=6)
        if out.returncode == 0 and out.stdout.strip():
            name, memory = out.stdout.strip().splitlines()[0].split(',')
            vram = float(memory.lower().replace('mib', '').strip()) / 1024
            return True, name.strip(), round(vram, 1)
    except Exception:
        pass
    if platform.system() == 'Darwin':
        try:
            out = subprocess.run(['system_profiler', 'SPDisplaysDataType'], capture_output=True, text=True, timeout=8)
            for line in out.stdout.splitlines():
                if 'Chipset Model' in line:
                    return True, line.split(':', 1)[1].strip(), 0.0
        except Exception:
            pass
    return False, '', 0.0


def _network_mbps() -> float:
    """A cheap estimate: the link speed of the default interface, not a throughput test."""
    if psutil is None:
        return 0.0
    try:
        stats = psutil.net_if_stats()
        best = 0.0
        for name, stat in stats.items():
            if stat.isup and not name.lower().startswith(('lo', 'loopback')):
                best = max(best, stat.speed)
        return float(best)
    except Exception:
        return 0.0


def probe() -> Hardware:
    started = time.perf_counter()
    system = platform.system()
    cores_logical = psutil.cpu_count(logical=True) if psutil else (shutil.os.cpu_count() or 1)
    cores_physical = psutil.cpu_count(logical=False) if psutil else cores_logical
    ram_gb = psutil.virtual_memory().total / 1024 ** 3 if psutil else 0.0
    usage = shutil.disk_usage('/' if system != 'Windows' else 'C:\\')
    has_gpu, gpu_name, vram = _gpu()
    battery = psutil.sensors_battery() if psutil and hasattr(psutil, 'sensors_battery') else None

    return Hardware(
        os=f'{system} {platform.release()}',
        machine=platform.machine(),
        cpu_model=_cpu_model(),
        cores_physical=cores_physical or 1,
        cores_logical=cores_logical or 1,
        ram_gb=round(ram_gb, 1),
        disk_free_gb=round(usage.free / 1024 ** 3, 1),
        disk_total_gb=round(usage.total / 1024 ** 3, 1),
        has_gpu=has_gpu,
        gpu_name=gpu_name,
        gpu_vram_gb=vram,
        network_mbps=_network_mbps(),
        wired=not any(name.lower().startswith(('wl', 'wi-fi', 'wlan')) for name in
                      (psutil.net_if_stats().keys() if psutil else [])),
        on_battery=bool(battery and not battery.power_plugged),
        uptime_hours=round((time.time() - psutil.boot_time()) / 3600, 2) if psutil else 0.0,
        hostname=socket.gethostname(),
        probe_ms=round((time.perf_counter() - started) * 1000, 1),
    )


if __name__ == '__main__':
    import json
    print(json.dumps(probe().to_dict(), indent=2, ensure_ascii=False))
