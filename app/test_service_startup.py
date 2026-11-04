"""Port conflicts are actionable errors and never start a worker."""
import errno
import socket
import sys
from types import SimpleNamespace
import pytest
from pasadhi.app import service


def test_busy_port_does_not_start_worker(monkeypatch):
    monkeypatch.setattr(service, 'load_config', lambda: {})
    monkeypatch.setattr(service.probe, 'probe', lambda: SimpleNamespace())
    monkeypatch.setattr(service.roles, 'decide', lambda *a: SimpleNamespace(role='worker',score=1))
    def unexpected_thread(*args, **kwargs):
        pytest.fail('Started worker before successfully binding listener')
    monkeypatch.setattr(service.threading, 'Thread', unexpected_thread)
    with socket.socket() as busy:
        busy.bind(('127.0.0.1',0));busy.listen()
        with pytest.raises(OSError):service.serve(busy.getsockname()[1], 'worker')


def test_main_busy_port_message_without_traceback(monkeypatch):
    monkeypatch.setattr(sys,'argv',['pasadhi','--port','8765'])
    monkeypatch.setattr(service.startup_urls,'load_network_env',lambda: None)
    monkeypatch.delenv('PASADHI_WORKERS',raising=False)
    monkeypatch.delenv('PASADHI_PUBLIC_URL',raising=False)
    def busy(*args):raise OSError(errno.EADDRINUSE,'busy')
    monkeypatch.setattr(service,'serve',busy)
    with pytest.raises(SystemExit) as result:service.main()
    assert 'already in use' in str(result.value)
    assert '--port 8766' in str(result.value)
