"""Startup links and explicit network settings for desktop and source builds."""
from pathlib import Path
import os
import socket
from urllib.parse import urlsplit

PAGES = [('This machine', '/'), ('Coordinator dashboard', '/dashboard'),
         ('Node resource API', '/api/node/resources'), ('Cluster resource API', '/api/cluster/resources'),
         ('Settings state API', '/api/state')]


def load_network_env():
    for path in [Path.cwd()/'.env', Path(__file__).resolve().parents[1]/'.env']:
        if not path.is_file():
            continue
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            if '=' not in line or line.lstrip().startswith('#'):
                continue
            key, value = line.split('=', 1)
            if key.strip() in ('PASADHI_HOST', 'PASADHI_PORT', 'PASADHI_WORKERS', 'PASADHI_PUBLIC_URL'):
                os.environ.setdefault(key.strip(), value.strip().strip('\"\''))
        break


def public_url():
    raw = os.environ.get('PASADHI_PUBLIC_URL', '').strip().rstrip('/')
    if not raw:
        return None
    parsed = urlsplit(raw)
    if (parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or
            parsed.password or parsed.path not in ('', '/') or parsed.query or parsed.fragment):
        raise ValueError('PASADHI_PUBLIC_URL must be an http(s) base URL without credentials or path')
    return raw


def startup_links(host, port, extra_pages=()):
    bases = [('Local', 'http://127.0.0.1:'+str(port))] if host in ('127.0.0.1', '0.0.0.0', 'localhost') else [('Bound address', f'http://{host}:{port}')]
    if host == '0.0.0.0':
        addresses = set()
        try:
            import psutil
            for entries in psutil.net_if_addrs().values():
                for entry in entries:
                    if entry.family == socket.AF_INET and not entry.address.startswith(('127.', '169.254.')):
                        addresses.add(entry.address)
        except (ImportError, OSError):
            pass
        bases.extend(('LAN', f'http://{address}:{port}') for address in sorted(addresses))
    stable = public_url()
    if stable:
        bases.insert(0, ('Configured DNS / reverse proxy (DNS must resolve)', stable))
    lines = []
    for scope, base in bases:
        lines.append(scope+':')
        lines.extend(f'  {label}: {base}{path}' for label, path in [*PAGES, *extra_pages])
    return '\n'.join(lines)
