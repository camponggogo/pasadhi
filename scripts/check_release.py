"""Validate checksums, archive startup, and website download/image references."""
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
from urllib.parse import urlsplit
import zipfile

ROOT = Path(__file__).resolve().parents[1]
downloads = ROOT / 'web/download'
entries = json.loads((downloads / 'release.json').read_text())
for entry in entries:
    archive = downloads / entry['file']
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == entry['sha256']
    target = ROOT / 'paper/_build/check' / entry['platform']
    target.mkdir(parents=True, exist_ok=True)
    if archive.suffix == '.zip':
        with zipfile.ZipFile(archive) as handle:
            assert handle.testzip() is None
            handle.extractall(target)
    else:
        with tarfile.open(archive) as handle:
            handle.extractall(target, filter='data')
    package = target / 'PASADHI'
    executable = [str(package / 'pasadhi.exe')] if entry['kind'] == 'native' else [sys.executable, '-m', 'pasadhi.app.service']
    environment = dict(os.environ, LOCALAPPDATA=str(target / 'config'), PYTHONIOENCODING='utf-8')
    result = subprocess.run(executable + ['--once', '--port', '0'], cwd=package,
                            env=environment, capture_output=True, timeout=60)
    assert result.returncode == 0, result.stderr.decode(errors='replace')
    state = json.loads(result.stdout.decode('utf-8'))
    assert {'hardware', 'share', 'role', 'limits'} <= state.keys()
    print(entry['platform'], 'archive checksum + startup PASS')

class Links(HTMLParser):
    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        for key in ('src', 'href'):
            ref = values.get(key, '')
            if 'download/' in ref or 'brand/' in ref:
                path = urlsplit(ref).path
                assert (self.folder / path).is_file(), path

site = ROOT.parent / 'landing-pasadhi'
for name in ('index.html', 'th/index.html', 'story.html', 'th/story.html'):
    parser = Links()
    parser.folder = (site / name).parent
    parser.feed((site / name).read_text(encoding='utf-8'))
    print(name, 'download/image references PASS')
