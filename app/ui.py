"""Offline multilingual settings UI, embedded in native and source builds."""
import json
from .i18n import CATALOG, LANGUAGES
from .ui_client import SCRIPT

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PASADHI</title><style>
:root{color-scheme:dark;--bg:#0f1412;--panel:#171f1b;--line:#2c3830;--lime:#d1ff68;--ink:#ecf0e6;--muted:#9aa89d}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.6 system-ui,sans-serif}.wrap{max-width:960px;margin:auto;padding:28px 22px 60px}header{display:flex;gap:14px;align-items:center;justify-content:space-between;flex-wrap:wrap;border-bottom:1px solid var(--line);padding-bottom:16px}h1{font-size:20px;margin:0}h1 span{color:var(--lime)}.badge{font-size:12px;padding:6px 12px;border-radius:20px;background:#22301f;color:var(--lime);border:1px solid #47603a}.language{display:flex;align-items:center;gap:8px}.grid{display:grid;grid-template-columns:1.15fr 1fr;gap:18px;margin-top:22px}.card{min-width:0;background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px}.card h2{font-size:14px;color:var(--muted);margin:0 0 14px}.row{display:grid;grid-template-columns:minmax(80px,1fr) 2fr 52px;gap:12px;align-items:center;margin:12px 0}.row label{overflow-wrap:anywhere}input[type=range]{width:100%;min-width:0;accent-color:var(--lime)}output{text-align:right;color:var(--lime)}.money{font-size:36px;line-height:1.4;color:var(--lime);margin:4px 0}.money small{font-size:14px;color:var(--muted)}.sub,.note{font-size:12px;color:var(--muted)}.sub{margin:6px 0}.note{margin-top:12px}table{width:100%;border-collapse:collapse;font-size:12px;margin-top:8px}td{padding:5px 0;border-bottom:1px solid #212b24}td:last-child{text-align:right;padding-left:12px}.mono{font-family:ui-monospace,monospace;font-size:12px;overflow-wrap:anywhere}button,select{background:#22301f;color:var(--lime);border:1px solid #47603a;border-radius:8px;padding:8px 12px;font:inherit;max-width:100%}button{cursor:pointer}.switch{display:flex;align-items:center;gap:10px;margin-top:10px;flex-wrap:wrap}.foot{margin-top:18px;font-size:12px;color:var(--muted);overflow-wrap:anywhere}#status{color:#ffd29a;min-height:1.6em;margin-bottom:0}button:focus-visible,select:focus-visible,input:focus-visible{outline:2px solid var(--lime);outline-offset:3px}@media(max-width:760px){.grid{grid-template-columns:1fr}.wrap{padding:20px 16px}.money small{display:block}}
</style></head><body><div class="wrap">
<header><h1>PASADHI <span>· ปัสสัทธิ</span></h1><div class="language"><label for="language" data-i18n="language">Language</label><select id="language"></select></div><div class="badge" id="role">…</div></header>
<p id="status" role="status" aria-live="polite"></p><div class="grid"><section class="card"><h2 data-i18n="share"></h2>
<div class="row"><label for="cpu">CPU</label><input id="cpu" type="range" min="0" max="90" step="5"><output for="cpu" id="cpu_o"></output></div>
<div class="row"><label for="gpu">GPU</label><input id="gpu" type="range" min="0" max="100" step="10"><output for="gpu" id="gpu_o"></output></div>
<div class="row"><label for="ram">RAM</label><input id="ram" type="range" min="0" max="80" step="5"><output for="ram" id="ram_o"></output></div>
<div class="row"><label for="disk" data-i18n="disk"></label><input id="disk" type="range" min="0" max="50" step="5"><output for="disk" id="disk_o"></output></div>
<div class="row"><label for="network" data-i18n="network"></label><input id="network" type="range" min="0" max="80" step="5"><output for="network" id="network_o"></output></div>
<div class="switch"><input id="autostart" type="checkbox"><label for="autostart" data-i18n="autostart"></label></div><p class="note" data-i18n="limitsNote"></p></section>
<section class="card"><h2 data-i18n="earnings"></h2><p class="money"><span id="monthly">0</span> <small data-i18n="month"></small></p>
<p class="sub">≈ <span id="daily">0</span> <span data-i18n="day"></span> · <span id="hourly">0</span> <span data-i18n="hour"></span></p>
<table><tbody><tr><td>CPU</td><td id="b_cpu">–</td></tr><tr><td>GPU</td><td id="b_gpu">–</td></tr><tr><td>RAM</td><td id="b_ram">–</td></tr><tr><td data-i18n="disk"></td><td id="b_disk">–</td></tr><tr><td data-i18n="limits"></td><td id="limits">–</td></tr></tbody></table>
<p class="note" data-i18n="creditsNote"></p></section></div>
<section class="card" style="margin-top:18px"><h2 data-i18n="deviceHeading"></h2><p class="mono" id="device">–</p><p class="mono" id="token">–</p><div class="switch"><button id="rotate" data-i18n="rotate"></button><span class="sub" id="rotated" role="status"></span></div><p class="note" data-i18n="tokenNote"></p></section>
<p class="foot" id="hardware">–</p></div><script>""" + 'const I18N = ' + json.dumps({'languages': LANGUAGES, 'catalog': CATALOG}, ensure_ascii=False).replace('<', '\\u003c') + ';\n' + SCRIPT + '</script></body></html>'

PAGE = PAGE.replace("<body>", '<body><nav aria-label="Application pages" style="padding:12px 22px;background:#10232b"><a style="color:#68dfbc" href="/dashboard">Coordinator dashboard / ภาพรวมระบบ</a></nav>', 1)
