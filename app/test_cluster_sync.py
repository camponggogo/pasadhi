import copy
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pasadhi.app import cluster
from pasadhi.app.test_cluster import node


def test_snapshot_is_immutable_and_reused(monkeypatch):
    monkeypatch.setattr(cluster.time, 'time', lambda: 1501)
    monkeypatch.setenv('PASADHI_WORKERS', '')
    cache = cluster.SnapshotCache()
    first = cache.snapshot(node('a', used=2), None)
    second = cache.snapshot(node('a', used=7), None)
    assert first == second
    first['sync']['state'] = 'modified'
    assert cache.snapshot(node('a'), None)['sync']['state'] == 'synchronized'
    monkeypatch.setattr(cluster.time, 'time', lambda: 1516)
    assert cache.snapshot(node('a', used=7), None)['totals']['usage']['cpu_cores']['value'] == 7


def test_different_nodes_receive_identical_coordinator_values(monkeypatch):
    monkeypatch.setenv('PASADHI_WORKERS', '')
    leader = node('a');leader['role'] = 'coordinator'
    cache = cluster.SnapshotCache()
    snapshot = cache.snapshot(leader, None)
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            assert self.path == '/api/cluster/snapshot'
            self.send_response(200);self.end_headers();self.wfile.write(json.dumps(snapshot).encode())
        def log_message(self, *args):pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True);thread.start()
    class Discovery:
        def peers(self):return [{'node_id':'a','role':'coordinator','lan_enabled':True,'url':f'http://127.0.0.1:{server.server_port}'}]
    try:
        one = cluster.synchronized_resources(node('b', used=1), Discovery(), cluster.SnapshotCache())
        two = cluster.synchronized_resources(node('c', used=6), Discovery(), cluster.SnapshotCache())
        assert one == two
        assert one['totals'] == snapshot['totals']
        assert one['sync'] == snapshot['sync']
        assert one['nodes'][0]['url'].endswith(str(server.server_port))
    finally:server.shutdown();server.server_close();thread.join()


def test_unavailable_coordinator_is_explicitly_degraded(monkeypatch):
    monkeypatch.setenv('PASADHI_WORKERS', '')
    class Discovery:
        def peers(self):return [{'node_id':'a','role':'coordinator','lan_enabled':True,'url':'http://127.0.0.1:1'}]
        def status(self):return {'enabled':True}
    result = cluster.synchronized_resources(node('b'), Discovery(), cluster.SnapshotCache())
    assert result['sync']['state'] == 'degraded'
