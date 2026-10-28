"""Read-only smoke checks for the published PASADHI release."""
import hashlib,json
from pathlib import Path
from urllib.request import urlopen,Request
root=Path(__file__).resolve().parents[1]
base='https://campong.online/projects/pasadhi/'
for name,needle in [('','prototype-status'),('pitch/','24-month'),('theme.css','prototype-status'),('motion.js','pasadhi-motion')]:
    with urlopen(base+name,timeout=30) as r:
        body=r.read().decode('utf-8');assert r.status==200 and needle in body
    print(name or 'homepage','200 PASS')
name='download/PASADHI-pitch-2026.pptx'
with urlopen(base+name,timeout=60) as r:
    body=r.read();assert hashlib.sha256(body).digest()==hashlib.sha256((root/'web'/name).read_bytes()).digest()
print('Published PPTX SHA256 PASS')
entries=json.loads((root/'web/download/release.json').read_text())
for entry in entries:
    with urlopen(Request(base+'download/'+entry['file'],method='HEAD'),timeout=30) as r:
        assert r.status==200 and int(r.headers['Content-Length'])==entry['bytes']
    print(entry['platform'],'download HEAD / bytes PASS')
for url in ['https://pasadhi.tech/','http://pasadhi.tech/']:
    try:
        with urlopen(url,timeout=20) as r: print(url,r.status,'prototype-status' in r.read().decode('utf-8'))
    except Exception as e: print(url,type(e).__name__,str(e))
