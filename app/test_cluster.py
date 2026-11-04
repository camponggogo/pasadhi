"""Coordinator telemetry contracts and startup link regression tests."""
import copy
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import pytest
from pasadhi.app import cluster, startup_urls


def node(identifier='one', cpu=8, used=2):
    return {'schema':cluster.SCHEMA,'node_id':identifier,'hostname':identifier,'role':'worker',
            'sampled_at':time.time(),'source':'test',
            'capacity':{'cpu_cores':cpu,'ram_gib':16,'disk_gib':100,'gpu_vram_gib':0},
            'offered':{'cpu_cores':cpu/2,'ram_gib':4,'disk_gib':10,'gpu_vram_gib':0},
            'usage':{'cpu_cores':used,'ram_gib':3,'disk_gib':30,'gpu_vram_gib':None}}


def test_aggregate_partial_offline_and_duplicate():
    remote=node('two',4,1)
    reports=[{'url':'remote','status':'online','node':remote},
             {'url':'alias','status':'online','node':copy.deepcopy(remote)},
             {'url':'offline','status':'offline'}]
    data=cluster.aggregate(node(),reports)
    assert data['online_nodes']==2 and data['offline_nodes']==1
    assert data['totals']['capacity']['cpu_cores']['value']==12
    assert data['totals']['usage']['cpu_cores']['value']==3
    assert data['totals']['offered']['cpu_cores']['value']==6
    assert data['totals']['usage']['gpu_vram_gib']['value'] is None
    assert data['totals']['usage']['gpu_vram_gib']['reported_nodes']==0
    assert reports[1]['status']=='duplicate'


@pytest.mark.parametrize('url',['file:///etc/passwd','http://name/path','http://user:password@host','http://host?x=1','ftp://host'])
def test_only_configured_http_base_urls(url):
    with pytest.raises(ValueError):cluster.configured_workers(url)


def test_worker_dns_and_deduplication():
    assert cluster.configured_workers('http://worker-1.lan:8765,http://worker-1.lan:8765')==['http://worker-1.lan:8765']


def test_stale_or_invalid_samples_excluded():
    n=node();n['sampled_at']-=45
    with pytest.raises(ValueError):cluster.validate_node(n)
    n=node();n['usage']['cpu_cores']=float('nan')
    with pytest.raises(ValueError):cluster.validate_node(n)


def test_real_http_collection_and_closed_port():
    class Fake(BaseHTTPRequestHandler):
        def do_GET(self):
            assert self.path=='/api/node/resources'
            self.send_response(200);self.end_headers();self.wfile.write(json.dumps(node('remote')).encode())
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Fake)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    url=f'http://127.0.0.1:{server.server_port}'
    try:assert cluster.fetch_node(url)['status']=='online'
    finally:server.shutdown();server.server_close();thread.join()
    assert cluster.fetch_node(url)['status']=='offline'


def test_startup_links_use_real_port_and_explicit_dns(monkeypatch):
    monkeypatch.setenv('PASADHI_PUBLIC_URL','http://pasadhi-coordinator.lan:8765')
    links=startup_urls.startup_links('127.0.0.1',12345)
    assert 'http://127.0.0.1:12345/dashboard' in links
    assert 'http://pasadhi-coordinator.lan:8765/dashboard' in links
    assert 'http://0.0.0.0' not in links
    monkeypatch.setenv('PASADHI_PUBLIC_URL','http://user:secret@host')
    with pytest.raises(ValueError):startup_urls.public_url()
