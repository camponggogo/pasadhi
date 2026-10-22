"""Build an accessible static presentation from the same content as the editable PPTX."""
from html import escape as e
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PITCH=ROOT/'web/pitch'
data=json.loads((PITCH/'deck.json').read_text(encoding='utf-8'))

def esc(value):
    return e(str(value)).replace('\n','<br>')

def slide_html(d,i):
    kind=d['kind']
    cls=f'slide {kind}' + (' light' if d.get('light') else '') + (' artwork' if kind in ('cover','ask') else '')
    content=f'<h1>{esc(d["title"])}</h1>'
    if kind in ('cover','ask'):
        content='<div class="wordmark"><img src="assets/logo.png" alt=""><b>PASADHI</b></div>'+content
    if d.get('subtitle'):
        content+=f'<p class="subtitle">{esc(d["subtitle"])}</p>'
    if d.get('big'):
        content+=f'<p class="big">{esc(d["big"])}</p>'
    if d.get('metrics'):
        content+='<div class="metrics">'+''.join(f'<div><strong>{esc(a)}</strong><b>{esc(b)}</b><p>{esc(c)}</p></div>' for a,b,c in d['metrics'])+'</div>'
    if kind=='product':
        content+='<img class="system" src="assets/system.png" alt="Target architecture with office devices, compute pool, gateway and storage; distributed plane is a roadmap item">'
    if d.get('table'):
        content+='<div class="table-wrap"><table><thead><tr>'+''.join(f'<th scope="col">{esc(x)}</th>' for x in d['table'][0])+'</tr></thead><tbody>'
        content+=''.join('<tr>'+''.join(f'<td>{esc(x)}</td>' for x in row)+'</tr>' for row in d['table'][1:])+'</tbody></table></div>'
    if d.get('chart'):
        chart=d['chart']
        content+='<div class="chart" role="img" aria-label="Time to first token: cold prefix 111.4 seconds; reused prefix 0.71 seconds">'
        for name,value in zip(chart['categories'],chart['values']):
            content+=f'<div class="bar-row"><b>{esc(name)}</b><span style="--bar:{value/chart["max"]*100:.3f}%"></span><strong>{value:g} s</strong></div>'
        content+='</div>'
    if d.get('items'):
        content+='<div class="items">'
        for row in d['items']:
            if len(row)==3:
                a,b,c=row
                content+=f'<div><small>{esc(a)}</small><b>{esc(b)}</b><p>{esc(c)}</p></div>'
            else:
                a,b=row
                content+=f'<div><b>{esc(a)}</b><p>{esc(b)}</p></div>'
        content+='</div>'
    content+=f'<p class="takeaway">{esc(d["takeaway"])}</p><footer><span>PASADHI · {"Investor pitch" if i<data["coreCount"] else "Research & financial appendix"} · 23 Oct 2026</span><b>{i+1:02}</b></footer>'
    return f'<section class="{cls}" id="slide-{i+1}" aria-label="Slide {i+1}: {e(d["title"])}" aria-hidden="true">{content}</section>'

body='\n'.join(slide_html(d,i) for i,d in enumerate(data['slides']))
notes='\n'.join(f'<article data-note="{i}"><h2>{esc(d["title"])}</h2><p lang="th">{esc(d["notes"])}</p><h3>Sources</h3><ul>'+''.join(f'<li>{f"<a href={chr(34)}{e(s)}{chr(34)} target={chr(34)}_blank{chr(34)} rel={chr(34)}noopener{chr(34)}>{e(s)}</a>" if s.startswith("https://") else e(s)}</li>' for s in d['sources'])+'</ul></article>' for i,d in enumerate(data['slides']))
html=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PASADHI · Investor & research presentation</title><meta name="description" content="PASADHI pitch: existing hardware, reproducible research, a proposed six-month funding plan, and transparent operating scenarios.">
<link rel="canonical" href="https://campong.online/projects/pasadhi/pitch/"><link rel="stylesheet" href="../fonts/fonts.css"><link rel="stylesheet" href="present.css"></head>
<body><header class="toolbar"><a href="../">← PASADHI</a><label>View <select id="mode"><option value="investor">Investor · {data['coreCount']} slides</option><option value="full">Full · {len(data['slides'])} slides</option></select></label><a href="../download/PASADHI-pitch-2026.pptx" download>Download PPTX</a><a href="funding-plan.md">Funding plan</a><button id="notes-toggle" aria-pressed="false">Notes / แหล่งข้อมูล</button><button id="fullscreen">Fullscreen</button></header>
<main id="stage" tabindex="0" aria-label="Presentation; use left and right arrows to navigate">{body}</main>
<nav class="controls" aria-label="Slide navigation"><button id="prev" aria-label="Previous slide">←</button><label>Slide <input id="jump" type="number" min="1" max="{data['coreCount']}" value="1" aria-label="Go to slide"></label><span id="count" role="status" aria-live="polite"></span><button id="next" aria-label="Next slide">→</button><span class="hint">← → navigate · N notes · F fullscreen</span></nav>
<aside id="speaker-notes" hidden>{notes}<p><a href="../download/PASADHI-solution.pdf">Solution paper</a> · <a href="../download/PASADHI-full-paper.pdf">Full paper</a> · <a href="financial-plan.json">Financial model</a></p></aside>
<script src="present.js" defer></script></body></html>'''
(PITCH/'index.html').write_text(html,encoding='utf-8')
print(f'Built web presentation: {len(data["slides"])} slides, {data["coreCount"]}-slide investor mode, Thai notes and sources.')
