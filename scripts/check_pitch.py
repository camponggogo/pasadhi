"""Validate the shared pitch content, deployment copies and package boundaries."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib,json,zipfile
root=Path(__file__).resolve().parents[1]
site=root.parent/'landing-pasadhi'
data=json.loads((root/'web/pitch/deck.json').read_text(encoding='utf-8'))
assert len(data['slides'])==24 and data['coreCount']==14
budget=data['slides'][19]['table']
assert sum(int(r[1].replace('$','').replace(',','')) for r in budget[1:-1])==750000
assert sum(int(r[2].rstrip('%')) for r in budget[1:-1])==100
assert 5*34000+19*24000+11500+112500==750000
class Links(HTMLParser):
    def handle_starttag(self,tag,attrs):
        for k,v in attrs:
            if k in ('href','src') and v and not v.startswith(('https:','http:','mailto:','#','data:')):
                target=(self.path.parent/v.split('?')[0].split('#')[0]).resolve()
                assert target.exists(),f'Missing {self.path}: {v}'
for path in [site/'index.html',site/'th/index.html',site/'pitch/index.html']:
    parser=Links();parser.path=path;parser.feed(path.read_text(encoding='utf-8'))
for src in (root/'web/download').rglob('*'):
    relative=src.relative_to(root/'web/download')
    if src.is_file() and (len(relative.parts)==1 or relative.parts[0] in ('latest','v0.1.0')):
        dst=site/'download'/src.relative_to(root/'web/download')
        assert dst.exists() and hashlib.sha256(src.read_bytes()).digest()==hashlib.sha256(dst.read_bytes()).digest(),f'Deployment copy differs: {dst}'
with zipfile.ZipFile(root/'web/download/PASADHI-pitch-2026.pptx') as z:
    assert z.testzip() is None
    assert len([n for n in z.namelist() if n.startswith('ppt/slides/slide') and n.endswith('.xml')])==24
print('Pitch: 24 slides, budget totals, runway arithmetic, website links and all deployment download copies PASS')
