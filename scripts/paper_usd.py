"""Convert the two English PASADHI papers to USD; preserve shared/Thai model assets."""
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
RATE = Decimal('33.65')
SOURCE = 'https://app.bot.or.th/BTWS_STAT/statistics/BOTWEBSTAT.aspx?language=eng&reportID=123'
NUMBER = r'\d+(?:[ ,]\d{3})*(?:\.\d+)?'


def load_plot(code, path, name, **extra):
    module = types.ModuleType(name)
    module.__dict__.update(__file__=str(path), **extra)
    sys.modules[name] = module
    exec(compile(code.lstrip('\ufeff'), str(path), 'exec'), module.__dict__)
    return module.__dict__


def dollars(value):
    value = Decimal(str(value).replace(' ', '').replace(',', '')) / RATE
    if abs(value) >= 1:
        return '$' + f'{value:,.2f}'
    places = 4 if abs(value) >= Decimal('.01') else 8
    return '$' + f'{value:.{places}f}'.rstrip('0').rstrip('.')


def money_label(value):
    return ('-' if value < 0 else '') + f'${abs(value):,.0f}'


def convert(text):
    # Make inherited units explicit before converting, including caption-only amounts.
    replacements = {
        '฿1.77–88.66': '฿1.77–฿88.66',
        'Cost ฿0.016 / 0.028 / 0.001': 'Cost ฿0.016 / ฿0.028 / ฿0.001',
        'credits 391 500': 'credits ฿391 500',
        'machine cost 798 950': 'machine cost ฿798 950',
        'opex 160 000': 'opex ฿160 000',
        'reserve 204 400': 'reserve ฿204 400',
        'credits cap at 1 697 225': 'credits cap at ฿1 697 225',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r'฿(' + NUMBER + r')\s+M\b', lambda m: dollars(Decimal(m[1].replace(' ', '')) * 1_000_000), text)
    text = re.sub(r'(' + NUMBER + r')\s*(?:THB|฿)', lambda m: dollars(m[1]), text)
    text = re.sub(r'฿(' + NUMBER + r')', lambda m: dollars(m[1]), text)
    return text


