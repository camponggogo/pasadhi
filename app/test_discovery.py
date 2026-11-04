"""Discovery inventory, trust boundaries and automatic resource collection."""
import ipaddress
from types import SimpleNamespace
from pasadhi.app import discovery,cluster
from pasadhi.app.test_cluster import node

NET=[ipaddress.ip_network('192.168.1.0/24')]
def info(node_id='peer',addresses=('192.168.1.20',),lan=True):
    return SimpleNamespace(port=8766,properties={b'node_id':node_id.encode(),b'role':b'worker',b'schema':b'pasadhi.resources.v1',b'lan':b'1' if lan else b'0'},parsed_addresses=lambda:list(addresses))

def test_record_filters_self_public_loopback_and_other_subnets():
    assert discovery.peer_record(info('self'),NET,'self') is None
    for address in ['127.0.0.1','169.254.169.254','8.8.8.8','192.168.2.1','192.168.1.255']:
        assert discovery.peer_record(info(addresses=[address]),NET,'self') is None
    assert discovery.peer_record(info(),NET,'self')['url']=='http://192.168.1.20:8766'

def test_add_change_remove_lan_disabled_and_self():
    current=[info()]
    zc=SimpleNamespace(get_service_info=lambda *a,**kw:current[0])
    peer=discovery.PeerDiscovery('self','worker',8766,False,networks=lambda:NET)
    peer.add_service(zc,discovery.TYPE,'peer');assert len(peer.peers())==1
    current[0]=info(addresses=['192.168.1.30'],lan=False);peer.update_service(zc,discovery.TYPE,'peer')
    assert peer.peers()[0]['url']=='http://192.168.1.30:8766'
    assert peer.peers()[0]['lan_enabled'] is False
    peer.remove_service(zc,discovery.TYPE,'peer');assert not peer.peers()
    current[0]=info('self');peer.add_service(zc,discovery.TYPE,'self');assert not peer.peers()

def test_automatic_collection_without_manual_worker_addresses(monkeypatch):
    monkeypatch.delenv('PASADHI_WORKERS',raising=False)
    records=[discovery.peer_record(info(),NET,'self'),discovery.peer_record(info('disabled',addresses=['192.168.1.21'],lan=False),NET,'self')]
    manager=SimpleNamespace(peers=lambda:records,status=lambda:{'enabled':True,'ready':True,'lan_enabled':True})
    calls=[]
    def fetch(url):
        calls.append(url);return {'url':url,'status':'online','node':node('peer')}
    monkeypatch.setattr(cluster,'fetch_node',fetch)
    data=cluster.cluster_resources(node('self'),manager)
    assert data['online_nodes']==2 and data['discovered_nodes']==2
    assert len(calls)==1 and data['nodes'][-1]['status']=='lan-disabled'

def test_discovered_identity_mismatch_not_counted(monkeypatch):
    monkeypatch.delenv('PASADHI_WORKERS',raising=False)
    manager=SimpleNamespace(peers=lambda:[discovery.peer_record(info(),NET,'self')],status=lambda:{})
    monkeypatch.setattr(cluster,'fetch_node',lambda u:{'url':u,'status':'online','node':node('wrong-id')})
    data=cluster.cluster_resources(node('self'),manager)
    assert data['online_nodes']==1 and data['offline_nodes']==1
