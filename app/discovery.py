"""LAN DNS-SD peer discovery. Announcements are inventory, not authentication."""
from __future__ import annotations
import hashlib
import ipaddress
import threading
from .mdns import CoordinatorMDNS, lan_addresses

TYPE = '_pasadhi._tcp.local.'


def local_networks(interface=None):
    import psutil
    selected=set(lan_addresses(interface));networks=[]
    for entries in psutil.net_if_addrs().values():
        for entry in entries:
            if entry.address in selected and entry.netmask:
                networks.append(ipaddress.ip_network(f'{entry.address}/{entry.netmask}',strict=False))
    return networks


def peer_record(info, networks, local_id):
    if info is None or not 1 <= (info.port or 0) <= 65535:
        return None
    fields=info.properties
    try:
        node_id=fields[b'node_id'].decode('utf-8')
        if not node_id or len(node_id)>128 or node_id==local_id:
            return None
        if fields.get(b'schema')!=b'pasadhi.resources.v1':return None
        role=fields[b'role'].decode('ascii')
        if role not in ('coordinator','worker','client'):return None
        addresses=[]
        for raw in info.parsed_addresses():
            address=ipaddress.ip_address(raw)
            if address.version!=4 or not address.is_private or address.is_link_local:continue
            if any(address in net and address not in (net.network_address,net.broadcast_address) for net in networks):
                addresses.append(str(address))
        if not addresses:return None
        return {'node_id':node_id,'role':role,'url':f'http://{sorted(addresses)[0]}:{info.port}',
                'lan_enabled':fields.get(b'lan')==b'1'}
    except (KeyError,UnicodeError,ValueError,TypeError,AttributeError):
        return None


class PeerDiscovery(CoordinatorMDNS):
    service_type=TYPE
    def __init__(self,node_id,role,port,lan_enabled,interface=None,address_source=None,networks=None,backend=None,browser_factory=None):
        super().__init__('pasadhi-node-'+hashlib.sha256(node_id.encode()).hexdigest()[:16],port,
                         interface=interface,address_source=address_source,backend=backend)
        self.node_id,self.role,self.lan_enabled=node_id,role,lan_enabled
        self._networks=networks or (lambda:local_networks(interface))
        self._browser_factory=browser_factory
        self._browser=None;self._peers={};self._lock=threading.Lock()

    def service_name(self):return self.name+'.'+TYPE
    def properties(self):
        return {'node_id':self.node_id,'role':self.role,'schema':'pasadhi.resources.v1',
                'lan':'1' if self.lan_enabled else '0'}

    def registered(self,zc):
        factory=self._browser_factory
        if factory is None:
            from zeroconf import ServiceBrowser
            factory=ServiceBrowser
        self._browser=factory(zc,TYPE,listener=self)

    def _withdraw(self):
        if self._browser is not None:
            self._browser.cancel();self._browser=None
        with self._lock:self._peers.clear()
        super()._withdraw()

    def add_service(self,zc,type_,name):self.update_service(zc,type_,name)
    def update_service(self,zc,type_,name):
        # ServiceBrowser dispatches these on its dedicated listener thread.
        info=zc.get_service_info(type_,name,timeout=1000)
        record=peer_record(info,self._networks(),self.node_id)
        with self._lock:
            if record is None:self._peers.pop(name,None)
            elif name in self._peers or len(self._peers)<128:self._peers[name]=record
    def remove_service(self,zc,type_,name):
        with self._lock:self._peers.pop(name,None)
    def peers(self):
        with self._lock:return [dict(peer) for peer in self._peers.values()]
    def status(self):
        return {'enabled':True,'ready':self._zc is not None,
                'peers':len(self.peers()),'error':self.last_error,
                'lan_enabled':self.lan_enabled,
                'message':('LAN discovery active' if self._zc is not None else
                           'Waiting for LAN interfaces' if not self.last_error else self.last_error)}
