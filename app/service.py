"""PASADHI application service: one process that is client, worker and coordinator at once.

    python pasadhi/app/service.py --port 8765 [--role auto|worker|coordinator|client]

It serves a local settings UI on 127.0.0.1, runs a duty-cycled worker that respects the user's CPU budget,
and records earnings in the same config directory as the device identity.
"""
from __future__ import annotations

import argparse
import errno
import json
import logging
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
from pasadhi.app import cluster, startup_urls, mdns, discovery
from pasadhi.app.coordinator_page import PAGE as COORDINATOR_PAGE

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


def save_earnings() -> None:
    """Persist worker credits even before settings or identity have been saved."""
    EARNINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    EARNINGS_PATH.write_text(json.dumps({'credits_thb': STATE['credits_thb'],
                                         'saved_at': time.time()}), encoding='utf-8')


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
            try:
                save_earnings()
            except OSError:
                logging.getLogger(__name__).warning('Could not save worker earnings; will retry', exc_info=True)
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
        elif self.path in ('/dashboard', '/dashboard/'):
            self._send(200, COORDINATOR_PAGE.encode('utf-8'), 'text/html; charset=utf-8')
        elif self.path in ('/api/node/resources', '/api/cluster/resources', '/api/cluster/snapshot'):
            try:
                local = cluster.node_resources(self.hardware, self.share_ref, self.decision.role,
                                               ident.load_or_create(CONFIG_DIR).device_id)
                discovery = getattr(self.server, 'pasadhi_discovery', None)
                if self.path == '/api/cluster/resources':
                    payload = cluster.synchronized_resources(local, discovery, self.server.pasadhi_snapshot)
                elif self.path == '/api/cluster/snapshot':
                    payload = self.server.pasadhi_snapshot.snapshot(local, discovery)
                else:
                    payload = local
                self._send(200, json.dumps(payload, ensure_ascii=False).encode('utf-8'))
            except ValueError as error:
                self._send(400, json.dumps({'error': str(error)}).encode('utf-8'))
            except Exception:
                self._send(503, b'{"error":"Resource telemetry unavailable"}')
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


def serve(port: int, role: str, host: str = '127.0.0.1') -> ThreadingHTTPServer:
    config = load_config()
    hardware = probe.probe()
    decision = roles.decide(hardware, role or config.get('role', 'auto'))
    share = config.get('share', budget.Share().to_dict())

    Handler.hardware = hardware
    Handler.decision = decision
    Handler.config = config
    Handler.share_ref = dict(share)

    # Bind before starting background work: a busy port must not launch a worker.
    server = ThreadingHTTPServer((host, port), Handler)
    stop = threading.Event()
    thread = threading.Thread(target=worker_loop, args=(stop, hardware, Handler.share_ref), daemon=True)
    thread.start()
    server.pasadhi_snapshot = cluster.SnapshotCache()
    server.pasadhi_stop = stop
    return server


def main():
    parser = argparse.ArgumentParser()
    startup_urls.load_network_env()
    parser.add_argument('--port', type=int, default=int(os.environ.get('PASADHI_PORT', '8765')))
    parser.add_argument('--host', default=os.environ.get('PASADHI_HOST', '127.0.0.1'))
    parser.add_argument('--role', default='auto')
    parser.add_argument('--lan', action='store_true', help='Listen on LAN and share telemetry with discovered peers')
    parser.add_argument('--no-discovery', action='store_true', default=os.environ.get('PASADHI_DISCOVERY') == '0')
    parser.add_argument('--mdns', action='store_true', default=os.environ.get('PASADHI_MDNS') == '1')
    parser.add_argument('--mdns-name', default=os.environ.get('PASADHI_MDNS_NAME', 'pasadhi'))
    parser.add_argument('--mdns-port', type=int, default=os.environ.get('PASADHI_MDNS_PORT') or None, help='Advertised proxy port; defaults to actual app port')
    parser.add_argument('--once', action='store_true', help='print the state and exit (for tests)')
    args = parser.parse_args()
    if args.lan:
        args.host = '0.0.0.0'

    if args.mdns and (args.role != 'coordinator' or args.host != '0.0.0.0'):
        parser.error('--mdns requires --role coordinator --host 0.0.0.0')
    if args.mdns:
        mdns.validate_name(args.mdns_name)
        if args.mdns_port is not None and not 1 <= args.mdns_port <= 65535:
            parser.error('--mdns-port must be 1..65535')
    cluster.configured_workers()
    startup_urls.public_url()
    try:
        server = serve(args.port, args.role, args.host)
    except OSError as error:
        if error.errno == errno.EADDRINUSE or getattr(error, 'winerror', None) == 10048:
            raise SystemExit(
                f'PASADHI cannot start: port {args.port} on {args.host} is already in use. '
                'An older PASADHI instance may still be running. Stop it with Ctrl+C, '
                f'or restart this launcher with --port {args.port + 1} '
                '(choose another free port if needed).') from None
        raise
    if args.once:
        state = Handler._state(Handler.__new__(Handler))
        print(json.dumps(state, indent=2, ensure_ascii=False))
        server.pasadhi_stop.set()
        server.server_close()
        return
    port = server.server_address[1]
    announcer = None
    peer_discovery = None
    if not args.no_discovery:
        peer_discovery = discovery.PeerDiscovery(
            ident.load_or_create(CONFIG_DIR).device_id, Handler.decision.role, port,
            not server.server_address[0].startswith('127.'), os.environ.get('PASADHI_MDNS_INTERFACE') or None)
        server.pasadhi_discovery = peer_discovery
        try:
            peer_discovery.start()
        except RuntimeError as error:
            peer_discovery.last_error = str(error)
            print(f'PASADHI discovery unavailable: {error}', flush=True)
    if args.mdns:
        announcer = mdns.CoordinatorMDNS(args.mdns_name, args.mdns_port or port, os.environ.get('PASADHI_MDNS_INTERFACE') or None)
        try:
            announcer.start()
        except RuntimeError as error:
            if peer_discovery is not None:
                peer_discovery.close()
            server.pasadhi_stop.set()
            server.server_close()
            raise SystemExit(str(error)) from None
    print(f'PASADHI role={Handler.decision.role} score={Handler.decision.score}', flush=True)
    print(startup_urls.startup_links(args.host, port), flush=True)
    print('LAN discovery: ' + ('disabled' if args.no_discovery else 'enabled') + '. Main launchers enable LAN access by default; manual PASADHI_WORKERS remains supported.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            if announcer is not None:
                announcer.close()
            if peer_discovery is not None:
                peer_discovery.close()
        finally:
            server.pasadhi_stop.set()
            server.server_close()


if __name__ == '__main__':
    main()
