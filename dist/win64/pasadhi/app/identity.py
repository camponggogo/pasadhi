"""Per-install identity: one application token per machine, rotatable, never shared between installs."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import stat
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path

ALPHABET = 'abcdefghjkmnpqrstuvwxyz23456789'   # no look-alike characters


def config_dir() -> Path:
    if sys.platform == 'win32':
        base = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
    elif sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Application Support'
    else:
        base = Path(os.environ.get('XDG_CONFIG_HOME', Path.home() / '.config'))
    return base / 'pasadhi'


def _harden(path: Path) -> None:
    try:
        if sys.platform == 'win32':
            import subprocess
            subprocess.run(['icacls', str(path), '/inheritance:r', '/grant:r', f'{os.environ.get("USERNAME")}:F'],
                           capture_output=True, timeout=10)
        else:
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except Exception:
        pass


def _pretty(token: str) -> str:
    return '-'.join(token[i:i + 4] for i in range(0, len(token), 4))


@dataclass
class Identity:
    device_id: str
    token: str
    created_at: float
    install_id: str

    def masked(self) -> str:
        pretty = _pretty(self.token)
        return pretty[:9] + '••••••' + pretty[-4:]

    def to_dict(self) -> dict:
        return asdict(self)


def load_or_create(directory: Path | None = None) -> Identity:
    directory = directory or config_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / 'identity.json'
    if path.exists():
        payload = json.loads(path.read_text(encoding='utf-8'))
        return Identity(**payload)

    raw = ''.join(secrets.choice(ALPHABET) for _ in range(32))
    device_id = 'psd_' + hashlib.sha256(raw.encode()).hexdigest()[:16]
    identity = Identity(device_id=device_id, token=raw, created_at=time.time(),
                        install_id=secrets.token_hex(8))
    path.write_text(json.dumps(identity.to_dict(), indent=2), encoding='utf-8')
    _harden(path)
    return identity


def rotate(identity: Identity, directory: Path | None = None) -> Identity:
    directory = directory or config_dir()
    path = directory / 'identity.json'
    raw = ''.join(secrets.choice(ALPHABET) for _ in range(32))
    rotated = Identity(device_id=identity.device_id, token=raw, created_at=time.time(),
                       install_id=secrets.token_hex(8))
    path.write_text(json.dumps(rotated.to_dict(), indent=2), encoding='utf-8')
    _harden(path)
    return rotated


def sign(identity: Identity, payload: bytes) -> str:
    """Device proofs are HMACs over the token; the server stores only the hash of the token."""
    return hmac.new(identity.token.encode(), payload, hashlib.sha256).hexdigest()


def token_hash(identity: Identity) -> str:
    return hashlib.sha256(identity.token.encode()).hexdigest()


if __name__ == '__main__':
    ident = load_or_create()
    print('device_id', ident.device_id)
    print('token    ', ident.masked())
    print('hash     ', token_hash(ident)[:32], '…')
