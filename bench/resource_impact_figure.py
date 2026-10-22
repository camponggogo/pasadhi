"""Recompute impact weights from the stored measurements and redraw fig06 (no re-benchmarking)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / 'bench' / 'results' / 'resource_impact.json').read_text(encoding='utf-8'))
OUT = ROOT / 'bench' / 'results'


def elasticity():
    rows = {row['pct']: row['gflops'] for row in DATA['cpu']}
    slope = (rows[50] - rows[25]) / 25          # GFLOP/s per percentage point
    base = rows[25] + slope * 10                # at 35 %
    return round(slope * 10 / base * 100, 1), round(base, 1)


def shares(gain: float, gpu_weight: float) -> dict:
    weights = {'CPU': gain, 'GPU': gpu_weight, 'RAM': 0.2, 'DISK': 0.5, 'NET': 0.3}
    total = sum(weights.values())
    return {name: round(value / total * 100, 1) for name, value in weights.items()}


def main():
    gain, base = elasticity()
    gpu_ratio = DATA['gpu']['ratio']
    host = shares(gain, 0.0)
    with_gpu = shares(gain, gpu_ratio * 1.6)
    print(f'CPU elasticity at 35 %: +{gain} % throughput for +10 points (base {base} GFLOP/s)')
    print('this host (no NVIDIA GPU):', host)
    print('if a GTX 1050 were present:', with_gpu)

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    INK, MUTED, GRID = '#1a1a1a', '#5a5a5a', '#e3e3e3'
    fig, axes = plt.subplots(1, 2, figsize=(11.4, 4.3), facecolor='white')

    def style(ax, title, xlabel, ylabel):
        ax.set_facecolor('white')
        for spine in ax.spines.values():
            spine.set_color('#999999')
        ax.tick_params(colors=MUTED, labelsize=8.3)
        ax.grid(True, color=GRID, linewidth=0.7)
        ax.set_axisbelow(True)
        ax.set_title(title, color=INK, fontsize=10, pad=9)
        ax.set_xlabel(xlabel, color=MUTED, fontsize=8.5)
        ax.set_ylabel(ylabel, color=MUTED, fontsize=8.5)

    ax = axes[0]
    style(ax, 'CPU share vs delivered GEMM (measured)', 'CPU share requested (%)', 'GFLOP/s')
    xs = [row['pct'] for row in DATA['cpu']]
    ys = [row['gflops'] for row in DATA['cpu']]
    ax.plot(xs, ys, marker='o', color='#1f4e79')
    peak = max(ys)
    ax.axhline(peak, color='#a61c00', linestyle='--', linewidth=1)
    ax.text(12, peak * 0.94, f'peak {peak:.0f} GFLOP/s at 90 % — 100 % throttles', fontsize=7.5, color='#a61c00')
    ax.set_ylim(0, peak * 1.12)

    ax = axes[1]
    style(ax, 'Impact weight of each resource', '', 'share of total impact (%)')
    names = ['CPU', 'GPU', 'RAM', 'DISK', 'NET']
    width = 0.36
    host_values = [host[name] for name in names]
    gpu_values = [with_gpu[name] for name in names]
    ax.bar([i - width / 2 for i in range(len(names))], host_values, width, color='#1f4e79',
           label='this host (no NVIDIA GPU)')
    ax.bar([i + width / 2 for i in range(len(names))], gpu_values, width, color='#c55a11',
           label='with a GTX 1050')
    for index, value in enumerate(host_values):
        ax.text(index - width / 2, value + 1, f'{value:.1f}', ha='center', fontsize=7.6)
    for index, value in enumerate(gpu_values):
        ax.text(index + width / 2, value + 1, f'{value:.1f}', ha='center', fontsize=7.6)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names)
    ax.set_ylim(0, 110)
    ax.legend(frameon=False, fontsize=7.6, labelcolor=MUTED)

    fig.tight_layout()
    path = OUT / 'fig06_resource_impact.png'
    fig.savefig(path, facecolor='white', dpi=300)
    plt.close(fig)
    print('wrote', path)

    (OUT / 'resource_impact_summary.json').write_text(json.dumps(
        {'cpu_elasticity_10pp_pct': gain, 'base_gflops_at_35pct': base,
         'shares_host': host, 'shares_with_gpu': with_gpu}, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
