"""Figure for the group model: utilisation vs the 30 % share, and the three commercial modes."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))

from pasadhi.app import group as gp  # noqa: E402


def main():
    office = gp.default_office(120, 20, 10)
    office.share_pct = 0.30

    rows = []
    for mode in ('internal', 'shared', 'hybrid'):
        office.mode = mode
        row = gp.economics(office)
        row['mode'] = mode
        rows.append(row)

    hours = list(range(24))
    curves = {}
    for machine, count in ((office.machines[0], 120), (office.machines[1], 20), (office.machines[2], 10)):
        values = []
        for hour in hours:
            band = 'day' if 9 <= hour < 18 else ('evening' if 18 <= hour < 24 else 'night')
            values.append(machine.profile[band] * count)
        curves[machine.kind] = values

    total_utilisation = [sum(curves[kind][i] for kind in curves) for i in hours]
    total_machines = 150
    utilisation_pct = [value / total_machines * 100 for value in total_utilisation]

    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    INK, MUTED, GRID = '#1a1a1a', '#5a5a5a', '#e3e3e3'
    fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.4), facecolor='white')

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
    style(ax, 'Office utilisation vs the 30 % share (150 machines)', 'hour of day', '% of capacity')
    ax.plot(hours, utilisation_pct, color='#1f4e79', linewidth=2, label='average utilisation')
    ax.axhline(30, color='#c55a11', linestyle='--', linewidth=1.2, label='PASADHI share 30 %')
    spare = [min(30.0, max(0.0, 100 - v)) for v in utilisation_pct]
    ax.fill_between(hours, 0, spare, color='#c55a11', alpha=0.12, label='share available (cap 30 %)')
    ax.set_ylim(0, 100)
    ax.set_xticks([0, 6, 9, 12, 15, 18, 21, 24])
    ax.legend(frameon=False, fontsize=8, labelcolor=MUTED, loc='upper left')

    ax = axes[1]
    style(ax, 'Monthly net position by mode', '', 'THB per month')
    labels = [row['mode'] for row in rows]
    values = [row['net_thb_month'] for row in rows]
    colours = ['#c55a11' if value < 0 else '#1f4e79' for value in values]
    bars = ax.bar(labels, values, color=colours, width=0.55)
    for bar, value in zip(bars, values):
        offset = 6000 if value >= 0 else -12000
        ax.text(bar.get_x() + bar.get_width() / 2, value + offset, f'{value/1000:,.0f}k', ha='center',
                fontsize=9)
    ax.axhline(0, color='#999999', linewidth=0.8)

    fig.tight_layout()
    out = ROOT / 'bench' / 'results' / 'fig07_group.png'
    fig.savefig(out, facecolor='white', dpi=300)
    plt.close(fig)
    print('wrote', out)
    (ROOT / 'bench' / 'results' / 'group_modes.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
