from pathlib import Path
import os,sys,types,json,time,ipaddress,threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
r=Path.cwd();sys.path.insert(0,str(r/'test-deps'));p=types.ModuleType('pasadhi');p.__path__=[str(r)];sys.modules['pasadhi']=p
from pasadhi.app.discovery import PeerDiscovery
from pasadhi.app import cluster
from pasadhi.app.test_cluster import node
os.environ.pop('PASADHI_WORKERS',None)
identifier='loopback-peer-'+str(os.getpid())
class Resource(BaseHTTPRequestHandler):
 def do_GET(self):
  self.send_response(200);self.end_headers();self.wfile.write(json.dumps(node(identifier+'-b')).encode())
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),Resource);threading.Thread(target=server.serve_forever,daemon=True).start()
network=lambda:[ipaddress.ip_network('127.0.0.0/8')]
a=PeerDiscovery(identifier+'-a','coordinator',8766,True,address_source=lambda:['127.0.0.1'],networks=network)
b=PeerDiscovery(identifier+'-b','worker',server.server_port,True,address_source=lambda:['127.0.0.1'],networks=network)
try:
 a.refresh();b.refresh();deadline=time.monotonic()+12
 while not a.peers() and time.monotonic()<deadline:time.sleep(.1)
 assert any(x['node_id']==identifier+'-b' for x in a.peers()),a.peers()
 data=cluster.cluster_resources(node(identifier+'-a'),a)
 assert data['online_nodes']==2 and data['nodes'][1]['source']=='discovered',data
 b.close();deadline=time.monotonic()+8
 while a.peers() and time.monotonic()<deadline:time.sleep(.1)
 assert not a.peers(),a.peers()
 print('PASS real multicast: worker discovered automatically without configured IPs, HTTP resources aggregated, and goodbye removed worker. Test transport is loopback, not a physical LAN certification.')
finally:
 a.close();b.close();server.shutdown();server.server_close()