def figures():
    """Replot monetary figures from model data, into an English-paper-only directory."""
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib.figure import Figure
    out = ROOT / 'paper/figures/usd'
    out.mkdir(parents=True, exist_ok=True)
    artifacts = []
    original_save = Figure.savefig

    def record(figure, filename, *args, **kwargs):
        assert all('THB' not in (ax.get_title() + ax.get_xlabel() + ax.get_ylabel()) for ax in figure.axes)
        for ax in figure.axes:
            if 'USD' in ax.get_title() + ax.get_ylabel():
                if ax.get_yscale() == 'linear':
                    low, high = ax.get_ylim()
                    span = high - low
                    ax.set_ylim(low - span * .07, high + span * .04)
                else:
                    for text in ax.texts:
                        if text.get_text().startswith('cloud ='):
                            text.set_position((.01, .96))
        artifacts.append({'file': Path(filename).name,
                          'axes': [{'title': ax.get_title(), 'x': ax.get_xlabel(), 'y': ax.get_ylabel(),
                                    'annotations': [t.get_text() for t in ax.texts]} for ax in figure.axes]})
        return original_save(figure, filename, *args, **kwargs)

    Figure.savefig = record
    try:
        # Cost chart: convert both data and annotations, preserving its original log scale.
        path = ROOT / 'commercial/pricing.py'
        code = path.read_text(encoding='utf-8').replace('THB per delivered', 'USD ($) per delivered')
        code = code.replace("f'{value:.3f}'", "f'${value:.8f}'")
        namespace = load_plot(code, path, 'paper_pricing')
        namespace['OUT'] = out
        data = json.loads((ROOT / 'commercial/results/pricing.json').read_text())
        node, cloud = data['node'].copy(), data['cloud'].copy()
        node['thb_per_tflop'] /= float(RATE)
        for key in ('cloud_cpu_thb_per_tflop', 'cloud_gpu_thb_per_tflop'):
            cloud[key] /= float(RATE)
        namespace['sketch'](None, node, cloud)

        # Token chart: all money fields converted; percentages and hours are unchanged.
        path = ROOT / 'commercial/token_model.py'
        code = path.read_text(encoding='utf-8').replace('(THB)', '(USD $)')
        code = code.replace("f'{value/1000:,.0f}k'", 'money_label(value)')
        code = code.replace('30_000 if value >= 0 else -70_000', f'{30000 / float(RATE)} if value >= 0 else {-70000 / float(RATE)}')
        namespace = load_plot(code, path, 'paper_tokens', money_label=money_label)
        namespace['OUT'] = out
        data = json.loads((ROOT / 'commercial/results/token_model.json').read_text())
        result = data['result']
        for key in ('revenue', 'credits'):
            result[key] = {k: (v / float(RATE) if not isinstance(v, bool) else v) for k, v in result[key].items()}
        for key in ('cost', 'opex', 'revenue_net', 'profit_gross', 'reserve_thb', 'profit_after_reserve'):
            result[key] /= float(RATE)
        namespace['figure'](result, data['sweep'])

        # Office chart: keep utilisation in percent, convert the net-position series.
        path = ROOT / 'bench/group_figure.py'
        code = path.read_text(encoding='utf-8').replace('THB per month', 'USD ($) per month')
        code = code.replace("f'{value/1000:,.0f}k'", 'money_label(value)')
        code = code.replace("values = [row['net_thb_month'] for row in rows]", f"values = [row['net_thb_month'] / {RATE} for row in rows]")
        code = code.replace('6000 if value >= 0 else -12000', f'{6000 / float(RATE)} if value >= 0 else {-12000 / float(RATE)}')
        code = code.replace("ROOT / 'bench' / 'results' / 'fig07_group.png'", "USD / 'fig07_group.png'")
        code = code.replace("(ROOT / 'bench' / 'results' / 'group_modes.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')", "# Original model data stays in bench/results; no local-currency copy is published here.")
        namespace = load_plot(code, path, 'paper_group', USD=out, money_label=money_label)
        namespace['main']()
    finally:
        Figure.savefig = original_save
    (out / 'conversion.json').write_text(json.dumps({'reporting_currency': 'USD', 'local_units_per_usd': str(RATE),
        'rate_date': '2026-10-22', 'source': SOURCE, 'figures': artifacts}, indent=2) + '\n', encoding='utf-8')


def main():
    files = [ROOT / 'paper/SOLUTION.md', ROOT / 'paper/SOLUTION_FULL.md']
    if any('**Currency:**' in path.read_text(encoding='utf-8') for path in files):
        raise SystemExit('Already converted. Edit USD values directly; refusing a second conversion.')
    # Check shared assets are byte-identical after producing separate USD figures.
    shared = [ROOT / 'commercial/results/fig01_cost_per_tflop.png',
              ROOT / 'commercial/results/fig04_token_economy.png', ROOT / 'bench/results/fig07_group.png']
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in shared}
    figures()
    for path, digest in before.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    for path in files:
        text = convert(path.read_text(encoding='utf-8'))
        text = text.replace('pasadhi/commercial/results/fig01_cost_per_tflop.png', 'pasadhi/paper/figures/usd/fig01_cost_per_tflop.png')
        text = text.replace('pasadhi/commercial/results/fig04_token_economy.png', 'pasadhi/paper/figures/usd/fig04_token_economy.png')
        text = text.replace('pasadhi/bench/results/fig07_group.png', 'pasadhi/paper/figures/usd/fig07_group.png')
        assert not re.search(r'฿|\bTHB\b', text), path
        note = (f'**Currency:** All prices and monetary amounts are in US dollars ($). Original local-currency '
                f'amounts are divided by {RATE}, using the [Bank of Thailand reference rate for 22 October 2026]({SOURCE}). '
                'This is a reporting-currency conversion; model assumptions, margins and performance ratios are unchanged.\n\n')
        text = text.replace('## Abstract', note + '## Abstract', 1)
        path.write_text(text, encoding='utf-8')
    print('Converted both English papers and three monetary figures to USD; shared originals unchanged.')


if __name__ == '__main__':
    main()
