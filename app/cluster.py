"""Measured node telemetry and aggregation of explicitly configured PASADHI nodes."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
import json
import math
import os
from pathlib import Path
import shutil
import socket
import time
from urllib.parse import urlsplit
from urllib.request import build_opener, HTTPRedirectHandler, ProxyHandler

SCHEMA = 'pasadhi.resources.v1'

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def configured_workers(value=None):
    """Only operator-supplied base URLs; never accept a URL from an HTTP query."""
    result = []
    for raw in (os.environ.get('PASADHI_WORKERS', '') if value is None else value).split(','):
        raw = raw.strip().rstrip('/')
        if not raw:
            continue
        parsed = urlsplit(raw)
        if (parsed.scheme not in ('http', 'https') or not parsed.hostname or
                parsed.username or parsed.password or parsed.query or parsed.fragment or
                parsed.path not in ('', '/')):
            raise ValueError('PASADHI_WORKERS requires comma-separated http(s) base URLs without credentials or paths')
        if raw not in result:
            result.append(raw)
    if len(result) > 128:
        raise ValueError('PASADHI_WORKERS supports at most 128 configured nodes')
    return result


def node_resources(hardware, share, role, node_id):
    from . import budget
    capacity = {'cpu_cores': hardware.cores_logical, 'ram_gib': hardware.ram_gb,
                'disk_gib': hardware.disk_total_gb, 'gpu_vram_gib': hardware.gpu_vram_gb}
    usage = {'cpu_cores': None, 'ram_gib': None, 'disk_gib': None,
             'gpu_vram_gib': None, 'process_rss_gib': None,
             'network_sent_bytes': None, 'network_recv_bytes': None}
    source = 'unavailable'
    try:
        import psutil
        vm = psutil.virtual_memory()
        capacity['ram_gib'] = vm.total / 1024**3
        usage['cpu_cores'] = hardware.cores_logical * psutil.cpu_percent(interval=0.1) / 100
        usage['ram_gib'] = (vm.total - vm.available) / 1024**3
        usage['process_rss_gib'] = psutil.Process().memory_info().rss / 1024**3
        net = psutil.net_io_counters()
        usage['network_sent_bytes'], usage['network_recv_bytes'] = net.bytes_sent, net.bytes_recv
        source = 'psutil'
    except (ImportError, OSError, RuntimeError):
        pass
    disk = shutil.disk_usage(Path.home())
    capacity['disk_gib'] = disk.total / 1024**3
    usage['disk_gib'] = disk.used / 1024**3
    limits = budget.limits(budget.Share(**share), hardware.cores_logical,
                           capacity['ram_gib'], disk.free / 1024**3,
                           hardware.network_mbps, hardware.gpu_vram_gb)
    offered = {'cpu_cores': limits['cpu_cores'], 'ram_gib': limits['ram_gb'],
               'disk_gib': limits['disk_gb'], 'gpu_vram_gib': limits['vram_gb']}
    return {'schema': SCHEMA, 'node_id': node_id, 'hostname': hardware.hostname,
            'role': role, 'sampled_at': time.time(), 'source': source,
            'capacity': capacity, 'offered': offered, 'usage': usage}


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def validate_node(node):
    if (not isinstance(node, dict) or node.get('schema') != SCHEMA or
            not isinstance(node.get('node_id'), str) or not node['node_id']):
        raise ValueError('Node is missing resource telemetry; upgrade this worker')
    if not _number(node.get('sampled_at')) or abs(time.time() - node['sampled_at']) > 30:
        raise ValueError('Stale sample or node clock differs by more than 30 seconds')
    for group in ['capacity', 'offered', 'usage']:
        if not isinstance(node.get(group), dict):
            raise ValueError('Invalid telemetry')
        for value in node[group].values():
            if value is not None and not _number(value):
                raise ValueError('Invalid resource value')
    for key in ['cpu_cores', 'ram_gib', 'disk_gib', 'gpu_vram_gib']:
        if not _number(node['capacity'].get(key)) or not _number(node['offered'].get(key)):
            raise ValueError('Missing capacity or offered capacity')
    return node


def fetch_node(base):
    try:
        opener = build_opener(ProxyHandler({}), NoRedirect())
        with opener.open(base + '/api/node/resources', timeout=1.5) as response:
            body = response.read(65537)
        if len(body) > 65536:
            raise ValueError('Telemetry exceeds size limit')
        node = validate_node(json.loads(body))
        return {'url': base, 'status': 'online', 'node': node}
    except Exception:
        return {'url': base, 'status': 'offline',
                'error': 'No fresh telemetry: check worker version, address, port and clock'}


def aggregate(local, reports):
    nodes = [local]
    seen = {local['node_id']}
    for report in reports:
        if report['status'] != 'online':
            continue
        node = report['node']
        if node['node_id'] in seen:
            report['status'] = 'duplicate'
            continue
        seen.add(node['node_id']); nodes.append(node)
    totals = {}
    for group in ['capacity', 'offered', 'usage']:
        totals[group] = {}
        for key in local[group]:
            vals = [n[group].get(key) for n in nodes]
            known = [v for v in vals if _number(v)]
            totals[group][key] = {'value': sum(known) if known else None,
                                  'reported_nodes': len(known), 'total_nodes': len(nodes)}
    return {'schema': SCHEMA, 'sampled_at': time.time(), 'online_nodes': len(nodes),
            'configured_nodes': len(reports) + 1,
            'offline_nodes': sum(r['status'] == 'offline' for r in reports),
            'totals': totals, 'nodes': [{'url': 'local', 'status': 'online', 'node': local}] + reports,
            'scope': 'Host usage includes other applications. Offered resources are configured limits, not reservations. Network bytes are host counters since boot. GPU usage is unavailable.'}


def cluster_resources(local):
    workers = configured_workers()
    with ThreadPoolExecutor(max_workers=min(16, max(1, len(workers)))) as pool:
        reports = list(pool.map(fetch_node, workers))
    return aggregate(local, reports)
