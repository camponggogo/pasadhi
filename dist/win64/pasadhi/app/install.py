"""One installer for every platform: probe, choose a role, create the token, write autostart, print earnings.

    python pasadhi/app/install.py --role auto --cpu 20 --gpu 0 --ram 10 --disk 5 --network 10
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pasadhi.app import autostart, budget, identity as ident, probe, roles  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--role', default='auto', choices=['auto', 'worker', 'coordinator', 'client'])
    parser.add_argument('--cpu', type=int, default=20)
    parser.add_argument('--gpu', type=int, default=0)
    parser.add_argument('--ram', type=int, default=10)
    parser.add_argument('--disk', type=int, default=5)
    parser.add_argument('--network', type=int, default=10)
    parser.add_argument('--autostart', action='store_true', help='install the boot entry (needs admin on Windows)')
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()

    hardware = probe.probe()
    decision = roles.decide(hardware, args.role)
    share = budget.Share(cpu_pct=args.cpu, gpu_pct=args.gpu, ram_pct=args.ram,
                         disk_pct=args.disk, network_pct=args.network, autostart=args.autostart).clamp()
    limits = budget.limits(share, hardware.cores_logical, hardware.ram_gb, hardware.disk_free_gb,
                           hardware.network_mbps, hardware.gpu_vram_gb)
    earnings = budget.hourly_earnings(share, hardware.cores_logical, hardware.ram_gb,
                                      hardware.disk_free_gb, hardware.network_mbps, hardware.gpu_vram_gb)

    record = ident.load_or_create()
    config_dir = ident.config_dir()
    config = {'role': args.role, 'share': share.to_dict(), 'port': 8765, 'autostart': args.autostart}
    (config_dir / 'config.json').write_text(json.dumps(config, indent=2), encoding='utf-8')

    files = autostart.write(config_dir / 'autostart', sys.executable,
                            str(Path(__file__).resolve().parent / 'service.py'))
    applied = autostart.apply(files) if args.autostart else False

    report = {
        'role': decision.role, 'score': decision.score, 'reasons': decision.reasons,
        'hardware': hardware.to_dict(), 'limits': limits, 'earnings': earnings,
        'identity': {'device_id': record.device_id, 'token_masked': record.masked()},
        'autostart': {'files': files, 'applied': applied},
        'next': 'เปิดหน้าตั้งค่า: python pasadhi/app/service.py --port 8765',
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return report


if __name__ == '__main__':
    main()
