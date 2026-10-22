"""Heterogeneous fleet model: 1 450 cards from a 2 GB GTX 1050 to a 40 GB A100.

    python pasadhi/bench/hetero_model.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))

from pasadhi.core import hetero  # noqa: E402

OUT = ROOT / 'bench' / 'results'
OUT.mkdir(parents=True, exist_ok=True)


def main():
    mix = hetero.MIXED
    scenarios = {'mixed': hetero.job_stream(4000, scenario='mixed'),
                 'no_huge': hetero.job_stream(4000, scenario='no_huge')}

    runs = []
    for scenario, jobs in scenarios.items():
        for policy in ('best_fit', 'fastest', 'worst_fit'):
            result = hetero.run(policy, jobs, mix, scenario=scenario)
            runs.append(result)
            print(f"{scenario:<8} {policy:<10} makespan {result.makespan:>8} s  wait {result.mean_wait:>7} s  "
                  f"tput {result.throughput_tflops:>7} TFLOPS  rejected {result.rejected}")
            print(f"         utilisation {result.utilisation}")
            print(f"         finish by class {result.class_finish}")

    f32 = hetero.aggregate(mix, 'f32')
    int8 = hetero.aggregate(mix, 'int8')
    print('aggregate f32:', f32)
    print('aggregate int8:', int8)

    summary = {
        'note': 'card figures are published specifications; scheduling is simulated, not run on hardware',
        'inventory': {card.name: count for card, count in mix.items()},
        'aggregate_f32': f32,
        'aggregate_int8': int8,
        'runs': [result.__dict__ for result in runs],
    }
    (OUT / 'hetero_model.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    INK, MUTED, GRID = '#1a1a1a', '#5a5a5a', '#e3e3e3'

    def style(ax, title, xlabel=None, ylabel=None):
        ax.set_facecolor('white')
        for spine in ax.spines.values():
            spine.set_color('#999999')
        ax.tick_params(colors=MUTED, labelsize=8.2)
        ax.grid(True, color=GRID, linewidth=0.7)
        ax.set_axisbelow(True)
        ax.set_title(title, color=INK, fontsize=10, pad=9)
        if xlabel:
            ax.set_xlabel(xlabel, color=MUTED, fontsize=8.5)
        if ylabel:
            ax.set_ylabel(ylabel, color=MUTED, fontsize=8.5)

    fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.4), facecolor='white')

    ax = axes[0]
    style(ax, 'Makespan by placement policy (4 000 jobs)', 'policy', 'seconds (lower is better)')
    policies = ['best_fit', 'fastest', 'worst_fit']
    width = 0.36
    for offset, (scenario, colour) in enumerate({'mixed': '#1f4e79', 'no_huge': '#c55a11'}.items()):
        values = [next(r.makespan for r in runs if r.policy == p and r.scenario == scenario) for p in policies]
        ax.bar([index + (offset - 0.5) * width for index in range(3)], values, width, color=colour,
               label=scenario)
        for index, value in enumerate(values):
            ax.text(index + (offset - 0.5) * width, value * 1.02, f'{value:.1f}', ha='center', fontsize=8)
    ax.set_xticks(range(3))
    ax.set_xticklabels([p.replace('_', ' ') for p in policies])
    ax.legend(frameon=False, fontsize=8, labelcolor=MUTED)

    ax = axes[1]
    style(ax, 'Utilisation by card class (no-huge scenario)', 'utilisation during the run', '')
    classes = list(runs[0].utilisation.keys())
    for offset, (policy, colour) in enumerate({'best_fit': '#1f4e79', 'fastest': '#c55a11'}.items()):
        values = [next(r.utilisation[name] for r in runs if r.policy == policy and r.scenario == 'no_huge')
                  for name in classes]
        ax.barh([index + (offset - 0.5) * width for index in range(len(classes))], values, height=width,
                color=colour, label=policy)
    ax.set_yticks(range(len(classes)))
    ax.set_yticklabels(classes)
    ax.set_xlim(0, 1.05)
    ax.legend(frameon=False, fontsize=8, labelcolor=MUTED, loc='lower right')

    fig.tight_layout()
    path = OUT / 'fig03_hetero_fleet.png'
    fig.savefig(path, facecolor='white', dpi=300)
    plt.close(fig)
    print('wrote', OUT / 'hetero_model.json')
    print('wrote', path)


if __name__ == '__main__':
    main()
