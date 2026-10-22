"""PASADHI application service: one process that is client, worker and coordinator at once.

    python pasadhi/app/service.py --port 8765 [--role auto|worker|coordinator|client]

It serves a local settings UI on 127.0.0.1, runs a duty-cycled worker that respects the user's CPU budget,
and records earnings in the same config directory as the device identity.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pasadhi.app import budget, identity as ident, probe, roles  # noqa: E402
from pasadhi.app.ui import PAGE  # noqa: E402

CONFIG_DIR = ident.config_dir()
CONFIG_PATH = CONFIG_DIR / 'config.json'
EARNINGS_PATH = CONFIG_DIR / 'earnings.json'

STATE = {
    'started_at': time.time(),
    'credits_thb': 0.0,
    'work_seconds': 0.0,
    'idle_seconds': 0.0,
    'ticks': 0,
}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
    return {'role': 'auto', 'share': budget.Share().to_dict(), 'port': 8765, 'autostart': True}


def save_config(config: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding='utf-8')


def load_earnings() -> float:
    if EARNINGS_PATH.exists():
        try:
            return float(json.loads(EARNINGS_PATH.read_text(encoding='utf-8')).get('credits_thb', 0.0))
        except Exception:
            return 0.0
    return 0.0


def worker_loop(stop: threading.Event, hardware: probe.Hardware, share_ref: dict) -> None:
    """Duty-cycled work: run for `duty` of every 100 ms, sleep the rest, so the CPU share is real."""
    last_save = time.time()
    while not stop.is_set():
        share = budget.Share(**share_ref)
        limits = budget.limits(share, hardware.cores_logical, hardware.ram_gb, hardware.disk_free_gb,
                               hardware.network_mbps, hardware.gpu_vram_gb)
        duty = min(0.9, limits['cpu_cores'] / max(1, hardware.cores_logical))
        window = 0.1
        work = window * duty
        if work > 0:
            deadline = time.perf_counter() + work
            value = 0.0
            while time.perf_counter() < deadline:      # a small, honest matrix loop
                value += sum(i * i for i in range(200))
            STATE['work_seconds'] += work
            rate = budget.hourly_earnings(share, hardware.cores_logical, hardware.ram_gb,
                                          hardware.disk_free_gb, hardware.network_mbps,
                                          hardware.gpu_vram_gb)['hourly_thb']
            STATE['credits_thb'] += rate * work / 3600
        if window - work > 0:
            stop.wait(window - work)
            STATE['idle_seconds'] += window - work
        STATE['ticks'] += 1
        if time.time() - last_save > 10:
            EARNINGS_PATH.write_text(json.dumps({'credits_thb': STATE['credits_thb'],
                                                 'saved_at': time.time()}), encoding='utf-8')
            last_save = time.time()


class Handler(BaseHTTPRequestHandler):
    hardware: probe.Hardware
    decision: roles.Decision
    config: dict
    share_ref: dict

    def log_message(self, *args):
        pass

    def _send(self, code: int, body: bytes, content_type: str = 'application/json') -> None:
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def _state(self) -> dict:
        share = budget.Share(**self.share_ref)
        limits = budget.limits(share, self.hardware.cores_logical, self.hardware.ram_gb,
                               self.hardware.disk_free_gb, self.hardware.network_mbps,
                               self.hardware.gpu_vram_gb)
        earnings = budget.hourly_earnings(share, self.hardware.cores_logical, self.hardware.ram_gb,
                                          self.hardware.disk_free_gb, self.hardware.network_mbps,
                                          self.hardware.gpu_vram_gb)
        record = ident.load_or_create(CONFIG_DIR)
        uptime = time.time() - STATE['started_at']
        return {
            'hardware': self.hardware.to_dict(),
            'role': self.decision.role,
            'score': self.decision.score,
            'reasons': self.decision.reasons,
            'share': share.to_dict(),
            'limits': limits,
            'earnings': earnings,
            'session': {'uptime_s': round(uptime, 1), 'credits_thb': round(STATE['credits_thb'], 3),
                        'work_s': round(STATE['work_seconds'], 1), 'ticks': STATE['ticks']},
            'identity': {'device_id': record.device_id, 'token_masked': record.masked()},
            'autostart': self.config.get('autostart', True),
        }

    def do_GET(self):
        if self.path in ('/', '/index.html'):
            self._send(200, PAGE.encode('utf-8'), 'text/html; charset=utf-8')
        elif self.path == '/api/state':
            self._send(200, json.dumps(self._state(), ensure_ascii=False).encode('utf-8'))
        else:
            self._send(404, b'{"error":"not found"}')

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        payload = json.loads(self.rfile.read(length) or b'{}')
        if self.path == '/api/share':
            share = budget.Share(**{**self.share_ref, **payload}).clamp()
            self.share_ref.clear()
            self.share_ref.update(share.__dict__)
            self.config['share'] = self.share_ref
            save_config(self.config)
            self._send(200, json.dumps(self._state(), ensure_ascii=False).encode('utf-8'))
        elif self.path == '/api/rotate':
            ident.rotate(ident.load_or_create(CONFIG_DIR), CONFIG_DIR)
            self._send(200, json.dumps(self._state(), ensure_ascii=False).encode('utf-8'))
        elif self.path == '/api/autostart':
            self.config['autostart'] = bool(payload.get('enabled', True))
            save_config(self.config)
            self._send(200, json.dumps(self._state(), ensure_ascii=False).encode('utf-8'))
        else:
            self._send(404, b'{"error":"not found"}')


def serve(port: int, role: str) -> ThreadingHTTPServer:
    config = load_config()
    hardware = probe.probe()
    decision = roles.decide(hardware, role or config.get('role', 'auto'))
    share = config.get('share', budget.Share().to_dict())

    Handler.hardware = hardware
    Handler.decision = decision
    Handler.config = config
    Handler.share_ref = dict(share)

    stop = threading.Event()
    thread = threading.Thread(target=worker_loop, args=(stop, hardware, Handler.share_ref), daemon=True)
    thread.start()

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.pasadhi_stop = stop
    return server


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--role', default='auto')
    parser.add_argument('--once', action='store_true', help='print the state and exit (for tests)')
    args = parser.parse_args()

    server = serve(args.port, args.role)
    if args.once:
        state = Handler._state(Handler.__new__(Handler))
        print(json.dumps(state, indent=2, ensure_ascii=False))
        server.pasadhi_stop.set()
        return
    print(f'PASADHI app on http://127.0.0.1:{args.port}  role={Handler.decision.role} '
          f'score={Handler.decision.score}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.pasadhi_stop.set()


if __name__ == '__main__':
    main()
