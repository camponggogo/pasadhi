"""Group worker: 100–200 machines inside one office, one group id, self-managed.

The group has a local controller (elected from the members), so the office keeps working when the WAN is down.
Two commercial modes per group:

    internal  the group pays a subscription and uses its own capacity (monthly / yearly / premium)
    shared    the group releases capacity to the public network and earns credits
    hybrid    a reserved slice for internal jobs, the rest shared

    python pasadhi/app/group.py --demo
"""
from __future__ import annotations

import argparse
import hashlib
import json
import secrets
from dataclasses import dataclass, field, asdict
from pathlib import Path

RATE_PER_CORE_HOUR_THB = 0.55
GROUP_DISCOUNT = 0.33          # groups pay less per node than a single office
LIST_PRICE_THB = 1_490.0       # per node-month, from the commercial model
PREMIUM_PRICE_THB = 3_490.0


@dataclass
class Machine:
    name: str
    kind: str            # desktop | server | laptop
    threads: int
    peak_gflops: float
    profile: dict        # utilisation by band: day / evening / night
    nodes: int = 1


@dataclass
class Group:
    group_id: str
    name: str
    mode: str = 'hybrid'            # internal | shared | hybrid
    plan: str = 'yearly'            # monthly | yearly | premium
    share_pct: float = 0.30         # of each machine's capacity
    reserve_pct: float = 0.05       # kept for the group's own jobs
    machines: list = field(default_factory=list)

    def join_token(self) -> str:
        seed = f'{self.group_id}:{self.name}'.encode()
        return 'grp_' + hashlib.sha256(seed).hexdigest()[:24]

    def totals(self) -> dict:
        threads = sum(m.threads * m.nodes for m in self.machines)
        peak = sum(m.peak_gflops * m.nodes for m in self.machines)
        return {'machines': sum(m.nodes for m in self.machines), 'threads': threads,
                'peak_gflops': round(peak, 1)}


BANDS = {'day': (9, 18), 'evening': (18, 24), 'night': (0, 9)}


def node_hours_available(group: Group, days=30, weekday_ratio=0.73) -> dict:
    """How many node-hours per month can actually be shared, given each machine's own utilisation."""
    total = {'day': 0.0, 'evening': 0.0, 'night': 0.0}
    for machine in group.machines:
        for band, (start, end) in BANDS.items():
            hours = end - start
            utilisation = machine.profile[band]
            usable = max(0.0, min(group.share_pct, 1.0 - utilisation))
            total[band] += usable * hours * machine.nodes

    weekday_hours = total['day'] * 22 + total['evening'] * 22 + total['night'] * 30
    weekend_hours = total['day'] * 8 + total['evening'] * 8 + total['night'] * 8
    month_hours = weekday_hours + weekend_hours
    return {'band_hours_per_day': {k: round(v, 1) for k, v in total.items()},
            'node_hours_month': round(month_hours, 0),
            'thread_hours_month': round(month_hours * (sum(m.threads * m.nodes for m in group.machines)
                                                       / max(1, sum(m.nodes for m in group.machines))), 0)}


def economics(group: Group) -> dict:
    totals = group.totals()
    hours = node_hours_available(group)
    threads_per_node = totals['threads'] / max(1, totals['machines'])
    shared_thread_hours = hours['node_hours_month'] * threads_per_node

    shared_earnings = shared_thread_hours * RATE_PER_CORE_HOUR_THB

    list_price = LIST_PRICE_THB * (1 - GROUP_DISCOUNT) if group.plan != 'premium' else PREMIUM_PRICE_THB * (1 - GROUP_DISCOUNT * 0.5)
    subscription = list_price * totals['machines']

    if group.mode == 'internal':
        net = -subscription
    elif group.mode == 'shared':
        net = shared_earnings
    else:
        reserved = group.reserve_pct / max(group.share_pct, 1e-9)
        net = shared_earnings * (1 - reserved) - subscription

    capacity_gflops = totals['peak_gflops'] * group.share_pct

    return {
        'machines': totals['machines'],
        'threads': totals['threads'],
        'peak_gflops': totals['peak_gflops'],
        'shared_capacity_gflops': round(capacity_gflops, 1),
        'node_hours_month': hours['node_hours_month'],
        'shared_thread_hours_month': round(shared_thread_hours, 0),
        'shared_earnings_thb_month': round(shared_earnings, 0),
        'subscription_thb_month': round(subscription, 0),
        'net_thb_month': round(net, 0),
        'per_node_month': round(net / totals['machines'], 0),
    }


def default_office(desktops=120, servers=20, laptops=10) -> Group:
    machines = [
        Machine('desktop', 'desktop', 8, 74.0, {'day': 0.65, 'evening': 0.15, 'night': 0.10}, desktops),
        Machine('server', 'server', 16, 120.0, {'day': 0.80, 'evening': 0.70, 'night': 0.60}, servers),
        Machine('laptop', 'laptop', 8, 60.0, {'day': 0.45, 'evening': 0.20, 'night': 0.05}, laptops),
    ]
    return Group(group_id='grp_' + secrets.token_hex(6), name='Office group', machines=machines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--demo', action='store_true')
    parser.add_argument('--machines', default='120,20,10', help='desktops,servers,laptops')
    parser.add_argument('--share', type=float, default=0.30)
    args = parser.parse_args()

    counts = [int(value) for value in args.machines.split(',')]
    group = default_office(*counts)
    group.share_pct = args.share

    rows = []
    for mode in ('internal', 'shared', 'hybrid'):
        group.mode = mode
        row = economics(group)
        row['mode'] = mode
        rows.append(row)
        print(f"{mode:<9} {row['machines']:>4} nodes  {row['shared_capacity_gflops']:>7} GFLOP/s  "
              f"earn {row['shared_earnings_thb_month']:>10,.0f}  sub {row['subscription_thb_month']:>10,.0f}  "
              f"net {row['net_thb_month']:>11,.0f}  per node {row['per_node_month']:>7,.0f}")

    out = Path(__file__).resolve().parents[1] / 'bench' / 'results' / 'group_model.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({'group': asdict(group), 'rows': rows,
                               'join_token': group.join_token()}, indent=2), encoding='utf-8')
    print('join token', group.join_token())
    print('wrote', out)


if __name__ == '__main__':
    main()
