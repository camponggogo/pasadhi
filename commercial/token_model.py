"""PASADHI token economy: capacity split, contribution credits, and a profit-backed liquidity reserve.

Layers (share of the fleet):
    free     10 %  — schools, NGOs, open-source; no invoice, but they earn contribution credits
    standard 40 %  — monthly or annual rental
    premium  50 %  — enterprise, pay a premium for SLA and isolation

Money flows:
    customers pay rent  →  a share of profit (10 %) is moved to a reserve that backs the liquidity token
    customers who contribute idle machines earn compute credits, capped at 50 % of their invoice

    python pasadhi/commercial/token_model.py --nodes 1450
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'commercial' / 'results'
OUT.mkdir(parents=True, exist_ok=True)


@dataclass
class Model:
    nodes: int = 1450
    free_share: float = 0.10
    standard_share: float = 0.40
    premium_share: float = 0.50

    cost_thb_node_month: float = 551.0      # measured: amortisation + energy + support
    standard_price_thb: float = 1_490.0     # per node-month
    premium_price_thb: float = 3_490.0      # 2.3x for SLA, isolation, 24x7

    credit_thb_per_hour: float = 2.5        # what one contributed node-hour earns
    contributed_hours_per_node: float = 120.0   # ~4 h/day of idle time
    redemption_cap: float = 0.50            # cannot discount more than half an invoice

    profit_to_reserve: float = 0.10
    reserve_backing_thb: float = 1.0        # 1 PSD = 1 THB of reserve book value
    monthly_opex_thb: float = 160_000.0     # 2 FTE, room, spares for the fleet

    # boot cost: a machine that is already on pays almost nothing extra to start working
    boot_seconds: float = 45.0
    idle_watts: float = 12.0
    load_watts: float = 45.0
    kwh_thb: float = 4.2


def monthly(model: Model) -> dict:
    free_nodes = round(model.nodes * model.free_share)
    standard_nodes = round(model.nodes * model.standard_share)
    premium_nodes = model.nodes - free_nodes - standard_nodes

    revenue_standard = standard_nodes * model.standard_price_thb
    revenue_premium = premium_nodes * model.premium_price_thb
    revenue_gross = revenue_standard + revenue_premium

    cost = model.nodes * model.cost_thb_node_month

    # Contribution credits: only paying customers contribute (the free layer earns credits, it does not spend).
    contributing_nodes = standard_nodes + premium_nodes
    hours = contributing_nodes * model.contributed_hours_per_node
    credits_issued = hours * model.credit_thb_per_hour

    # Redemption is capped per invoice; the cap binds when credits exceed it.
    cap_value = (revenue_standard + revenue_premium) * model.redemption_cap
    credits_redeemed = min(credits_issued, cap_value)

    revenue_net = revenue_gross - credits_redeemed
    profit_gross = revenue_net - cost - model.monthly_opex_thb
    reserve = max(0.0, profit_gross * model.profit_to_reserve)
    profit_after_reserve = profit_gross - reserve

    tokens_outstanding = reserve / model.reserve_backing_thb

    boot_kwh = (model.load_watts - model.idle_watts) / 1000 * model.boot_seconds / 3600
    boot_cost = boot_kwh * model.kwh_thb
    hourly_price = model.standard_price_thb / (30 * 24)

    return {
        'nodes': {'free': free_nodes, 'standard': standard_nodes, 'premium': premium_nodes},
        'revenue': {'standard': round(revenue_standard), 'premium': round(revenue_premium),
                    'gross': round(revenue_gross)},
        'cost': round(cost),
        'opex': round(model.monthly_opex_thb),
        'credits': {'issued_thb': round(credits_issued), 'redeemed_thb': round(credits_redeemed),
                    'cap_thb': round(cap_value), 'cap_binding': credits_issued > cap_value},
        'revenue_net': round(revenue_net),
        'profit_gross': round(profit_gross),
        'margin_pct': round(profit_gross / revenue_net * 100, 1) if revenue_net else None,
        'reserve_thb': round(reserve),
        'profit_after_reserve': round(profit_after_reserve),
        'psd_outstanding': round(tokens_outstanding, 0),
        'boot': {'cost_thb': round(boot_cost, 4),
                 'share_of_one_hour': round(boot_cost / hourly_price * 100, 2)},
        'credit_liability_ratio': round(credits_issued / revenue_gross, 3) if revenue_gross else None,
    }


def sweep_credits(model: Model, hours=(30.0, 60.0, 120.0, 240.0, 360.0)) -> list[dict]:
    rows = []
    saved = model.contributed_hours_per_node
    for value in hours:
        model.contributed_hours_per_node = value
        result = monthly(model)
        rows.append({'hours': value,
                     'redeemed_thb': result['credits']['redeemed_thb'],
                     'share_of_revenue': round(
                         result['credits']['redeemed_thb'] / result['revenue']['gross'] * 100, 1),
                     'cap_binding': result['credits']['cap_binding'],
                     'profit_gross': result['profit_gross'],
                     'margin_pct': result['margin_pct']})
    model.contributed_hours_per_node = saved
    return rows


def figure(result: dict, sweep: list[dict]):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    INK, MUTED, GRID = '#1a1a1a', '#5a5a5a', '#e3e3e3'
    fig, axes = plt.subplots(1, 2, figsize=(11.4, 4.3), facecolor='white')

    def style(ax, title, xlabel=None, ylabel=None):
        ax.set_facecolor('white')
        for spine in ax.spines.values():
            spine.set_color('#999999')
        ax.tick_params(colors=MUTED, labelsize=8.5)
        ax.grid(True, color=GRID, linewidth=0.7)
        ax.set_axisbelow(True)
        ax.set_title(title, color=INK, fontsize=10, pad=9)
        if xlabel:
            ax.set_xlabel(xlabel, color=MUTED, fontsize=8.5)
        if ylabel:
            ax.set_ylabel(ylabel, color=MUTED, fontsize=8.5)

    ax = axes[0]
    style(ax, 'Monthly money flow at 1 450 nodes (THB)', '', '')
    labels = ['standard rent', 'premium rent', 'credits redeemed', 'cost', 'profit', 'reserve (10 %)']
    values = [result['revenue']['standard'], result['revenue']['premium'],
              -result['credits']['redeemed_thb'], -result['cost'], result['profit_gross'],
              -result['reserve_thb']]
    colours = ['#2e75b6', '#1f4e79', '#c55a11', '#7f7f7f', '#5b9bd5', '#a61c00']
    bars = ax.bar(labels, values, color=colours, width=0.6)
    for bar, value in zip(bars, values):
        offset = 30_000 if value >= 0 else -70_000
        ax.text(bar.get_x() + bar.get_width() / 2, value + offset, f'{value/1000:,.0f}k', ha='center',
                fontsize=7.6)
    ax.tick_params(axis='x', labelsize=7, rotation=18)
    ax.axhline(0, color='#999999', linewidth=0.8)

    ax = axes[1]
    style(ax, 'Does the discount mechanism stay solvent?', 'contributed hours per node per month', 'margin %')
    ax.plot([row['hours'] for row in sweep], [row['margin_pct'] for row in sweep],
            marker='o', color='#1f4e79')
    ax.axhline(0, color='#a61c00', linestyle='--', linewidth=1)
    ax.set_ylim(min(-10, min(row['margin_pct'] for row in sweep) - 5), 80)

    fig.tight_layout()
    path = OUT / 'fig04_token_economy.png'
    fig.savefig(path, facecolor='white', dpi=300)
    plt.close(fig)
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--nodes', type=int, default=1450)
    args = parser.parse_args()

    model = Model(nodes=args.nodes)
    result = monthly(model)
    sweep = sweep_credits(model)

    print(json.dumps(result, indent=2))
    for row in sweep:
        print(f"hours {row['hours']:>5.0f}  redeemed {row['redeemed_thb']:>10,} "
              f"({row['share_of_revenue']:>4.1f} % of revenue, cap {row['cap_binding']})  "
              f"profit {row['profit_gross']:>12,}  margin {row['margin_pct']}")

    (OUT / 'token_model.json').write_text(
        json.dumps({'model': asdict(model), 'result': result, 'sweep': sweep}, indent=2), encoding='utf-8')
    print('wrote', OUT / 'token_model.json')
    print('wrote', figure(result, sweep))


if __name__ == '__main__':
    main()
