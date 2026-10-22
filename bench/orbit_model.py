"""Planetary and interplanetary link budget for PASADHI.

    python pasadhi/bench/orbit_model.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))

from pasadhi.core import orbit  # noqa: E402

OUT = ROOT / 'bench' / 'results'
OUT.mkdir(parents=True, exist_ok=True)


def main():
    rows = orbit.table()
    print(f"{'link':<28}{'RTT':>12}{'GEMM eff':>12}{'batch 10 min':>14}{'min job (90 %)':>16}")
    for row in rows:
        print(f"{row['link']:<28}{row['rtt_ms']:>10.0f} ms{row['gemm_eff']*100:>11.4f}%"
              f"{row['batch_eff_10min']*100:>13.1f}%{row['min_job_s_for_90pct']:>13.0f} s")

    summary = {'note': 'speed-of-light arithmetic; no hardware assumptions beyond the link budget',
               'links': rows}
    (OUT / 'orbit_model.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    INK, MUTED, GRID = '#1a1a1a', '#5a5a5a', '#e3e3e3'
    fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.4), facecolor='white')

    def style(ax, title, xlabel, ylabel):
        ax.set_facecolor('white')
        for spine in ax.spines.values():
            spine.set_color('#999999')
        ax.tick_params(colors=MUTED, labelsize=8.2)
        ax.grid(True, color=GRID, linewidth=0.7)
        ax.set_axisbelow(True)
        ax.set_title(title, color=INK, fontsize=10, pad=9)
        ax.set_xlabel(xlabel, color=MUTED, fontsize=8.5)
        ax.set_ylabel(ylabel, color=MUTED, fontsize=8.5)

    names = [row['link'].replace(' · ', '\n') for row in rows]
    ax = axes[0]
    style(ax, 'A 4 096³ GEMM sharded across the link', '', 'share of card compute (%)')
    values = [row['gemm_eff'] * 100 for row in rows]
    bars = ax.barh(names, values, color='#1f4e79')
    for bar, value in zip(bars, values):
        ax.text(max(value, 0.002) * 1.15, bar.get_y() + bar.get_height() / 2,
                f'{value:.3f} %' if value < 1 else f'{value:.1f} %', va='center', fontsize=7.5)
    ax.set_xscale('log')
    ax.set_xlim(0.0005, 60)
    ax.invert_yaxis()

    ax = axes[1]
    style(ax, 'Shortest job that still keeps 90 % of its time doing work', '', 'seconds')
    values = [row['min_job_s_for_90pct'] for row in rows]
    bars = ax.barh(names, values, color='#c55a11')
    for bar, value in zip(bars, values):
        ax.text(max(value, 1) * 1.15, bar.get_y() + bar.get_height() / 2, f'{value:,.0f} s', va='center',
                fontsize=7.5)
    ax.set_xscale('log')
    ax.invert_yaxis()

    fig.tight_layout()
    path = OUT / 'fig05_orbit.png'
    fig.savefig(path, facecolor='white', dpi=300)
    plt.close(fig)
    print('wrote', OUT / 'orbit_model.json')
    print('wrote', path)


if __name__ == '__main__':
    main()
