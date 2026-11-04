"""mDNS lifecycle tests do not announce the production pasadhi.local name."""
from types import SimpleNamespace
import pytest
from pasadhi.app.mdns import CoordinatorMDNS, validate_name

class FakeZC:
    instances=[]
    fail=False
    def __init__(self,**kw):
        self.options=kw;self.registered=[];self.withdrawn=[];self.closed=False;self.instances.append(self)
    def register_service(self,info,**kw):
        assert kw=={'allow_name_change':False}
        if self.fail:raise RuntimeError('duplicate service')
        self.registered.append(info)
    def unregister_service(self,info):self.withdrawn.append(info)
    def close(self):self.closed=True

def info(kind,name,**kw):return SimpleNamespace(kind=kind,name=name,**kw)

@pytest.fixture(autouse=True)
def reset():
    FakeZC.instances=[];FakeZC.fail=False


def test_ip_change_recreates_interfaces_and_updates_same_name():
    ips=[['192.168.1.10']]
    a=CoordinatorMDNS('pasadhi',8766,address_source=lambda:ips[0],backend=(FakeZC,info,'v4'))
    assert a.refresh()
    first=FakeZC.instances[-1]
    assert first.options['interfaces']==['192.168.1.10']
    assert first.registered[0].server=='pasadhi.local.'
    assert a.url=='http://pasadhi.local:8766/dashboard'
    assert not a.refresh()
    ips[0]=['192.168.1.20'];assert a.refresh()
    assert first.closed and first.withdrawn
    second=FakeZC.instances[-1]
    assert second.registered[0].server=='pasadhi.local.'
    assert second.registered[0].parsed_addresses==['192.168.1.20']
    a.close();assert second.closed and second.withdrawn


def test_disconnect_withdraws_and_reconnects():
    ips=[['192.168.1.10']]
    a=CoordinatorMDNS('pasadhi',80,address_source=lambda:ips[0],backend=(FakeZC,info,'v4'))
    a.refresh();old=FakeZC.instances[-1];ips[0]=[];a.refresh();assert old.closed
    assert a.url=='http://pasadhi.local/dashboard'
    ips[0]=['192.168.1.11'];a.refresh();assert len(FakeZC.instances)==2
    a.close()


def test_conflict_closes_backend_without_silently_renaming():
    a=CoordinatorMDNS('pasadhi',8766,address_source=lambda:['192.168.1.10'],backend=(FakeZC,info,'v4'))
    FakeZC.fail=True
    with pytest.raises(RuntimeError):a.refresh()
    assert FakeZC.instances[-1].closed
    FakeZC.fail=False;assert a.refresh();a.close()


@pytest.mark.parametrize('name',['Pasadhi','pasadhi.local','-pasadhi','x'*64,'bad/name'])
def test_bad_dns_labels_rejected(name):
    with pytest.raises(ValueError):validate_name(name)


def test_real_dependency_service_info_compatibility():
    from zeroconf import ServiceInfo
    a=CoordinatorMDNS('pasadhi',8766,address_source=lambda:['192.168.1.10'],backend=(FakeZC,ServiceInfo,'v4'))
    a.refresh();actual=FakeZC.instances[-1].registered[0]
    assert actual.parsed_addresses()==['192.168.1.10']
    assert actual.properties[b'path']==b'/dashboard'
    assert actual.port==8766
    a.close()


@pytest.mark.parametrize('arguments', [
    ['--mdns', '--host', '0.0.0.0'],
    ['--mdns', '--role', 'coordinator', '--host', '127.0.0.1'],
])
def test_mdns_requires_explicit_coordinator_and_lan_binding(monkeypatch, arguments):
    import sys
    from pasadhi.app import service
    monkeypatch.setattr(service.startup_urls, 'load_network_env', lambda: None)
    monkeypatch.setattr(sys, 'argv', ['pasadhi', *arguments])
    def unexpected(*args):
        pytest.fail('Invalid mDNS configuration must not start the service')
    monkeypatch.setattr(service, 'serve', unexpected)
    with pytest.raises(SystemExit) as result:
        service.main()
    assert result.value.code == 2
