"""Opt-in LAN mDNS announcement for a single coordinator (no router/DNS changes)."""
from __future__ import annotations
import ipaddress
import logging
import re
import socket
import threading

LOG = logging.getLogger(__name__)
TYPE = '_http._tcp.local.'


def validate_name(name):
    if not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', name):
        raise ValueError('mDNS name must be a single lowercase DNS label, e.g. pasadhi')
    return name


def lan_addresses(interface=None):
    import psutil
    stats = psutil.net_if_stats()
    result = []
    for name, entries in psutil.net_if_addrs().items():
        if interface and name != interface:
            continue
        if not interface and name.lower().startswith(('vethernet', 'veth', 'docker', 'br-', 'tun', 'tap')):
            continue
        if name not in stats or not stats[name].isup:
            continue
        for entry in entries:
            if entry.family != socket.AF_INET:
                continue
            address = ipaddress.ip_address(entry.address)
            if address.is_private and not address.is_loopback and not address.is_link_local:
                result.append(str(address))
    return tuple(sorted(set(result)))


class CoordinatorMDNS:
    def __init__(self, name, port, interface=None, address_source=None, backend=None):
        self.name = validate_name(name)
        if not 1 <= port <= 65535:
            raise ValueError('mDNS advertised port must be 1..65535')
        self.port, self.interface = port, interface
        self._addresses = address_source or (lambda: lan_addresses(interface))
        self._backend = backend
        self._current = None
        self._zc = self._info = None
        self._stop = threading.Event()
        self._thread = None
        self.last_error = None

    @property
    def url(self):
        return f'http://{self.name}.local' + ('' if self.port == 80 else f':{self.port}') + '/dashboard'

    def prepare(self):
        if self._backend is None:
            try:
                from zeroconf import IPVersion, ServiceInfo, Zeroconf
            except ImportError as error:
                raise RuntimeError('mDNS needs zeroconf: install requirements.txt first') from error
            self._backend = (Zeroconf, ServiceInfo, IPVersion.V4Only)

    def _withdraw(self):
        zc, info = self._zc, self._info
        self._zc = self._info = None
        if zc is not None:
            try:
                if info is not None:
                    zc.unregister_service(info)
            finally:
                zc.close()

    def refresh(self):
        addresses = tuple(sorted(set(self._addresses())))
        if addresses == self._current:
            return False
        # Recreate multicast sockets when interfaces/IPs change, rather than
        # retaining sockets joined to an interface that no longer has this IP.
        self._withdraw()
        self._current = None
        if not addresses:
            self._current = addresses
            LOG.warning('PASADHI mDNS waiting for a usable LAN IPv4 address')
            return True
        self.prepare()
        zc_cls, info_cls, version = self._backend
        zc = zc_cls(interfaces=list(addresses), ip_version=version)
        info = info_cls(TYPE, f'PASADHI {self.name} coordinator.{TYPE}',
                        parsed_addresses=list(addresses), port=self.port,
                        server=f'{self.name}.local.', host_ttl=60, other_ttl=60,
                        properties={'path': '/dashboard', 'role': 'coordinator'})
        try:
            # Do not silently rename a competing coordinator's service.
            zc.register_service(info, allow_name_change=False)
        except Exception:
            zc.close()
            raise
        self._zc, self._info, self._current = zc, info, addresses
        self.last_error = None
        print(f'PASADHI mDNS: {self.url} -> {", ".join(addresses)}', flush=True)
        return True

    def start(self):
        self.prepare()  # Missing optional dependency is actionable before serving.
        self._thread = threading.Thread(target=self._run, name='pasadhi-mdns', daemon=True)
        self._thread.start()

    def _run(self):
        while not self._stop.is_set():
            try:
                self.refresh()
            except Exception as error:
                message = f'{type(error).__name__}: {error}'
                if message != self.last_error:
                    LOG.warning('PASADHI mDNS announcement failed (%s); IP URLs remain usable', message)
                self.last_error = message
            self._stop.wait(5)

    def close(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join()  # Do not close sockets while refresh owns them.
        self._withdraw()
