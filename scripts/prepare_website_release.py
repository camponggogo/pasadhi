"""Copy validated release downloads into the landing site and update both languages."""
from pathlib import Path
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT.parent / 'landing-pasadhi'
release = json.loads((ROOT / 'web/download/release.json').read_text())
for path in (ROOT / 'web/download').rglob('*'):
    if path.is_file():
        destination = SITE / 'download' / path.relative_to(ROOT / 'web/download')
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)

for locale in ('en', 'th'):
    path = SITE / ('index.html' if locale == 'en' else 'th/index.html')
    text = path.read_text(encoding='utf-8')
    prefix = './' if locale == 'en' else '../'
    labels = {'windows': ('🪟', 'Windows', 'Standalone x64 EXE' if locale == 'en' else 'EXE x64 ไม่ต้องติดตั้ง Python'),
              'linux': ('🐧', 'Linux', 'Python 3.10+ · tar.gz'),
              'macos': ('🍎', 'macOS', 'Python 3.10+ · tar.gz'),
              'android-termux': ('🤖', 'Android / Termux', 'Python package · not APK' if locale == 'en' else 'แพ็กเกจ Python · ไม่ใช่ APK'),
              'source': ('📦', 'Source', 'Python source code' if locale == 'en' else 'ซอร์สโค้ด Python')}
    cards = []
    for entry in release:
        icon, name, detail = labels[entry['platform']]
        size = f"{entry['bytes'] / 1024 / 1024:.1f} MB" if entry['bytes'] > 1024 * 1024 else f"{entry['bytes'] / 1024:.0f} KB"
        cards.append(f'    <a href="{prefix}download/{entry["file"]}" download><span class="os">{icon}</span><b>{name}</b><span>v{entry["version"]} · {detail} · {size}</span></a>')
    note = ('Windows includes Python. Linux and macOS require Python 3.10+; see README.txt inside each archive. Android requires Termux and Python; no native APK is available. These builds are unsigned. '
            if locale == 'en' else 'Windows รวม Python ในตัวแล้ว · Linux/macOS ต้องมี Python 3.10+ และทำตาม README.txt · Android ใช้ผ่าน Termux พร้อม Python ยังไม่มี APK · ไฟล์ยังไม่ได้เซ็นชื่อดิจิทัล ')
    block = '<div class="dl">\n' + '\n'.join(cards) + '\n  </div>\n  <p class="note">' + note + f'<a href="{prefix}download/SHA256SUMS.txt">SHA-256 checksums</a></p>'
    start = text.index('<section class="wrap" id="download">')
    before, section = text[:start], text[start:]
    section, count = re.subn(r'<div class="dl">.*?</div>\s*<p class="note">.*?</p>', lambda _: block, section, count=1, flags=re.S)
    assert count == 1
    path.write_text(before + section, encoding='utf-8')

for filename, variable in (('deploy_pasadhi_assets.py', 'FILES'), ('deploy_pasadhi.py', 'PUBLIC_FILES')):
    path = ROOT.parent / 'deploy' / filename
    text = path.read_text(encoding='utf-8')
    files = [p.relative_to(SITE).as_posix() for p in (SITE / 'download').rglob('*') if p.is_file()]
    for file in files:
        if repr(file) not in text:
            text = text.replace(variable + ' = (', variable + ' = (' + repr(file) + ', ', 1)
    path.write_text(text, encoding='utf-8')
print('Prepared bilingual website with five platform downloads and checksums.')
