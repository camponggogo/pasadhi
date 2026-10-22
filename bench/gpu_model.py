"""GPU fleet model: 1 000 × GTX 1050 2 GB, two modes, and where the network eats the gain.

    python pasadhi/bench/gpu_model.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))

from pasadhi.core import gpu  # noqa: E402

OUT = ROOT / 'bench' / 'results'
OUT.mkdir(parents=True, exist_ok=True)


def main():
    card = gpu.GTX1050
    sizes = [512, 1024, 2048, 4096, 8192]
    links = [1.0, 10.0]

    curve = []
    for n in sizes:
        row = {'n': n}
        for link in links:
            for dtype, label in ((4, 'f32'), (1, 'int8')):
                row[f'{label}_{int(link)}g'] = round(gpu.shard_efficiency(n, card, link, dtype), 3)
        curve.append(row)

    crossovers = {
        'f32_1gbe': round(gpu.crossover_n(card, 1.0, 4)),
        'f32_10gbe': round(gpu.crossover_n(card, 10.0, 4)),
        'int8_1gbe': round(gpu.crossover_n(card, 1.0, 1)),
        'int8_10gbe': round(gpu.crossover_n(card, 10.0, 1)),
    }
    vram = {
        'f32_square': gpu.vram_max_square(card, 4),
        'int8_square': gpu.vram_max_square(card, 1),
    }

    fleets = {
        'independent_f32': gpu.fleet(card, 1000, 'independent', 4096, 1.0, 4),
        'independent_int8': gpu.fleet(card, 1000, 'independent', 4096, 1.0, 1),
        'sharded_f32_1gbe': gpu.fleet(card, 1000, 'sharded', 4096, 1.0, 4),
        'sharded_f32_10gbe': gpu.fleet(card, 1000, 'sharded', 4096, 10.0, 4),
        'sharded_int8_10gbe': gpu.fleet(card, 1000, 'sharded', 4096, 10.0, 1),
    }

    per_hour = gpu.cost_per_tflop_hour(card, card_cost_thb=2_500, count=1000)

    print(f'card: {card.name}  {card.tflops_f32} TFLOPS f32  {card.tops_int8} TOPS int8  '
          f'{card.bandwidth_gbps} GB/s  {card.vram_gb} GB')
    print('crossover n (compute == transfer):', crossovers)
    print('largest square matrix that fits:', vram)
    for n in sizes:
        row = next(item for item in curve if item['n'] == n)
        print(f"n={n:>5}  f32 1GbE {row['f32_1g']:>5}  10GbE {row['f32_10g']:>5}  "
              f"int8 1GbE {row['int8_1g']:>5}  10GbE {row['int8_10g']:>5}")
    for name, item in fleets.items():
        print(f"{name:<22} {item['aggregate_pflops']:>6} PFLOPS  efficiency {item['per_card_efficiency']}")
    print('THB per TFLOP-hour (1000 cards, 36 months, 60 % duty):', round(per_hour, 4))

    summary = {
        'note': 'GTX 1050 figures are published specifications, not measurements on this host',
        'card': card.__dict__,
        'crossover_n': crossovers,
        'vram_limits': vram,
        'efficiency_curve': curve,
        'fleets': fleets,
        'thb_per_tflop_hour': round(per_hour, 4),
    }
    (OUT / 'gpu_model.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')

    # figure
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    INK, MUTED, GRID = '#1a1a1a', '#5a5a5a', '#e3e3e3'
    fig, axes = plt.subplots(1, 2, figsize=(11.4, 4.3), facecolor='white')

    def style(ax, title, xlabel, ylabel):
        ax.set_facecolor('white')
        for spine in ax.spines.values():
            spine.set_color('#999999')
        ax.tick_params(colors=MUTED, labelsize=8.5)
        ax.grid(True, color=GRID, linewidth=0.7)
        ax.set_axisbelow(True)
        ax.set_title(title, color=INK, fontsize=10, pad=9)
        ax.set_xlabel(xlabel, color=MUTED, fontsize=8.5)
        ax.set_ylabel(ylabel, color=MUTED, fontsize=8.5)

    ax = axes[0]
    style(ax, 'Sharded GEMM: share of card compute that survives the link', 'matrix size n', 'efficiency')
    xs = [row['n'] for row in curve]
    ax.plot(xs, [row['f32_1g'] for row in curve], marker='o', color='#c55a11', label='f32 · 1 GbE')
    ax.plot(xs, [row['f32_10g'] for row in curve], marker='s', color='#1f4e79', label='f32 · 10 GbE')
    ax.plot(xs, [row['int8_1g'] for row in curve], marker='^', color='#8fa9c9', label='int8 · 1 GbE')
    ax.plot(xs, [row['int8_10g'] for row in curve], marker='D', color='#2e75b6', label='int8 · 10 GbE')
    ax.set_xscale('log', base=2)
    ax.set_ylim(0, 1.02)
    ax.legend(frameon=False, fontsize=7.5, labelcolor=MUTED)

    ax = axes[1]
    style(ax, '1 000 × GTX 1050: aggregate throughput by mode', '', 'PFLOPS (f32) / POPS (int8)')
    labels = ['independent\nf32', 'independent\nint8', 'sharded\nf32 1GbE', 'sharded\nf32 10GbE',
              'sharded\nint8 10GbE']
    keys = ['independent_f32', 'independent_int8', 'sharded_f32_1gbe', 'sharded_f32_10gbe',
            'sharded_int8_10gbe']
    values = [fleets[key]['aggregate_pflops'] for key in keys]
    colours = ['#1f4e79', '#2e75b6', '#c55a11', '#8fa9c9', '#5b9bd5']
    bars = ax.bar(labels, values, color=colours, width=0.6)
    ax.set_yscale('log')
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value * 1.1, f'{value:.2f}', ha='center', fontsize=8)
    ax.tick_params(axis='x', labelsize=7.2)

    fig.tight_layout()
    path = OUT / 'fig02_gpu_fleet.png'
    fig.savefig(path, facecolor='white', dpi=300)
    plt.close(fig)
    print('wrote', OUT / 'gpu_model.json')
    print('wrote', path)


if __name__ == '__main__':
    main()
