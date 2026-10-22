"""PASADHI commercial calculator: cost per node, price at target margin, and the cloud comparison.

Every hardware number comes from the M0 harness (i7-8550U, f32 BLAS, 74 GFLOP/s peak, 60 % sustained duty).
Cloud figures are indicative list prices for October 2026 and are labelled as such wherever they appear.

    python pasadhi/commercial/pricing.py
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'commercial' / 'results'
OUT.mkdir(parents=True, exist_ok=True)

FX_THB_PER_USD = 36.0


@dataclass
class Assumptions:
    machine_cost_thb: float = 12_000      # refurbished 4c/8t small-form-factor PC
    life_months: int = 36
    watts: float = 45                      # idle-to-load average for this class of box
    kwh_thb: float = 4.2                   # Thai commercial tariff, indicative
    duty: float = 0.60                     # sustained fraction after thermal throttling
    gflops_peak: float = 74.0              # measured, f32 BLAS, 8 threads
    hours_month: float = 730
    support_thb_per_node_month: float = 80  # update, monitoring, spare part pool
    target_margin: float = 0.70
    cloud_cpu_usd_hour: float = 0.17       # 4 vCPU class, indicative list price
    cloud_cpu_gflops: float = 60.0         # same class, f32
    cloud_gpu_usd_hour: float = 2.10       # 1x A100 40GB class, indicative
    cloud_gpu_gflops: float = 19_500.0     # f32 (non-tensor) for a like-for-like compare


def per_node(a: Assumptions) -> dict:
    amortisation = a.machine_cost_thb / a.life_months
    energy = a.watts / 1000 * a.hours_month * a.kwh_thb
    cost = amortisation + energy + a.support_thb_per_node_month
    price = cost / (1 - a.target_margin)
    effective_gflops = a.gflops_peak * a.duty
    tflop_month = effective_gflops * 1e9 * a.hours_month * 3600 / 1e12
    return {
        'amortisation_thb': round(amortisation, 1),
        'energy_thb': round(energy, 1),
        'support_thb': a.support_thb_per_node_month,
        'cost_thb_month': round(cost, 1),
        'price_thb_month': round(price, 0),
        'price_thb_year': round(price * 12, 0),
        'gross_margin_thb': round(price - cost, 0),
        'effective_gflops': round(effective_gflops, 1),
        'tflop_month': round(tflop_month, 0),
        'thb_per_tflop': round(price / tflop_month, 3),
    }


def cloud_comparison(a: Assumptions, node: dict) -> dict:
    cpu_tflop_per_hour = a.cloud_cpu_gflops * 1e9 * 3600 / 1e12
    cpu_thb_per_tflop = a.cloud_cpu_usd_hour * FX_THB_PER_USD / cpu_tflop_per_hour
    gpu_tflop_per_hour = a.cloud_gpu_gflops * 1e9 * 3600 / 1e12
    gpu_thb_per_tflop = a.cloud_gpu_usd_hour * FX_THB_PER_USD / gpu_tflop_per_hour
    return {
        'cloud_cpu_thb_per_tflop': round(cpu_thb_per_tflop, 3),
        'cloud_gpu_thb_per_tflop': round(gpu_thb_per_tflop, 3),
        'node_vs_cloud_cpu': round(cpu_thb_per_tflop / node['thb_per_tflop'], 1),
        'node_vs_cloud_gpu': round(gpu_thb_per_tflop / node['thb_per_tflop'], 2),
    }


def fleet(a: Assumptions, nodes: int) -> dict:
    node = per_node(a)
    revenue = node['price_thb_year'] * nodes
    cost = node['cost_thb_month'] * 12 * nodes
    return {
        'nodes': nodes,
        'revenue_thb_year': round(revenue),
        'cost_thb_year': round(cost),
        'gross_profit_thb_year': round(revenue - cost),
        'margin_pct': round((revenue - cost) / revenue * 100, 1),
    }


def sketch(a: Assumptions, node: dict, cloud: dict):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    labels = ['PASADHI node\n(60 % duty)', 'Cloud CPU\n(4 vCPU)', 'Cloud GPU\n(1× A100)']
    values = [node['thb_per_tflop'], cloud['cloud_cpu_thb_per_tflop'], cloud['cloud_gpu_thb_per_tflop']]
    colours = ['#1f4e79', '#7f7f7f', '#c55a11']

    fig, ax = plt.subplots(figsize=(7.6, 4.2), facecolor='white')
    ax.set_facecolor('white')
    for spine in ax.spines.values():
        spine.set_color('#999999')
    bars = ax.bar(labels, values, color=colours, width=0.55)
    ax.set_yscale('log')
    ax.set_ylim(min(values) / 1.6, max(values) * 3.2)
    ax.grid(True, axis='y', color='#e3e3e3', linewidth=0.7)
    ax.set_axisbelow(True)
    ax.tick_params(colors='#5a5a5a', labelsize=9)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value * 1.15, f'{value:.3f}', ha='center', fontsize=9,
                color='#1a1a1a')
    ax.set_ylabel('THB per delivered TFLOP (log)', color='#5a5a5a', fontsize=9)
    ax.set_title('Cost of delivered matrix throughput (indicative, Oct 2026)', color='#1a1a1a', fontsize=10.5)
    ax.text(0.01, 0.02, 'cloud = list price, no egress, no ops labour', transform=ax.transAxes,
            ha='left', fontsize=7, color='#5a5a5a')
    fig.tight_layout()
    path = OUT / 'fig01_cost_per_tflop.png'
    fig.savefig(path, facecolor='white', dpi=300)
    plt.close(fig)
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--nodes', default='10,50,200')
    parser.add_argument('--margin', type=float, default=0.70)
    args = parser.parse_args()

    assumptions = Assumptions(target_margin=args.margin)
    node = per_node(assumptions)
    cloud = cloud_comparison(assumptions, node)
    fleets = [fleet(assumptions, int(n)) for n in args.nodes.split(',')]

    print('per node / month')
    for key, value in node.items():
        print(f'  {key:<24} {value}')
    print('cloud comparison')
    for key, value in cloud.items():
        print(f'  {key:<24} {value}')
    print('fleets')
    for row in fleets:
        print(f"  {row['nodes']:>4} nodes  revenue {row['revenue_thb_year']:>12,}  profit "
              f"{row['gross_profit_thb_year']:>12,}  margin {row['margin_pct']} %")

    payload = {'assumptions': asdict(assumptions), 'node': node, 'cloud': cloud, 'fleets': fleets}
    (OUT / 'pricing.json').write_text(json.dumps(payload, indent=2), encoding='utf-8')
    path = sketch(assumptions, node, cloud)
    print('wrote', OUT / 'pricing.json')
    print('wrote', path)


if __name__ == '__main__':
    main()
