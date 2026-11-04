"""Regression coverage for first-run worker persistence."""
import itertools
import json
import sys
import threading
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from pasadhi.app import service


def test_save_earnings_creates_missing_parent(tmp_path, monkeypatch):
    target = tmp_path / '.config' / 'pasadhi' / 'earnings.json'
    monkeypatch.setattr(service, 'EARNINGS_PATH', target)
    service.save_earnings()
    assert json.loads(target.read_text())['credits_thb'] == service.STATE['credits_thb']
    target.unlink()
    target.parent.rmdir()
    service.save_earnings()
    assert target.is_file()


def test_worker_retries_after_persistence_error(tmp_path, monkeypatch):
    target = tmp_path / '.config' / 'pasadhi' / 'earnings.json'
    monkeypatch.setattr(service, 'EARNINGS_PATH', target)
    ticks = itertools.count(0, 11)
    monkeypatch.setattr(service.time, 'time', lambda: next(ticks))
    monkeypatch.setattr(service, '_host_cpu_pct', lambda: None, raising=False)
    if hasattr(service, 'aimod'):
        monkeypatch.setattr(service.aimod, 'poll', lambda: None)
    stop = threading.Event()
    real_save = service.save_earnings
    attempts = []
    def flaky_save():
        attempts.append(1)
        if len(attempts) == 1:
            raise PermissionError('temporary storage failure')
        real_save()
        stop.set()
    monkeypatch.setattr(service, 'save_earnings', flaky_save)
    hw = SimpleNamespace(cores_logical=1, ram_gb=1, disk_free_gb=1,
                         network_mbps=1, gpu_vram_gb=0)
    service.worker_loop(stop, hw, {'cpu_pct': 0})
    assert len(attempts) == 2
    assert target.is_file()


def test_macos_config_path_and_first_save(tmp_path, monkeypatch):
    monkeypatch.setattr(service.ident.sys, 'platform', 'darwin')
    monkeypatch.setattr(service.ident.Path, 'home', lambda: tmp_path)
    directory = service.ident.config_dir()
    assert directory == tmp_path / 'Library' / 'Application Support' / 'pasadhi'
    monkeypatch.setattr(service, 'EARNINGS_PATH', directory / 'earnings.json')
    service.save_earnings()
    assert (directory / 'earnings.json').is_file()
