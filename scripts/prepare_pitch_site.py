"""Integrate the presentation and night theme into the existing local landing site."""
from pathlib import Path
import ast
import re
import shutil

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT.parent/'landing-pasadhi'
shutil.copytree(ROOT/'web/pitch',SITE/'pitch',dirs_exist_ok=True)
for name in ('theme.css','motion.js'):
    shutil.copy2(ROOT/'web'/name,SITE/name)
pptx=ROOT/'web/download/PASADHI-pitch-2026.pptx'
if pptx.exists():
    shutil.copy2(pptx,SITE/'download'/pptx.name)

for name in ('index.html','th/index.html'):
    path=SITE/name
    text=path.read_text(encoding='utf-8')
    prefix='../' if name.startswith('th/') else './'
    thai=name.startswith('th/')
    if 'id="prototype-status"' not in text:
        status='สถานะ M0 prototype: แอปตรวจสเปกและควบคุมทรัพยากรพร้อมทดลอง ส่วนคลัสเตอร์หลายเครื่อง เครดิต รายได้ และบริการเชิงพาณิชย์เป็นแผนพัฒนา ราคาที่แสดงเป็นข้อเสนอ' if thai else 'M0 prototype: hardware probing and resource controls are available to test. Multi-host pooling, credits, payouts and commercial services are planned; displayed prices are proposals.'
        text=text.replace('<main>',f'<main><aside class="wrap prototype-status" id="prototype-status">{status}</aside>',1)
        if 'id="prototype-status"' not in text:
            text=text.replace('</header>',f'</header><aside class="wrap prototype-status" id="prototype-status">{status}</aside>',1)
        text=text.replace('AVAILABLE NOW','PROTOTYPE AVAILABLE').replace('ALWAYS AVAILABLE','PLANNED LICENCE')
    # Replace the old flat hero diagram with the new conceptual key visual.
    text=re.sub(r'(<div class="hero-art">)\s*<svg.*?</svg>',lambda m:m[1]+f'<img src="{prefix}pitch/assets/compute-background.png" alt="Conceptual artwork of connected compute devices; not a photograph of a deployed PASADHI system">',text,count=1,flags=re.S)
    if 'id="pitch"' not in text:
        title='ใช้เครื่องที่มี ให้คุ้มกับงานที่ต้องทำ' if thai else 'The compute you need starts with what you own'
        desc='ชม pitch สำหรับนักลงทุนและงานวิจัย พร้อมแผนทุน 24 เดือน ผลวัดจริง ข้อจำกัด และเป้าหมายที่ตรวจสอบได้' if thai else 'Explore the investor story, research evidence and a proposed 24-month funding plan with explicit milestones and assumptions.'
        watch='เปิด Presentation' if thai else 'Open presentation'
        promo=f'''<section class="wrap pitch-promo" id="pitch"><p class="eyebrow">PASADHI · PITCH &amp; RESEARCH</p><h2>{title}</h2><p class="sub">{desc}</p><div class="actions"><a class="btn primary" href="{prefix}pitch/">{watch}</a><a class="btn ghost" href="{prefix}download/PASADHI-pitch-2026.pptx" download>PowerPoint · 24 slides</a></div><p class="flow-hint">Mr. Supakrit Wapakpetch and AI Team · proposed plan, not a revenue forecast</p></section>'''
        text=text.replace('<section class="wrap" id="how">',promo+'\n<section class="wrap" id="how">')
    for page in ('pool','mesh'):
        pattern=r'<img src="'+re.escape(prefix)+r'anatomy/'+page+r'\.png"[^>]*>'
        frame=f'<div class="iso-live"><iframe data-iso loading="lazy" title="PASADHI {page}: illustrative animated isometric flow" src="{prefix}anatomy/{page}.html?embed=1"></iframe></div>'
        text=re.sub(pattern,lambda _:frame,text,count=1)
    if f'href="{prefix}pitch/"' not in text.split('</nav>')[0]:
        text=text.replace('</nav>',f'<a href="{prefix}pitch/">Pitch</a></nav>',1)
    path.write_text(text,encoding='utf-8')

# Same theme on the main pages, story pages and existing isometric scenes.
pages=list(SITE.glob('*.html'))+list((SITE/'th').glob('*.html'))+list((SITE/'anatomy').glob('*.html'))
for page in pages:
    text=page.read_text(encoding='utf-8')
    prefix='../' if page.parent!=SITE else './'
    if 'theme.css' not in text:
        text=text.replace('</head>',f'<link rel="stylesheet" href="{prefix}theme.css">\n</head>')
    if 'motion.js' not in text:
        text=text.replace('</body>',f'<script src="{prefix}motion.js" defer></script>\n</body>')
    page.write_text(text,encoding='utf-8')

# Keep the source isometric pages in this repository current without changing paper PNGs.
for source,target in (('pool.html','pasadhi-pool.html'),('mesh.html','pasadhi-mesh.html'),('pasadhi-system.html','pasadhi-system.html'),('pasadhi-install.html','pasadhi-install.html')):
    shutil.copy2(SITE/'anatomy'/source,ROOT/'web/anatomy'/target)

sitemap=SITE/'sitemap.xml'
text=sitemap.read_text(encoding='utf-8')
if 'https://pasadhi.tech/pitch/' not in text:
    text=text.replace('</urlset>','  <url><loc>https://pasadhi.tech/pitch/</loc><lastmod>2026-10-23</lastmod><priority>0.8</priority></url>\n</urlset>')
sitemap.write_text(text,encoding='utf-8')

for filename,variable in (('deploy_pasadhi_assets.py','FILES'),('deploy_pasadhi.py','PUBLIC_FILES')):
    path=ROOT.parent/'deploy'/filename
    text=path.read_text(encoding='utf-8')
    tree=ast.parse(text)
    assign=next(node for node in tree.body if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id==variable for t in node.targets))
    files=set(ast.literal_eval(assign.value))
    files.update(p.relative_to(SITE).as_posix() for p in (SITE/'pitch').rglob('*') if p.is_file())
    files.update(('theme.css','motion.js','download/PASADHI-pitch-2026.pptx'))
    replacement=variable+' = (\n'+''.join(f'    {file!r},\n' for file in sorted(files))+')\n'
    lines=text.splitlines(keepends=True)
    text=''.join(lines[:assign.lineno-1])+replacement+''.join(lines[assign.end_lineno:])
    path.write_text(text,encoding='utf-8')
print('Integrated pitch, 24-month plan, night theme and animated isometric embeds into the local website.')
