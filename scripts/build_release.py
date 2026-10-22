"""Build downloadable platform bundles; native binaries must be built on their target OS."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = '0.1.0'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--windows-exe', type=Path)
    args = parser.parse_args()
    output = ROOT / 'web/download'
    output.mkdir(parents=True, exist_ok=True)
    stage = ROOT / 'paper/_build/release'
    stage.mkdir(parents=True, exist_ok=True)
    entries = []
    for platform in ('windows', 'linux', 'macos', 'android-termux', 'source'):
        package = stage / platform / 'PASADHI'
        package.mkdir(parents=True, exist_ok=True)
        for directory in ('app', 'core'):
            shutil.copytree(ROOT / directory, package / 'pasadhi' / directory,
                            dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        shutil.copy2(ROOT / '__init__.py', package / 'pasadhi/__init__.py')
        for filename in ('LICENSE', 'NOTICE'):
            shutil.copy2(ROOT / filename, package / filename)
        (package / 'brand').mkdir(exist_ok=True)
        shutil.copy2(ROOT / 'brand/logo-light-transparent.png', package / 'brand/logo.png')
        (package / 'requirements.txt').write_text('psutil==7.2.2\n', encoding='utf-8')
        native = platform == 'windows' and args.windows_exe is not None
        if native:
            shutil.copy2(args.windows_exe, package / 'pasadhi.exe')
        windows = '@echo off\r\ncd /d "%~dp0"\r\n'
        windows += 'pasadhi.exe %*\r\npause\r\n' if native else 'python -m pasadhi.app.service %*\r\npause\r\n'
        (package / 'PASADHI.bat').write_bytes(windows.encode())
        unix = '#!/bin/sh\nset -eu\ncd "$(dirname "$0")"\n'
        unix += 'exec python -m pasadhi.app.service "$@"\n' if platform == 'android-termux' else 'exec python3 -m pasadhi.app.service "$@"\n'
        launcher = package / ('PASADHI.command' if platform == 'macos' else 'pasadhi.sh')
        launcher.write_text(unix, encoding='utf-8', newline='\n')
        install = ('pkg install python\npython -m pip install -r requirements.txt\nbash pasadhi.sh' if platform == 'android-termux'
                   else 'python3 -m pip install -r requirements.txt\nsh pasadhi.sh')
        if platform == 'macos':
            install = install.replace('sh pasadhi.sh', 'sh PASADHI.command')
        if platform == 'windows':
            install = 'Double-click PASADHI.bat. No Python installation needed.' if native else 'Install Python 3.10+, then run PASADHI.bat.'
        (package / 'README.txt').write_text(
            f'PASADHI {VERSION} - {platform}\n\n{install}\n\n'
            'Open http://127.0.0.1:8765 after starting. Ctrl+C stops the service.\n'
            + ('Standalone Windows x64 executable; unsigned.\n' if native else
               'Python source distribution; Python 3.10+ required. psutil enables full hardware probing.\n')
            + ('Android requires Termux; this archive is not an APK.\n' if platform == 'android-termux' else ''), encoding='utf-8')
        suffix = '.tar.gz' if platform in ('linux', 'macos') else '.zip'
        filename = f'PASADHI-{VERSION}-{platform}' + suffix
        archive = output / filename
        if suffix == '.zip':
            with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as target:
                for path in sorted(package.rglob('*')):
                    if path.is_file():
                        target.write(path, path.relative_to(package.parent))
        else:
            with tarfile.open(archive, 'w:gz') as target:
                for path in sorted(package.rglob('*')):
                    if path.is_file():
                        info = target.gettarinfo(str(path), str(path.relative_to(package.parent)).replace('\\', '/'))
                        info.mode = 0o755 if path == launcher else 0o644
                        with path.open('rb') as handle:
                            target.addfile(info, handle)
        entries.append({'file': filename, 'platform': platform, 'version': VERSION,
                        'kind': 'native' if native else 'python-source', 'bytes': archive.stat().st_size,
                        'sha256': hashlib.sha256(archive.read_bytes()).hexdigest()})
    (output / 'release.json').write_text(json.dumps(entries, indent=2) + '\n', encoding='utf-8')
    (output / 'SHA256SUMS.txt').write_text(''.join(f"{e['sha256']}  {e['file']}\n" for e in entries), encoding='utf-8')
    publish_aliases(output)
    print(json.dumps(entries, indent=2))


def publish_aliases(output):
    """Keep immutable version links and stable latest links with matching checksums."""
    entries = json.loads((output / 'release.json').read_text(encoding='utf-8'))
    version = entries[0]['version']
    latest = []
    for entry in entries:
        path = output / entry['file']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256']
        version_dir = output / f'v{version}'
        version_dir.mkdir(exist_ok=True)
        version_file = version_dir / path.name
        if version_file.exists() and version_file.read_bytes() != path.read_bytes():
            raise ValueError(f'Refusing to replace existing versioned release: {version_file}')
        shutil.copy2(path, version_file)
        latest_dir = output / 'latest'
        latest_dir.mkdir(exist_ok=True)
        alias = path.name.replace(f'-{version}-', '-')
        shutil.copy2(path, latest_dir / alias)
        latest.append(dict(entry, file=alias))
    shutil.copy2(output / 'release.json', version_dir / 'release.json')
    shutil.copy2(output / 'SHA256SUMS.txt', version_dir / 'SHA256SUMS.txt')
    (latest_dir / 'release.json').write_text(json.dumps(latest, indent=2) + '\n', encoding='utf-8')
    (latest_dir / 'SHA256SUMS.txt').write_text(''.join(f"{e['sha256']}  {e['file']}\n" for e in latest), encoding='utf-8')


if __name__ == '__main__':
    main()
