"""Verify download aliases, font provenance, and local stylesheet/font paths."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = ROOT / 'web/download'
for folder in (DOWNLOADS, DOWNLOADS / 'v0.1.0', DOWNLOADS / 'latest'):
    entries = json.loads((folder / 'release.json').read_text())
    for entry in entries:
        assert hashlib.sha256((folder / entry['file']).read_bytes()).hexdigest() == entry['sha256']
    print(folder.name, 'manifest/checksums PASS')

for label, ref in re.findall(r'\[([^\]]+)\]\(([^)]+)\)', (ROOT / 'README.md').read_text(encoding='utf-8')):
    if ref.startswith('web/download/') or ref.startswith('web/fonts/'):
        assert (ROOT / ref).is_file(), (label, ref)
print('README versioned/latest download links PASS')
fonts = ROOT / 'web/fonts'
for entry in json.loads((fonts / 'sources.json').read_text()):
    assert hashlib.sha256((fonts / entry['file']).read_bytes()).hexdigest() == entry['sha256'], entry['file']
for url in re.findall(r"url\('([^']+)'\)", (fonts / 'fonts.css').read_text()):
    assert (fonts / url).is_file(), url
assert 'font embedding exception' in (fonts / 'README.md').read_text()
assert 'special exception' in (fonts / 'THSarabunNew-LICENSE.txt').read_text()
print('Font provenance, licenses and CSS references PASS')

class Styles(HTMLParser):
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'link' and a.get('rel') == 'stylesheet' and not a.get('href', '').startswith('http'):
            assert (self.parent / a['href']).is_file(), (self.parent, a['href'])

for folder in (ROOT / 'web', ROOT.parent / 'landing-pasadhi'):
    for page in folder.rglob('*.html'):
        text = page.read_text(encoding='utf-8')
        assert 'fonts.googleapis.com' not in text and 'fonts.gstatic.com' not in text, page
        assert not any(name in text for name in ('Segoe UI', 'Times New Roman', 'Consolas', 'Helvetica', 'Georgia')), page
        parser = Styles()
        parser.parent = page.parent
        parser.feed(text)
print('Website font selections and local CSS paths PASS')

from pypdf import PdfReader
for filename in ('PASADHI-solution.pdf', 'PASADHI-full-paper.pdf'):
    reader = PdfReader(ROOT.parent / 'landing-pasadhi/download' / filename)
    names = set()
    for page in reader.pages:
        for font in page['/Resources'].get('/Font', {}).get_object().values():
            names.add(str(font.get_object().get('/BaseFont', 'Type3 outlines')))
    assert not any(any(name in font for name in ('Times', 'Cambria', 'Helvetica', 'Arial', 'Segoe', 'Consolas')) for font in names), names
    print(filename, len(reader.pages), 'pages; embedded-font audit PASS')
for kind in ('solution', 'full'):
    html = (ROOT / 'paper/_build' / (kind + '.html')).read_text(encoding='utf-8')
    assert '<table class="installation-steps">' in html
    assert 'width: 19%; white-space: nowrap;' in html
print('Both White Papers use the non-wrapping Step column PASS')
